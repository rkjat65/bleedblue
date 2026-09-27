/* Arena layer: reveal motion, count-ups, chart drawing, match-centre countdowns,
   section tracking and the quick-search palette. Pages are complete without it. */
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
  const blocks = $$('main > :is(section, .panel, .grid, .stats, .table-wrap, figure, div), .arena-band .band-cell, .rc-grid > li, .bento-tile, .race-panel, .home-insight-card, .format-card, .grid > .feature-card');
  if (!reduce && IO) {
    root.classList.add('arena-js');
    const fold = innerHeight * 0.92;
    const reveal = new IntersectionObserver(entries => entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); reveal.unobserve(e.target); }
    }), {rootMargin: '0px 0px -8% 0px'});
    blocks.forEach(el => {
      if (el.getBoundingClientRect().top < fold || el.closest('.cricket-hero')) return;
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

  /* Hero: pause the SMIL delivery with the existing motion toggle and when off screen. */
  const hero = $('[data-cricket-hero]');
  const delivery = $('.hero-delivery');
  if (hero && delivery && delivery.pauseAnimations) {
    let visible = true;
    const sync = () => (hero.classList.contains('motion-paused') || !visible || reduce) ? delivery.pauseAnimations() : delivery.unpauseAnimations();
    new MutationObserver(sync).observe(hero, {attributes: true, attributeFilter: ['class']});
    if (IO) new IntersectionObserver(([e]) => { visible = e.isIntersecting; sync(); }).observe(hero);
    document.addEventListener('visibilitychange', () => { visible = !document.hidden; sync(); });
    sync();
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

  /* Section jump bar highlights the section in view. */
  const jump = $('[data-arena-jump]');
  if (jump) {
    const links = $$('a', jump);
    const targets = links.map(a => document.getElementById(a.hash.slice(1)));
    let current = -1, queued = false;
    const spy = () => {
      queued = false;
      const line = innerHeight * 0.35;
      let index = -1;
      targets.forEach((t, i) => { if (t && t.getBoundingClientRect().top <= line) index = i; });
      if (index === current) return;
      current = index;
      links.forEach((a, i) => a.classList.toggle('is-active', i === index));
      const on = links[index];
      if (on) { const track = on.parentElement; track.scrollTo({left: on.offsetLeft - (track.clientWidth - on.offsetWidth) / 2, behavior: reduce ? 'auto' : 'smooth'}); }
    };
    addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(spy); } }, {passive: true});
    spy();
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

  /* Section guide: every page with 3-14 real sections gets numbered headings, a desktop
     rail, a mobile "section pill" and a short cue each time a new section takes over. */
  const guide = (() => {
    const jumpLinks = $$('[data-arena-jump] a');
    let heads;
    if (jumpLinks.length) {
      heads = jumpLinks.map(a => {
        const target = document.getElementById(a.hash.slice(1));
        return target && {el: target, label: a.textContent.trim()};
      }).filter(Boolean);
    } else {
      const h1 = ($('main h1')?.textContent || '').trim();
      heads = $$('main h2').filter(h => !h.closest('a, .feature-card, table, .palette, .race-panel, .cw-lab-grid, dialog, details:not([open])') && h.offsetParent !== null)
        .map(h => {
          let label = h.textContent.replace(/\s+/g, ' ').trim();
          if (h1 && label.startsWith(h1 + ':')) label = label.slice(h1.length + 1).trim();
          label = label.charAt(0).toUpperCase() + label.slice(1);
          return {el: h, label: label.length > 34 ? label.slice(0, 32).trimEnd() + '…' : label};
        });
    }
    if (heads.length < 3 || heads.length > 14) return null;
    const pad = n => String(n).padStart(2, '0');
    const slug = t => t.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'section';
    const used = new Set();
    heads.forEach((h, i) => {
      if (!h.el.id) { let id = 'sec-' + slug(h.label); while (used.has(id) || document.getElementById(id)) id += '-' + i; h.el.id = id; }
      used.add(h.el.id);
      h.mark = h.el.tagName === 'H2' ? h.el : $('h2', h.el);
      h.mark?.classList.add('sec-head');
      h.el.style.scrollMarginTop = '130px';
      if (!jumpLinks.length && h.el.tagName === 'H2' && !$('.sec-num', h.el)) h.el.insertAdjacentHTML('afterbegin', `<span class="sec-num" aria-hidden="true">${pad(i + 1)}</span>`);
    });

    const total = pad(heads.length);
    const railEl = document.createElement('nav');
    railEl.className = 'sec-rail';
    railEl.setAttribute('aria-label', 'Sections on this page');
    railEl.innerHTML = `<div class="sec-rail-track"><i class="sec-rail-fill"></i></div><ol>${heads.map((h, i) => `<li><a href="#${h.el.id}" data-i="${i}"><span class="sec-rail-num">${pad(i + 1)}</span><span class="sec-rail-label">${h.label.replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]))}</span></a></li>`).join('')}</ol><button type="button" class="sec-top" aria-label="Back to top">↑</button>`;
    document.body.append(railEl);

    const pill = document.createElement('div');
    pill.className = 'sec-pill';
    pill.hidden = Boolean(jumpLinks.length);
    pill.innerHTML = `<button type="button" class="sec-pill-main" aria-expanded="false"><span class="sec-pill-ball" aria-hidden="true"></span><span class="sec-pill-count"><b>01</b>/${total}</span><span class="sec-pill-label"></span></button><button type="button" class="sec-pill-next" aria-label="Next section">↓</button><div class="sec-sheet" hidden><p>On this page</p><ol>${heads.map((h, i) => `<li><a href="#${h.el.id}" data-i="${i}"><span>${pad(i + 1)}</span>${railEl.querySelectorAll('.sec-rail-label')[i].innerHTML}</a></li>`).join('')}</ol></div>`;
    document.body.append(pill);

    const cue = document.createElement('div');
    cue.className = 'sec-cue';
    cue.setAttribute('aria-hidden', 'true');
    document.body.append(cue);

    const railLinks = $$('ol a', railEl), sheetLinks = $$('.sec-sheet a', pill), sheet = $('.sec-sheet', pill), mainBtn = $('.sec-pill-main', pill);
    let current = -2, cueTimer, started = false;
    const go = i => { const h = heads[Math.max(0, Math.min(heads.length - 1, i))]; h.el.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', block: 'start'}); };
    const setSheet = open => { sheet.hidden = !open; mainBtn.setAttribute('aria-expanded', String(open)); };
    [...railLinks, ...sheetLinks].forEach(a => a.addEventListener('click', e => { e.preventDefault(); setSheet(false); go(+a.dataset.i); history.replaceState(null, '', a.hash); }));
    mainBtn.addEventListener('click', () => setSheet(sheet.hidden));
    $('.sec-pill-next', pill).addEventListener('click', () => current >= heads.length - 1 ? scrollTo({top: 0, behavior: reduce ? 'auto' : 'smooth'}) : go(current + 1));
    $('.sec-top', railEl).addEventListener('click', () => scrollTo({top: 0, behavior: reduce ? 'auto' : 'smooth'}));
    document.addEventListener('click', e => { if (!pill.contains(e.target)) setSheet(false); });

    function update() {
      const line = innerHeight * 0.38;
      let index = -1;
      heads.forEach((h, i) => { if (h.el.getBoundingClientRect().top <= line) index = i; });
      const first = heads[0].el.getBoundingClientRect().top + scrollY;
      const last = heads[heads.length - 1].el.getBoundingClientRect().top + scrollY;
      const span = Math.max(1, last - first);
      railEl.style.setProperty('--fill', Math.max(0, Math.min(1, (scrollY + line - first) / span)).toFixed(3));
      const visible = scrollY > innerHeight * 0.5;
      railEl.classList.toggle('is-on', visible);
      pill.classList.toggle('is-on', visible);
      if (index === current) return;
      const down = index > current;
      current = index;
      railLinks.forEach((a, i) => { a.classList.toggle('is-active', i === index); a.classList.toggle('is-done', i < index); });
      sheetLinks.forEach((a, i) => a.classList.toggle('is-active', i === index));
      const shown = Math.max(0, index);
      $('.sec-pill-count b', pill).textContent = pad(shown + 1);
      const label = $('.sec-pill-label', pill);
      label.textContent = heads[shown].label;
      pill.classList.remove('flip'); void pill.offsetWidth; pill.classList.add('flip');
      $('.sec-pill-next', pill).textContent = index >= heads.length - 1 ? '↑' : '↓';
      $('.sec-pill-next', pill).setAttribute('aria-label', index >= heads.length - 1 ? 'Back to top' : 'Next section: ' + (heads[index + 1]?.label || ''));
      if (index >= 0) {
        heads[index].mark?.classList.add('sec-live');
        if (started && !reduce) {
          const next = heads[index + 1];
          cue.innerHTML = `<span class="sec-cue-ball"></span><span class="sec-cue-num">${pad(index + 1)}<small>/${total}</small></span><span class="sec-cue-text"><b>${railLinks[index].querySelector('.sec-rail-label').innerHTML}</b>${next ? `<small>Next · ${railLinks[index + 1].querySelector('.sec-rail-label').innerHTML}</small>` : '<small>Last section</small>'}</span>`;
          cue.className = 'sec-cue is-on ' + (down ? 'from-below' : 'from-above');
          clearTimeout(cueTimer);
          cueTimer = setTimeout(() => cue.classList.remove('is-on'), 1900);
        }
      }
      started = true;
    }
    let queued = false;
    addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; update(); }); } }, {passive: true});
    addEventListener('resize', update);
    update();
    document.addEventListener('keydown', e => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
      if (typing || e.metaKey || e.ctrlKey || e.altKey || (palette && !palette.hidden)) return;
      if (e.key === 'j') { e.preventDefault(); go(current + 1); }
      else if (e.key === 'k') { e.preventDefault(); go(current - 1); }
      else if (e.key === 'Escape') setSheet(false);
    });
    return heads;
  })();

  /* Recently viewed profiles, scorecards and team pages feed the palette's empty state. */
  const RECENT = 'cw-recent';
  const readRecent = () => { try { return JSON.parse(localStorage.getItem(RECENT)) || []; } catch { return []; } };
  const kindOf = path => ({players: 'Player', matches: 'Match', teams: 'Team', grounds: 'Ground', series: 'Series'})[path.split('/')[1]];
  if (kindOf(location.pathname) && location.pathname.split('/').length > 3) {
    const title = ($('main h1')?.textContent || document.title.replace(/ \| Cricket Wicket$/, '')).trim();
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
      const sections = guide || [];
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
