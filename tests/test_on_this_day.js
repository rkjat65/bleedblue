const assert = require('node:assert/strict');
const {indiaKey, calendarPath} = require('../web/on-this-day.js');
assert.equal(indiaKey(new Date('2026-09-15T18:29:59Z')), '09-15');
assert.equal(indiaKey(new Date('2026-09-15T18:30:00Z')), '09-16');
assert.equal(indiaKey(new Date('2026-12-31T18:30:00Z')), '01-01');
assert.equal(calendarPath(2,29), '/on-this-day/february-29/');
assert.equal(calendarPath(2,30), null);
assert.equal(calendarPath(4,31), null);
assert.equal(calendarPath(13,1), null);
console.log('India midnight, year rollover, leap-day and invalid date checks passed.');
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  let now = '2026-09-15T18:29:59Z', tick, requests = 0, offline = false;
  const panel = {dataset:{otdKey:'09-14',otdLive:'home'},innerHTML:'14 September',querySelector(){return null;}};
  const context = {
    Intl,
    Date: class extends Date { constructor(...args){super(...(args.length ? args : [now]));} },
    document:{querySelectorAll(){return [panel];},addEventListener(){}},
    setInterval(fn){tick=fn;},
    fetch:async () => {requests++;if(offline)throw new Error('Offline');return {ok:true,json:async()=>({key:indiaKey(new Date(now)),home:indiaKey(new Date(now))})};}
  };
  vm.runInNewContext(fs.readFileSync('web/on-this-day.js','utf8'),context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(panel.dataset.otdKey,'09-15','Stale server HTML updates to the current India date');
  await tick();
  assert.equal(requests,1,'Clock ticks do not fetch repeatedly on the same day');
  now='2026-09-15T18:30:00Z';
  await tick();
  assert.equal(panel.innerHTML,'09-16','Open pages update after midnight IST');
  offline=true;now='2026-09-16T18:30:00Z';
  await tick();
  assert.equal(panel.dataset.otdKey,'09-16','Network failure preserves the explicitly dated card');
  offline=false;await tick();
  assert.equal(panel.dataset.otdKey,'09-17','A later tick recovers after a network failure');
  console.log('Live rollover, no redundant fetches, and offline recovery passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
