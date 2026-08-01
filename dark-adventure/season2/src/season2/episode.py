"""Episode CLI — the Phase 4 loop.

  poetry run python -m season2.episode register-ep1
  poetry run python -m season2.episode plan 2
  poetry run python -m season2.episode write 2
  poetry run python -m season2.episode show 2 [--scene 1]
  poetry run python -m season2.episode approve 2
  poetry run python -m season2.episode reject 2
  poetry run python -m season2.episode status
"""
from __future__ import annotations

import argparse
import sys

# Windows consoles default to cp1252; model output contains arrows, em
# dashes, etc. Force UTF-8 and never crash on an unprintable character.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import sys

# Windows consoles default to cp1252; force UTF-8 so prose/diffs with
# arrows, em-dashes etc. never crash a print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .db import client
from .bootstrap import fetch_campaign
from .engine import loop


def main() -> None:
    ap = argparse.ArgumentParser(prog="episode")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("register-ep1")
    for cmd in ("plan", "write", "approve", "reject"):
        p = sub.add_parser(cmd); p.add_argument("number", type=int)
        if cmd == "write":
            p.add_argument("--resume", action="store_true",
                           help="keep already-written scenes, continue from crash")
    sh = sub.add_parser("show"); sh.add_argument("number", type=int)
    sh.add_argument("--scene", type=int, default=None)
    sh.add_argument("--out", default=None,
                    help="write UTF-8 file directly (avoids console mangling)")
    sub.add_parser("status")
    a = ap.parse_args()

    if a.cmd == "register-ep1":
        loop.register_ep1()
    elif a.cmd == "plan":
        loop.plan_episode(a.number)
    elif a.cmd == "write":
        loop.write_episode(a.number, resume=getattr(a, "resume", False))
    elif a.cmd == "approve":
        loop.approve_episode(a.number)
    elif a.cmd == "reject":
        loop.reject_episode(a.number)
    elif a.cmd == "show":
        if a.out:
            f = open(a.out, "w", encoding="utf-8")
            import builtins
            _print = builtins.print
            builtins.print = lambda *args, **kw: _print(*args, **{**kw, "file": f})
        c = client(); camp = fetch_campaign(c)
        ep = (c.table("episodes").select("*").eq("campaign_id", camp["id"])
              .eq("number", a.number).execute().data)[0]
        scenes = (c.table("scenes").select("*").eq("episode_id", ep["id"])
                  .order("index").execute().data)
        print(f"== Episode {a.number}: {ep.get('title')} [{ep['status']}] ==")
        for s in scenes:
            if a.scene and s["index"] != a.scene:
                continue
            print(f"\n---- Scene {s['index']} [{s['location']}] "
                  f"audited={s['audited']} ----\n")
            print(s["full_text"])
            print("\n[STATE DIFF]", s["state_diff"])
    elif a.cmd == "status":
        c = client(); camp = fetch_campaign(c)
        eps = (c.table("episodes").select("number, title, status")
               .eq("campaign_id", camp["id"]).order("number").execute().data)
        print(f"Campaign: {camp['name']} — party at {camp.get('current_area')}")
        for e in eps:
            print(f"  ep {e['number']:>2}  [{e['status']:<9}] {e.get('title') or ''}")


if __name__ == "__main__":
    main()
