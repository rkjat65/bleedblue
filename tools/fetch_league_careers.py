"""Fetch IPL and T20 World Cup data from the analytics app.

The app builds it from Cricsheet ball-by-ball data and keys every player by
the Cricsheet registry id, the same id as data/careers.json. Files:

  data/leagues/ipl.json, t20wc.json   player careers (profile tabs)
  data/leagues/ipl-venues.json        IPL grounds (ground tabs)
  data/leagues/t20wc-teams.json       T20 World Cup teams (team tabs)

Each snapshot is checked before it replaces the committed one; on any failure
the current file stays, so a refresh never loses the tabs.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'data' / 'leagues'
SOURCE = 'https://crickrida.com/api/export/{kind}?tournament={slug}'
# (slug, kind, file, collection, minimum entries, a key that must be present)
SNAPSHOTS = (
    ('ipl', 'careers', 'ipl.json', 'players', 500, 'ba607b88'),
    ('t20wc', 'careers', 't20wc.json', 'players', 500, 'ba607b88'),
    ('ipl', 'venues', 'ipl-venues.json', 'venues', 20, 'Wankhede Stadium, Mumbai'),
    ('t20wc', 'teams', 't20wc-teams.json', 'teams', 15, 'India'),
)


def fetch(slug, kind):
    req = urllib.request.Request(SOURCE.format(kind=kind, slug=slug), headers={'User-Agent': 'crickrida-archive/1.0'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode('utf-8'))


def problem(data, slug, collection, minimum, probe, previous):
    meta, items = data.get('meta') or {}, data.get(collection) or {}
    if meta.get('tournament') != slug or len(items) < minimum:
        return f'unexpected export: tournament={meta.get("tournament")} {collection}={len(items)}'
    if probe not in items:
        return f'{probe} missing'
    if previous.exists():
        old = json.loads(previous.read_text(encoding='utf-8'))
        if len(items) < len(old.get(collection) or {}) * 0.99 or meta.get('matches', 0) < (old.get('meta') or {}).get('matches', 0):
            return 'export shrank; keeping the current snapshot'
    return None


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for slug, kind, name, collection, minimum, probe in SNAPSHOTS:
        target = DEST / name
        try:
            data = fetch(slug, kind)
            issue = problem(data, slug, collection, minimum, probe, target)
        except Exception as exc:  # noqa: BLE001 - network or JSON failure keeps the snapshot
            issue = f'{type(exc).__name__}: {exc}'
        if issue:
            print(f'{name}: {issue}. Current snapshot retained.', file=sys.stderr)
            if not target.exists():
                sys.exit(1)
            continue
        pending = target.with_suffix('.json.pending')
        pending.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')
        pending.replace(target)
        print(f'{name}: {len(data[collection]):,} {collection}, {data["meta"]["matches"]:,} matches to {data["meta"]["last"]}')


if __name__ == '__main__':
    main()
