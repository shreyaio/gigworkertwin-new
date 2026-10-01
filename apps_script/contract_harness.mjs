/**
 * Runs the Edge Function's row builder under Node and prints the rows as JSON.
 *
 * This is what makes `docs/04` §8's "one contract, two implementations" an executable claim rather
 * than a comment. `tests/test_m9_intake.py` runs this harness over
 * `apps_script/sample_payload.json` and asserts the output is identical to
 * `src/twinlab/ingest/survey_intake.build_rows` — so the TypeScript and the Python cannot drift.
 *
 * It imports `rows.mjs` unmodified, the same file the Edge Function imports, and reads the same two
 * generated assets. Nothing here reimplements anything; if it did, the test would be testing the
 * harness.
 *
 * Usage:
 *   node apps_script/contract_harness.mjs <payload.json> [rawObjectPath]
 *
 * Deno is not installed in this environment, so the Edge Function's HTTP/HMAC/Storage layer in
 * `index.ts` is NOT exercised by this harness — only the row building, which is the half the contract
 * test is about. See `docs/DECISIONS.md` → M9.
 */

import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildRows, rawObjectPath } from '../supabase/functions/survey_intake/rows.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const functionDir = join(here, '..', 'supabase', 'functions', 'survey_intake');

const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'));

const [payloadPath, overridePath] = process.argv.slice(2);
if (!payloadPath) {
  console.error('usage: node apps_script/contract_harness.mjs <payload.json> [rawObjectPath]');
  process.exit(2);
}

const payload = readJson(resolve(payloadPath));
const formMap = readJson(join(functionDir, 'form_map.json'));
const spec = readJson(join(functionDir, 'register_spec.json'));

const rows = buildRows(payload, {
  rawObjectPath: overridePath ?? rawObjectPath(payload.response_id),
  formMap,
  spec,
});

process.stdout.write(JSON.stringify(rows, null, 2));
