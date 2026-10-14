"""
Fetch the frozen Pokémon TCG dataset from the public Limitless Tournament API.

Purpose
-------
This script documents how data/raw/decklists_snapshot.csv was collected.
The analysis notebook does NOT call the API every time; it reads the frozen snapshot
so the submitted report can be reproduced exactly.

Privacy / minimization
----------------------
Player names may appear temporarily in the API response but are NOT written to the
repository. Published deck IDs are anonymous sequential IDs (D0001, D0002, ...).

Run from repository root:
    python src/fetch_limitless_api.py

Output:
    data/raw/decklists_snapshot.csv
    data/raw/decklists_summary.csv
    data/raw/tournaments.csv
    data/raw/source_audit.csv
"""

from pathlib import Path
import importlib.util
import subprocess
import sys
import time
import json
import re

required = ["requests", "pandas"]
missing = [p for p in required if importlib.util.find_spec(p) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])

import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

API = "https://play.limitlesstcg.com/api"
GAME = "PTCG"
ORGANIZER_ID = 36
TOURNAMENT_NAME_FILTER = "pumpkaweekly"
START = pd.Timestamp("2026-09-14T00:00:00Z")
END = pd.Timestamp("2026-09-29T00:00:00Z")  # exclusive

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "MADT7202-academic-network-analysis/1.0"

COUNT_KEYS = {"count", "quantity", "amount", "copies", "qty"}

def get_json(path, params=None, retries=5):
    url = API + path
    last = None
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=45)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10 * (attempt + 1)))
                print(f"HTTP 429: wait {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            print(f"HTTP {r.status_code} | {r.url}")
            return r.json()
        except Exception as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"API request failed: {url}\n{last}")

def category_from(path):
    p = " ".join(map(str, path)).lower()
    if "pokemon" in p or "pokémon" in p:
        return "Pokemon"
    if "trainer" in p:
        return "Trainer"
    if "energy" in p:
        return "Energy"
    return "Unknown"

def parse_text_decklist(text):
    rows, category = [], "Unknown"
    for raw in str(text).splitlines():
        line = raw.strip()
        low = line.lower()
        if not line:
            continue
        if low.startswith(("pokemon:", "pokémon:")):
            category = "Pokemon"; continue
        if low.startswith("trainer:"):
            category = "Trainer"; continue
        if low.startswith("energy:"):
            category = "Energy"; continue
        if low.startswith("total cards"):
            continue

        m = re.match(r"^(\d+)\s+(.+)$", line)
        if not m:
            continue

        copies = int(m.group(1))
        rest = m.group(2).strip()
        name = re.sub(
            r"\s+[A-Z0-9-]{2,12}\s+\d+[A-Za-z-]*(?:\s+PH)?$",
            "",
            rest
        ).strip()
        rows.append((name or rest, copies, category))
    return rows

def parse_decklist(obj):
    found = []

    if isinstance(obj, str):
        found.extend(parse_text_decklist(obj))
    else:
        def walk(x, path=()):
            if isinstance(x, dict):
                keymap = {str(k).lower(): k for k in x}

                copies = None
                for ck in COUNT_KEYS:
                    if ck in keymap:
                        try:
                            val = int(x[keymap[ck]])
                            if val > 0:
                                copies = val
                                break
                        except Exception:
                            pass

                name = None
                for nk in ("name", "cardname", "card_name"):
                    if nk in keymap and isinstance(x[keymap[nk]], str):
                        name = x[keymap[nk]].strip()
                        break

                if name is None and copies is not None:
                    card = x.get("card")
                    if isinstance(card, str):
                        name = card.strip()
                    elif isinstance(card, dict) and isinstance(card.get("name"), str):
                        name = card["name"].strip()

                if name and copies:
                    found.append((name, copies, category_from(path)))
                    return

                for k, v in x.items():
                    if isinstance(v, str) and str(k).lower() in {
                        "text", "list", "decktext", "deck_text"
                    }:
                        found.extend(parse_text_decklist(v))
                    else:
                        walk(v, path + (k,))

            elif isinstance(x, list):
                for y in x:
                    walk(y, path)
            elif isinstance(x, str):
                parsed = parse_text_decklist(x)
                if parsed:
                    found.extend(parsed)

        walk(obj)

    if not found:
        return []

    d = pd.DataFrame(found, columns=["card", "copies", "category"])
    d["card"] = d["card"].astype(str).str.strip()
    d = d[(d["card"] != "") & (d["copies"] > 0)].copy()

    g = d.groupby(["card", "category"], as_index=False)["copies"].sum()
    best_category = (
        g.sort_values("copies", ascending=False)
         .drop_duplicates("card")
         .set_index("card")["category"]
    )
    total = g.groupby("card", as_index=False)["copies"].sum()
    total["category"] = total["card"].map(best_category)
    return total.to_dict("records")

