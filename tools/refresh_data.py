"""Refresh into an isolated staging checkout; preserve current data on failure."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def counts(root):
    def load(name):
        return json.loads((root / 'data' / name).read_text(encoding='utf-8'))
    archive, careers, history = [load(x) for x in ('international.json', 'careers.json', 'historical_matches.json')]
    return {'archive_matches': len(archive['matches']), 'career_players': len(careers['players']),
            'all_matches': len(archive['matches']) + len(history['matches'])}


def main():
    before = counts(ROOT)
    with tempfile.TemporaryDirectory(prefix='cricket-wicket-refresh-') as work:
        stage = Path(work)
        shutil.copytree(ROOT / 'tools', stage / 'tools')
        shutil.copytree(ROOT / 'data',stage / 'data')
        shutil.copytree(ROOT / 'web', stage / 'web')
        for script, flags in [('build_international.py', ['--refresh']),
                              ('import_careers.py', ['--refresh']),
                              ('import_match_catalog.py', []), ('build_record_layers.py', [])]:
            subprocess.run([sys.executable, str(stage / 'tools' / script), *flags], check=True, cwd=stage)
        for report, expected in [('career_import_report.json', 18), ('match_import_report.json', 6)]:
            scopes = json.loads((stage / 'data' / report).read_text())['scopes']
            if len(scopes) != expected or not all(s.get('complete') for s in scopes):
                raise RuntimeError(f'Incomplete source import: {report}. Current data retained.')
        # Reuse verified historical data and refresh only absent/stale summaries.
        sys.path.insert(0,str(stage/'tools'))
        from backfill_free_data import write
        from import_careers import CLASSES
        people={p['id']:p for p in json.loads((stage/'data/careers.json').read_text(encoding='utf-8'))['players']}
        for r in json.loads((stage/'data/career_enrichment.json').read_text(encoding='utf-8'))['records']:
            if r['id'] not in people:continue
            cls=next(k for k,v in CLASSES.items() if v==(r['format'],people[r['id']]['gender']))
            write(stage/'.data-cache/free-backfill/careers'/f'{r["espn_id"]}-{cls}.json',r)
        for r in json.loads((stage/'data/bowling_enrichment.json').read_text(encoding='utf-8'))['records']:
            if r['id'] not in people:continue
            cls=next(k for k,v in CLASSES.items() if v==(r['format'],people[r['id']]['gender']))
            write(stage/'.data-cache/free-backfill/bowling'/f'{r["espn_id"]}-{cls}.json',r)
        for file in (stage/'data/historical_scorecards').glob('*.json'):
            for mid,c in json.loads(file.read_text(encoding='utf-8')).items():write(stage/'.data-cache/free-backfill/scorecards'/f'{mid}.json',c)
        for script,args in [('backfill_free_data.py',['careers','--workers','3']),('backfill_free_data.py',['bowling','--workers','3']),('backfill_free_data.py',['scorecards','--workers','3']),('reconcile_careers.py',[]),('backfill_grounds.py',[])]:
            subprocess.run([sys.executable,str(stage/'tools'/script),*args],cwd=stage,check=True)
        after = counts(stage)
        for key, value in before.items():
            if after[key] < value * .99:
                raise RuntimeError(f'Suspicious decrease in {key}: {value} -> {after[key]}. Current data retained.')
        shutil.copytree(ROOT / 'tests', stage / 'tests')
        # Only data tests run here. Publication audit runs after the complete build.
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], cwd=stage, check=True)
        report = {'before': before, 'after': after, 'validated': True}
        (stage / 'data' / 'refresh_report.json').write_text(json.dumps(report, indent=2))
        # Each file replacement is atomic. Live publication happens only after the later build audit passes.
        for source in (stage / 'data').rglob('*.json'):
            target = ROOT / 'data' / source.relative_to(stage / 'data')
            target.parent.mkdir(parents=True, exist_ok=True)
            pending = target.with_suffix('.json.pending')
            shutil.copy2(source, pending)
            pending.replace(target)
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
