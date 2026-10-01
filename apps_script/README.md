# Apps Script — the Google Form and its webhook

Two scripts and an offline harness. Between them the Form is **built by code, not typed**, which
is the only way to be sure not one of its 112 titles has a stray em dash in it.

| File | What it is |
|---|---|
| `build_form.gs` | **Generated.** Creates the whole Form — 22 sections, 112 questions, every setting. |
| `intake.gs` | The webhook. Signs each submission and posts it to `/api/survey/intake`. |
| `test_harness.js` | Runs both, offline, in Node against a stubbed Forms API. No Google account. |
| `sample_payload.json` | **Generated.** A full submission as the Form would send it. Used by `tests/test_apps_script_contract.py`. |

## Do not hand-edit `build_form.gs`

Its `DEFINITION` block is generated from `config/form_map.yaml` and
`data/reference/instrument.json`. A title changed here and not there is a 422 on every submission.
Change the map, then regenerate.

## Checking it without a Google account

```bash
node apps_script/test_harness.js --payload
```

This builds the Form against a stubbed `FormApp`, runs `verifyForm()`, reads the result back
through `buildPayload()` exactly as a real submission would, checks all 112 keys against
`form_map.yaml`, and verifies `hmacHex` against Node's own HMAC-SHA256. It writes
`sample_payload.json`, which the Python suite then posts at the real intake route:

```bash
python -m pytest tests/test_apps_script_contract.py -q
```

Those two commands together prove the whole chain — Form definition → payload shape → signature →
intake → persona — without Google, a network, a model or a database anywhere in it.

## Using them for real

1. **Create the Form.** script.google.com → New project → paste `build_form.gs` → run `buildForm`.
   Authorise it. The execution log prints the edit URL and the public URL.
2. **Open the new Form** → ⋮ → Apps Script. This is a *different*, form-bound script project.
   Paste **both** `build_form.gs` (for `verifyForm`) and `intake.gs` into it.
3. **Set the secret**: Project Settings → Script Properties → `INTAKE_HMAC_SECRET`, the same value
   as `.env`.
4. **Set `ENDPOINT`** at the top of `intake.gs` to your tunnel or Space URL.
5. **Fill the Form in yourself once**, then run `verifyForm` and `printKeys`.
6. **Run `testWithLastResponse`.** Expect `intake ok: {"status":"ok","twin_id":…}`.
7. **Add the trigger**: Triggers → Add Trigger → `onFormSubmit` / From form / On form submit,
   failure notification **Immediately**. It must be an installable trigger — the bare function
   name does not carry the authorisation `UrlFetchApp` needs.

Full detail, including what each response code means: `docs/GOOGLE_FORM.md` §5.

## If the endpoint was down

```javascript
resendSince('2026-09-20')
```

Google keeps every response whatever the webhook did, so a failed post is never lost data. This
re-posts everything since that date; intake is idempotent on `response_id`, so running it twice is
safe.

## Regenerating `build_form.gs`

```bash
python tools/gen_build_form.py
```

If `form_map.yaml` changes, regenerate rather than editing, then re-run the harness and the
contract test — both will tell you
immediately if the three artefacts have drifted apart.