# Discover the three tournaments from the API.
tour = get_json(
    "/tournaments",
    {"game": GAME, "organizerId": ORGANIZER_ID, "limit": 50}
)
t = pd.DataFrame(tour)
t["date"] = pd.to_datetime(t["date"], utc=True)

selected = t[
    (t["game"] == GAME)
    & (t["date"] >= START)
    & (t["date"] < END)
    & t["name"].str.lower().str.contains(TOURNAMENT_NAME_FILTER, na=False)
].sort_values("date").copy()

if selected.empty:
    raise RuntimeError("No target tournaments found.")
if selected["format"].nunique() != 1:
    raise RuntimeError("Selected tournaments have different formats.")

selected.to_csv(OUT / "tournaments.csv", index=False)

all_decks = []
all_cards = []
source_rows = []
deck_counter = 0

for _, trow in selected.iterrows():
    tid = trow["id"]
    details = get_json(f"/tournaments/{tid}/details")
    standings = get_json(f"/tournaments/{tid}/standings")

    source_rows.append({
        "tournament_id": tid,
        "tournament_name": trow["name"],
        "date": trow["date"].isoformat(),
        "format": trow["format"],
        "listed_players": int(trow["players"]),
        "standings_rows": len(standings),
        "decklists_setting": details.get("decklists"),
        "is_public": details.get("isPublic"),
        "public_page": f"https://play.limitlesstcg.com/tournament/{tid}/details",
        "api_standings": f"{API}/tournaments/{tid}/standings",
    })

    for s in standings:
        payload = s.get("decklist")
        parsed = parse_decklist(payload) if payload is not None else []
        total_copies = int(sum(x["copies"] for x in parsed))

        # Only retain validated 60-card decklists.
        if total_copies != 60:
            continue

        deck_counter += 1
        deck_id = f"D{deck_counter:04d}"

        deck_obj = s.get("deck")
        archetype = deck_obj.get("name") if isinstance(deck_obj, dict) else None

        all_decks.append({
            "deck_id": deck_id,
            "tournament_id": tid,
            "tournament": trow["name"],
            "tournament_date": trow["date"].isoformat(),
            "archetype": archetype,
            "unique_card_names": len(parsed),
            "total_copies": total_copies,
            "valid_60": True,
        })

        for card in parsed:
            all_cards.append({
                "deck_id": deck_id,
                "tournament_id": tid,
                "tournament_date": trow["date"].isoformat(),
                "archetype": archetype,
                "card": card["card"],
                "category": card["category"],
                "copies": card["copies"],
            })

    time.sleep(0.35)

deck_df = pd.DataFrame(all_decks)
card_df = pd.DataFrame(all_cards)
audit_df = pd.DataFrame(source_rows)

deck_df.to_csv(OUT / "decklists_summary.csv", index=False)
card_df.to_csv(OUT / "decklists_snapshot.csv", index=False)
audit_df.to_csv(OUT / "source_audit.csv", index=False)

print("\nFETCH COMPLETE")
print("Valid 60-card decklists:", len(deck_df))
print("Card-line rows:", len(card_df))
print("Saved to:", OUT)
