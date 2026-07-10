#!/usr/bin/env python3
"""Rebuild dashboard/stats.json from Cricsheet India match JSON files.

Usage (from Team India folder or dashboard folder):
  python3 dashboard/build_stats.py
  python3 build_stats.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if not list(ROOT.glob("*.json")):
    # maybe running from parent already
    ROOT = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parent / "stats.json"

# India home venue/city heuristics
INDIA_HOME_KW = [
    "Mumbai", "Delhi", "Kolkata", "Chennai", "Bengaluru", "Bangalore", "Hyderabad",
    "Ahmedabad", "Pune", "Jaipur", "Mohali", "Chandigarh", "Indore", "Nagpur",
    "Kanpur", "Cuttack", "Rajkot", "Visakhapatnam", "Guwahati", "Dharamsala",
    "Dharamshala", "Ranchi", "Lucknow", "Thiruvananthapuram", "Kochi", "Cochin",
    "Raipur", "Vadodara", "Baroda", "Jamshedpur", "Gwalior", "Faridabad",
    "Greater Noida", "Noida", "Wankhede", "Eden Gardens", "Chepauk", "Chinnaswamy",
    "Narendra Modi", "Brabourne", "Green Park", "Sawai Mansingh", "Holkar",
    "JSCA", "Barsapara", "Uppal", "Motera", "Barabati", "Kotla", "Arun Jaitley",
    "Feroz Shah", "Ekana", "Greenfield", "DY Patil", "Mullanpur", "New Chandigarh",
    "Fatorda", "Margao", "Sector 16", "Vidarbha", "PCA", "ACA-VDCA",
]


def is_india_home(venue: str, city: str) -> bool:
    text = f"{venue or ''} {city or ''}".lower()
    return any(k.lower() in text for k in INDIA_HOME_KW)


def empty_batter():
    return {
        "matches": set(), "innings": 0, "runs": 0, "balls": 0,
        "fours": 0, "sixes": 0, "not_outs": 0, "dismissals": 0,
        "highest": 0, "highest_no": False, "fifties": 0, "hundreds": 0, "ducks": 0,
        "by_format": defaultdict(lambda: {
            "matches": set(), "innings": 0, "runs": 0, "balls": 0,
            "fours": 0, "sixes": 0, "not_outs": 0, "dismissals": 0,
            "highest": 0, "highest_no": False, "fifties": 0, "hundreds": 0,
        }),
    }


def empty_bowler():
    return {
        "matches": set(), "innings": 0, "balls": 0, "runs": 0, "wickets": 0,
        "dots": 0, "maidens": 0, "fours": 0, "sixes": 0, "wides": 0, "noballs": 0,
        "best_wickets": 0, "best_runs": 999, "four_w": 0, "five_w": 0,
        "by_format": defaultdict(lambda: {
            "matches": set(), "innings": 0, "balls": 0, "runs": 0, "wickets": 0,
            "dots": 0, "maidens": 0, "best_wickets": 0, "best_runs": 999,
            "four_w": 0, "five_w": 0,
        }),
    }


def classify_result(info: dict) -> str:
    outcome = info.get("outcome") or {}
    if "winner" in outcome:
        return "won" if outcome["winner"] == "India" else "lost"
    res = (outcome.get("result") or "").lower()
    if res == "draw":
        return "draw"
    if res == "tie":
        return "tied"
    if "no result" in res or res in ("n/r", "no_result", "abandon", "abandoned"):
        return "nr"
    if not outcome:
        return "nr"
    return "nr"


def finalize_batter(name, b):
    matches = len(b["matches"])
    avg = round(b["runs"] / b["dismissals"], 2) if b["dismissals"] else None
    sr = round(b["runs"] / b["balls"] * 100, 2) if b["balls"] else 0
    hi_str = f"{b['highest']}*" if b["highest_no"] and b["highest"] else str(b["highest"])
    formats = {}
    for fmt, bf in b["by_format"].items():
        favg = round(bf["runs"] / bf["dismissals"], 2) if bf["dismissals"] else None
        fsr = round(bf["runs"] / bf["balls"] * 100, 2) if bf["balls"] else 0
        formats[fmt] = {
            "matches": len(bf["matches"]), "innings": bf["innings"], "runs": bf["runs"],
            "balls": bf["balls"], "avg": favg, "sr": fsr, "fours": bf["fours"], "sixes": bf["sixes"],
            "fifties": bf["fifties"], "hundreds": bf["hundreds"],
            "highest": f"{bf['highest']}*" if bf["highest_no"] and bf["highest"] else bf["highest"],
            "not_outs": bf["not_outs"],
        }
    return {
        "name": name, "matches": matches, "innings": b["innings"], "runs": b["runs"],
        "balls": b["balls"], "avg": avg, "sr": sr, "fours": b["fours"], "sixes": b["sixes"],
        "fifties": b["fifties"], "hundreds": b["hundreds"], "ducks": b["ducks"],
        "highest": hi_str, "not_outs": b["not_outs"], "by_format": formats,
    }


def finalize_bowler(name, b):
    matches = len(b["matches"])
    overs = f"{b['balls'] // 6}.{b['balls'] % 6}"
    avg = round(b["runs"] / b["wickets"], 2) if b["wickets"] else None
    econ = round(b["runs"] / (b["balls"] / 6), 2) if b["balls"] else None
    sr = round(b["balls"] / b["wickets"], 2) if b["wickets"] else None
    best = f"{b['best_wickets']}/{b['best_runs']}" if b["best_wickets"] or b["best_runs"] != 999 else "-"
    formats = {}
    for fmt, bf in b["by_format"].items():
        favg = round(bf["runs"] / bf["wickets"], 2) if bf["wickets"] else None
        fecon = round(bf["runs"] / (bf["balls"] / 6), 2) if bf["balls"] else None
        fsr = round(bf["balls"] / bf["wickets"], 2) if bf["wickets"] else None
        fbest = f"{bf['best_wickets']}/{bf['best_runs']}" if bf["best_wickets"] or bf["best_runs"] != 999 else "-"
        formats[fmt] = {
            "matches": len(bf["matches"]), "innings": bf["innings"],
            "balls": bf["balls"], "overs": f"{bf['balls'] // 6}.{bf['balls'] % 6}",
            "runs": bf["runs"], "wickets": bf["wickets"], "avg": favg, "econ": fecon, "sr": fsr,
            "maidens": bf["maidens"], "best": fbest, "four_w": bf["four_w"], "five_w": bf["five_w"],
        }
    return {
        "name": name, "matches": matches, "innings": b["innings"], "balls": b["balls"],
        "overs": overs, "runs": b["runs"], "wickets": b["wickets"], "avg": avg, "econ": econ,
        "sr": sr, "maidens": b["maidens"], "dots": b["dots"], "best": best,
        "four_w": b["four_w"], "five_w": b["five_w"], "wides": b["wides"], "noballs": b["noballs"],
        "by_format": formats,
    }


def main():
    files = sorted(ROOT.glob("*.json"))
    # exclude stats if ever placed at root
    files = [f for f in files if f.name != "stats.json"]
    if not files:
        print(f"No match JSON files found in {ROOT}", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(files)} matches from {ROOT} ...")

    batters = defaultdict(empty_batter)
    bowlers = defaultdict(empty_bowler)
    fielders = defaultdict(lambda: {"catches": 0, "stumpings": 0, "runouts": 0, "matches": set()})
    overall = {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0}
    by_format = defaultdict(lambda: {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0})
    by_opponent = defaultdict(lambda: {
        "played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0,
        "by_format": defaultdict(lambda: {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0}),
    })
    by_year = defaultdict(lambda: {
        "played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0,
        "by_format": defaultdict(lambda: {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0}),
    })
    by_venue = defaultdict(lambda: {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0, "city": "", "home": False})
    by_home_away = defaultdict(lambda: {"played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0})
    toss_stats = {
        "won_toss": 0, "lost_toss": 0, "won_bat_first": 0, "won_chase": 0,
        "bat_first_matches": 0, "chase_matches": 0, "toss_and_win": 0, "toss_and_lose": 0,
    }
    pom = Counter()
    highest_totals, lowest_totals = [], []
    notable_innings, notable_bowling = [], []
    biggest_wins_runs, biggest_wins_wickets, biggest_defeats_runs = [], [], []
    match_list = []
    by_event = defaultdict(lambda: {
        "played": 0, "won": 0, "lost": 0, "draw": 0, "tied": 0, "nr": 0,
        "formats": set(), "match_ids": [], "first": "", "last": "",
    })
    quality = {"full": 0, "partial": 0, "empty": 0}

    for idx, path in enumerate(files):
        if idx % 100 == 0:
            print(f"  {idx}/{len(files)}")
        mid = path.stem
        with path.open() as f:
            data = json.load(f)
        info = data["info"]
        innings = data.get("innings") or []
        mt = info.get("match_type", "?")
        teams = info.get("teams") or []
        opp = next((t for t in teams if t != "India"), "Unknown")
        dates = info.get("dates") or []
        date = dates[0] if dates else ""
        year = date[:4] if date else "?"
        venue = info.get("venue", "")
        city = info.get("city", "")
        event = info.get("event") or {}
        event_name = event.get("name", "")
        stage = event.get("stage", "")
        toss = info.get("toss") or {}
        outcome = info.get("outcome") or {}
        result = classify_result(info)
        players = info.get("players") or {}
        india_xi = set(players.get("India") or [])
        pom_list = info.get("player_of_match") or []

        overall["played"] += 1
        overall[result] = overall.get(result, 0) + 1
        by_format[mt]["played"] += 1
        by_format[mt][result] = by_format[mt].get(result, 0) + 1
        by_opponent[opp]["played"] += 1
        by_opponent[opp][result] = by_opponent[opp].get(result, 0) + 1
        by_opponent[opp]["by_format"][mt]["played"] += 1
        by_opponent[opp]["by_format"][mt][result] = by_opponent[opp]["by_format"][mt].get(result, 0) + 1
        by_year[year]["played"] += 1
        by_year[year][result] = by_year[year].get(result, 0) + 1
        by_year[year]["by_format"][mt]["played"] += 1
        by_year[year]["by_format"][mt][result] = by_year[year]["by_format"][mt].get(result, 0) + 1

        home = is_india_home(venue, city)
        loc = "home" if home else "away"
        by_home_away[loc]["played"] += 1
        by_home_away[loc][result] = by_home_away[loc].get(result, 0) + 1
        by_venue[venue]["played"] += 1
        by_venue[venue][result] = by_venue[venue].get(result, 0) + 1
        by_venue[venue]["city"] = city
        by_venue[venue]["home"] = home

        if toss.get("winner") == "India":
            toss_stats["won_toss"] += 1
            if result == "won":
                toss_stats["toss_and_win"] += 1
            elif result == "lost":
                toss_stats["toss_and_lose"] += 1
        else:
            toss_stats["lost_toss"] += 1

        if innings and mt in ("ODI", "T20") and result in ("won", "lost"):
            india_batted_first = innings[0].get("team") == "India"
            if india_batted_first:
                toss_stats["bat_first_matches"] += 1
                if result == "won":
                    toss_stats["won_bat_first"] += 1
            else:
                toss_stats["chase_matches"] += 1
                if result == "won":
                    toss_stats["won_chase"] += 1

        for p in pom_list:
            pom[p] += 1

        india_totals = []
        opp_totals = []
        india_bat_card = []  # condensed scorecard for match detail
        india_bowl_card = []
        total_deliveries = 0
        for inn_idx, inn in enumerate(innings):
            team = inn.get("team")
            overs = inn.get("overs") or []
            if team == "India":
                bat_state = defaultdict(lambda: {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False})
                total_runs = 0
                total_wkts = 0
                legal = 0
                for over in overs:
                    for d in over.get("deliveries") or []:
                        total_deliveries += 1
                        batter = d.get("batter")
                        runs = d.get("runs") or {}
                        extras = d.get("extras") or {}
                        br = runs.get("batter", 0)
                        total_runs += runs.get("total", 0)
                        bat_state[batter]["runs"] += br
                        if "wides" not in extras:
                            bat_state[batter]["balls"] += 1
                        if "wides" not in extras and "noballs" not in extras:
                            legal += 1
                        if br == 4:
                            bat_state[batter]["fours"] += 1
                        elif br == 6:
                            bat_state[batter]["sixes"] += 1
                        if "wickets" in d:
                            for w in d["wickets"]:
                                if w.get("player_out"):
                                    bat_state[w["player_out"]]["out"] = True
                                if w.get("kind") != "retired hurt":
                                    total_wkts += 1

                # scorecard lines
                for name, st in bat_state.items():
                    india_bat_card.append({
                        "player": name, "runs": st["runs"], "balls": st["balls"],
                        "fours": st["fours"], "sixes": st["sixes"], "out": st["out"],
                        "innings": inn_idx + 1,
                    })

                for name, st in bat_state.items():
                    b = batters[name]
                    b["matches"].add(mid)
                    b["innings"] += 1
                    b["runs"] += st["runs"]
                    b["balls"] += st["balls"]
                    b["fours"] += st["fours"]
                    b["sixes"] += st["sixes"]
                    if st["out"]:
                        b["dismissals"] += 1
                    else:
                        b["not_outs"] += 1
                    hi = st["runs"]
                    if hi > b["highest"] or (hi == b["highest"] and not st["out"]):
                        b["highest"] = hi
                        b["highest_no"] = not st["out"]
                    if st["out"] and hi == 0:
                        b["ducks"] += 1
                    if hi >= 100:
                        b["hundreds"] += 1
                    elif hi >= 50:
                        b["fifties"] += 1
                    bf = b["by_format"][mt]
                    bf["matches"].add(mid)
                    bf["innings"] += 1
                    bf["runs"] += st["runs"]
                    bf["balls"] += st["balls"]
                    bf["fours"] += st["fours"]
                    bf["sixes"] += st["sixes"]
                    if st["out"]:
                        bf["dismissals"] += 1
                    else:
                        bf["not_outs"] += 1
                    if hi > bf["highest"] or (hi == bf["highest"] and not st["out"]):
                        bf["highest"] = hi
                        bf["highest_no"] = not st["out"]
                    if hi >= 100:
                        bf["hundreds"] += 1
                    elif hi >= 50:
                        bf["fifties"] += 1
                    if hi >= 80:
                        notable_innings.append({
                            "player": name, "runs": hi, "balls": st["balls"],
                            "fours": st["fours"], "sixes": st["sixes"],
                            "not_out": not st["out"], "format": mt,
                            "opponent": opp, "date": date, "venue": venue,
                            "match_id": mid, "event": event_name,
                        })

                india_totals.append({"runs": total_runs, "wickets": total_wkts, "balls": legal, "innings": inn_idx + 1})
                highest_totals.append({
                    "runs": total_runs, "wickets": total_wkts, "overs": f"{legal // 6}.{legal % 6}",
                    "format": mt, "opponent": opp, "date": date, "venue": venue, "match_id": mid, "event": event_name,
                })
                if total_wkts >= 10 or (mt in ("ODI", "T20") and total_wkts >= 8):
                    lowest_totals.append({
                        "runs": total_runs, "wickets": total_wkts, "overs": f"{legal // 6}.{legal % 6}",
                        "format": mt, "opponent": opp, "date": date, "venue": venue, "match_id": mid,
                    })
            else:
                bowl_state = defaultdict(lambda: {
                    "balls": 0, "runs": 0, "wickets": 0, "dots": 0, "fours": 0, "sixes": 0,
                    "wides": 0, "noballs": 0, "maidens": 0,
                })
                opp_runs = 0
                opp_wkts = 0
                opp_legal = 0
                for over in overs:
                    bowler_overs_runs = defaultdict(int)
                    bowler_overs_legal = defaultdict(int)
                    for d in over.get("deliveries") or []:
                        total_deliveries += 1
                        bowler = d.get("bowler")
                        runs = d.get("runs") or {}
                        extras = d.get("extras") or {}
                        total = runs.get("total", 0)
                        br = runs.get("batter", 0)
                        opp_runs += total
                        bowl_state[bowler]["runs"] += total
                        is_wide = "wides" in extras
                        is_nb = "noballs" in extras
                        if is_wide:
                            bowl_state[bowler]["wides"] += 1
                        if is_nb:
                            bowl_state[bowler]["noballs"] += 1
                        if not is_wide and not is_nb:
                            bowl_state[bowler]["balls"] += 1
                            bowler_overs_legal[bowler] += 1
                            opp_legal += 1
                            if total == 0:
                                bowl_state[bowler]["dots"] += 1
                        if br == 4:
                            bowl_state[bowler]["fours"] += 1
                        elif br == 6:
                            bowl_state[bowler]["sixes"] += 1
                        bowler_overs_runs[bowler] += total
                        if "wickets" in d:
                            for w in d["wickets"]:
                                kind = w.get("kind", "")
                                if kind != "retired hurt":
                                    opp_wkts += 1
                                if kind in ("bowled", "lbw", "caught", "stumped", "hit wicket", "caught and bowled"):
                                    bowl_state[bowler]["wickets"] += 1
                                for fl in w.get("fielders") or []:
                                    fname = fl.get("name") if isinstance(fl, dict) else fl
                                    if fname and fname in india_xi:
                                        if kind in ("caught", "caught and bowled"):
                                            fielders[fname]["catches"] += 1
                                            fielders[fname]["matches"].add(mid)
                                        elif kind == "stumped":
                                            fielders[fname]["stumpings"] += 1
                                            fielders[fname]["matches"].add(mid)
                                        elif kind == "run out":
                                            fielders[fname]["runouts"] += 1
                                            fielders[fname]["matches"].add(mid)
                                if kind == "caught and bowled" and bowler in india_xi:
                                    fielders[bowler]["catches"] += 1
                                    fielders[bowler]["matches"].add(mid)
                    for bowler, legal_ct in bowler_overs_legal.items():
                        if legal_ct >= 6 and bowler_overs_runs[bowler] == 0:
                            bowl_state[bowler]["maidens"] += 1

                opp_totals.append({
                    "runs": opp_runs, "wickets": opp_wkts, "balls": opp_legal, "innings": inn_idx + 1,
                })
                for name, st in bowl_state.items():
                    if st["balls"] or st["wickets"] or st["runs"]:
                        india_bowl_card.append({
                            "player": name, "wickets": st["wickets"], "runs": st["runs"],
                            "balls": st["balls"], "maidens": st["maidens"], "innings": inn_idx + 1,
                        })

                for name, st in bowl_state.items():
                    if st["balls"] == 0 and st["wickets"] == 0 and st["runs"] == 0:
                        continue
                    b = bowlers[name]
                    b["matches"].add(mid)
                    b["innings"] += 1
                    b["balls"] += st["balls"]
                    b["runs"] += st["runs"]
                    b["wickets"] += st["wickets"]
                    b["dots"] += st["dots"]
                    b["maidens"] += st["maidens"]
                    b["fours"] += st["fours"]
                    b["sixes"] += st["sixes"]
                    b["wides"] += st["wides"]
                    b["noballs"] += st["noballs"]
                    if st["wickets"] > b["best_wickets"] or (st["wickets"] == b["best_wickets"] and st["runs"] < b["best_runs"]):
                        b["best_wickets"] = st["wickets"]
                        b["best_runs"] = st["runs"]
                    if st["wickets"] >= 5:
                        b["five_w"] += 1
                    elif st["wickets"] >= 4:
                        b["four_w"] += 1
                    bf = b["by_format"][mt]
                    bf["matches"].add(mid)
                    bf["innings"] += 1
                    bf["balls"] += st["balls"]
                    bf["runs"] += st["runs"]
                    bf["wickets"] += st["wickets"]
                    bf["dots"] += st["dots"]
                    bf["maidens"] += st["maidens"]
                    if st["wickets"] > bf["best_wickets"] or (st["wickets"] == bf["best_wickets"] and st["runs"] < bf["best_runs"]):
                        bf["best_wickets"] = st["wickets"]
                        bf["best_runs"] = st["runs"]
                    if st["wickets"] >= 5:
                        bf["five_w"] += 1
                    elif st["wickets"] >= 4:
                        bf["four_w"] += 1
                    if st["wickets"] >= 4:
                        notable_bowling.append({
                            "player": name, "wickets": st["wickets"], "runs": st["runs"],
                            "balls": st["balls"], "overs": f"{st['balls'] // 6}.{st['balls'] % 6}",
                            "format": mt, "opponent": opp, "date": date, "venue": venue,
                            "match_id": mid, "event": event_name,
                        })

        margin = ""
        if "by" in outcome:
            by = outcome["by"]
            if "runs" in by:
                margin = f"by {by['runs']} runs"
                rec = {"margin": by["runs"], "opponent": opp, "date": date, "format": mt, "venue": venue, "match_id": mid}
                if result == "won":
                    biggest_wins_runs.append(rec)
                elif result == "lost":
                    biggest_defeats_runs.append(rec)
            elif "wickets" in by:
                margin = f"by {by['wickets']} wickets"
                if result == "won":
                    biggest_wins_wickets.append({
                        "margin": by["wickets"], "opponent": opp, "date": date,
                        "format": mt, "venue": venue, "match_id": mid,
                    })
            elif "innings" in by:
                margin = f"by innings and {by.get('runs', 0)} runs"
        elif outcome.get("result"):
            margin = str(outcome.get("result"))

        # quality bucket
        if total_deliveries >= 50:
            q = "full"
        elif total_deliveries > 0:
            q = "partial"
        else:
            q = "empty"
        quality[q] += 1

        # series / event rollup
        ename = event_name or "(unnamed series)"
        ev = by_event[ename]
        ev["played"] += 1
        ev[result] = ev.get(result, 0) + 1
        ev["formats"].add(mt)
        if len(ev["match_ids"]) < 80:
            ev["match_ids"].append(mid)
        if not ev["first"] or (date and date < ev["first"]):
            ev["first"] = date
        if not ev["last"] or (date and date > ev["last"]):
            ev["last"] = date

        # sort scorecard lines
        india_bat_card.sort(key=lambda x: (-x["runs"], x["innings"]))
        india_bowl_card.sort(key=lambda x: (-x["wickets"], x["runs"]))

        match_list.append({
            "id": mid, "date": date, "format": mt, "opponent": opp,
            "venue": venue, "city": city, "result": result,
            "winner": outcome.get("winner", outcome.get("result", "")),
            "margin": margin, "event": event_name, "stage": stage,
            "pom": pom_list, "toss": f"{toss.get('winner', '')} ({toss.get('decision', '')})",
            "home": home, "season": info.get("season", ""),
            "match_type_number": info.get("match_type_number"),
            "india_totals": india_totals,
            "opp_totals": opp_totals,
            "xi": list(india_xi)[:15],
            "balls": total_deliveries,
            "quality": q,
            "bat_card": india_bat_card[:22],
            "bowl_card": india_bowl_card[:15],
        })

    print("Serializing...")
    batting_list = sorted((finalize_batter(n, b) for n, b in batters.items()), key=lambda x: -x["runs"])
    bowling_list = sorted((finalize_bowler(n, b) for n, b in bowlers.items()), key=lambda x: -x["wickets"])
    fielding_list = sorted(
        ({
            "name": n, "catches": f["catches"], "stumpings": f["stumpings"],
            "runouts": f["runouts"], "dismissals": f["catches"] + f["stumpings"] + f["runouts"],
            "matches": len(f["matches"]),
        } for n, f in fielders.items()),
        key=lambda x: -x["dismissals"],
    )

    notable_innings.sort(key=lambda x: -x["runs"])
    notable_bowling.sort(key=lambda x: (-x["wickets"], x["runs"]))
    highest_totals.sort(key=lambda x: -x["runs"])
    lowest_completed = sorted(
        [t for t in lowest_totals if t["wickets"] >= 10 or (t["format"] != "Test" and t["wickets"] >= 8)],
        key=lambda x: x["runs"],
    )
    biggest_wins_runs.sort(key=lambda x: -x["margin"])
    biggest_wins_wickets.sort(key=lambda x: -x["margin"])
    biggest_defeats_runs.sort(key=lambda x: -x["margin"])
    match_list.sort(key=lambda x: x["date"], reverse=True)

    opp_list = []
    for name, s in by_opponent.items():
        p = s["played"]
        opp_list.append({
            "opponent": name, "played": p, "won": s.get("won", 0), "lost": s.get("lost", 0),
            "draw": s.get("draw", 0), "tied": s.get("tied", 0), "nr": s.get("nr", 0),
            "win_pct": round(s.get("won", 0) / p * 100, 1) if p else 0,
            "by_format": {k: dict(v) for k, v in s["by_format"].items()},
        })
    opp_list.sort(key=lambda x: -x["played"])

    year_list = []
    for y, s in sorted(by_year.items()):
        p = s["played"]
        year_list.append({
            "year": y, "played": p, "won": s.get("won", 0), "lost": s.get("lost", 0),
            "draw": s.get("draw", 0), "tied": s.get("tied", 0), "nr": s.get("nr", 0),
            "win_pct": round(s.get("won", 0) / p * 100, 1) if p else 0,
            "by_format": {k: dict(v) for k, v in s["by_format"].items()},
        })

    venue_list = sorted(
        ({
            "venue": v, "city": s.get("city", ""), "home": s.get("home", False),
            "played": s["played"], "won": s.get("won", 0), "lost": s.get("lost", 0),
            "draw": s.get("draw", 0), "tied": s.get("tied", 0), "nr": s.get("nr", 0),
            "win_pct": round(s.get("won", 0) / s["played"] * 100, 1) if s["played"] else 0,
        } for v, s in by_venue.items()),
        key=lambda x: -x["played"],
    )

    fmt_out = {k: dict(v) for k, v in by_format.items()}
    for v in fmt_out.values():
        p = v["played"]
        v["win_pct"] = round(v.get("won", 0) / p * 100, 1) if p else 0

    # Official career totals (Wikipedia / ESPNcricinfo mid-2026)
    official = {
        "Test": {"total": 599, "won": 186, "lost": 188, "draw": 224, "tied": 1},
        "ODI": {"total": 1078, "won": 574, "lost": 450, "tied": 10, "nr": 44},
        "T20": {"total": 283, "won": 187, "lost": 80, "tied": 1, "nr": 9},
    }
    our = {fmt: by_format[fmt]["played"] for fmt in ("Test", "ODI", "T20")}
    earliest = min(m["date"] for m in match_list if m["date"])
    latest = max(m["date"] for m in match_list if m["date"])

    # full-ball matches only for quality-aware coverage note
    full_by_fmt = Counter(m["format"] for m in match_list if m.get("quality") == "full")

    missing = {
        "summary": {
            "dataset_matches": len(match_list),
            "full_ball_matches": quality["full"],
            "partial_matches": quality["partial"],
            "empty_shells": quality["empty"],
            "cricsheet_claimed": 1009,
            "withheld_afghanistan_policy": 18,
            "date_range": [earliest, latest],
            "note": "Cricsheet + recovered India male internationals. Empty shells lack ball-by-ball; official totals are independent.",
        },
        "quality": quality,
        "by_format_vs_official": {
            fmt: {
                "in_dataset": our[fmt],
                "full_ball": full_by_fmt.get(fmt, 0),
                "official_approx": official[fmt]["total"],
                "estimated_missing": max(0, official[fmt]["total"] - our[fmt]),
                "coverage_pct": round(our[fmt] / official[fmt]["total"] * 100, 1) if official[fmt]["total"] else 0,
                "full_ball_pct": round(full_by_fmt.get(fmt, 0) / official[fmt]["total"] * 100, 1) if official[fmt]["total"] else 0,
                "official_source_note": "Wikipedia / ICC career totals as of mid-2026",
            }
            for fmt in ("Test", "ODI", "T20")
        },
        "historical_gap": {
            "tests_before_dataset": "India played Tests from 1932. Full ball-by-ball is sparse pre-2000s.",
            "odis_before_dataset": "India ODIs from 1974. Largest gap vs official ~1,078 is pre-archive + incomplete shells.",
            "t20_coverage": "T20Is from 2006; archive is near/at full career count (reconcile ties/NR vs official 283).",
        },
        "withheld": {
            "count": 18,
            "reason": "Cricsheet policy: matches featuring Afghanistan men's team or Afghanistan Premier League are withheld.",
            "url": "https://cricsheet.org/withheld-matches",
            "impact": "India vs Afghanistan internationals (and any APL-related) after the policy are not always present.",
        },
        "coverage": {
            fmt: f"{our[fmt]} of ~{official[fmt]['total']} ({round(our[fmt] / official[fmt]['total'] * 100, 1)}%); full-ball {full_by_fmt.get(fmt, 0)}"
            for fmt in ("Test", "ODI", "T20")
        },
    }

    event_list = []
    for name, s in by_event.items():
        p = s["played"]
        event_list.append({
            "name": name,
            "played": p,
            "won": s.get("won", 0),
            "lost": s.get("lost", 0),
            "draw": s.get("draw", 0),
            "tied": s.get("tied", 0),
            "nr": s.get("nr", 0),
            "win_pct": round(s.get("won", 0) / p * 100, 1) if p else 0,
            "formats": sorted(s["formats"]),
            "first": s["first"],
            "last": s["last"],
            "match_ids": s["match_ids"][:40],
        })
    event_list.sort(key=lambda x: -x["played"])

    india_names = set(batters) | set(bowlers)
    pom_list_out = [{"player": p, "awards": c} for p, c in pom.most_common() if p in india_names]

    out = {
        "meta": {
            "title": "Team India Cricket Dashboard",
            "generated": datetime.now().isoformat(timespec="seconds"),
            "source": "Cricsheet India male international JSON",
            "matches": len(match_list),
            "date_range": [earliest, latest],
            "formats": fmt_out,
            "design_inspired_by": "https://crickrida.rkjat.in",
        },
        "overall": {**overall, "win_pct": round(overall["won"] / overall["played"] * 100, 1) if overall["played"] else 0},
        "by_format": fmt_out,
        "by_home_away": {
            k: {**v, "win_pct": round(v.get("won", 0) / v["played"] * 100, 1) if v["played"] else 0}
            for k, v in by_home_away.items()
        },
        "toss": toss_stats,
        "opponents": opp_list,
        "years": year_list,
        "venues": venue_list[:80],
        "batting": batting_list[:200],
        "bowling": bowling_list[:200],
        "fielding": fielding_list[:100],
        "pom": pom_list_out[:50],
        "events": event_list[:200],
        "records": {
            "highest_totals": highest_totals[:40],
            "lowest_totals": lowest_completed[:25],
            "highest_individual": notable_innings[:50],
            "best_bowling": notable_bowling[:50],
            "biggest_wins_runs": biggest_wins_runs[:20],
            "biggest_wins_wickets": biggest_wins_wickets[:20],
            "biggest_defeats_runs": biggest_defeats_runs[:15],
        },
        "matches": match_list,
        "missing": missing,
    }

    with OUT.open("w") as f:
        json.dump(out, f)
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024 / 1024:.1f} MB)")
    print("Overall:", out["overall"])
    print("Missing:", json.dumps(missing["by_format_vs_official"], indent=2))


if __name__ == "__main__":
    main()
