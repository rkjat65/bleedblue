"""Validate the bundled archive and write a public coverage manifest."""
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent


def audit(data):
    matches = data['matches']
    ids = [str(m['id']) for m in matches]
    assert len(ids) == len(set(ids)), 'Duplicate match IDs'
    assert len(matches) == data['meta']['matches'], 'Catalog count mismatch'
    included = [m for m in matches if m.get('in_analytics_set')]
    assert len(included) == data['overall']['played'], 'Analytics count mismatch'
    assert all(m['quality'] == 'full' for m in included), 'Incomplete matches in analytics'
    assert sum(data['overall'].get(k, 0) for k in ('won', 'lost', 'draw', 'tied', 'nr')) == len(included)
    for fmt, totals in data['by_format'].items():
        assert totals['played'] == sum(m['format'] == fmt for m in included), f'{fmt} count mismatch'
    return {
        'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'generated_at': data['meta']['generated'],
        'latest_match': max(m['date'] for m in matches),
        'earliest_match': min(m['date'] for m in matches),
        'catalog_matches': len(matches),
        'analytics_matches': len(included),
        'quality': dict(Counter(m['quality'] for m in matches)),
        'players': len(set(p['name'] for p in data['batting'] + data['bowling'])),
        'source': 'https://cricsheet.org/',
        'live_scores': False,
        'complete_historical_coverage': False,
        'note': 'Archive statistics cover available ball data, not complete career totals. Legacy recovered entries retain their original source labels.'
    }


if __name__ == '__main__':
    report = audit(json.loads((ROOT / 'stats.json').read_text(encoding='utf-8')))
    (ROOT / 'data_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
