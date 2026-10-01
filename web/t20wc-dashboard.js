(() => {
  const root = document.querySelector('#wc-dashboard');
  if (!root) return;
  const status = document.querySelector('#wc-status');
  const editionSelect = document.querySelector('#wc-edition');
  const fmt = new Intl.NumberFormat('en-IN');
  let payload;
  let index;
  const sorts = { batting: ['runs', false], bowling: ['wickets', false] };

  const value = (row, key) => row[index[key]];
  const safeRate = (top, bottom, factor = 1) => bottom ? top * factor / bottom : null;
  const number = n => fmt.format(Math.round(n || 0));
  const decimal = n => n == null || !Number.isFinite(n) ? '-' : n.toFixed(2);
  const setText = (selector, text) => { const node = document.querySelector(selector); if (node) node.textContent = text; };

  function inningsKey(row) { return `${value(row, 'match_id')}|${value(row, 'innings')}`; }
  function playerInningsKey(row, player) { return `${inningsKey(row)}|${player}`; }

  function aggregate(deliveries, matches) {
    const innings = new Map();
    const batting = new Map();
    const bowling = new Map();
    const phaseDefs = [
      ['Powerplay', 'Overs 1 to 6', over => over < 6],
      ['Middle overs', 'Overs 7 to 15', over => over >= 6 && over < 15],
      ['Death overs', 'Overs 16 to 20', over => over >= 15],
    ];
    const phases = phaseDefs.map(([name, label]) => ({ name, label, runs: 0, balls: 0, dots: 0, boundaries: 0, wickets: 0 }));
    const batterInnings = new Map();
    const bowlerInnings = new Map();

    deliveries.forEach(row => {
      const key = inningsKey(row);
      const inn = innings.get(key) || { match: value(row, 'match_id'), number: value(row, 'innings'), team: value(row, 'batting_team'), runs: 0, wickets: 0 };
      inn.runs += value(row, 'total_runs');
      inn.wickets += value(row, 'wicket') ? 1 : 0;
      innings.set(key, inn);

      const batter = value(row, 'batter');
      if (batter) {
        const stat = batting.get(batter) || { name: batter, runs: 0, balls: 0, dismissals: 0, fours: 0, sixes: 0, fifties: 0, hundreds: 0 };
        stat.runs += value(row, 'batter_runs');
        stat.balls += value(row, 'batter_ball') ? 1 : 0;
        stat.fours += value(row, 'batter_runs') === 4 ? 1 : 0;
        stat.sixes += value(row, 'batter_runs') === 6 ? 1 : 0;
        batting.set(batter, stat);
        const bik = playerInningsKey(row, batter);
        batterInnings.set(bik, (batterInnings.get(bik) || 0) + value(row, 'batter_runs'));
      }
      const dismissed = value(row, 'player_out');
      if (dismissed && value(row, 'wicket_kind') !== 'retired hurt') {
        const stat = batting.get(dismissed) || { name: dismissed, runs: 0, balls: 0, dismissals: 0, fours: 0, sixes: 0, fifties: 0, hundreds: 0 };
        stat.dismissals += 1;
        batting.set(dismissed, stat);
      }

      const bowler = value(row, 'bowler');
      if (bowler) {
        const stat = bowling.get(bowler) || { name: bowler, wickets: 0, runs: 0, balls: 0, fourW: 0, fiveW: 0 };
        stat.wickets += value(row, 'bowler_wicket') ? 1 : 0;
        stat.runs += value(row, 'bowler_runs');
        stat.balls += value(row, 'legal') ? 1 : 0;
        bowling.set(bowler, stat);
        const bok = playerInningsKey(row, bowler);
        const spell = bowlerInnings.get(bok) || { bowler, wickets: 0 };
        spell.wickets += value(row, 'bowler_wicket') ? 1 : 0;
        bowlerInnings.set(bok, spell);
      }

      const over = value(row, 'over');
      const phaseIndex = phaseDefs.findIndex(([, , test]) => test(over));
      if (phaseIndex >= 0) {
        const phase = phases[phaseIndex];
        phase.runs += value(row, 'total_runs');
        phase.wickets += value(row, 'wicket') ? 1 : 0;
        if (value(row, 'legal')) {
          phase.balls += 1;
          phase.dots += value(row, 'total_runs') === 0 ? 1 : 0;
          phase.boundaries += [4, 6].includes(value(row, 'batter_runs')) ? 1 : 0;
        }
      }
    });

    batterInnings.forEach((runs, key) => {
      const name = key.split('|').slice(2).join('|');
      const stat = batting.get(name);
      if (runs >= 100) stat.hundreds += 1;
      else if (runs >= 50) stat.fifties += 1;
    });
    bowlerInnings.forEach(spell => {
      const stat = bowling.get(spell.bowler);
      if (spell.wickets >= 5) stat.fiveW += 1;
      else if (spell.wickets >= 4) stat.fourW += 1;
    });
    batting.forEach(stat => {
      stat.average = safeRate(stat.runs, stat.dismissals);
      stat.strikeRate = safeRate(stat.runs, stat.balls, 100);
    });
    bowling.forEach(stat => {
      stat.average = safeRate(stat.runs, stat.wickets);
      stat.economy = safeRate(stat.runs, stat.balls, 6);
      stat.strikeRate = safeRate(stat.balls, stat.wickets);
    });

    const wins = new Map();
    matches.forEach(match => { if (match.winner) wins.set(match.winner, (wins.get(match.winner) || 0) + 1); });
    return { innings: [...innings.values()], batting: [...batting.values()], bowling: [...bowling.values()], phases, wins };
  }

  function renderBars(target, entries, maximumRows = 10) {
    const node = document.querySelector(target);
    const rows = entries.sort((a, b) => b[1] - a[1]).slice(0, maximumRows);
    const max = Math.max(...rows.map(row => row[1]), 1);
    node.innerHTML = rows.map(([label, count]) => `<div class="wc-bar-row"><span title="${label}">${label}</span><div><i style="width:${count / max * 100}%"></i></div><strong>${count}</strong></div>`).join('');
  }

  function renderTable(id, rows, columns, sortState) {
    const [key, ascending] = sorts[sortState];
    const sorted = [...rows].sort((a, b) => {
      const left = a[key] == null ? (ascending ? '\uffff' : -Infinity) : a[key];
      const right = b[key] == null ? (ascending ? '\uffff' : -Infinity) : b[key];
      return typeof left === 'string' ? left.localeCompare(right) * (ascending ? 1 : -1) : (left - right) * (ascending ? 1 : -1);
    }).slice(0, 15);
    document.querySelector(`${id} tbody`).innerHTML = sorted.map(row => `<tr>${columns.map(([field, format]) => `<td>${format ? format(row[field]) : row[field]}</td>`).join('')}</tr>`).join('');
  }

  function renderSuperOvers(deliveries, matches) {
    const matchMap = new Map(matches.map(match => [match.id, match]));
    const innings = new Map();
    deliveries.filter(row => value(row, 'super_over')).forEach(row => {
      const key = inningsKey(row);
      const item = innings.get(key) || { matchId: value(row, 'match_id'), team: value(row, 'batting_team'), runs: 0, wickets: 0, balls: 0 };
      item.runs += value(row, 'total_runs');
      item.wickets += value(row, 'wicket') ? 1 : 0;
      item.balls += value(row, 'legal') ? 1 : 0;
      innings.set(key, item);
    });
    const grouped = new Map();
    innings.forEach(item => {
      const list = grouped.get(item.matchId) || [];
      list.push(item);
      grouped.set(item.matchId, list);
    });
    const cards = [...grouped.entries()].map(([matchId, scores]) => ({ match: matchMap.get(matchId), scores })).filter(item => item.match).sort((a, b) => b.match.date.localeCompare(a.match.date));
    const target = document.querySelector('#wc-super-overs');
    target.innerHTML = cards.length ? cards.map(({ match, scores }) => `<article class="wc-super"><span>${match.date} · ${match.edition}</span><h3>${match.teams.join(' v ')}</h3><div>${scores.map(score => `<p><strong>${score.team}</strong><b>${score.runs}/${score.wickets}</b><small>${score.balls} legal balls</small></p>`).join('')}</div><em>${match.winner} won the Super Over</em></article>`).join('') : '<p class="muted">No Super Over was played in this edition.</p>';
  }

  function render() {
    const edition = editionSelect.value;
    const matches = payload.matches.filter(match => edition === 'all' || String(match.edition) === edition);
    const matchIds = new Set(matches.map(match => match.id));
    const allDeliveries = payload.deliveries.filter(row => matchIds.has(value(row, 'match_id')));
    const deliveries = allDeliveries.filter(row => !value(row, 'super_over'));
    const stats = aggregate(deliveries, matches);
    const runs = deliveries.reduce((sum, row) => sum + value(row, 'total_runs'), 0);
    const wickets = deliveries.filter(row => value(row, 'wicket')).length;
    const fours = deliveries.filter(row => value(row, 'batter_runs') === 4).length;
    const sixes = deliveries.filter(row => value(row, 'batter_runs') === 6).length;
    const highest = [...stats.innings].sort((a, b) => b.runs - a.runs)[0];
    const topSixes = [...stats.batting].sort((a, b) => b.sixes - a.sixes)[0];
    const topFours = [...stats.batting].sort((a, b) => b.fours - a.fours)[0];
    const topWickets = [...stats.bowling].sort((a, b) => b.wickets - a.wickets)[0];

    const kpis = { matches: matches.length, runs, wickets, boundaries: fours + sixes, average: safeRate(runs, stats.innings.length), sixes };
    Object.entries(kpis).forEach(([key, val]) => setText(`[data-kpi="${key}"]`, key === 'average' ? decimal(val) : number(val)));
    setText('[data-spot="total"]', highest ? `${highest.runs}/${highest.wickets}` : '-');
    setText('[data-spot-note="total"]', highest ? highest.team : '');
    setText('[data-spot="sixes"]', topSixes ? topSixes.name : '-');
    setText('[data-spot-note="sixes"]', topSixes ? `${topSixes.sixes} sixes` : '');
    setText('[data-spot="fours"]', topFours ? topFours.name : '-');
    setText('[data-spot-note="fours"]', topFours ? `${topFours.fours} fours` : '');
    setText('[data-spot="wickets"]', topWickets ? topWickets.name : '-');
    setText('[data-spot-note="wickets"]', topWickets ? `${topWickets.wickets} wickets` : '');

    renderBars('#wc-team-wins', [...stats.wins.entries()]);
    renderBars('#wc-titles', Object.entries(payload.titles), 8);
    renderSuperOvers(allDeliveries, matches);
    document.querySelector('#wc-phases').innerHTML = stats.phases.map(phase => `<article class="wc-phase"><span>${phase.label}</span><h3>${phase.name}</h3><dl><dt>Run rate</dt><dd>${decimal(safeRate(phase.runs, phase.balls, 6))}</dd><dt>Dot-ball rate</dt><dd>${decimal(safeRate(phase.dots, phase.balls, 100))}%</dd><dt>Boundary rate</dt><dd>${decimal(safeRate(phase.boundaries, phase.balls, 100))}%</dd><dt>Wickets</dt><dd>${number(phase.wickets)}</dd></dl></article>`).join('');

    renderTable('#wc-batting', stats.batting, [['name'], ['runs', number], ['average', decimal], ['strikeRate', decimal], ['fifties', number], ['hundreds', number], ['sixes', number]], 'batting');
    renderTable('#wc-bowling', stats.bowling, [['name'], ['wickets', number], ['average', decimal], ['economy', decimal], ['strikeRate', decimal], ['fourW', number], ['fiveW', number]], 'bowling');

    const recent = [...matches].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 12);
    document.querySelector('#wc-matches').innerHTML = recent.map(match => `<article class="wc-match"><span>${match.date} · ${match.edition}</span><h3>${match.teams.join(' v ')}</h3><p>${match.venue || 'Venue not recorded'}</p><strong>${match.winner ? `${match.winner} won${match.decided_by ? ` · ${match.decided_by}` : ''}` : 'No result'}</strong></article>`).join('');
    setText('#wc-match-count', `${matches.length} matches`);
    const noPlay = payload.gaps.filter(gap => gap.reason === 'no play').length;
    setText('#wc-coverage-note', `${payload.meta.fixtures} scheduled tournament fixtures are recorded: ${payload.meta.matches} played matches contain ${number(payload.meta.regulation_deliveries)} regulation deliveries plus ${number(payload.meta.super_over_deliveries)} Super Over deliveries across ${payload.meta.super_over_matches} tied matches; ${noPlay} no-play fixtures correctly contain no deliveries. ${payload.reconciliation.length} Afghanistan matches were independently reconciled.`);
    status.textContent = `${edition === 'all' ? 'All editions' : edition} · ${matches.length} matches`;
  }

  function bindSort(tableId, state) {
    document.querySelectorAll(`${tableId} th[data-key]`).forEach(th => th.addEventListener('click', () => {
      const current = sorts[state];
      sorts[state] = [th.dataset.key, current[0] === th.dataset.key ? !current[1] : th.dataset.key === 'name'];
      render();
    }));
  }

  fetch(root.dataset.source).then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).then(data => {
    payload = data;
    index = Object.fromEntries(payload.fields.map((field, i) => [field, i]));
    payload.meta.editions.forEach(year => editionSelect.insertAdjacentHTML('beforeend', `<option value="${year}">${year}</option>`));
    editionSelect.addEventListener('change', render);
    bindSort('#wc-batting', 'batting');
    bindSort('#wc-bowling', 'bowling');
    render();
  }).catch(error => {
    status.textContent = 'Dataset could not be loaded';
    root.innerHTML = `<p class="wc-load-error">The dashboard data could not be loaded (${error.message}). Please refresh the page.</p>`;
  });
})();
