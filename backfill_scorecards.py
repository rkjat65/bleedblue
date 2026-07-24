#!/usr/bin/env python3
"""Backfill match-level scorecards from ESPN public summary API.

Fills scorecard_cards (batting/bowling tables) and/or scorecard_totals
(innings linescores) for shells and meta-only matches. Never invents
ball-by-ball deliveries.

Usage:
  python3 dashboard/backfill_scorecards.py
  python3 dashboard/backfill_scorecards.py --max 100 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELLS = Path(__file__).resolve().parent / "shells"
REPORT = Path(__file__).resolve().parent / "scorecard_backfill_report.json"
MIN_FULL = 50
UA = {
    "User-Agent": "TeamIndiaRecords/1.0 (research; cricket.rkjat.in)",
    "Accept": "application/json",
}


def delivery_count(doc: dict) -> int:
    return sum(
        len(o.get("deliveries") or [])
        for inn in doc.get("innings") or []
        for o in inn.get("overs") or []
    )


def http_get(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def fetch_summary(league_id: str, event_id: str) -> dict | None:
    for base in ("https://site.web.api.espn.com", "https://site.api.espn.com"):
        url = f"{base}/apis/site/v2/sports/cricket/{league_id}/summary?event={event_id}"
        try:
            return http_get(url, timeout=18)
        except Exception:
            continue
    return None


def overs_to_balls(overs_val) -> int | None:
    if overs_val is None or overs_val == "":
        return None
    try:
        ov = float(overs_val)
    except (TypeError, ValueError):
        return None
    whole = int(ov)
    frac = round((ov - whole) * 10)
    return whole * 6 + frac


def parse_score_string(score: str) -> tuple[int | None, int | None]:
    """Parse '301/3d' or '387' style totals."""
    if not score:
        return None, None
    s = str(score).strip().lower().replace(" ", "")
    m = re.match(r"^(\d+)(?:/(\d+))?", s)
    if not m:
        return None, None
    runs = int(m.group(1))
    wkts = int(m.group(2)) if m.group(2) else None
    if "all out" in s or wkts == 10:
        wkts = 10
    return runs, wkts


def extract_linescore_totals(summary: dict) -> list[dict]:
    header = summary.get("header") or {}
    comps = (header.get("competitions") or [{}])[0]
    out = []
    for comp in comps.get("competitors") or []:
        team = (comp.get("team") or {}).get("displayName")
        if not team:
            continue
        score_str = comp.get("score") or ""
        for idx, ls in enumerate(comp.get("linescores") or [], start=1):
            runs = ls.get("runs")
            wkts = ls.get("wickets")
            if runs is None and ls.get("score"):
                runs, wkts = parse_score_string(ls["score"])
            if runs is None and score_str and "&" in score_str:
                parts = [p.strip() for p in score_str.split("&")]
                if idx <= len(parts):
                    runs, wkts = parse_score_string(parts[idx - 1])
            if runs is None:
                continue
            balls = overs_to_balls(ls.get("overs"))
            out.append({
                "team": team,
                "innings": idx,
                "runs": int(runs),
                "wickets": int(wkts) if wkts is not None else None,
                "balls": balls,
                "description": ls.get("description") or "",
            })
    return out


def has_scorecard_data(doc: dict) -> bool:
    info = doc.get("info") or {}
    if info.get("scorecard_cards"):
        return True
    totals = info.get("scorecard_totals") or []
    return any(t.get("runs") is not None for t in totals)


def iter_targets() -> list[Path]:
    paths: list[Path] = []
    if SHELLS.exists():
        paths.extend(sorted(SHELLS.glob("*.json")))
    for p in sorted(ROOT.glob("*.json")):
        if not p.stem.isdigit():
            continue
        doc = json.loads(p.read_text())
        if delivery_count(doc) < MIN_FULL:
            paths.append(p)
    # de-dupe by stem, prefer root over shell
    by_id: dict[str, Path] = {}
    for p in paths:
        if p.stem not in by_id or p.parent == ROOT:
            by_id[p.stem] = p
    return sorted(by_id.values(), key=lambda x: x.stem)


def backfill_file(path: Path, dry_run: bool = False) -> dict:
    doc = json.loads(path.read_text())
    meta = doc.setdefault("meta", {})
    info = doc.setdefault("info", {})
    balls = delivery_count(doc)
    if balls >= MIN_FULL:
        return {"id": path.stem, "action": "skip_full", "deliveries": balls}

    eid = meta.get("espn_event_id") or path.stem
    lid = meta.get("espn_league_id")
    if not lid:
        return {"id": path.stem, "action": "skip_no_league"}

    summary = fetch_summary(str(lid), str(eid))
    if not summary:
        return {"id": path.stem, "action": "fetch_failed"}

    cards = summary.get("matchcards") or []
    totals = extract_linescore_totals(summary)
    changed = False
    action_parts = []

    if cards and not info.get("scorecard_cards"):
        info["scorecard_cards"] = cards
        changed = True
        action_parts.append("cards")

    if totals and not info.get("scorecard_totals"):
        info["scorecard_totals"] = totals
        changed = True
        action_parts.append("totals")

    # Refresh rosters / outcome when sparse
    if not info.get("players"):
        players = {}
        for roster in summary.get("rosters") or []:
            team = (roster.get("team") or {}).get("displayName")
            if not team:
                continue
            names = [
                ((p.get("athlete") or {}).get("displayName") or (p.get("athlete") or {}).get("fullName"))
                for p in (roster.get("roster") or [])
            ]
            names = [n for n in names if n]
            if names:
                players[team] = names
        if players:
            info["players"] = players
            changed = True
            action_parts.append("xi")

    if not changed:
        return {"id": path.stem, "action": "unchanged", "cards": len(cards), "totals": len(totals)}

    meta["quality"] = "scorecard-only"
    meta["scorecard_source"] = "espn-summary-api"
    meta["analytics_excluded"] = True
    meta["note"] = (
        "Match-level scorecard from ESPN public summary — no ball-by-ball; "
        "excluded from W/L and player aggregates"
    )
    if not dry_run:
        path.write_text(json.dumps(doc, indent=1))
    return {
        "id": path.stem,
        "action": "filled_" + "+".join(action_parts),
        "cards": len(cards),
        "totals": len(totals),
        "path": str(path.relative_to(ROOT.parent)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="Max files to process (0=all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.06)
    args = ap.parse_args()

    targets = iter_targets()
    # Prioritize files without any scorecard data
    def priority(p: Path) -> tuple[int, str]:
        doc = json.loads(p.read_text())
        return (0 if has_scorecard_data(doc) else 1, p.stem)

    targets.sort(key=priority, reverse=True)
    if args.max:
        targets = targets[: args.max]

    print(f"Backfilling scorecards for up to {len(targets)} files...", flush=True)
    report = {"filled": [], "unchanged": 0, "failed": 0, "skipped": 0, "actions": {}}
    for i, path in enumerate(targets):
        if i and i % 50 == 0:
            print(f"  {i}/{len(targets)}", flush=True)
        try:
            rec = backfill_file(path, dry_run=args.dry_run)
        except Exception as e:
            report["failed"] += 1
            print(f"  ERR {path.stem}: {e}", flush=True)
            time.sleep(args.sleep)
            continue
        act = rec.get("action", "?")
        report["actions"][act] = report["actions"].get(act, 0) + 1
        if act.startswith("filled"):
            report["filled"].append(rec)
            print(f"  OK {path.stem} {act} cards={rec.get('cards',0)} totals={rec.get('totals',0)}", flush=True)
        elif act == "unchanged":
            report["unchanged"] += 1
        else:
            report["skipped"] += 1
        time.sleep(args.sleep)

    report["summary"] = {
        "targets": len(targets),
        "filled_count": len(report["filled"]),
        "with_cards": sum(1 for r in report["filled"] if r.get("cards")),
        "with_totals_only": sum(1 for r in report["filled"] if r.get("totals") and not r.get("cards")),
    }
    if not args.dry_run:
        REPORT.write_text(json.dumps(report, indent=2))
        print(f"Report: {REPORT}", flush=True)
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
