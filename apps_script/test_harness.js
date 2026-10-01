/**
 * Offline harness for the Apps Script files. Node, no Google account, no network.
 *
 *   node apps_script/test_harness.js            # build the form, check every key
 *   node apps_script/test_harness.js --payload  # also print the JSON a submission would POST
 *
 * It stubs the tiny slice of the Apps Script API the two scripts use, runs `buildForm()`, then
 * runs `buildPayload()` from intake.gs over a simulated response. That exercises the real code
 * paths — the section index, the grid-row expansion, the key shape — against the real form
 * definition, which is the part that is expensive to get wrong in production.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const DIR = __dirname;
const ItemType = {
  PAGE_BREAK: 'PAGE_BREAK',
  SECTION_HEADER: 'SECTION_HEADER',
  GRID: 'GRID',
  CHECKBOX_GRID: 'CHECKBOX_GRID',
  SCALE: 'SCALE',
  MULTIPLE_CHOICE: 'MULTIPLE_CHOICE',
  CHECKBOX: 'CHECKBOX',
  TEXT: 'TEXT',
  PARAGRAPH_TEXT: 'PARAGRAPH_TEXT'
};

let nextId = 1;

/** One form item. Every setter returns `this`, as the real API does. */
function makeItem(type) {
  const item = {
    _type: type,
    _id: nextId++,
    _title: '',
    _help: '',
    _rows: [],
    _columns: [],
    _options: [],
    _required: false,
    _points: null,
    getType: () => type,
    getId: function () { return this._id; },
    getTitle: function () { return this._title; },
    setTitle: function (t) { this._title = t; return this; },
    setHelpText: function (t) { this._help = t; return this; },
    setRequired: function (v) { this._required = v; return this; },
    setRows: function (r) { this._rows = r; return this; },
    setColumns: function (c) { this._columns = c; return this; },
    setChoiceValues: function (v) { this._options = v; return this; },
    setBounds: function (lo, hi) { this._points = hi; return this; },
    setLabels: function () { return this; },
    setValidation: function () { return this; },
    asGridItem: function () { return this; },
    asCheckboxGridItem: function () { return this; },
    getRows: function () { return this._rows; }
  };
  return item;
}

function makeForm(title) {
  const items = [];
  const form = {
    _title: title,
    _settings: {},
    getId: () => 'FORM_STUB_ID',
    getEditUrl: () => 'https://docs.google.com/forms/d/FORM_STUB_ID/edit',
    getPublishedUrl: () => 'https://docs.google.com/forms/d/e/FORM_STUB_ID/viewform',
    getItems: () => items,
    getResponses: () => [],
    setTitle: function (t) { this._title = t; return this; },
    setDescription: function (t) { this._settings.description = t; return this; },
    setConfirmationMessage: function (t) { this._settings.confirmation = t; return this; },
    setCollectEmail: function (v) { this._settings.collectEmail = v; return this; },
    setAllowResponseEdits: function (v) { this._settings.allowEdits = v; return this; },
    setProgressBar: function (v) { this._settings.progressBar = v; return this; },
    setShuffleQuestions: function (v) { this._settings.shuffle = v; return this; },
    setLimitOneResponsePerUser: function (v) { this._settings.limitOne = v; return this; }
  };
  const add = (type) => { const i = makeItem(type); items.push(i); return i; };
  form.addPageBreakItem = () => add(ItemType.PAGE_BREAK);
  form.addSectionHeaderItem = () => add(ItemType.SECTION_HEADER);
  form.addGridItem = () => add(ItemType.GRID);
  form.addScaleItem = () => add(ItemType.SCALE);
  form.addMultipleChoiceItem = () => add(ItemType.MULTIPLE_CHOICE);
  form.addCheckboxItem = () => add(ItemType.CHECKBOX);
  form.addTextItem = () => add(ItemType.TEXT);
  form.addParagraphTextItem = () => add(ItemType.PARAGRAPH_TEXT);
  return form;
}

let activeForm = null;

const logs = [];
const sandbox = {
  FormApp: {
    ItemType,
    create: (t) => { activeForm = makeForm(t); return activeForm; },
    getActiveForm: () => activeForm,
    createTextValidation: () => ({
      setHelpText() { return this; },
      requireNumber() { return this; },
      build() { return {}; }
    })
  },
  Logger: {
    log: (...args) => logs.push(args.map(String).join(' '))
  },
  console,
  Utilities: {
    newBlob: (s) => ({ getBytes: () => Array.from(Buffer.from(String(s), 'utf8')) }),
    computeHmacSha256Signature: (msgBytes, keyBytes) => {
      const crypto = require('crypto');
      const mac = crypto.createHmac('sha256', Buffer.from(keyBytes));
      mac.update(Buffer.from(msgBytes));
      // Apps Script returns signed bytes; mirror that so hmacHex's sign handling is exercised.
      return Array.from(mac.digest()).map((b) => (b > 127 ? b - 256 : b));
    }
  },
  PropertiesService: {
    getScriptProperties: () => ({
      getProperty: (k) => (k === 'INTAKE_HMAC_SECRET' ? process.env.TEST_SECRET || 'test-secret' : null)
    })
  },
  UrlFetchApp: {
    fetch: () => { throw new Error('the harness never posts; use --payload and curl'); }
  }
};
vm.createContext(sandbox);

