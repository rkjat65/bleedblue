const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('web/theme.js', 'utf8');
function boot(value, blocked = false) {
  let ready, click, stored = value, mounted = false;
  const attrs = {}, meta = {}, root = {dataset: {}};
  const button = {setAttribute(k, v) { attrs[k] = v; }, addEventListener(k, fn) { click = fn; }};
  const document = {
    documentElement: root,
    querySelector() { return {setAttribute(k, v) { meta[k] = v; }}; },
    getElementById() { return mounted ? button : null; },
    addEventListener(k, fn) { ready = fn; }
  };
  vm.runInNewContext(source, {document, localStorage: {
    getItem() { if (blocked) throw new Error('Blocked'); return stored; },
    setItem(k, v) { if (blocked) throw new Error('Blocked'); stored = v; }
  }});
  return {root, attrs, meta, mount() { mounted = true; ready(); }, toggle() { click(); }, saved() { return stored; }};
}
const dark = boot('"dark"');
assert.equal(dark.root.dataset.theme, 'dark', 'Saved dark mode applies before the body exists');
assert.equal(dark.meta.content, '#0a0a0f');
dark.mount();
assert.equal(dark.attrs['aria-pressed'], 'true');
assert.equal(dark.attrs['aria-label'], 'Switch to light mode');
dark.toggle();
assert.equal(dark.root.dataset.theme, 'light');
assert.equal(dark.saved(), '"light"');
assert.equal(dark.meta.content, '#10233f');
assert.equal(boot(dark.saved()).root.dataset.theme, 'light');
for (const invalid of [null, '{broken', '"unexpected"']) assert.equal(boot(invalid).root.dataset.theme, 'light');
const blocked = boot(null, true);
blocked.mount();
blocked.toggle();
assert.equal(blocked.root.dataset.theme, 'dark', 'Toggle works without storage access');
console.log('Theme persistence, first paint, toggle accessibility and blocked storage passed.');
