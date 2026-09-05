/* Career snapshots and delivery-derived statistics are intentionally independent. */
(() => {
  'use strict';
  const sum = (rows, key) => rows.length && rows.every(r => r[key] != null) ? rows.reduce((n, r) => n + Number(r[key]), 0) : null;
  const ratio = (a, b, factor = 1) => a != null && b > 0 ? Number((a / b * factor).toFixed(2)) : null;
  function careerStats(player, format = 'all') {
    const formats = player.career || {};
    const rows = format === 'all' ? Object.values(formats) : [formats[format]].filter(Boolean);
    if (!rows.length) return null;
    if (rows.length === 1) return {...rows[0]};
    const total = {};
    for (const key of ['matches', 'innings', 'runs', 'balls', 'outs', 'notouts', 'fours', 'sixes', 'hundreds', 'fifties', 'ducks', 'wickets', 'conceded', 'legal', 'catches', 'stumpings', 'five_w', 'ten_w']) total[key] = sum(rows, key);
    total.highest = rows.every(r => r.highest != null) ? Math.max(...rows.map(r => r.highest)) : null;
    if (total.highest != null) total.highest_display = rows.filter(r => r.highest === total.highest).sort((a, b) => Number(String(b.highest_display).endsWith('*')) - Number(String(a.highest_display).endsWith('*')))[0].highest_display;
    const bowling = rows.map(r => r.best_bowling).filter(v => /^\d+\/\d+$/.test(v || ''));
    if (bowling.length) total.best_bowling = bowling.sort((a, b) => {const [aw, ar] = a.split('/').map(Number), [bw, br] = b.split('/').map(Number); return bw - aw || ar - br;})[0];
    total.avg = ratio(total.runs, total.outs);
    total.sr = ratio(total.runs, total.balls, 100);
    total.bowlAvg = ratio(total.conceded, total.wickets);
    total.econ = ratio(total.conceded, total.legal, 6);
    total.bowlSr = ratio(total.legal, total.wickets);
    for (const key of ['bowling_innings', 'maidens', 'four_w', 'fielding_innings', 'dismissals', 'keeper_catches', 'fielder_catches']) total[key] = sum(rows, key);
    total.dismissals_per_innings = ratio(total.dismissals, total.fielding_innings);
    total.match_count_conflict = rows.some(r => r.match_count_conflict);
    return total;
  }
  function merge(archive, careers, history) {
    archive.archiveMeta = {...archive.meta};
    archive.careerMeta = careers?.meta || null;
    archive.historyMeta = history?.meta || null;
    const people = new Map(archive.players.map(p => [p.id, {...p}]));
    for (const record of careers?.players || []) {
      const p = people.get(record.id) || {...record, formats: {}, first: '', last: ''};
      p.career = record.formats;
      p.espn_id = record.espn_id;
      p.source_name = record.source_name;
      p.careerFirst = record.first;
      p.careerLast = record.last;
      people.set(record.id, p);
    }
    archive.players = [...people.values()];
    archive.meta.players = careers?.meta?.combined_players || people.size;
    const known = new Set(archive.matches.map(m => m.id));
    archive.matches.push(...(history?.matches || []).filter(m => !known.has(m.id)));
    archive.matches.sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
    if (history?.meta) {
      if (history.meta.format_summary) archive.format_summary = history.meta.format_summary;
      archive.meta.matches = archive.archiveMeta.matches + history.meta.added_matches;
      archive.meta.first = history.meta.first && history.meta.first < archive.meta.first ? history.meta.first : archive.meta.first;
      archive.meta.last = history.meta.last && history.meta.last > archive.meta.last ? history.meta.last : archive.meta.last;
      archive.meta.teams = [...new Set([...archive.meta.teams, ...(history.meta.teams || [])])].sort();
      archive.meta.gender = {...archive.meta.gender};
      for (const [gender, count] of Object.entries(history.meta.gender || {})) archive.meta.gender[gender] = (archive.meta.gender[gender] || 0) + count;
    }
    return archive;
  }
  window.RecordLayers = {careerStats, merge};
})();
