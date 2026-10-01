/**
 * Supabase Edge Function: survey intake. `docs/04` §8, `ARCHITECTURE.md` §6.2.
 *
 * Intake lives HERE and not in the Space. A Gradio Space sleeping after 48 hours idle would silently
 * drop driver submissions; an Edge Function is always warm. This is portability rule 2 in
 * `CLAUDE.md`, and it is binding.
 *
 * The four steps, in this order, and the order IS the invariant:
 *
 *   1. Verify the HMAC over the RAW body. Bad signature -> 401.
 *   2. Write the raw payload to Storage. A failure here aborts BEFORE any table write (I16).
 *   3. Map "<section>|<title>" -> item_id. An unmapped question is a 422, never a dropped answer.
 *   4. Insert survey_submissions + survey_answers.
 *
 * Step 2 precedes step 4 so a failed insert leaves a replayable object for
 * `src/twinlab/ingest/replay_raw.py`. Reverse them and a submission that failed to store is gone.
 *
 * Row building lives in `rows.mjs`, which is shared verbatim with the contract harness, so this file
 * holds only HTTP, HMAC and I/O. Persona building is deliberately NOT here: it is cheap Python, but
 * doing it in an Edge Function would duplicate the template library outside the repo.
 *
 * Deploy:
 *   supabase functions deploy survey_intake --no-verify-jwt
 *   supabase secrets set INTAKE_HMAC_SECRET=... SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
 * then point `apps_script/intake.gs`'s ENDPOINT at the function URL. `--no-verify-jwt` is required:
 * the caller is Apps Script holding an HMAC secret, not a Supabase user with a JWT.
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { buildRows, rawObjectPath, UnmappedQuestion } from './rows.mjs';
import formMap from './form_map.json' with { type: 'json' };
import spec from './register_spec.json' with { type: 'json' };

const RAW_BUCKET = 'raw-surveys';

function hex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/** Hex HMAC-SHA256 over the exact UTF-8 bytes, matching `hmac.new(...).hexdigest()`. */
async function sign(body: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return hex(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body)));
}

/** Constant-time compare. A timing-variable `===` leaks the digest one byte at a time. */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

Deno.serve(async (request: Request): Promise<Response> => {
  if (request.method !== 'POST') return json(405, { error: 'POST only' });

  const secret = Deno.env.get('INTAKE_HMAC_SECRET') ?? '';
  if (!secret) {
    // Refuse rather than accept unsigned submissions.
    return json(500, { error: 'INTAKE_HMAC_SECRET is not configured' });
  }

  // The raw text, never a re-serialised object: a round trip through JSON.parse/stringify can
  // reorder keys and change whitespace, and the signature would then never match.
  const body = await request.text();
  const signature = (request.headers.get('X-Signature') ?? '').trim().toLowerCase();
  if (!signature || !timingSafeEqual(await sign(body, secret), signature)) {
    return json(401, { error: 'bad signature' });
  }

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(body);
  } catch {
    return json(400, { error: 'body is not valid JSON' });
  }
  if (!payload.response_id || !payload.submitted_at) {
    return json(400, { error: 'payload needs response_id and submitted_at' });
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL') ?? '',
    Deno.env.get('SUPABASE_SERVICE_KEY') ?? '',
  );

  // Step 2 — BEFORE any table write (I16).
  const path = rawObjectPath(payload.response_id as string);
  const stored = await supabase.storage
    .from(RAW_BUCKET)
    .upload(path, new Blob([body], { type: 'application/json' }), { upsert: true });
  if (stored.error) {
    return json(500, { error: `could not store the raw object: ${stored.error.message}` });
  }

  // Steps 3 and 4.
  let rows;
  try {
    rows = buildRows(payload, { rawObjectPath: path, formMap, spec });
  } catch (error) {
    if (error instanceof UnmappedQuestion) return json(422, { error: error.message });
    throw error;
  }

  const submission = await supabase
    .from('survey_submissions')
    .upsert(rows.submission, { onConflict: 'submission_id' });
  if (submission.error) {
    // The raw object survives, so `replay_raw.py` can re-drive this submission.
    return json(500, {
      error: `insert failed: ${submission.error.message}`,
      replayable: path,
    });
  }
  if (rows.answers.length > 0) {
    const answers = await supabase
      .from('survey_answers')
      .upsert(rows.answers, { onConflict: 'submission_id,item_id' });
    if (answers.error) {
      return json(500, { error: `answers insert failed: ${answers.error.message}`, replayable: path });
    }
  }

  return json(200, {
    status: 'ok',
    submission_id: rows.submission.submission_id,
    consent_twin: rows.submission.consent_twin,
  });
});
