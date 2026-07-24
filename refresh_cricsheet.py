#!/usr/bin/env python3
"""Refresh India male international JSON from Cricsheet.

Downloads india_male_json.zip, merges into the Team India folder.
When a file already exists, keeps whichever copy has more ball-by-ball deliveries.

Usage:
  python3 dashboard/refresh_cricsheet.py
  python3 refresh_cricsheet.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_URL = "https://cricsheet.org/downloads/india_male_json.zip"
MIN_FULL = 50


def delivery_count(doc: dict) -> int:
    return sum(
        len(o.get("deliveries") or [])
        for inn in doc.get("innings") or []
        for o in inn.get("overs") or []
    )


def merge_file(src: Path, dest: Path) -> str:
    new_doc = json.loads(src.read_text())
    new_balls = delivery_count(new_doc)
    if not dest.exists():
        dest.write_text(json.dumps(new_doc, indent=1))
        return "added" if new_balls >= MIN_FULL else "added_shell"
    try:
        old_doc = json.loads(dest.read_text())
    except Exception:
        old_doc = {}
    old_balls = delivery_count(old_doc)
    if new_balls > old_balls:
        dest.write_text(json.dumps(new_doc, indent=1))
        return "upgraded" if new_balls >= MIN_FULL else "upgraded_partial"
    return "kept_existing"


def main():
    print(f"Downloading {ZIP_URL} ...", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "india_male_json.zip"
        urllib.request.urlretrieve(ZIP_URL, zpath)
        print(f"  saved {zpath.stat().st_size / 1024 / 1024:.1f} MB", flush=True)
        counts = {"added": 0, "added_shell": 0, "upgraded": 0, "upgraded_partial": 0, "kept_existing": 0}
        with zipfile.ZipFile(zpath) as zf:
            names = [n for n in zf.namelist() if n.endswith(".json")]
            print(f"Extracting {len(names)} Cricsheet files into {ROOT} ...", flush=True)
            for i, name in enumerate(names):
                if i and i % 200 == 0:
                    print(f"  {i}/{len(names)}", flush=True)
                stem = Path(name).stem
                if not stem.isdigit():
                    continue
                zf.extract(name, tmp)
                action = merge_file(Path(tmp) / name, ROOT / f"{stem}.json")
                counts[action] = counts.get(action, 0) + 1
    print("Merge summary:", json.dumps(counts, indent=2), flush=True)
    report = Path(__file__).resolve().parent / "cricsheet_refresh_report.json"
    report.write_text(json.dumps({"url": ZIP_URL, "counts": counts}, indent=2))
    print(f"Report: {report}", flush=True)


if __name__ == "__main__":
    main()
