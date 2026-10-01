/**
 * Payload -> survey_submissions + survey_answers. The Edge Function half of ONE contract.
 *
 * `docs/04` §8: "One contract, two implementations." This module is the TypeScript/JavaScript twin of
 * `src/twinlab/ingest/survey_intake.py`'s `build_rows`, and a contract test asserts both produce
 * identical rows from `apps_script/sample_payload.json`. If you change one, change the other, or the
 * test fails — which is the point.
 *
 * Deliberately PURE and dependency-free ESM: no Deno globals, no npm imports, no YAML parsing. The
 * form map and the frozen item register arrive as plain data, so this same file runs under Deno in
 * the Edge Function and under Node in the contract harness. A second parser in here would be a second
 * thing to drift.
 */

/** Consent statements 1-6 are "consented". Statement 7 is `consent:twin` and gates the twin. */
export const CONSENT_STATEMENTS = [1, 2, 3, 4, 5, 6].map((n) => `statement_${n}`);

export const AFFIRMATIVE = new Set([
  'yes',
  'i agree',
  'true',
  'agree',
  'yes, i agree to take part',
]);

export class UnmappedQuestion extends Error {
  constructor(message) {
    super(message);
    this.name = 'UnmappedQuestion';
    this.status = 422;
  }
}

/**
 * Whether a Yes/No or checkbox answer means yes.
 *
 * A Google Forms checkbox answers as a LIST, so consent statement 6 arrives as `["I agree"]`. The
 * Python side had exactly this bug once: stringifying the array compared "['i agree']" against the
 * allow-list, so every consent read as false and every submission became `no_consent`.
 */
export function affirmative(value) {
  if (Array.isArray(value)) return value.some(affirmative);
  return AFFIRMATIVE.has(String(value ?? '').trim().toLowerCase());
}

/** A Likert answer as an integer, or null. NEVER coerced — a non-numeric value becomes text. */
export function asInt(value) {
  if (typeof value === 'boolean') return null;
  if (typeof value === 'number') return Number.isInteger(value) ? value : null;
  if (Array.isArray(value)) return value.length === 1 ? asInt(value[0]) : null;
  const match = /^\s*(-?\d+)/.exec(String(value ?? ''));
  return match ? Number.parseInt(match[1], 10) : null;
}

function textOrNone(value) {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text === '' ? null : text;
}

/** Group answers by target prefix. Throws UnmappedQuestion — nothing is ever dropped. */
export function mapAnswers(payload, formMap) {
  const grouped = {};
  const unmapped = [];
  for (const answer of payload.answers ?? []) {
    const key = `${answer.section ?? ''}|${answer.title ?? ''}`;
    const target = formMap.map[key];
    if (target === undefined) {
      unmapped.push(key);
      continue;
    }
    const idx = target.indexOf(':');
    const prefix = idx === -1 ? 'item' : target.slice(0, idx);
    const name = idx === -1 ? target : target.slice(idx + 1);
    (grouped[prefix] ??= []).push([name, answer.value]);
  }
  if (unmapped.length > 0) {
    throw new UnmappedQuestion(
      `${unmapped.length} Form question(s) are not in form_map.yaml (version ${formMap.version}): ` +
        `${JSON.stringify(unmapped.slice(0, 5))}. Nothing is dropped — add them to the map.`,
    );
  }
  return grouped;
}

function toObject(pairs) {
  const out = {};
  for (const [k, v] of pairs ?? []) out[k] = v;
  return out;
}

/**
 * The submission row and its answer rows. Pure: no clock, no randomness, no I/O.
 *
 * `spec` is the frozen register as data: { itemIds, scalePoints, batteryItemIds, attention,
 * whyProbeAnchor }.
 *
 * `eligible` is COMPUTED AND RECORDED BUT NEVER USED TO EXCLUDE, and `outcome` is never
 * 'screened_out' — `docs/GOOGLE_FORM.md` is explicit that making eligibility exclude a response is a
 * research decision the researcher has not made.
 */
export function buildRows(payload, options) {
  const {
    rawObjectPath,
    dataType = 'REAL',
    batchId = null,
    arm = null,
    armSource = null,
    formMap,
    spec,
  } = options;

  const grouped = mapAnswers(payload, formMap);
  const consents = toObject(grouped.consent);
  const fields = toObject(grouped.field);
  const meta = toObject(grouped.meta);
  const screens = toObject(grouped.screen);
  const checks = toObject(grouped.check);
  const whys = toObject(grouped.why);
  const items = grouped.item ?? [];

  const consented = CONSENT_STATEMENTS.every((s) => affirmative(consents[s]));
  const consentTwin = affirmative(consents.twin);

  const eligible =
    ['age_18_plus', 'tenure_3_months', 'active_30_days', 'reads_survey_language', 'in_india'].every(
      (k) => affirmative(screens[k]),
    ) && !['uber_employee', 'earlier_stage', 'deactivated'].some((k) => affirmative(screens[k]));

  const answersByItem = {};
  for (const [itemId, value] of items) {
    if (!spec.itemIds.includes(itemId)) {
      throw new UnmappedQuestion(
        `form_map.yaml points at "${itemId}", which is not in the frozen item register`,
      );
    }
    const number = asInt(value);
    answersByItem[itemId] = {
      submission_id: payload.response_id,
      item_id: itemId,
      value_num: number,
      value_text: number === null ? textOrNone(value) : null,
      why_text: null,
      language: meta.language ?? null,
      legacy_scale: false,
    };
  }

  for (const [probeId, text] of Object.entries(whys)) {
    const anchor = spec.whyProbeAnchor[probeId];
    if (anchor === undefined) {
      throw new UnmappedQuestion(
        `why-probe "${probeId}" has no anchor item; it would be lost`,
      );
    }
    if (answersByItem[anchor]) answersByItem[anchor].why_text = textOrNone(text);
  }

  const attentionPassed = Object.entries(spec.attention).every(
    ([itemId, expected]) => (answersByItem[itemId]?.value_num ?? null) === expected,
  );

  const batteryPresent = spec.batteryItemIds.filter(
    (i) => (answersByItem[i]?.value_num ?? null) !== null,
  );
  const complete = batteryPresent.length === spec.batteryItemIds.length;
  const outcome = consented && complete ? 'complete' : !consented ? 'no_consent' : 'partial';

  const batteryValues = spec.batteryItemIds
    .map((i) => answersByItem[i]?.value_num ?? null)
    .filter((v) => v !== null);
  const straightLiner = batteryValues.length > 1 && new Set(batteryValues).size === 1;

  const submission = {
    submission_id: payload.response_id,
    data_type: dataType,
    batch_id: batchId,
    eligible,
    consented,
    consent_twin: consentTwin,
    attention_passed: attentionPassed,
    completion_seconds: payload.completion_seconds ?? null,
    straight_liner: straightLiner,
    outcome,
    arm,
    arm_source: armSource,
    mc_answer: textOrNone(checks.manipulation),
    city: textOrNone(fields.city),
    service: textOrNone(fields.service),
    language: meta.language ?? null,
    raw_object_path: rawObjectPath,
    started_at: payload.started_at ?? null,
    submitted_at: payload.submitted_at,
  };

  const answers = Object.keys(answersByItem)
    .sort()
    .map((i) => answersByItem[i]);

  return { submission, answers };
}

/** `raw/survey_<id>.json`. Must match the Python `raw_object_path` exactly. */
export function rawObjectPath(responseId) {
  return `raw/survey_${String(responseId).replace(/[^A-Za-z0-9_.-]/g, '_')}.json`;
}
