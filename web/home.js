/* Homepage motion is optional; archive values remain available without JavaScript. */
(() => {
  'use strict';
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
