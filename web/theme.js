/* Apply the saved theme before styles paint, then wire the accessible toggle. */
(() => {
  'use strict';
  const root = document.documentElement;
  function apply(mode) {
    const dark = mode !== 'light';
    root.dataset.theme = dark ? 'dark' : 'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0a0a0f' : '#10233f');
    const button = document.getElementById('theme');
    if (button) {
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
      button.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
    }
  }
  let saved = 'dark';
  try { saved = JSON.parse(localStorage.getItem('cw-theme')); } catch { /* Storage may be disabled. */ }
  apply(saved);
  document.addEventListener('DOMContentLoaded', () => {
    apply(root.dataset.theme);
    document.getElementById('theme')?.addEventListener('click', () => {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      apply(next);
      try { localStorage.setItem('cw-theme', JSON.stringify(next)); } catch { /* The toggle still works. */ }
    });
  });
})();
