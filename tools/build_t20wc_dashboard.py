"""Build delivery-level Men's T20 World Cup data for the static dashboard.

Cricsheet remains the primary source. Afghanistan matches that Cricsheet does
not publish can be reconstructed from ESPN's public play-by-play feed with
``--fetch-afghanistan``. Only factual delivery fields are retained; commentary
prose is deliberately discarded. Every reconstructed innings is reconciled
against the independently stored scorecard before publication.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".data-cache"
ESPN_CACHE = CACHE / "t20wc-espn"
MANUAL_DIR = ROOT / "data" / "t20wc_manual"
MATCH_DIR = ROOT / "data" / "t20wc_matches"
DEST = ROOT / "data" / "t20wc_deliveries.json"
NO_PLAY_PATH = ROOT / "data" / "t20wc_no_play.json"
FIELDS = [
    "match_id", "edition", "innings", "super_over", "over", "ball", "batting_team",
    "bowling_team", "batter", "non_striker", "bowler", "batter_runs",
    "extras", "total_runs", "bowler_runs", "legal", "batter_ball",
    "wicket", "bowler_wicket", "wicket_kind", "player_out", "source",
]
NON_BOWLER = {"run out", "retired hurt", "retired out", "obstructing the field"}

sys.path.insert(0, str(ROOT / "tools"))
from build_international import download  # noqa: E402
from world_cup import attach_unlabelled, family_key  # noqa: E402


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compact(row):
    return [row.get(field) for field in FIELDS]


def edition_for(day):
    return int(str(day)[:4])


def cricsheet_rows(raw, match_id):
    info = raw["info"]
    day = str(info["dates"][0])
    edition = edition_for(day)
    rows = []
    for innings_no, innings in enumerate(raw.get("innings", []), 1):
        batting = innings["team"]
        bowling = next((team for team in info["teams"] if team != batting), "")
        for over in innings.get("overs", []):
            for ball_index, delivery in enumerate(over.get("deliveries", []), 1):
                extras = delivery.get("extras") or {}
                runs = delivery.get("runs") or {}
                wickets = delivery.get("wickets") or []
                wicket = next((w for w in wickets if w.get("kind") != "retired hurt"), None)
                rows.append(compact({
                    "match_id": match_id,
                    "edition": edition,
                    "innings": innings_no,
                    "super_over": bool(innings.get("super_over")),
                    "over": int(over["over"]),
                    "ball": ball_index,
                    "batting_team": batting,
                    "bowling_team": bowling,
                    "batter": delivery.get("batter", ""),
                    "non_striker": delivery.get("non_striker", ""),
                    "bowler": delivery.get("bowler", ""),
                    "batter_runs": int(runs.get("batter", 0)),
                    "extras": int(runs.get("extras", 0)),
                    "total_runs": int(runs.get("total", 0)),
                    "bowler_runs": int(runs.get("total", 0))
                    - int(extras.get("byes", 0))
                    - int(extras.get("legbyes", 0))
                    - int(extras.get("penalty", 0)),
                    "legal": not bool(extras.get("wides") or extras.get("noballs")),
                    "batter_ball": not bool(extras.get("wides")),
                    "wicket": bool(wicket),
                    "bowler_wicket": bool(wicket and wicket.get("kind") not in NON_BOWLER),
                    "wicket_kind": (wicket or {}).get("kind", ""),
                    "player_out": (wicket or {}).get("player_out", ""),
                    "source": "cricsheet",
                }))
    return rows


def fetch_espn(match_id):
    ESPN_CACHE.mkdir(parents=True, exist_ok=True)
    target = ESPN_CACHE / f"{match_id}.json"
    if target.exists():
        return load_json(target)
    try:
        from curl_cffi import requests
    except ImportError as exc:
        raise RuntimeError(
            "Fetching Afghanistan deliveries requires curl_cffi. "
            "Install it temporarily or reuse a verified cache."
        ) from exc
    url = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/8676/playbyplay"
    session = requests.Session(impersonate="chrome")
    items = []
    page = 1
    while True:
        print(f"Fetching ESPN play-by-play {match_id} page {page}", file=sys.stderr)
        response = None
        for attempt in range(6):
            try:
                response = session.get(url, params={"event": match_id, "page": page}, timeout=45)
                response.raise_for_status()
                break
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(min(15, 2 ** attempt))
        commentary = response.json().get("commentary") or {}
        batch = commentary.get("items") or []
        if not batch:
            break
        items.extend(batch)
        if page >= int(commentary.get("pageCount") or 1):
            break
        page += 1
    if not items:
        raise RuntimeError(f"No ESPN play-by-play returned for {match_id}")
    # The cache is local and ignored. It exists only to make reconciliation
    # reproducible; commentary prose never enters the published dataset.
    target.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return items


def espn_rows(items, match):
    rows = []
    seen = set()
    for item in sorted(items, key=lambda row: int(row.get("sequence") or 0)):
        event_key = (item.get("id"), item.get("sequence"))
        if event_key in seen:
            continue
        seen.add(event_key)
        over = item.get("over") or {}
        innings = item.get("innings") or {}
        batter = item.get("batsman") or {}
        non_striker = item.get("otherBatsman") or {}
        bowler = item.get("bowler") or {}
        dismissal = item.get("dismissal") or {}
        batting_team = (item.get("team") or {}).get("displayName", "")
        bowling_team = (bowler.get("team") or {}).get("displayName", "")
        if not over or not innings or not batting_team:
            continue
        batter_runs = int(batter.get("runs") or 0)
        total_runs = int(item.get("scoreValue") or 0)
        byes = int(over.get("byes") or 0)
        leg_byes = int(over.get("legByes") or 0)
        kind = str(dismissal.get("type") or "").lower()
        is_wicket = bool(dismissal.get("dismissal")) and kind != "retired hurt"
        rows.append(compact({
            "match_id": match["id"],
            "edition": edition_for(match["date"]),
            "innings": int(innings.get("number") or item.get("period") or 0),
            "super_over": False,
            "over": max(0, int(over.get("number") or 1) - 1),
            "ball": int(over.get("ball") or 0),
            "batting_team": batting_team,
            "bowling_team": bowling_team,
            "batter": ((batter.get("athlete") or {}).get("displayName") or ""),
            "non_striker": ((non_striker.get("athlete") or {}).get("displayName") or ""),
            "bowler": (((bowler.get("athlete") or {}).get("displayName")) or ""),
            "batter_runs": batter_runs,
            "extras": max(0, total_runs - batter_runs),
            "total_runs": total_runs,
            "bowler_runs": max(0, total_runs - byes - leg_byes),
            "legal": not bool(over.get("wide") or over.get("noBall")),
            "batter_ball": not bool(over.get("wide")),
            "wicket": is_wicket,
            "bowler_wicket": bool(is_wicket and kind not in NON_BOWLER),
            "wicket_kind": kind,
            "player_out": ((((dismissal.get("batsman") or {}).get("athlete") or {}).get("displayName") or "") if is_wicket else ""),
            "source": "espn-reconstructed",
        }))
    return rows


def scorecard(match_id):
    for folder in ("historical_scorecards", "scorecards"):
        path = ROOT / "data" / folder / f"{match_id[:3]}.json"
        if path.exists():
            card = load_json(path).get(match_id)
            if card:
                return card
    return None


def _stat_value(line, name):
    for category in (line.get("statistics") or {}).get("categories", []):
        for stat in category.get("stats", []):
            if stat.get("name") == name:
                value = stat.get("value")
                return int(float(value)) if value not in (None, "") else None
    return None


def fetch_summary_expected(match_id):
    try:
        from curl_cffi import requests
    except ImportError as exc:
        raise RuntimeError("Fetching ESPN scorecard summaries requires curl_cffi") from exc
    url = "https://site.api.espn.com/apis/site/v2/sports/cricket/8676/summary"
    response = requests.get(url, params={"event": match_id}, impersonate="chrome", timeout=45)
    response.raise_for_status()
    competition = response.json()["header"]["competitions"][0]
    expected = []
    for competitor in competition.get("competitors", []):
        team = (competitor.get("team") or {}).get("displayName", "")
        for line in competitor.get("linescores") or []:
            if not line.get("runs"):
                continue
            expected.append({
                "innings": int(line.get("period") or 0),
                "team": team,
                "runs": int(line.get("runs") or 0),
                "wickets": int(line.get("wickets") or 0),
                "balls": _stat_value(line, "balls"),
            })
    return sorted(expected, key=lambda row: row["innings"])


def validate_match(match, rows, expected_override=None):
    card = scorecard(match["id"])
    if not card and not expected_override:
        return {"match_id": match["id"], "passed": False, "reason": "scorecard missing"}
    by_innings = defaultdict(list)
    for row in rows:
        if row[FIELDS.index("super_over")]:
            continue
        by_innings[int(row[FIELDS.index("innings")])].append(row)
    expected = expected_override or [inn for inn in card.get("innings", []) if not inn.get("super_over")]
    checks = []
    for number, innings in enumerate(expected, 1):
        balls = by_innings.get(number, [])
        actual_runs = sum(int(row[FIELDS.index("total_runs")] or 0) for row in balls)
        actual_legal = sum(bool(row[FIELDS.index("legal")]) for row in balls)
        actual_wickets = sum(bool(row[FIELDS.index("wicket")]) for row in balls)
        expected_balls = innings.get("balls")
        five_ball_over = (
            match["id"] == "1298172" and number == 1
            and actual_legal == 119 and expected_balls == 120
        )
        checks.append({
            "innings": number,
            "runs": [actual_runs, innings.get("runs")],
            "legal_balls": [actual_legal, expected_balls],
            "wickets": [actual_wickets, innings.get("wickets")],
            "note": "Official scorecard records a five-ball fourth over" if five_ball_over else "",
            "passed": actual_runs == innings.get("runs")
            and (expected_balls is None or actual_legal == expected_balls or five_ball_over)
            and actual_wickets == innings.get("wickets"),
        })
    return {
        "match_id": match["id"],
        "passed": bool(checks) and all(check["passed"] for check in checks),
        "innings": checks,
    }


def load_manual(match_id, allow_schema_mismatch=False):
    path = MANUAL_DIR / f"{match_id}.json"
    if not path.exists():
        return None
    payload = load_json(path)
    if payload.get("fields") != FIELDS and not allow_schema_mismatch:
        raise RuntimeError(f"Manual delivery schema mismatch: {path}")
    return payload


def save_manual(match_id, rows, expected=None):
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "match_id": match_id,
        "fields": FIELDS,
        "source": "ESPN public play-by-play; factual fields only",
        "expected": expected,
        "deliveries": rows,
    }
    (MANUAL_DIR / f"{match_id}.json").write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
    )


def main(fetch_afghanistan=False):
    archive = load_json(ROOT / "data" / "international.json")
    history = load_json(ROOT / "data" / "historical_matches.json")
    all_matches = archive["matches"] + history["matches"]
    current = {m["id"]: m for m in all_matches}
    wanted = {
        m["id"]: m for m in all_matches
        if m.get("format") == "T20I" and m.get("gender") == "Men"
        and (
            family_key(m) == "mens-t20"
            or ("Afghanistan" in m.get("teams", []) and attach_unlabelled(m) == "mens-t20")
        )
    }

    rows = []
    matches = {}
    source_zip = download("t20s_male_json.zip")
    with zipfile.ZipFile(source_zip) as archive_zip:
        for filename in archive_zip.namelist():
            match_id = Path(filename).stem
            if match_id not in wanted or not filename.endswith(".json"):
                continue
            raw = json.loads(archive_zip.read(filename))
            match = wanted[match_id]
            match_rows = cricsheet_rows(raw, match_id)
            rows.extend(match_rows)
            matches[match_id] = {
                "id": match_id,
                "date": match["date"],
                "edition": edition_for(match["date"]),
                "teams": match["teams"],
                "venue": match.get("venue", ""),
                "winner": (match.get("outcome") or {}).get("winner") or (match.get("outcome") or {}).get("eliminator"),
                "decided_by": "Super Over" if (match.get("outcome") or {}).get("eliminator") else "",
                "result": match.get("outcome") or {},
                "source": "Cricsheet",
                "source_url": "https://cricsheet.org/",
                "verified": True,
            }

    gaps = []
    audits = []
    for match_id, match in sorted(wanted.items(), key=lambda item: (item[1]["date"], item[0])):
        if match_id in matches:
            continue
        card = scorecard(match_id)
        no_result = (match.get("outcome") or {}).get("result") == "no result"
        if "Afghanistan" not in match.get("teams", []) or no_result:
            gaps.append({"id": match_id, "date": match["date"], "teams": match["teams"], "reason": "no play" if no_result else "deliveries unavailable"})
            continue
        manual = load_manual(match_id, allow_schema_mismatch=fetch_afghanistan)
        match_rows = manual.get("deliveries") if manual else None
        expected = manual.get("expected") if manual else None
        if fetch_afghanistan:
            match_rows = None
        cache = ESPN_CACHE / f"{match_id}.json"
        if match_rows is None and not cache.exists() and not fetch_afghanistan:
            gaps.append({"id": match_id, "date": match["date"], "teams": match["teams"], "reason": "Afghanistan reconstruction pending"})
            continue
        if match_rows is None:
            items = fetch_espn(match_id)
            match_rows = espn_rows(items, match)
        if not card and not expected and fetch_afghanistan:
            expected = fetch_summary_expected(match_id)
        audit = validate_match(match, match_rows, expected)
        audits.append(audit)
        if not audit["passed"]:
            raise RuntimeError(f"Afghanistan delivery reconciliation failed: {json.dumps(audit)}")
        if fetch_afghanistan:
            save_manual(match_id, match_rows, expected)
        rows.extend(match_rows)
        matches[match_id] = {
            "id": match_id,
            "date": match["date"],
            "edition": edition_for(match["date"]),
            "teams": match["teams"],
            "venue": match.get("venue", ""),
            "winner": (match.get("outcome") or {}).get("winner") or (match.get("outcome") or {}).get("eliminator"),
            "decided_by": "Super Over" if (match.get("outcome") or {}).get("eliminator") else "",
            "result": match.get("outcome") or {},
            "source": "ESPN play-by-play (facts reconstructed)",
            "source_url": match.get("source") or f"https://www.espncricinfo.com/matches/{match_id}",
            "verified": True,
        }

    rows.sort(key=lambda row: (row[1], row[0], row[2], row[3], row[4]))
    ordered_matches = sorted(matches.values(), key=lambda m: (m["date"], m["id"]))
    canonical_no_play = load_json(NO_PLAY_PATH)["matches"]
    no_play_ids = {match["id"] for match in canonical_no_play}
    unexpected_gaps = [gap for gap in gaps if gap["id"] not in no_play_ids]
    gaps = canonical_no_play + unexpected_gaps
    no_play_matches = [{
        "id": match["id"],
        "date": match["date"],
        "edition": edition_for(match["date"]),
        "teams": match["teams"],
        "venue": match.get("venue", ""),
        "winner": None,
        "decided_by": "",
        "result": {"result": match.get("status", "no result")},
        "source": "ESPNcricinfo tournament match-results record",
        "source_url": match["source"],
        "verified": True,
        "no_play": True,
    } for match in canonical_no_play]
    tournament = load_json(ROOT / "data" / "world_cup_history.json")["families"]["mens-t20"]
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "scope": "ICC Men's T20 World Cup main tournament",
            "first_delivery_date": ordered_matches[0]["date"] if ordered_matches else None,
            "last_delivery_date": ordered_matches[-1]["date"] if ordered_matches else None,
            "matches": len(ordered_matches),
            "fixtures": len(ordered_matches) + len(no_play_matches),
            "no_play": len(no_play_matches),
            "deliveries": len(rows),
            "regulation_deliveries": sum(not bool(row[FIELDS.index("super_over")]) for row in rows),
            "super_over_deliveries": sum(bool(row[FIELDS.index("super_over")]) for row in rows),
            "super_over_matches": sum(match.get("decided_by") == "Super Over" for match in ordered_matches),
            "editions": sorted({m["edition"] for m in ordered_matches}),
            "sources": ["Cricsheet", "ESPN play-by-play factual reconstruction"],
            "note": "Commentary prose is not retained. Reconstructed innings must match independent scorecards exactly.",
        },
        "fields": FIELDS,
        "matches": ordered_matches,
        "deliveries": rows,
        "titles": tournament.get("titles", {}),
        "editions": tournament.get("editions", []),
        "gaps": gaps,
        "reconciliation": audits,
    }
    MATCH_DIR.mkdir(parents=True, exist_ok=True)
    rows_by_match = defaultdict(list)
    for row in rows:
        rows_by_match[row[FIELDS.index("match_id")]].append(row)
    current_files = set()
    for match in ordered_matches + no_play_matches:
        match_id = match["id"]
        match_rows = rows_by_match[match_id]
        target = MATCH_DIR / f"{match_id}.json"
        current_files.add(target.name)
        match_payload = {
            "match": match,
            "fields": FIELDS,
            "deliveries": match_rows,
            "counts": {
                "deliveries": len(match_rows),
                "regulation": sum(not bool(row[FIELDS.index("super_over")]) for row in match_rows),
                "super_over": sum(bool(row[FIELDS.index("super_over")]) for row in match_rows),
            },
        }
        target.write_text(json.dumps(match_payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    for stale in MATCH_DIR.glob("*.json"):
        if stale.name not in current_files:
            stale.unlink()
    DEST.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(json.dumps({**payload["meta"], "gaps": len(gaps), "reconciled": len(audits)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-afghanistan", action="store_true")
    args = parser.parse_args()
    main(args.fetch_afghanistan)
