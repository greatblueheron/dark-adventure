"""Supabase client + read utilities. The database is the source of truth
for the campaign; these commands are how you look at it.

Usage:
  python -m season2.db check    # connectivity + campaign list
  python -m season2.db roster   # full party from the DB (stats, alignment, spells)
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def check() -> None:
    c = client()
    res = c.table("campaigns").select("id, name, status").execute()
    print(f"OK — connected. {len(res.data)} campaign(s) found.")
    for row in res.data:
        print(f"  {row['name']} [{row['status']}]")


def roster() -> None:
    c = client()
    rows = (c.table("characters")
             .select("name, is_protagonist, ancestry, class, alignment, level, xp, "
                     "current_hp, max_hp, armor_class, status, stats, spells_known, "
                     "spell_slots, conditions")
             .order("is_protagonist", desc=True).order("name").execute().data)
    if not rows:
        print("No characters found — has the campaign been seeded?")
        return
    for r in rows:
        tag = "  [PROTAGONIST]" if r["is_protagonist"] else ""
        dead = "" if r["status"] == "alive" else f"  ({r['status'].upper()})"
        print(f"{r['name']} — {r['ancestry']} {r['class']} {r['level']}, "
              f"{r['alignment']}{tag}{dead}")
        print(f"  HP {r['current_hp']}/{r['max_hp']}  AC {r['armor_class']}  "
              f"XP {r['xp']}  {r['stats']}")
        if r["spells_known"]:
            print(f"  Spells known: {', '.join(r['spells_known'])}  "
                  f"(slots: {r['spell_slots']})")
        if r["conditions"]:
            print(f"  Conditions: {r['conditions']}")
    print(f"{len(rows)} characters. The database is the source of truth.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "check":
        check()
    elif cmd == "roster":
        roster()
    else:
        print("Usage: python -m season2.db [check|roster]")
