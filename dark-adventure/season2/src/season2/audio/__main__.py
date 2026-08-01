"""audio CLI:
  poetry run python -m season2.audio dry-run [--episode N]
  poetry run python -m season2.audio script N
  poetry run python -m season2.audio render N [--scene I] [--estimate]
"""
import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    ap = argparse.ArgumentParser(prog="audio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run")
    d.add_argument("--episode", type=int, default=None)
    sc = sub.add_parser("script")
    sc.add_argument("number", type=int)
    re_ = sub.add_parser("render")
    re_.add_argument("number", type=int)
    re_.add_argument("--scene", type=int, default=None)
    re_.add_argument("--estimate", action="store_true")
    a = ap.parse_args()
    if a.cmd == "dry-run":
        from .dryrun import dry_run
        dry_run(a.episode)
    elif a.cmd == "script":
        from .render import generate_scripts
        generate_scripts(a.number)
    elif a.cmd == "render":
        from .render import render_episode
        render_episode(a.number, a.scene, a.estimate)


main()
