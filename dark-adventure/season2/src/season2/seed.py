"""Seed the campaign: roll the 10-character party and insert everything.

Usage:
  poetry run python -m season2.seed --dry-run          # print, insert nothing
  poetry run python -m season2.seed                    # insert into Supabase
  poetry run python -m season2.seed --seed 1974        # reproducible party
  poetry run python -m season2.seed --protagonist-class Fighter

Safe to inspect with --dry-run as many times as you like; reroll by varying
--seed until you get a party you like, then run for real ONCE.
"""
from __future__ import annotations

import argparse
import json

from .rules.chargen import generate_party, DEFAULT_COMPOSITION
from .rules.dice import Dice

# Placeholder names — rename freely (or have the Phase 3 bootstrap
# generate names; these exist so the seed is runnable today).
DEFAULT_NAMES = [
    "PROTAGONIST", "Branwen", "Cedric", "Mother Aldith", "Josserand",
    "Wystan", "Fenna", "Durgan Ironvein", "Sylvaris", "Perrin Underbough",
]

CAMPAIGN_NAME = "Whispers in Green Static — Season 2"


def build(seed: int | None, protagonist_class: str | None) -> dict:
    dice = Dice(seed=seed)
    comp = list(DEFAULT_COMPOSITION)
    if protagonist_class:
        comp[0] = protagonist_class
    party = generate_party(dice, DEFAULT_NAMES, protagonist_index=0, composition=comp)
    return dict(campaign=dict(name=CAMPAIGN_NAME, status="active", ruleset="B/X (OSE)"),
                party=party)


def insert(payload: dict) -> None:
    from .db import client
    c = client()
    camp = c.table("campaigns").insert(payload["campaign"]).execute().data[0]
    print(f"Campaign created: {camp['id']}")
    for entry in payload["party"]:
        ch = dict(entry["character"], campaign_id=camp["id"])
        row = c.table("characters").insert(ch).execute().data[0]
        items = [dict(i, campaign_id=camp["id"], character_id=row["id"])
                 for i in entry["starting_items"]]
        c.table("inventory_items").insert(items).execute()
        tag = " [PROTAGONIST]" if row["is_protagonist"] else ""
        print(f"  {row['name']}: {row['class']} — HP {row['max_hp']}, "
              f"AC {row['armor_class']}{tag}")
    print("Done. Check the party_sheet view in Supabase.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--protagonist-class", default=None)
    args = ap.parse_args()

    payload = build(args.seed, args.protagonist_class)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        for e in payload["party"]:
            ch = e["character"]
            tag = " [PROTAGONIST]" if ch["is_protagonist"] else ""
            print(f"{ch['name']:>18}: {ch['class']:<10} HP {ch['max_hp']:>2} "
                  f"AC {ch['armor_class']} {ch['stats']}{tag}")
    else:
        insert(payload)


if __name__ == "__main__":
    main()
