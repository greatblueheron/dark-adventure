"""Supabase client + read utilities. The database is the source of truth
for the campaign; these commands are how you look at it.

Usage:
  python -m season2.db check    # connectivity + campaign list
  python -m season2.db roster   # full party from the DB (stats, alignment, spells)
  python -m season2.db export-json  # zero-install JSON export -> backups/
  python -m season2.db dump     # pg_dump snapshot -> backups/ (needs pg_dump
                                #   installed + SUPABASE_DB_URL in .env)
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


def dump(label: str | None = None) -> None:
    """Logical backup of the whole campaign database via pg_dump.
    Requires SUPABASE_DB_URL in .env (the *session* connection string,
    port 5432 — not the transaction pooler on 6543) and pg_dump on PATH."""
    import shutil
    import subprocess
    from datetime import datetime

    url = os.environ.get("SUPABASE_DB_URL")
    assert url, "set SUPABASE_DB_URL in .env (Supabase: Connect -> Session pooler URI)"
    assert shutil.which("pg_dump"), (
        "pg_dump not found on PATH - install PostgreSQL client tools")
    os.makedirs("backups", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    name = f"backups/season2-{stamp}" + (f"-{label}" if label else "") + ".sql"
    subprocess.run(["pg_dump", url, "--schema=public", "--no-owner",
                    "--no-privileges", "-f", name], check=True)
    size = os.path.getsize(name) // 1024
    print(f"Snapshot written: {name} ({size} KB). Store a copy off this "
          f"machine; it contains ALL hidden truths and module text - keep "
          f"it out of anything public.")


TABLES = ["campaigns", "modules", "characters", "inventory_items", "npcs",
          "episodes", "scenes", "events", "summaries", "documents"]


def export_json(label: str | None = None) -> None:
    """Zero-install logical export: every row of every table via the API,
    written to backups/ as one JSON file. Embeddings are excluded (they are
    regenerable from content). Not a pg_restore file - but a complete,
    human-readable copy of the campaign that could be reloaded via the API."""
    import json
    from datetime import datetime
    c = client()
    out = {}
    for t in TABLES:
        rows, page = [], 0
        while True:
            batch = (c.table(t).select("*").range(page * 1000, page * 1000 + 999)
                     .execute().data)
            rows.extend(batch)
            if len(batch) < 1000:
                break
            page += 1
        for r in rows:
            r.pop("embedding", None)
        out[t] = rows
        print(f"  {t}: {len(rows)} rows")
    os.makedirs("backups", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    name = f"backups/season2-{stamp}" + (f"-{label}" if label else "") + ".json"
    with open(name, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print(f"Export written: {name} ({os.path.getsize(name)//1024} KB). "
          f"Contains all hidden truths and module text - private storage only.")


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
    print(f"\n{len(rows)} characters. The database is the source of truth.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "check":
        check()
    elif cmd == "roster":
        roster()
    elif cmd == "dump":
        dump(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "export-json":
        export_json(sys.argv[2] if len(sys.argv) > 2 else None)
    else:
        print("Usage: python -m season2.db [check|roster]")
