const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('record-layers.js', 'utf8'), context);
const {careerStats, merge} = context.window.RecordLayers;
const player = {career: {
  Test: {matches: 10, runs: 1000, outs: 20, balls: null, wickets: 10, conceded: 300, legal: 600},
  ODI: {matches: 5, runs: 200, outs: 4, balls: 250, wickets: 2, conceded: 100, legal: 120}
}};
const all = careerStats(player);
assert.equal(all.matches, 15);
assert.equal(all.runs, 1200);
assert.equal(all.avg, 50);
assert.equal(all.bowlAvg, 33.33);
assert.equal(all.econ, 3.33);
assert.equal(all.balls, null);
assert.equal(all.sr, null);
assert.equal(careerStats(player, 'T20I'), null);
assert.equal(careerStats(player, 'ODI').runs, 200);
const archive = {meta: {matches: 1, first: '2001-01-01', last: '2026-01-01', teams: ['India'], gender: {Men: 1}}, players: [{id: 'a', formats: {Test: {runs: 99}}}], matches: [{id: '1', date: '2001-01-01'}]};
const merged = merge(archive, {players: [{id: 'a', espn_id: '99', formats: player.career}, {id: 'espn-1', formats: {Test: {runs: 50}}}], meta: {combined_players: 2}}, {meta: {added_matches: 1, first: '1877-03-15', last: '1877-03-15', teams: ['England'], gender: {Men: 1}}, matches: [{id: '1', date: '2001-01-01'}, {id: '2', date: '1877-03-15'}]});
assert.equal(merged.matches.length, 2);
assert.equal(merged.players.length, 2);
assert.equal(merged.players[0].formats.Test.runs, 99);
assert.equal(careerStats(merged.players[0], 'Test').runs, 1000);
assert.equal(Object.keys(merged.players[1].formats).length, 0);
assert.equal(merged.meta.matches, 2);
assert.equal(merged.archiveMeta.matches, 1);
assert.equal(merged.meta.first, '1877-03-15');
console.log('Record-layer calculations, null handling, joins and deduplication passed.');
