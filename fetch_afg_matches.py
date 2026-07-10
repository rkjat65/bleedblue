#!/usr/bin/env python3
"""
Fetch India vs Afghanistan ball-by-ball data from ESPN public APIs
and write Cricsheet-compatible JSON into the Team India folder.

ESPN endpoints used:
  summary:   /apis/site/v2/sports/cricket/{league}/summary?event={id}
  playbyplay:/apis/site/v2/sports/cricket/{league}/playbyplay?event={id}&page=N
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

# (league_or_series_id, event_id) — known + discovered seeds
# league id from ESPN header works for both summary and playbyplay
SEED_MATCHES = [
    # 2026 Afghanistan tour of India
    ("1527147", "1527150"),  # Only Test
    ("1527147", "1527151"),  # 1st ODI
    ("1527147", "1527152"),  # 2nd ODI
    ("1527147", "1527153"),  # 3rd ODI
    # 2024 T20I series (India)
    ("1389385", "1389396"),
    ("1389385", "1389397"),
    ("1389385", "1389398"),
    ("22003", "1389396"),
    ("22003", "1389397"),
    ("22003", "1389398"),
    # 2018 Only Test
    ("1133250", "1133983"),
    ("18543", "1133983"),
    # Multi-nation candidates (will be validated)
    # WC 2019 IND vs AFG ~22 Jun 2019
    ("1144413", "1144510"),
    ("1144413", "1144511"),
    ("1144413", "1144512"),
    ("1144413", "1144513"),
    ("1144413", "1144514"),
    ("1144413", "1144515"),
    # WC 2023 IND vs AFG
    ("1367856", "1384401"),
    ("1367856", "1384402"),
    ("1367856", "1384399"),
    ("1367856", "1384400"),
    ("1367856", "1384403"),
    ("1367856", "1384404"),
    ("1367856", "1384405"),
    ("1367856", "1384406"),
    ("1367856", "1384407"),
    ("1367856", "1384408"),
    # Asia Cup 2022
    ("1327269", "1327274"),
    ("1327269", "1327275"),
    ("1327269", "1327276"),
    ("1327269", "1327277"),
    ("1327269", "1327278"),
    ("1327269", "1327279"),
    ("1327269", "1327280"),
    # Asia Cup 2023
    ("1388374", "1388394"),
    ("1388374", "1388395"),
    ("1388374", "1388396"),
    ("1388374", "1388397"),
    ("1388374", "1388398"),
    ("1388374", "1388399"),
    ("1388374", "1388400"),
    ("1388374", "1388401"),
    ("1388374", "1388402"),
    ("1388374", "1388403"),
    ("1388374", "1388404"),
    ("1388374", "1388405"),
    ("1388374", "1388406"),
    ("1388374", "1388407"),
    ("1388374", "1388408"),
    ("1388374", "1388409"),
    ("1388374", "1388410"),
    ("1388374", "1388411"),
    ("1388374", "1388412"),
    ("1388374", "1388413"),
    # Asia Cup 2014 (first ODI meeting)
    ("690349", "690355"),
    ("690349", "690357"),
    ("690349", "690359"),
    ("690349", "690361"),
    ("656395", "656441"),
    ("656395", "656443"),
    ("656395", "656445"),
    ("656395", "656447"),
    # Asia Cup 2018
    ("1144981", "1144987"),
    ("1144981", "1144988"),
    ("1144981", "1144989"),
    ("1144981", "1144990"),
    ("1144981", "1144991"),
    # T20 WC 2024 Super 8 / group
    ("1410505", "1412536"),
    ("1410505", "1412540"),
    ("1410505", "1412545"),
    ("1410505", "1412550"),
    ("1410505", "1412555"),
    ("1410505", "1412560"),
    ("1410505", "1412565"),
    ("1410505", "1412570"),
    ("1410505", "1412575"),
    ("1410505", "1412580"),
    ("1410505", "1412525"),
    ("1410505", "1412530"),
    ("1410505", "1412531"),
    ("1410505", "1412532"),
    ("1410505", "1412533"),
    ("1410505", "1412534"),
    ("1410505", "1412535"),
    ("1410505", "1412537"),
    ("1410505", "1412538"),
    ("1410505", "1412539"),
    # T20 WC 2022
    ("1298134", "1298155"),
    ("1298134", "1298160"),
    ("1298134", "1298165"),
    ("1298134", "1298170"),
    ("1298134", "1298175"),
    # Asia Cup 2025
    ("1496900", "1496920"),
    ("1496900", "1496921"),
    ("1496900", "1496922"),
    ("1496900", "1496923"),
    ("1496900", "1496924"),
    ("1496900", "1496925"),
    ("1496900", "1496926"),
    ("1496900", "1496927"),
    ("1496900", "1496928"),
    ("1496900", "1496929"),
    ("1496900", "1496930"),
    ("1496900", "1496931"),
    ("1496900", "1496932"),
    ("1496900", "1496933"),
    ("1496900", "1496934"),
    ("1496900", "1496935"),
    ("1496900", "1496936"),
    ("1496900", "1496937"),
    ("1496900", "1496938"),
    ("1496900", "1496939"),
]

# Also expand sequential windows around known series
SERIES_WINDOWS = [
    ("1527147", range(1527148, 1527160)),
    ("1389385", range(1389394, 1389405)),
    ("22003", range(1389394, 1389405)),
    ("1133250", range(1133980, 1133990)),
    ("18543", range(1133980, 1133990)),
]


def http_get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def is_ind_afg(summary: dict) -> bool:
    header = summary.get("header") or {}
    comps = header.get("competitions") or []
    if not comps:
        return False
    teams = []
    for c in comps[0].get("competitors") or []:
        t = (c.get("team") or {}).get("displayName")
        if t:
            teams.append(t)
    return {"India", "Afghanistan"} <= set(teams)


def discover_matches() -> list[dict]:
    found = {}
    candidates = list(SEED_MATCHES)
    for series, window in SERIES_WINDOWS:
        for eid in window:
            candidates.append((str(series), str(eid)))

    # de-dupe preserving order
    seen_pair = set()
    uniq = []
    for lid, eid in candidates:
        key = (str(lid), str(eid))
        if key in seen_pair:
            continue
        seen_pair.add(key)
        uniq.append(key)

    print(f"Probing {len(uniq)} candidate (league,event) pairs...", flush=True)
    for i, (lid, eid) in enumerate(uniq):
        if eid in found:
            continue
        url = f"https://site.api.espn.com/apis/site/v2/sports/cricket/{lid}/summary?event={eid}"
        try:
            d = http_get(url, timeout=12)
        except Exception:
            continue
        if not is_ind_afg(d):
            continue
        header = d["header"]
        comps = header["competitions"][0]
        teams = [(c.get("team") or {}).get("displayName") for c in comps.get("competitors") or []]
        class_info = comps.get("class") or {}
        match_type = (
            class_info.get("description")
            or class_info.get("name")
            or class_info.get("abbreviation")
            or ""
        )
        # normalize
        mt = match_type
        if re.search(r"T20|Twenty", mt, re.I):
            mt = "T20"
        elif re.search(r"ODI|One.Day", mt, re.I):
            mt = "ODI"
        elif re.search(r"Test", mt, re.I):
            mt = "Test"
        rec = {
            "event_id": str(eid),
            "league_id": str(lid),
            "name": header.get("name"),
            "description": header.get("description") or header.get("title"),
            "teams": teams,
            "date": comps.get("date"),
            "match_type": mt,
            "summary": d,
        }
        found[str(eid)] = rec
        print(f"  FOUND {eid} [{mt}] {rec['description']}", flush=True)
        if i % 20 == 0:
            time.sleep(0.05)
    print(f"Discovered {len(found)} India vs Afghanistan matches", flush=True)
    return list(found.values())


def fetch_all_balls(league_id: str, event_id: str) -> list[dict]:
    items = []
    page = 1
    page_count = 1
    while page <= page_count:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/cricket/{league_id}"
            f"/playbyplay?event={event_id}&page={page}"
        )
        try:
            d = http_get(url, timeout=25)
        except Exception as e:
            print(f"    pbp page {page} failed: {e}", flush=True)
            break
        comm = d.get("commentary") or {}
        page_count = int(comm.get("pageCount") or 1)
        batch = comm.get("items") or []
        if not batch:
            break
        items.extend(batch)
        page += 1
        time.sleep(0.08)
    return items


def athlete_name(obj: dict | None) -> str:
    if not obj:
        return ""
    a = obj.get("athlete") or obj
    return (
        a.get("fullName")
        or a.get("displayName")
        or a.get("name")
        or a.get("shortName")
        or ""
    )


def map_dismissal_type(d: dict) -> str:
    t = (d.get("type") or "").lower().strip()
    text = (d.get("text") or "").lower()
    if d.get("bowled"):
        return "bowled"
    mapping = {
        "caught": "caught",
        "catch": "caught",
        "bowled": "bowled",
        "lbw": "lbw",
        "run out": "run out",
        "stumped": "stumped",
        "hit wicket": "hit wicket",
        "caught and bowled": "caught and bowled",
        "c & b": "caught and bowled",
        "retired hurt": "retired hurt",
        "retired out": "retired out",
        "obstructing the field": "obstructing the field",
        "handled the ball": "handled the ball",
        "timed out": "timed out",
        "hit the ball twice": "hit the ball twice",
    }
    for k, v in mapping.items():
        if k in t or k in text:
            return v
    if "c & b" in text or "caught and bowled" in text:
        return "caught and bowled"
    if text.startswith("c ") or " caught " in f" {text} ":
        return "caught"
    if "lbw" in text:
        return "lbw"
    if "run out" in text:
        return "run out"
    if "stumped" in text:
        return "stumped"
    if "bowled" in text:
        return "bowled"
    return t or "caught"


def parse_short_text_names(short: str) -> tuple[str, str]:
    """'Arshdeep Singh to Rahmanullah Gurbaz, no run' -> bowler, batter"""
    if not short:
        return "", ""
    m = re.match(r"^(.+?)\s+to\s+(.+?),\s*", short)
    if not m:
        return "", ""
    return m.group(1).strip(), m.group(2).strip()


def convert_to_cricsheet(meta: dict, balls: list[dict]) -> dict:
    summary = meta["summary"]
    header = summary["header"]
    comps = header["competitions"][0]
    teams = [t for t in meta["teams"] if t]
    # Ensure India naming
    teams = ["India" if t in ("IND",) else "Afghanistan" if t in ("AFG",) else t for t in teams]

    # Dates
    date_str = (comps.get("date") or meta.get("date") or "")[:10]
    dates = [date_str] if date_str else []
    # multi-day from notes / description
    desc = header.get("description") or ""

    # Match type
    mt = meta.get("match_type") or "ODI"
    if mt not in ("Test", "ODI", "T20"):
        if "Test" in desc:
            mt = "Test"
        elif "T20" in desc:
            mt = "T20"
        else:
            mt = "ODI"

    # Venue
    venue_info = (summary.get("gameInfo") or {}).get("venue") or {}
    venue = venue_info.get("fullName") or venue_info.get("shortName") or ""
    address = venue_info.get("address") or {}
    city = address.get("city") or ""

    # Toss / result from status / notes / description text
    status = (comps.get("status") or {}).get("type") or {}
    result_detail = status.get("description") or status.get("detail") or ""
    notes = summary.get("notes") or []

    outcome = {}
    winner = None
    for n in notes:
        text = n.get("text") or ""
        if "won by" in text.lower():
            # e.g. "India won by 7 wickets"
            m = re.search(r"(India|Afghanistan)\s+won\s+by\s+(.+)", text, re.I)
            if m:
                winner = "India" if m.group(1).lower() == "india" else "Afghanistan"
                margin = m.group(2).strip()
                outcome["winner"] = winner
                if "wicket" in margin.lower():
                    nm = re.search(r"(\d+)", margin)
                    if nm:
                        outcome["by"] = {"wickets": int(nm.group(1))}
                elif "run" in margin.lower():
                    nm = re.search(r"(\d+)", margin)
                    if nm:
                        outcome["by"] = {"runs": int(nm.group(1))}
                elif "innings" in margin.lower():
                    nm = re.search(r"(\d+)", margin)
                    outcome["by"] = {"innings": True, "runs": int(nm.group(1)) if nm else 0}
            break
    if not outcome:
        # From competitors winner flag
        for c in comps.get("competitors") or []:
            if c.get("winner"):
                winner = (c.get("team") or {}).get("displayName")
                outcome["winner"] = winner
                break
        if not outcome and "draw" in result_detail.lower():
            outcome["result"] = "draw"
        elif not outcome and "no result" in result_detail.lower():
            outcome["result"] = "no result"

    # Rosters
    players = {}
    registry = {"people": {}}
    for roster in summary.get("rosters") or []:
        team_name = (roster.get("team") or {}).get("displayName")
        if not team_name:
            continue
        names = []
        for p in roster.get("roster") or []:
            a = p.get("athlete") or {}
            name = a.get("displayName") or a.get("fullName") or a.get("name") or ""
            if not name:
                continue
            names.append(name)
            pid = str(a.get("id") or name)
            registry["people"][name] = pid
        players[team_name] = names

    # Officials
    officials = {"umpires": [], "match_referees": [], "tv_umpires": [], "reserve_umpires": []}
    for off in (summary.get("gameInfo") or {}).get("officials") or []:
        name = off.get("displayName") or ""
        pos = ((off.get("position") or {}).get("displayName") or "").lower()
        if not name:
            continue
        if "referee" in pos:
            officials["match_referees"].append(name)
        elif "tv" in pos or "third" in pos:
            officials["tv_umpires"].append(name)
        elif "reserve" in pos or "fourth" in pos:
            officials["reserve_umpires"].append(name)
        else:
            officials["umpires"].append(name)
    # drop empty
    officials = {k: v for k, v in officials.items() if v}

    # Player of match from notes
    pom = []
    for n in notes:
        text = n.get("text") or ""
        if "player of the match" in text.lower() or n.get("type") == "pom":
            m = re.search(r"([A-Z][A-Za-z .'-]+)$", text.strip())
            # better: often "Player of the Match: X"
            m2 = re.search(r"Player of the Match[:\s]+(.+)", text, re.I)
            if m2:
                pom.append(m2.group(1).strip())
            elif ":" in text:
                pom.append(text.split(":", 1)[1].strip())

    # Event
    league = header.get("league") or (header.get("leagues") or [{}])[0]
    event = {"name": league.get("name") or league.get("shortName") or "India vs Afghanistan"}
    # stage/match number from description
    mnum = re.search(r"(\d+)(st|nd|rd|th)\s+(ODI|T20I|Test)", desc, re.I)
    if mnum:
        event["match_number"] = int(mnum.group(1))
    if re.search(r"Only Test|Final|Semi", desc, re.I):
        if "Final" in desc:
            event["stage"] = "Final"
        elif "Only Test" in desc:
            pass

    # Season
    season = date_str[:4] if date_str else ""

    # Filter real deliveries (skip pure pre-match commentary)
    deliveries_raw = []
    for b in balls:
        if not b.get("bowler") and not b.get("batsman"):
            # might still be first ball with names only in shortText
            short = b.get("shortText") or ""
            if " to " not in short:
                continue
        if b.get("over") is None and not b.get("shortText"):
            continue
        deliveries_raw.append(b)

    # Group into innings/overs
    innings_map = defaultdict(lambda: defaultdict(list))  # inn_num -> over_num -> [dels]
    innings_team = {}

    for b in deliveries_raw:
        inn = b.get("innings") or {}
        inn_num = inn.get("number") or b.get("period") or 1
        team = (b.get("team") or {}).get("displayName") or (b.get("team") or {}).get("name")
        if team:
            innings_team[inn_num] = team
        over_info = b.get("over") or {}
        # ESPN over.number is 1-based over index; ball is 1-6 within over
        over_num = int(over_info.get("number") or 1) - 1  # cricsheet 0-based
        if over_num < 0:
            over_num = 0
        innings_map[inn_num][over_num].append(b)

    cricsheet_innings = []
    for inn_num in sorted(innings_map.keys()):
        team = innings_team.get(inn_num, teams[0] if teams else "Unknown")
        overs_out = []
        for over_num in sorted(innings_map[inn_num].keys()):
            dels = innings_map[inn_num][over_num]
            # sort by ball number / sequence
            dels.sort(key=lambda x: (x.get("sequence") or 0, (x.get("over") or {}).get("ball") or 0))
            delivery_list = []
            for b in dels:
                short = b.get("shortText") or ""
                bowler_name = athlete_name(b.get("bowler"))
                batter_name = athlete_name(b.get("batsman"))
                non_striker = athlete_name(b.get("otherBatsman"))
                st_bowl, st_bat = parse_short_text_names(short)
                if not bowler_name:
                    bowler_name = st_bowl
                if not batter_name:
                    batter_name = st_bat

                play = ((b.get("playType") or {}).get("description") or "").lower()
                bat_runs = int((b.get("batsman") or {}).get("runs") or 0)
                score_value = int(b.get("scoreValue") or 0)
                inn = b.get("innings") or {}
                over_info = b.get("over") or {}

                extras = {}
                runs_extras = 0
                # Classify extras
                if play in ("wide", "wides"):
                    extras["wides"] = max(1, score_value)
                    runs_extras = extras["wides"]
                    bat_runs = 0
                elif play in ("no ball", "noball", "no-ball"):
                    # score_value includes nb + bat runs usually
                    extras["noballs"] = 1
                    runs_extras = 1
                    # bat runs already in batsman.runs
                elif play in ("leg bye", "leg byes", "legbye"):
                    extras["legbyes"] = max(1, score_value)
                    runs_extras = extras["legbyes"]
                    bat_runs = 0
                elif play in ("bye", "byes"):
                    extras["byes"] = max(1, score_value)
                    runs_extras = extras["byes"]
                    bat_runs = 0
                elif play in ("four",):
                    bat_runs = 4
                elif play in ("six",):
                    bat_runs = 6
                elif play in ("no run", "dot"):
                    bat_runs = 0
                elif play in ("run", "runs"):
                    if bat_runs == 0 and score_value:
                        bat_runs = score_value

                total = bat_runs + runs_extras
                if play in ("wide", "wides", "leg bye", "leg byes", "bye", "byes"):
                    total = score_value or runs_extras
                elif play in ("no ball", "noball", "no-ball"):
                    total = bat_runs + 1

                deliv = {
                    "batter": batter_name or "Unknown",
                    "bowler": bowler_name or "Unknown",
                    "non_striker": non_striker or "",
                    "runs": {
                        "batter": bat_runs,
                        "extras": runs_extras,
                        "total": total,
                    },
                }
                if extras:
                    deliv["extras"] = extras

                # Wicket
                dismissal = b.get("dismissal") or {}
                if dismissal.get("dismissal") or play == "out":
                    kind = map_dismissal_type(dismissal)
                    player_out = athlete_name(dismissal.get("batsman")) or batter_name
                    wicket = {"kind": kind, "player_out": player_out}
                    # fielders from text if caught/run out/stumped
                    text = (dismissal.get("text") or b.get("text") or short or "")
                    # crude fielder parse: c X b Y / run out (X)
                    fielders = []
                    m = re.search(r"\bc(?:aught)?\s+([^b]+?)\s+b\s+", text, re.I)
                    if m and kind == "caught":
                        fielders.append({"name": m.group(1).strip(" .")})
                    m = re.search(r"run out\s*\(([^)]+)\)", text, re.I)
                    if m and kind == "run out":
                        for part in re.split(r"[,/&]", m.group(1)):
                            if part.strip():
                                fielders.append({"name": part.strip()})
                    m = re.search(r"st\s+([^b]+?)\s+b\s+", text, re.I)
                    if m and kind == "stumped":
                        fielders.append({"name": m.group(1).strip(" .")})
                    if fielders:
                        wicket["fielders"] = fielders
                    deliv["wickets"] = [wicket]

                # ball number within over
                ball_n = over_info.get("ball")
                if ball_n:
                    deliv["actual_delivery"] = f"{over_num}.{ball_n}"

                delivery_list.append(deliv)

            if delivery_list:
                overs_out.append({"over": over_num, "deliveries": delivery_list})

        if overs_out:
            inn_obj = {"team": team, "overs": overs_out}
            # powerplays for limited overs
            if mt in ("ODI", "T20"):
                max_pp = 9 if mt == "ODI" else 5
                inn_obj["powerplays"] = [
                    {"from": 0.1, "to": float(max_pp) + 0.6, "type": "mandatory"}
                ]
            cricsheet_innings.append(inn_obj)

    # Toss — try extract from first ball preText / notes
    toss = {}
    for b in balls[:5]:
        pre = b.get("preText") or ""
        m = re.search(r"(India|Afghanistan).{0,40}won the toss and elected to (bat|field|bowl)", pre, re.I)
        if m:
            toss = {
                "winner": "India" if m.group(1).lower() == "india" else "Afghanistan",
                "decision": "bat" if m.group(2).lower() == "bat" else "field",
            }
            break
        m = re.search(r"(Gill|Shahidi|India|Afghanistan).{0,80}(bowl|bat) first", pre, re.I)
        if m:
            # weaker
            pass

    info = {
        "balls_per_over": 6,
        "city": city,
        "dates": dates,
        "event": event,
        "gender": "male",
        "match_type": mt,
        "officials": officials,
        "outcome": outcome,
        "player_of_match": pom,
        "players": players,
        "registry": registry,
        "season": season,
        "team_type": "international",
        "teams": teams if len(teams) == 2 else ["India", "Afghanistan"],
        "toss": toss,
        "venue": venue,
    }
    if mt in ("ODI", "T20"):
        info["overs"] = 50 if mt == "ODI" else 20
        # reduced overs from balls if available
        for b in deliveries_raw:
            lim = (b.get("over") or {}).get("limit")
            if lim:
                info["overs"] = int(float(lim))
                break

    # Drop empty optional fields
    if not info["officials"]:
        del info["officials"]
    if not info["player_of_match"]:
        del info["player_of_match"]
    if not info["toss"]:
        del info["toss"]
    if not info["city"]:
        del info["city"]

    meta_out = {
        "data_version": "1.2.0",
        "created": datetime.utcnow().strftime("%Y-%m-%d"),
        "revision": 1,
        "source": "espn-api-reconstructed",
        "espn_event_id": meta["event_id"],
        "espn_league_id": meta["league_id"],
    }

    return {"meta": meta_out, "info": info, "innings": cricsheet_innings}


def main():
    print("=== India vs Afghanistan ball-by-ball recovery ===", flush=True)
    matches = discover_matches()
    if not matches:
        print("No matches discovered.", flush=True)
        sys.exit(1)

    written = []
    for m in sorted(matches, key=lambda x: x.get("date") or ""):
        eid = m["event_id"]
        lid = m["league_id"]
        out_path = OUT_DIR / f"{eid}.json"
        print(f"\nProcessing {eid}: {m.get('description')}", flush=True)
        balls = fetch_all_balls(lid, eid)
        print(f"  balls fetched: {len(balls)}", flush=True)
        if len(balls) < 5:
            print("  WARNING: very few balls — still writing metadata if possible", flush=True)
        doc = convert_to_cricsheet(m, balls)
        # basic validation
        n_dels = sum(
            len(d.get("deliveries") or [])
            for inn in doc.get("innings") or []
            for d in inn.get("overs") or []
        )
        print(f"  innings={len(doc.get('innings') or [])} deliveries={n_dels} outcome={doc['info'].get('outcome')}", flush=True)
        with out_path.open("w") as f:
            json.dump(doc, f, indent=1)
        written.append({"id": eid, "path": str(out_path), "deliveries": n_dels, "desc": m.get("description")})
        print(f"  wrote {out_path.name}", flush=True)
        time.sleep(0.15)

    report = OUT_DIR / "dashboard" / "afg_recovery_report.json"
    with report.open("w") as f:
        json.dump({"written": written, "count": len(written)}, f, indent=2)
    print(f"\nDone. Wrote {len(written)} match files. Report: {report}", flush=True)


if __name__ == "__main__":
    main()
