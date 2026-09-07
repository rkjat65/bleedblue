/* Homepage motion is optional; archive values remain available without JavaScript. */
(() => {
  'use strict';
  const hero = document.querySelector('[data-cricket-hero]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  if (hero) {
    const button = hero.querySelector('.hero-motion');
    let paused = reduced.matches;
    const sync = () => {
      hero.classList.toggle('motion-paused', paused || document.hidden);
      hero.classList.toggle('motion-enabled', !paused && !document.hidden);
      button.setAttribute('aria-pressed', String(paused));
      button.textContent = paused ? 'Play animation' : 'Pause animation';
      button.hidden = false;
    };
    button.addEventListener('click', () => { paused = !paused; sync(); });
    reduced.addEventListener('change', () => { paused = reduced.matches; sync(); });
    document.addEventListener('visibilitychange', sync);
    hero.addEventListener('pointermove', event => {
      if (paused || event.pointerType !== 'mouse') return;
      const rect = hero.getBoundingClientRect();
      hero.style.setProperty('--art-x', `${(event.clientX - rect.left - rect.width / 2) / 65}px`);
      hero.style.setProperty('--art-y', `${(event.clientY - rect.top - rect.height / 2) / 65}px`);
    });
    hero.addEventListener('pointerleave', () => {
      hero.style.setProperty('--art-x', '0px');
      hero.style.setProperty('--art-y', '0px');
    });
    sync();
  }
  const story = document.querySelector('[data-archive-story]');
  if (!story) return;
  const rows = JSON.parse(document.querySelector('#archive-chart-data').textContent);
  const format = story.querySelector('[data-chart-format]');
  const gender = story.querySelector('[data-chart-gender]');
  const number = n => n.toLocaleString('en-GB');
  function render() {
    const decades = [...new Set(rows.map(r => r[0]))].sort();
    const totals = new Map(decades.map(d => [d, 0]));
    for (const [d, f, g, count] of rows) {
      if ((!format.value || f === format.value) && (!gender.value || g === gender.value)) totals.set(d, totals.get(d) + count);
    }
    const max = Math.max(1, ...totals.values());
    story.querySelector('.archive-bars').innerHTML = [...totals].map(([d, n]) => `<div class="archive-column"><strong>${number(n)}</strong><i style="--bar-height:${n ? Math.max(1, n / max * 100) : 0}%;${n ? '' : 'min-height:0'}"></i><span>${d}s</span></div>`).join('');
    story.querySelector('[data-chart-rows]').innerHTML = [...totals].map(([d, n]) => `<tr><th scope="row">${d}s</th><td>${number(n)}</td></tr>`).join('');
    story.querySelector('.chart-summary').innerHTML = `<strong>${number([...totals.values()].reduce((a, b) => a + b, 0))}</strong> recorded matches · ${format.value || 'all formats'} · ${gender.value || 'men & women'}`;
  }
  format.addEventListener('change', render);
  gender.addEventListener('change', render);
})();
