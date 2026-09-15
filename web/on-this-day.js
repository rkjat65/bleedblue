/* Dated HTML works without JavaScript; enhancement keeps open pages on India's date. */
(() => {
  'use strict';
  const months = ['january','february','march','april','may','june','july','august','september','october','november','december'];
  function indiaKey(now = new Date()) {
    const parts = new Intl.DateTimeFormat('en-GB', {timeZone:'Asia/Kolkata', month:'2-digit', day:'2-digit'}).formatToParts(now);
    return parts.find(p => p.type === 'month').value + '-' + parts.find(p => p.type === 'day').value;
  }
  function calendarPath(month, day) {
    const date = new Date(Date.UTC(2000, month-1, day));
    return month >= 1 && month <= 12 && day >= 1 && date.getUTCMonth() === month-1 && date.getUTCDate() === day ? `/on-this-day/${months[month-1]}-${day}/` : null;
  }
  function filter(section, reset = true) {
    const form = section.querySelector('.otd-filters');
    if (!form) return;
    const focus = form.elements.focus.value, gender = form.elements.gender.value, format = form.elements.format.value;
    if (reset) section.dataset.limit = '12';
    const limit = Number(section.dataset.limit || 12);
    let count = 0;
    section.querySelectorAll('.otd-event').forEach(row => {
      const match = (!gender || row.dataset.gender === gender) && (!format || row.dataset.format === format) && (focus === 'all' || row.dataset[focus === 'india' ? 'india' : 'player'] === 'true');
      row.hidden = !match || ++count > limit;
    });
    section.querySelector('.otd-result-count').textContent = `${count} historical entries · ${Math.min(count, limit)} shown`;
    section.querySelector('.otd-empty').hidden = count !== 0;
    section.querySelector('.otd-show-more').hidden = count <= limit;
  }
  // Export the date rules for the small Node regression test; no browser work there.
  if (typeof module !== 'undefined' && module.exports) { module.exports = {indiaKey, calendarPath}; return; }
  document.querySelectorAll('.otd-section').forEach(s => filter(s));
  document.addEventListener('submit', event => {
    if (event.target.matches('.otd-filters')) { event.preventDefault(); filter(event.target.closest('.otd-section')); }
    if (event.target.matches('.otd-calendar')) {
      event.preventDefault();
      const form = event.target, path = calendarPath(Number(form.elements.month.value), Number(form.elements.day.value));
      if (path) location.assign(path);
      else form.querySelector('.otd-calendar-error').textContent = 'Choose a valid calendar date.';
    }
  });
  document.addEventListener('change', event => {
    if (event.target.closest('.otd-filters')) filter(event.target.closest('.otd-section'));
  });
  document.addEventListener('click', event => {
    if (event.target.closest('.otd-show-more')) {
      const section = event.target.closest('.otd-section');
      section.dataset.limit = String(Number(section.dataset.limit || 12) + 12);
      filter(section, false);
    }
  });
  let fetching = false;
  async function refresh() {
    if (fetching) return;
    const key = indiaKey();
    const sections = [...document.querySelectorAll('[data-otd-live]')].filter(s => s.dataset.otdKey !== key);
    if (!sections.length) return;
    fetching = true;
    try {
      const response = await fetch(`/data/on-this-day/${key}.json`, {cache:'no-cache'});
      if (!response.ok) throw new Error('Calendar unavailable');
      const data = await response.json();
      if (data.key !== key || indiaKey() !== key) return;
      for (const section of sections) {
        const markup = data[section.dataset.otdLive];
        if (typeof markup !== 'string') continue;
        section.innerHTML = markup;
        section.dataset.otdKey = key;
        filter(section);
      }
    } catch { /* Keep the dated, crawlable fallback and retry on the next clock tick. */ }
    finally { fetching = false; }
  }
  refresh();
  setInterval(refresh, 30000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
