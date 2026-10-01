/**
 * Twin Lab survey intake.
 *
 * Posts each submission to /api/survey/intake, signed with HMAC-SHA256 over the raw body.
 * The section a question sits in is part of its key, because question titles repeat: Part 16
 * re-asks Part 7's and Part 9's questions and Part 17 asks the same three questions six times.
 *
 * Setup: Project Settings > Script Properties > INTAKE_HMAC_SECRET, then set ENDPOINT below,
 * then Triggers > Add Trigger > onFormSubmit / From form / On form submit.
 */

// The tunnel or Space URL. Must be https and publicly reachable: Apps Script runs on Google's
// servers and cannot see localhost.
const ENDPOINT = 'https://REPLACE-ME/api/survey/intake';

// Items before the first page break belong to this section.
const FIRST_SECTION = 'PART 1 — A FEW QUICK CHECKS';

function onFormSubmit(e) {
  postToTwinLab(buildPayload(e.response));
}

/** Response -> the JSON body the intake route expects. */
function buildPayload(response) {
  const sectionByItemId = buildSectionIndex(FormApp.getActiveForm());
  const answers = [];

  response.getItemResponses().forEach(function (itemResponse) {
    const item = itemResponse.getItem();
    const section = sectionByItemId[item.getId()] || FIRST_SECTION;
    const value = itemResponse.getResponse();
    const type = item.getType();

    if (type === FormApp.ItemType.GRID) {
      // One answer per row, keyed by the row label: that is what form_map.yaml holds.
      const rows = item.asGridItem().getRows();
      for (var i = 0; i < rows.length; i++) {
        if (value[i] === null || value[i] === '') continue;
        answers.push({ section: section, title: rows[i], value: value[i] });
      }
    } else if (type === FormApp.ItemType.CHECKBOX_GRID) {
      const rows = item.asCheckboxGridItem().getRows();
      for (var j = 0; j < rows.length; j++) {
        if (!value[j] || value[j].length === 0) continue;
        answers.push({ section: section, title: rows[j], value: value[j] });
      }
    } else {
      answers.push({ section: section, title: item.getTitle(), value: value });
    }
  });

  return {
    response_id: response.getId(),
    submitted_at: response.getTimestamp().toISOString(),
    answers: answers
  };
}

/** item id -> the section header it sits under. Page breaks are the section boundaries. */
function buildSectionIndex(form) {
  const index = {};
  var current = FIRST_SECTION;
  form.getItems().forEach(function (item) {
    if (item.getType() === FormApp.ItemType.PAGE_BREAK) {
      current = item.getTitle();
    } else {
      index[item.getId()] = current;
    }
  });
  return index;
}

function postToTwinLab(payload) {
  const secret = PropertiesService.getScriptProperties()
    .getProperty('INTAKE_HMAC_SECRET');
  if (!secret) {
    throw new Error('Script property INTAKE_HMAC_SECRET is not set.');
  }

  const body = JSON.stringify(payload);
  const response = UrlFetchApp.fetch(ENDPOINT, {
    method: 'post',
    contentType: 'application/json',
    payload: body,
    headers: { 'X-Signature': hmacHex(body, secret) },
    muteHttpExceptions: true
  });

  const code = response.getResponseCode();
  if (code !== 200) {
    // Throwing makes it visible in Executions and in the failure-notification email.
    throw new Error('Twin Lab intake failed (' + code + '): ' + response.getContentText());
  }
  Logger.log('intake ok: ' + response.getContentText());
  return response;
}

/** Hex HMAC-SHA256 over the exact UTF-8 bytes of the body, matching hmac.new(...).hexdigest(). */
function hmacHex(message, key) {
  const signature = Utilities.computeHmacSha256Signature(
    Utilities.newBlob(message).getBytes(),
    Utilities.newBlob(key).getBytes()
  );
  return signature.map(function (byte) {
    const value = (byte < 0 ? byte + 256 : byte).toString(16);
    return value.length === 1 ? '0' + value : value;
  }).join('');
}

/**
 * Run this by hand before going live. Posts the most recent submission again.
 * Intake is idempotent on response_id, so re-posting is safe.
 */
function testWithLastResponse() {
  const responses = FormApp.getActiveForm().getResponses();
  if (responses.length === 0) {
    throw new Error('Fill the form in once yourself first.');
  }
  postToTwinLab(buildPayload(responses[responses.length - 1]));
}

/**
 * Re-post everything submitted since a date, for when the endpoint was down.
 *   resendSince('2026-09-20')
 * Google keeps every response whatever the webhook did, so nothing is ever lost — this is how
 * you catch the database up afterwards.
 */
function resendSince(isoDate) {
  const since = new Date(isoDate);
  if (isNaN(since.getTime())) throw new Error('Pass a date, e.g. resendSince("2026-09-20")');

  const responses = FormApp.getActiveForm().getResponses(since);
  Logger.log('%s responses since %s', responses.length, isoDate);

  var ok = 0;
  const failed = [];
  responses.forEach(function (response) {
    try {
      postToTwinLab(buildPayload(response));
      ok++;
      Utilities.sleep(250);  // stay well inside the Space's rate limit
    } catch (err) {
      failed.push(response.getId() + ': ' + err.message);
    }
  });

  Logger.log('resent %s, failed %s', ok, failed.length);
  failed.forEach(function (f) { Logger.log('  ' + f); });
  return { ok: ok, failed: failed };
}

/** Prints every "<section>|<title>" key the form will send. Diff this against form_map.yaml. */
function printKeys() {
  const responses = FormApp.getActiveForm().getResponses();
  if (responses.length === 0) {
    throw new Error('Fill the form in once yourself first.');
  }
  const payload = buildPayload(responses[responses.length - 1]);
  payload.answers.forEach(function (a) {
    Logger.log(a.section + '|' + a.title);
  });
  Logger.log('%s answers', payload.answers.length);
}
