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
  return { appended, store, settings, window };
}

const fresh = mount();
assert.equal(fresh.appended.length, 1, 'new visitors load audience measurement without an interrupting prompt');
assert.equal(fresh.settings.textContent, 'Disable analytics');
fresh.settings.click();
assert.equal(fresh.store.get('cw-analytics-consent'), 'declined');
assert.equal(fresh.window.reloaded, true, 'revoking consent reloads without the tag');
assert.match(fresh.appended[0].src, /G-DXRDX6R7YY/);
const returning = mount('accepted');
assert.equal(returning.appended.length, 1, 'saved permission loads the tag');
const rejected = mount('declined');
assert.equal(rejected.appended.length, 0, 'saved refusal remains respected');
assert.equal(rejected.settings.textContent, 'Enable analytics');
rejected.settings.click();
assert.equal(rejected.store.get('cw-analytics-consent'), 'accepted');
assert.equal(rejected.appended.length, 1, 'reader can enable analytics from the footer');
console.log('Quiet analytics default, opt-out persistence and footer control passed.');
