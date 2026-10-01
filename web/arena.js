/* Arena layer: reveal motion, count-ups, chart drawing, match-centre countdowns
   and the quick-search palette. Pages are complete without it. */
(() => {
  'use strict';
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const IO = 'IntersectionObserver' in window;
  const root = document.documentElement;
  const fmt = n => Math.round(n).toLocaleString('en-US');

  /* Header shadow and scroll progress. */
  const header = $('body>header');
  const bar = document.createElement('div');
  bar.className = 'arena-progress';
  bar.setAttribute('aria-hidden', 'true');
  document.body.prepend(bar);
  let ticking = false;
  function onScroll() {
    ticking = false;
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.setProperty('--p', max > 0 ? Math.min(1, scrollY / max).toFixed(4) : 0);
    header?.classList.toggle('is-scrolled', scrollY > 12);
  }
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, {passive: true});
  onScroll();
  /* Loading cue while the next page is requested. */
  document.addEventListener('click', e => {
    const a = e.target.closest?.('a[href]');
    if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target || a.hasAttribute('download')) return;
    const url = new URL(a.href, location.href);
    if (url.origin !== location.origin || (url.pathname === location.pathname && url.hash)) return;
    bar.classList.add('is-loading');
  });
  addEventListener('pageshow', () => bar.classList.remove('is-loading'));

  /* Mobile bottom tab bar (CSS shows it on narrow screens only). */
  const tabs = [
    ['/', 'Home', '<path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/>'],
    ['/matches/', 'Matches', '<path d="M7 21V7M12 21V7M17 21V7M5.5 4.5h5M13.5 4.5h5"/>'],
    ['/players/', 'Players', '<path d="M14.5 3.5l6 6-9.8 9.8a2 2 0 0 1-2.8 0l-3.2-3.2a2 2 0 0 1 0-2.8zM4.2 19.8l2-2"/>'],
    ['/records/', 'Records', '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M8 20h8"/>'],
    ['/search/', 'Search', '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>']
  ];
  if (!$('.tabbar') && !document.body.classList.contains('embedded') && !location.pathname.startsWith('/embed')) {
    const here = location.pathname;
    const nav = document.createElement('nav');
    nav.className = 'tabbar';
    nav.setAttribute('aria-label', 'Quick navigation');
    nav.innerHTML = tabs.map(([url, name, path]) => `<a href="${url}"${(url === '/' ? here === '/' : here.startsWith(url)) ? ' aria-current="page"' : ''}><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${path}</svg><span>${name}</span></a>`).join('');
    document.body.append(nav);
  }

  /* Count-up numbers: explicit [data-count] plus the headline stat grids on profile pages. */
  function countUp(el) {
    const target = Number(el.dataset.count ?? el.textContent.replace(/,/g, ''));
    if (!Number.isFinite(target) || reduce || target < 10) return;
    const start = performance.now(), dur = Math.min(1800, 600 + target / 40);
    const tick = now => {
      const t = Math.min(1, (now - start) / dur), eased = 1 - Math.pow(1 - t, 4);
      el.textContent = fmt(target * eased);
      if (t < 1) requestAnimationFrame(tick);
    };
    el.textContent = '0';
    requestAnimationFrame(tick);
  }
  const counters = [...new Set([...$$('[data-count]'), ...$$('main .stats strong').filter(el => /^[\d,]+$/.test(el.textContent.trim()))])];

  /* Chart containers draw themselves when they scroll into view. */
  const chartBits = $$('main :is(svg.cw-svg, .race-bar, .home-dual-track, .home-world-track, .cw-hbar, .annual-fill, .format-card i[style*="width"])');
  const charts = [...new Set(chartBits.map(el => el.closest('figure, .race-panel, .format-card, .home-insight-card, .cw-lab, .panel, section') || el.parentElement))];
  charts.forEach(ch => {
    ch.classList.add('ch');
    $$('.cw-line', ch).forEach(line => { try { line.style.setProperty('--len', Math.ceil(line.getTotalLength()) + 1); } catch { /* Not rendered yet. */ } });
    $$('.cw-man-bar', ch).forEach((rect, n) => rect.style.setProperty('--n', n % 60));
  });

  /* Reveal blocks that start below the fold; anything already visible stays put. */
  const blocks = $$('main > :is(section, .panel, .grid, .stats, .table-wrap, figure, div), .rc-grid > li, .bento-tile, .race-panel, .home-insight-card, .format-card, .grid > .feature-card');
  if (!reduce && IO) {
    root.classList.add('arena-js');
    const fold = innerHeight * 0.92;
    const reveal = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); reveal.unobserve(e.target); }
    }), {rootMargin: '0px 0px -8% 0px'});
    blocks.forEach(el => {
      if (el.getBoundingClientRect().top < fold || el.closest('.home-hero')) return;
      const sibs = el.parentElement ? [...el.parentElement.children] : [];
      el.style.setProperty('--rv-delay', `${Math.min(sibs.indexOf(el), 6) * 70}ms`);
      el.classList.add('rv');
      reveal.observe(el);
    });
    const draw = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); draw.unobserve(e.target); }
    }), {threshold: 0.2});
    charts.forEach(ch => draw.observe(ch));
    const count = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { countUp(e.target); count.unobserve(e.target); }
    }), {threshold: 0.6});
    counters.forEach(el => count.observe(el));
  }

  /* Match centre: countdowns to IST start times and rail arrows. */
  const rail = $('[data-mc-rail]');
  if (rail) {
    const stamps = $$('[data-start]', rail).filter(a => a.dataset.start);
    const render = () => {
      const now = Date.now();
      stamps.forEach(a => {
        const out = $('[data-countdown]', a);
        const diff = Date.parse(a.dataset.start) - now;
        if (Number.isNaN(diff) || !out) return;
        out.classList.toggle('is-live', diff <= 0);
        if (diff <= 0) { out.textContent = diff > -9 * 3600e3 ? '● Started' : 'Earlier'; return; }
        const m = Math.floor(diff / 60e3), d = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60), mm = m % 60;
        out.textContent = 'in ' + (d ? `${d}d ${h}h` : h ? `${h}h ${String(mm).padStart(2, '0')}m` : `${mm}m`);
      });
    };
    render();
    setInterval(render, 30e3);
    const step = dir => rail.scrollBy({left: dir * (rail.clientWidth * 0.8), behavior: reduce ? 'auto' : 'smooth'});
    $('[data-mc-prev]')?.addEventListener('click', () => step(-1));
    $('[data-mc-next]')?.addEventListener('click', () => step(1));
  }

  /* Leaderboard tabs on narrow screens; both boards show side by side on wide screens. */
  const race = $('[data-race]');
  if (race) {
    const tabs = $$('[data-race-tab]');
    const panels = $$('.race-panel', race);
    const narrow = window.matchMedia('(max-width: 860px)');
    const select = index => {
      tabs.forEach((t, i) => t.setAttribute('aria-selected', String(i === index)));
      panels.forEach((p, i) => { p.hidden = narrow.matches && i !== index; if (i === index) p.classList.add('in'); });
    };
    tabs.forEach((t, i) => t.addEventListener('click', () => select(i)));
    const current = () => Math.max(0, tabs.findIndex(t => t.getAttribute('aria-selected') === 'true'));
    narrow.addEventListener?.('change', () => select(current()));
    select(0);
  }

  /* Homepage featured scorecard: show the worm and Manhattans, expand for the rest. */
  const lab = $('.home-match-lab');
  const labBody = lab && $('.cw-lab', lab);
  if (labBody && labBody.scrollHeight > 1300) {
    lab.classList.add('is-collapsed');
    const more = document.createElement('button');
    more.type = 'button';
    more.className = 'lab-toggle';
    more.setAttribute('aria-expanded', 'false');
    more.textContent = 'Show all match charts ↓';
    more.addEventListener('click', () => {
      const open = lab.classList.toggle('is-collapsed') === false;
      more.setAttribute('aria-expanded', String(open));
      more.textContent = open ? 'Show fewer charts ↑' : 'Show all match charts ↓';
      if (!open) lab.scrollIntoView({block: 'start'});
    });
    labBody.after(more);
  }


  /* Recently viewed profiles, scorecards and team pages feed the palette's empty state. */
  const RECENT = 'cw-recent';
  const readRecent = () => { try { return JSON.parse(localStorage.getItem(RECENT)) || []; } catch { return []; } };
  const kindOf = path => ({players: 'Player', matches: 'Match', teams: 'Team', grounds: 'Ground', series: 'Series'})[path.split('/')[1]];
  if (kindOf(location.pathname) && location.pathname.split('/').length > 3) {
    const title = ($('main h1')?.textContent || document.title.replace(/ \| Crickrida$/, '')).trim();
    const items = [{url: location.pathname, title, kind: kindOf(location.pathname)}, ...readRecent().filter(r => r.url !== location.pathname)].slice(0, 6);
    try { localStorage.setItem(RECENT, JSON.stringify(items)); } catch { /* Storage may be unavailable. */ }
  }

  /* Quick search palette: "/" or Ctrl/Cmd+K, and the header/tab-bar search links. */
  let palette, input, list, index, active = -1;
  async function loadIndex() {
    if (index) return index;
    const get = url => fetch(url).then(r => r.ok ? r.json() : []).catch(() => []);
    const [entities, players] = await Promise.all([get('/data/entity-index.json'), get('/data/player-index.json')]);
    const kinds = {teams: 'Team', grounds: 'Ground', series: 'Series', tournaments: 'Series'};
    index = [
      ...entities.map(e => ({name: e.name, url: e.url, kind: kinds[e.kind] || 'Page', rank: 0})),
      ...players.map(p => ({name: p.name, url: p.url, kind: (p.teams || []).join(' / ') || 'Player', rank: 1, weight: (p.runs || 0) + (p.wickets || 0) * 20}))
    ];
    return index;
  }
  function results(q) {
    const needle = q.trim().toLowerCase();
    if (!needle || !index) return [];
    const scored = [];
    for (const item of index) {
      const name = item.name.toLowerCase(), at = name.indexOf(needle);
      if (at < 0) continue;
      const word = at === 0 || name[at - 1] === ' ';
      scored.push([(at === 0 ? 0 : word ? 1 : 2) * 1e7 + item.rank * 1e6 - (item.weight || 0), item]);
    }
    return scored.sort((a, b) => a[0] - b[0]).slice(0, 8).map(s => s[1]);
  }
  function paint() {
    const q = input.value;
    const hits = results(q);
    active = hits.length ? 0 : -1;
    const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
    list.innerHTML = hits.map((h, i) => `<li><a href="${esc(h.url)}" role="option" aria-selected="${i === 0}"><span>${esc(h.name)}</span><small>${esc(h.kind)}</small></a></li>`).join('')
      + (q.trim() ? `<li><a href="/search/?q=${encodeURIComponent(q.trim())}" role="option" aria-selected="${!hits.length}"><span>Search all results for “${esc(q.trim())}”</span><small>Enter</small></a></li>` : '');
    if (!q.trim()) {
      const recent = readRecent().filter(r => r.url !== location.pathname);
      const sections = [];
      list.innerHTML = (recent.length ? '<li class="pal-group">Recently viewed</li>' + recent.map(r => `<li><a href="${esc(r.url)}" role="option"><span>${esc(r.title)}</span><small>${esc(r.kind)}</small></a></li>`).join('') : '')
        + (sections.length ? '<li class="pal-group">On this page</li>' + sections.map((h, i) => `<li><a href="#${esc(h.el.id)}" role="option" data-close><span>${String(i + 1).padStart(2, '0')} · ${esc(h.label)}</span><small>Section</small></a></li>`).join('') : '')
        + (!recent.length && !sections.length ? '<li class="pal-empty">Type a player, team, ground or series.</li>' : '');
      active = -1;
      $$('[data-close]', list).forEach(a => a.addEventListener('click', closePalette));
    }
  }
  function move(delta) {
    const items = $$('a', list);
    if (!items.length) return;
    active = (active + delta + items.length) % items.length;
    items.forEach((a, i) => a.setAttribute('aria-selected', String(i === active)));
    items[active].scrollIntoView({block: 'nearest'});
  }
  function openPalette(seed = '') {
    if (!palette) {
      palette = document.createElement('div');
      palette.className = 'palette';
      palette.hidden = true;
      palette.innerHTML = '<div class="palette-box" role="dialog" aria-modal="true" aria-label="Quick search"><input type="search" placeholder="Search players, teams, grounds…" aria-label="Quick search" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="palette-list"><ul class="palette-list" id="palette-list" role="listbox"></ul><div class="palette-hint"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Esc</kbd> close</span><span><kbd>J</kbd><kbd>K</kbd> next/prev section</span></div></div>';
      document.body.append(palette);
      input = $('input', palette);
      list = $('ul', palette);
      input.addEventListener('input', paint);
      input.addEventListener('keydown', e => {
        if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
        else if (e.key === 'Enter') { e.preventDefault(); const pick = $$('a', list)[Math.max(0, active)]; if (pick) { if (pick.hasAttribute('data-close')) closePalette(); location.href = pick.href; } }
        else if (e.key === 'Escape') closePalette();
      });
      palette.addEventListener('click', e => { if (e.target === palette) closePalette(); });
    }
    palette.hidden = false;
    document.body.style.overflow = 'hidden';
    input.value = seed;
    paint();
    input.focus();
    loadIndex().then(paint);
  }
  function closePalette() {
    if (!palette) return;
    palette.hidden = true;
    document.body.style.overflow = '';
  }
  document.addEventListener('keydown', e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
    if ((e.key === '/' && !typing) || (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey))) { e.preventDefault(); openPalette(); }
  });
  $$('a.search-link, .tabbar a[href="/search/"]').forEach(a => a.addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || location.pathname === '/search/') return;
    e.preventDefault();
    openPalette();
  }));
})();
