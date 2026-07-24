#!/usr/bin/env python3
"""
Fetch as many missing Team India internationals as possible from ESPN public APIs.
Writes Cricsheet-compatible JSON into the Team India folder.

Strategy:
  1. Discover India-related series (leagues) via ESPN search
  2. Pull scoreboard events + expand nearby event IDs
  3. For each India match not already on disk, download summary + full play-by-play
  4. Convert using the shared ESPN→Cricsheet converter

Usage:
  python3 fetch_missing_india.py
  python3 fetch_missing_india.py --max-new 50
  python3 fetch_missing_india.py --leagues-only   # discovery only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_afg_matches import (  # noqa: E402
    convert_to_cricsheet,
    fetch_all_balls,
    http_get,
    is_ind_afg,
)

OUT_DIR = ROOT
SHELLS_DIR = Path(__file__).resolve().parent / "shells"
STATE_PATH = Path(__file__).resolve().parent / "fetch_state.json"
MIN_ANALYTICS_DELIVERIES = 50  # matches build_stats "full" threshold
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

SEARCH_QUERIES = [
    "India tour of", "India in England", "India in Australia", "India in South Africa",
    "India in West Indies", "India in New Zealand", "India in Sri Lanka", "India in Bangladesh",
    "India in Pakistan", "India in Zimbabwe", "India in Ireland", "India in UAE",
    "India in Afghanistan", "India in Netherlands", "India in Scotland", "India in Namibia",
    "World Cup India", "Asia Cup India", "Champions Trophy India", "T20 World Cup India",
    "Border-Gavaskar", "England in India", "Australia in India", "South Africa in India",
    "New Zealand in India", "West Indies in India", "Sri Lanka in India", "Bangladesh in India",
    "Pakistan in India", "Afghanistan in India", "Zimbabwe in India", "Ireland in India",
    "Netherlands in India", "ICC World Test Championship India", "Super Over India",
]


def get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def load_existing_ids() -> set[str]:
    ids = set()
    for p in OUT_DIR.glob("*.json"):
        if p.name in ("stats.json",):
            continue
        # skip non-match dumps
        if not p.stem.isdigit():
            continue
        ids.add(p.stem)
    return ids


def discover_leagues() -> list[tuple[str, str]]:
    leagues: dict[str, str] = {}
    for q in SEARCH_QUERIES:
        url = (
            "https://site.web.api.espn.com/apis/common/v3/search?region=in&lang=en&query="
            + urllib.parse.quote(q)
            + "&limit=100&type=league"
        )
        try:
            d = get(url, timeout=25)
        except Exception as e:
            print(f"  search fail {q}: {e}", flush=True)
            continue
        for it in d.get("items") or []:
            name = it.get("displayName") or ""
            if re.search(r"Women|Under|U-?19|Youth|Lions|A tour|A in |Disabilit", name, re.I):
                continue
            if "India" not in name and "Indian" not in name:
                continue
            leagues[str(it["id"])] = name
        time.sleep(0.08)
    return sorted(leagues.items(), key=lambda x: x[1])


def teams_from_summary(summary: dict) -> list[str]:
    comps = (summary.get("header") or {}).get("competitions") or []
    if not comps:
        return []
    out = []
    for c in comps[0].get("competitors") or []:
        t = (c.get("team") or {}).get("displayName")
        if t:
            out.append(t)
    return out


def is_india_match(summary: dict) -> bool:
    teams = teams_from_summary(summary)
    return "India" in teams


def match_type_from_summary(summary: dict) -> str:
    comps = (summary.get("header") or {}).get("competitions") or []
    if not comps:
        return "ODI"
    cls = comps[0].get("class") or {}
    mt = cls.get("description") or cls.get("name") or cls.get("abbreviation") or ""
    if re.search(r"T20|Twenty", mt, re.I):
        return "T20"
    if re.search(r"Test", mt, re.I):
        return "Test"
    if re.search(r"ODI|One.?Day", mt, re.I):
        return "ODI"
    desc = (summary.get("header") or {}).get("description") or ""
    if re.search(r"T20", desc, re.I):
        return "T20"
    if re.search(r"Test", desc, re.I):
        return "Test"
    return "ODI"


def events_from_league(league_id: str) -> list[dict]:
    """Return event stubs from scoreboard + header APIs."""
    events = []
    for url in (
        f"https://site.api.espn.com/apis/site/v2/sports/cricket/{league_id}/scoreboard",
        f"https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=cricket&league={league_id}",
    ):
        try:
            d = get(url, timeout=15)
        except Exception:
            continue
        # scoreboard shape
        for ev in d.get("events") or []:
            events.append(ev)
        # header shape
        try:
            for lg in (d.get("sports") or [{}])[0].get("leagues") or []:
                for ev in lg.get("events") or []:
                    events.append(ev)
        except Exception:
            pass
        if events:
            break
    return events


def expand_event_ids(seed_ids: list[int], radius: int = 12) -> list[int]:
    out = set()
    for s in seed_ids:
        for e in range(s - radius, s + radius + 1):
            if e > 0:
                out.add(e)
    return sorted(out)


def try_summary(league_id: str, event_id: str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/{league_id}/summary?event={event_id}"
    try:
        return get(url, timeout=12)
    except Exception:
        return None


def fetch_balls_retry(league_id: str, event_id: str, retries: int = 4) -> list:
    items = []
    page = 1
    page_count = 1
    while page <= page_count:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/cricket/{league_id}"
            f"/playbyplay?event={event_id}&page={page}"
        )
        ok = False
        for attempt in range(retries):
            try:
                d = get(url, timeout=30)
                comm = d.get("commentary") or {}
                page_count = int(comm.get("pageCount") or 1)
                items.extend(comm.get("items") or [])
                ok = True
                break
            except Exception as e:
                time.sleep(1.2 * (attempt + 1))
                if attempt == retries - 1:
                    print(f"    pbp page {page} fail: {e}", flush=True)
        if not ok:
            break
        page += 1
        time.sleep(0.1)
    return items


def derive_outcome(summary: dict, mt: str) -> dict:
    notes = summary.get("notes") or []
    for n in notes:
        text = n.get("text") or ""
        m = re.search(r"(India|Afghanistan|Australia|England|South Africa|New Zealand|Pakistan|Sri Lanka|West Indies|Bangladesh|Zimbabwe|Ireland|Netherlands|Namibia|Scotland|UAE|United Arab Emirates)\s+won\s+by\s+(.+)", text, re.I)
        if m:
            winner = m.group(1)
            if winner.lower() in ("uae", "united arab emirates"):
                winner = "United Arab Emirates"
            margin = m.group(2).strip().rstrip(".")
            out = {"winner": winner}
            if "wicket" in margin.lower():
                nm = re.search(r"(\d+)", margin)
                if nm:
                    out["by"] = {"wickets": int(nm.group(1))}
            elif "innings" in margin.lower():
                nm = re.search(r"(\d+)", margin)
                out["by"] = {"innings": True, "runs": int(nm.group(1)) if nm else 0}
            elif "run" in margin.lower():
                nm = re.search(r"(\d+)", margin)
                if nm:
                    out["by"] = {"runs": int(nm.group(1))}
            return out
    # winner flag
    comps = (summary.get("header") or {}).get("competitions") or []
    if comps:
        for c in comps[0].get("competitors") or []:
            if c.get("winner"):
                return {"winner": (c.get("team") or {}).get("displayName")}
        status = ((comps[0].get("status") or {}).get("type") or {}).get("description") or ""
        if "draw" in status.lower():
            return {"result": "draw"}
        if "no result" in status.lower() or "abandon" in status.lower():
            return {"result": "no result"}
        if "tie" in status.lower():
            return {"result": "tie"}
    return {}


def save_match(league_id: str, event_id: str, summary: dict) -> dict | None:
    teams = teams_from_summary(summary)
    mt = match_type_from_summary(summary)
    header = summary.get("header") or {}
    comps = (header.get("competitions") or [{}])[0]
    # Prefer league id from summary header (more accurate for pbp)
    hdr_league = (header.get("league") or {}).get("id") or ((header.get("leagues") or [{}])[0].get("id"))
    pbp_league = str(hdr_league or league_id)
    meta = {
        "event_id": str(event_id),
        "league_id": pbp_league,
        "name": header.get("name"),
        "description": header.get("description") or header.get("title"),
        "teams": teams,
        "date": comps.get("date"),
        "match_type": mt,
        "summary": summary,
    }
    print(f"  FETCH {event_id} [{mt}] {meta['description']}", flush=True)
    balls = fetch_balls_retry(pbp_league, event_id)
    if len(balls) < 5 and pbp_league != str(league_id):
        balls2 = fetch_balls_retry(str(league_id), event_id)
        if len(balls2) > len(balls):
            balls = balls2
            meta["league_id"] = str(league_id)
    print(f"    balls={len(balls)}", flush=True)
    doc = convert_to_cricsheet(meta, balls)
    # force teams correctly (converter was AFG-oriented for some defaults)
    doc["info"]["teams"] = teams if len(teams) == 2 else doc["info"].get("teams")
    outcome = derive_outcome(summary, mt)
    if outcome:
        doc["info"]["outcome"] = outcome
    # Preserve scorecard cards when ball-by-ball unavailable
    cards = summary.get("matchcards") or []
    if cards:
        doc["info"]["scorecard_cards"] = cards
    # Try to fill rosters if empty
    if not doc["info"].get("players"):
        players = {}
        for roster in summary.get("rosters") or []:
            team = (roster.get("team") or {}).get("displayName")
            if not team:
                continue
            players[team] = [
                ((p.get("athlete") or {}).get("displayName") or (p.get("athlete") or {}).get("fullName"))
                for p in (roster.get("roster") or [])
                if (p.get("athlete") or {}).get("displayName") or (p.get("athlete") or {}).get("fullName")
            ]
        if players:
            doc["info"]["players"] = players
    nd = sum(
        len(d.get("deliveries") or [])
        for inn in doc.get("innings") or []
        for d in inn.get("overs") or []
    )
    if nd < MIN_ANALYTICS_DELIVERIES:
        # Do not pollute the analytics match set with ESPN meta-only shells.
        SHELLS_DIR.mkdir(exist_ok=True)
        shell_path = SHELLS_DIR / f"{event_id}.json"
        doc.setdefault("meta", {})["quality"] = "empty"
        doc["meta"]["analytics_excluded"] = True
        doc["meta"]["note"] = "ESPN summary only — no ball-by-ball; not used for W/L or player aggregates"
        with shell_path.open("w") as f:
            json.dump(doc, f, indent=1)
        print(
            f"    SKIP analytics set (dels={nd}) — saved meta shell to {shell_path.relative_to(ROOT.parent)}",
            flush=True,
        )
        return {
            "id": str(event_id),
            "league": str(league_id),
            "type": mt,
            "deliveries": nd,
            "desc": meta["description"],
            "teams": teams,
            "date": (meta.get("date") or "")[:10],
            "shell_only": True,
        }
    out_path = OUT_DIR / f"{event_id}.json"
    with out_path.open("w") as f:
        json.dump(doc, f, indent=1)
    print(f"    wrote {out_path.name} dels={nd} inns={len(doc.get('innings') or [])}", flush=True)
    return {
        "id": str(event_id),
        "league": str(league_id),
        "type": mt,
        "deliveries": nd,
        "desc": meta["description"],
        "teams": teams,
        "date": (meta.get("date") or "")[:10],
        "shell_only": False,
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"done_leagues": [], "written": [], "failed": []}


def save_state(state: dict):
    STATE_PATH.write_text(json.dumps(state, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-new", type=int, default=0, help="Stop after N new matches (0=unlimited)")
    ap.add_argument("--leagues-only", action="store_true")
    ap.add_argument("--radius", type=int, default=15, help="Event ID probe radius around seeds")
    ap.add_argument("--resume", action="store_true", default=True)
    args = ap.parse_args()

    print("=== Fetch missing India internationals ===", flush=True)
    existing = load_existing_ids()
    print(f"Existing match files: {len(existing)}", flush=True)

    print("Loading leagues...", flush=True)
    cache = Path(__file__).resolve().parent / "india_leagues.json"
    leagues = []
    if cache.exists():
        try:
            leagues = [(str(a), b) for a, b in json.loads(cache.read_text())]
            print(f"Loaded {len(leagues)} series from cache", flush=True)
        except Exception as e:
            print(f"  cache load fail: {e}", flush=True)
    if not leagues:
        print("Discovering leagues via ESPN search...", flush=True)
        leagues = discover_leagues()
    print(f"Found {len(leagues)} India-related series", flush=True)
    if args.leagues_only:
        for lid, name in leagues:
            print(lid, name)
        return

    state = load_state() if args.resume else {"done_leagues": [], "written": [], "failed": []}
    done_leagues = set(state.get("done_leagues") or [])
    written = list(state.get("written") or [])
    new_count = 0

    # Priority: recent first (higher league ids often newer)
    # Sort by name year if present else by id
    def sort_key(item):
        lid, name = item
        years = re.findall(r"(19|20)\d{2}", name)
        y = int(years[-1]) if years else 0
        return (-y, name)

    leagues_sorted = sorted(leagues, key=sort_key)

    for li, (league_id, league_name) in enumerate(leagues_sorted):
        if league_id in done_leagues:
            continue
        print(f"\n[{li+1}/{len(leagues_sorted)}] {league_name} ({league_id})", flush=True)
        seeds = []
        try:
            events = events_from_league(league_id)
        except Exception as e:
            print(f"  scoreboard fail: {e}", flush=True)
            events = []

        for ev in events:
            eid = ev.get("id") or (ev.get("competitions") or [{}])[0].get("id")
            if eid:
                try:
                    seeds.append(int(str(eid)))
                except ValueError:
                    pass


        if not seeds:
            # still mark done — nothing to expand
            print("  no seed events", flush=True)
            done_leagues.add(league_id)
            state["done_leagues"] = sorted(done_leagues)
            save_state(state)
            continue

        # Adaptive radius: if all seed event files already exist, only light probe
        seeds_missing = [s for s in seeds if str(s) not in existing]
        if not seeds_missing:
            radius = 2  # light probe only
        elif len(seeds_missing) <= 2:
            radius = min(args.radius, 10)
        else:
            radius = args.radius
        candidates = expand_event_ids(seeds, radius=radius)
        # Always include missing seeds
        for s in seeds_missing:
            if s not in candidates:
                candidates.append(s)
        candidates = sorted(set(candidates))
        print(
            f"  seeds={seeds[:5]}{'...' if len(seeds)>5 else ''} "
            f"missing_seeds={len(seeds_missing)} radius={radius} probing {len(candidates)} event ids",
            flush=True,
        )

        for eid in candidates:
            eid_s = str(eid)
            if eid_s in existing:
                continue
            summary = try_summary(league_id, eid_s)
            if not summary or not is_india_match(summary):
                continue
            # skip if no completed status sometimes still ok
            try:
                rec = save_match(league_id, eid_s, summary)
            except Exception as e:
                print(f"    ERROR {eid_s}: {e}", flush=True)
                state.setdefault("failed", []).append({"id": eid_s, "league": league_id, "error": str(e)})
                continue
            if rec:
                written.append(rec)
                existing.add(eid_s)
                new_count += 1
                state["written"] = written
                save_state(state)
                if args.max_new and new_count >= args.max_new:
                    print(f"\nReached --max-new={args.max_new}", flush=True)
                    print_summary(written, existing)
                    return
            time.sleep(0.05)

        done_leagues.add(league_id)
        state["done_leagues"] = sorted(done_leagues)
        save_state(state)
        time.sleep(0.1)

    print_summary(written, existing)


def print_summary(written, existing):
    print("\n=== SUMMARY ===", flush=True)
    print(f"New matches written this run (cumulative state): {len(written)}", flush=True)
    print(f"Total match files now: {len(existing)}", flush=True)
    by_type = {}
    for w in written:
        by_type[w.get("type", "?")] = by_type.get(w.get("type", "?"), 0) + 1
    print(f"By type: {by_type}", flush=True)
    report = Path(__file__).resolve().parent / "fetch_missing_report.json"
    report.write_text(json.dumps({"written": written, "total_files": len(existing)}, indent=2))
    print(f"Report: {report}", flush=True)


if __name__ == "__main__":
    main()