function load(file) {
  vm.runInContext(fs.readFileSync(path.join(DIR, file), 'utf8'), sandbox, { filename: file });
}

// ---------------------------------------------------------------- build the form

load('build_form.gs');
load('intake.gs');

const form = vm.runInContext('buildForm()', sandbox);
const verdict = vm.runInContext('verifyForm()', sandbox);

const settings = form._settings;
const problems = [];
if (settings.collectEmail !== false) problems.push('collectEmail must be false');
if (settings.allowEdits !== true) problems.push('allowResponseEdits must be true');
if (settings.shuffle !== false) problems.push('shuffleQuestions must be false');
if (verdict.unexpected.length) problems.push(`${verdict.unexpected.length} keys not in the map`);
if (verdict.missing.length) problems.push(`${verdict.missing.length} keys missing from the form`);

logs.forEach((l) => console.log('  ' + l));
console.log('');
console.log(`form questions ......... ${verdict.found}`);
console.log(`settings ............... collectEmail=${settings.collectEmail} ` +
            `allowEdits=${settings.allowEdits} shuffle=${settings.shuffle}`);

// ------------------------------------------------- simulate a submission and re-read it

/** A plausible answer for one form item, good enough to exercise intake end to end. */
function answerFor(item) {
  switch (item._type) {
    case ItemType.GRID:
      return item._rows.map(() => String(Math.min(4, item._columns.length)));
    case ItemType.SCALE:
      return String(Math.min(4, item._points));
    case ItemType.MULTIPLE_CHOICE:
      return item._options[0];
    case ItemType.CHECKBOX:
      return [item._options[0]];
    case ItemType.TEXT:
      return item._help && item._help.startsWith('In ') ? '4' : 'Ola and Rapido';
    case ItemType.PARAGRAPH_TEXT:
      return 'A steady day with airport trips and no cancellations.';
    default:
      return null;
  }
}

const itemResponses = form.getItems()
  .filter((i) => i._type !== ItemType.PAGE_BREAK && i._type !== ItemType.SECTION_HEADER)
  .map((item) => ({ getItem: () => item, getResponse: () => answerFor(item) }));

const response = {
  getId: () => '2_ABaOnudSTUBRESPONSEID',
  getTimestamp: () => new Date('2026-09-23T09:41:02Z'),
  getItemResponses: () => itemResponses
};

sandbox.__response = response;
const payload = vm.runInContext('buildPayload(__response)', sandbox);

const mapPath = path.join(DIR, '..', 'config', 'form_map.yaml');
const mapKeys = new Set(
  fs.readFileSync(mapPath, 'utf8')
    .split('\n')
    .map((l) => l.match(/^\s+"((?:[^"\\]|\\.)*)":/))
    .filter(Boolean)
    .map((m) => JSON.parse('"' + m[1] + '"'))
);

const payloadKeys = payload.answers.map((a) => a.section + '|' + a.title);
const notInMap = payloadKeys.filter((k) => !mapKeys.has(k));

console.log(`payload answers ........ ${payload.answers.length}`);
console.log(`form_map.yaml rows ..... ${mapKeys.size}`);
console.log(`payload keys not mapped  ${notInMap.length}`);
if (notInMap.length) {
  problems.push(`${notInMap.length} payload keys are not in form_map.yaml`);
  notInMap.slice(0, 10).forEach((k) => console.log('    ! ' + k));
}
if (payload.answers.length !== mapKeys.size) {
  problems.push(`payload has ${payload.answers.length} answers, map has ${mapKeys.size}`);
}

const hex = vm.runInContext("hmacHex('abc', 'key')", sandbox);
const expected = require('crypto').createHmac('sha256', 'key').update('abc').digest('hex');
console.log(`hmac matches node ...... ${hex === expected}`);
if (hex !== expected) problems.push('hmacHex does not match a reference HMAC-SHA256');

if (process.argv.includes('--payload')) {
  const out = path.join(DIR, 'sample_payload.json');
  fs.writeFileSync(out, JSON.stringify(payload, null, 1), 'utf8');
  console.log(`\nwrote ${out}`);
}

console.log('');
if (problems.length) {
  problems.forEach((p) => console.log('FAIL  ' + p));
  process.exit(1);
}
console.log('OK — the form builds, every key is in form_map.yaml, and the HMAC is correct.');
