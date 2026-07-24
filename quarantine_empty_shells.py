#!/usr/bin/env python3
"""Move empty ESPN meta shells out of the analytics match folder.

Existing ESPN-recovered files with no ball-by-ball are relocated to
dashboard/shells/ so the Team India root holds Cricsheet-quality data only.
Catalog pages still list shells via build_stats scanning (optional re-import).

Usage:
  python3 dashboard/quarantine_empty_shells.py
  python3 dashboard/quarantine_empty_shells.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELLS = Path(__file__).resolve().parent / "shells"
MIN_FULL = 50


def delivery_count(doc: dict) -> int:
    return sum(
        len(o.get("deliveries") or [])
        for inn in doc.get("innings") or []
        for o in inn.get("overs") or []
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    SHELLS.mkdir(exist_ok=True)
    moved = kept = 0
    for path in sorted(ROOT.glob("*.json")):
        if not path.stem.isdigit():
            continue
        doc = json.loads(path.read_text())
        balls = delivery_count(doc)
        src = (doc.get("meta") or {}).get("source", "")
        if balls >= MIN_FULL or "espn" not in src:
            kept += 1
            continue
        dest = SHELLS / path.name
        if args.dry_run:
            print(f"would move {path.name} -> shells/ (dels={balls})")
        else:
            shutil.move(str(path), str(dest))
        moved += 1
    print(f"Moved {moved} empty ESPN shells; kept {kept} analytics-ready files in root")


if __name__ == "__main__":
    main()
