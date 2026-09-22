const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../web/analytics.js'), 'utf8');

function mount(initialChoice) {
  const store = new Map();
  if (initialChoice) store.set('cw-analytics-consent', initialChoice);
  const appended = [];
  const panel = { hidden: false, setAttribute() {}, addEventListener(_name, fn) { this.click = fn; } };
  const settings = { addEventListener(_name, fn) { this.click = fn; } };
  const footer = { appendChild(node) { assert.equal(node, settings); } };
  const document = {
    readyState: 'complete',
    cookie: '',
    head: { appendChild(script) { appended.push(script); } },
    body: { appendChild(node) { assert.equal(node, panel); } },
    createElement(name) { return name === 'aside' ? panel : name === 'button' ? settings : {}; },
    getElementById(id) { return id === 'analytics-choice' ? panel : null; },
    querySelector(selector) { return selector === 'footer .muted' ? footer : null; }
  };
  const window = { location: { reload() { window.reloaded = true; } } };
  const context = { document, window, localStorage: { getItem: key => store.get(key), setItem: (key, value) => store.set(key, value) } };
  vm.runInNewContext(source, context);
  function choose(value) { panel.click({ target: { closest: () => ({ dataset: { analytics: value } }) } }); }
  return { appended, store, panel, settings, choose, window };
}

const fresh = mount();
assert.equal(fresh.appended.length, 0, 'new visitors must not load Google');
assert.equal(fresh.panel.hidden, false);
fresh.choose('declined');
assert.equal(fresh.appended.length, 0, 'declining must not load Google');
assert.equal(fresh.store.get('cw-analytics-consent'), 'declined');
fresh.settings.click();
assert.equal(fresh.panel.hidden, false, 'readers can reopen settings');
fresh.choose('accepted');
assert.equal(fresh.appended.length, 1);
assert.match(fresh.appended[0].src, /G-DXRDX6R7YY/);
fresh.choose('accepted');
assert.equal(fresh.appended.length, 1, 'one tag per page');
fresh.choose('declined');
assert.equal(fresh.window.reloaded, true, 'revoking consent reloads without the tag');
const returning = mount('accepted');
assert.equal(returning.appended.length, 1, 'saved permission loads the tag');
assert.equal(returning.panel.hidden, true);
const rejected = mount('declined');
assert.equal(rejected.appended.length, 0, 'saved refusal remains respected');
console.log('Analytics opt-in, refusal, persistence and tag deduplication passed.');
