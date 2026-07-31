"""Seed the campaign: roll the 10-character party and insert everything.

Usage:
  poetry run python -m season2.seed --dry-run                    # print only
  poetry run python -m season2.seed --seed 1974                  # reproducible party
  poetry run python -m season2.seed --seed 1974 --claude-names   # Claude names the cast
  poetry run python -m season2.seed --seed 1974 --claude-names --protagonist-name "..." 

Everything about the party — race, stats (5d6-drop-two-lowest IN ORDER), and
class — is decided by the dice; nobody arranges anything. The protagonist
is always Human (a modern person) with max level-1 HP.

Naming: the dice decide WHO exists (deterministic under --seed); Claude
proposes names for whoever they produced; you approve before anything is
inserted. Re-run for a fresh slate, or skip --claude-names to use
DEFAULT_NAMES / edit them by hand.

Safe to inspect with --dry-run as many times as you like; reroll by varying
--seed until you get a party you like, then run for real ONCE.
"""
from __future__ import annotations

import argparse
import json

from .rules.chargen import generate_party
from .rules.dice import Dice

# Placeholder names — rename freely (or have the Phase 3 bootstrap
# generate names; these exist so the seed is runnable today).
DEFAULT_NAMES = [
    "PROTAGONIST", "Branwen", "Cedric", "Mother Aldith", "Josserand",
    "Wystan", "Fenna", "Durgan Ironvein", "Sylvaris", "Perrin Underbough",
]

CAMPAIGN_NAME = "Whispers in Green Static — Season 2"


def build(seed: int | None) -> dict:
    dice = Dice(seed=seed)
    party = generate_party(dice, DEFAULT_NAMES, protagonist_index=0)
    return dict(campaign=dict(name=CAMPAIGN_NAME, status="active", ruleset="AD&D 1e (OSRIC)"),
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
        print(f"  {row['name']}: {row['ancestry']} {row['class']} — HP {row['max_hp']}, "
              f"AC {row['armor_class']}{tag}")
    print("Done. Check the party_sheet view in Supabase.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--claude-names", action="store_true",
                    help="have Claude propose names based on rolled class/race/stats")
    ap.add_argument("--protagonist-name", default=None,
                    help="override the protagonist's name (used with --claude-names)")
    ap.add_argument("--yes", action="store_true",
                    help="accept proposed names without interactive confirmation")
    args = ap.parse_args()

    payload = build(args.seed)

    if args.claude_names:
        from .engine.naming import name_party, apply_names
        names = name_party(payload["party"], protagonist_name=args.protagonist_name)
        print("Proposed names:")
        for entry, name in zip(payload["party"], names):
            c = entry["character"]
            tag = " [PROTAGONIST]" if c["is_protagonist"] else ""
            print(f"  {name:<24} {c['ancestry']} {c['class']}{tag}")
        if not args.yes and not args.dry_run:
            answer = input("Accept these names and continue? [y/N] ").strip().lower()
            if answer != "y":
                print("Aborted — re-run to get a fresh slate, or edit DEFAULT_NAMES manually.")
                return
        apply_names(payload["party"], names)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        for e in payload["party"]:
            ch = e["character"]
            tag = " [PROTAGONIST]" if ch["is_protagonist"] else ""
            print(f"{ch['name']:>18}: {ch['ancestry']:<8} {ch['class']:<11} "
                  f"{ch['alignment']:<15} HP {ch['max_hp']:>2} "
                  f"AC {ch['armor_class']} {ch['stats']}{tag}")
    else:
        insert(payload)


if __name__ == "__main__":
    main()
