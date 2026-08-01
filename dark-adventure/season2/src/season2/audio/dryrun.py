"""Phase 6 audio CLI — attribution dry-run over approved episodes.

  poetry run python -m season2.audio dry-run              # all approved
  poetry run python -m season2.audio dry-run --episode 3

Writes scripts/ep{N}-scene{I}.annotated.txt (+ .spans.jsonl) and prints
attribution statistics. No audio is generated; this is the measurement
stage that decides how ready the prose is for multi-voice.
"""
from __future__ import annotations

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ..db import client
from ..bootstrap import fetch_campaign
from ..engine import attribution as A
from ..engine.loop import llm


def cast_names(c, camp) -> set[str]:
    names = {r["name"] for r in c.table("characters").select("name")
             .eq("campaign_id", camp["id"]).execute().data}
    names |= {n["name"] for n in c.table("npcs").select("name")
              .eq("campaign_id", camp["id"]).execute().data}
    return names


def attribute_scene(text: str, legal: set[str]):
    """Shared by dry-run and script generation: quotes -> resolved spans."""
    quotes = A.detect_quotes(text)
    if not quotes:
        return []
    prompt = A.ATTRIBUTION.format(speakers=sorted(legal),
                                  numbered=A.numbered_text(text, quotes))
    p1 = A.parse_pass(llm("audit", prompt, 3000), quotes, legal)
    p2 = A.parse_pass(llm("diff", prompt, 3000), quotes, legal)
    return A.resolve(p1, p2, quotes)


def dry_run(episode: int | None) -> None:
    c = client()
    camp = fetch_campaign(c)
    legal = cast_names(c, camp) | {A.NARRATOR}
    q = (c.table("episodes").select("id, number").eq("campaign_id", camp["id"])
         .eq("status", "approved"))
    eps = sorted(q.execute().data, key=lambda e: e["number"])
    if episode:
        eps = [e for e in eps if e["number"] == episode]
    os.makedirs("scripts", exist_ok=True)
    totals = dict(quotes=0, cast_attributed=0, narrator_fallback=0,
                  disagreements=0)
    for ep in eps:
        scenes = (c.table("scenes").select("index, full_text")
                  .eq("episode_id", ep["id"]).order("index").execute().data)
        for s in scenes:
            text = s["full_text"] or ""
            spans = attribute_scene(text, legal)
            if not spans:
                continue
            st = A.stats(spans)
            base = f"scripts/ep{ep['number']}-scene{s['index']}"
            with open(base + ".annotated.txt", "w", encoding="utf-8") as f:
                f.write(A.annotate(text, spans))
            with open(base + ".spans.jsonl", "w", encoding="utf-8") as f:
                for sp in spans:
                    f.write(json.dumps(sp, ensure_ascii=False) + "\n")
            for k in totals:
                totals[k] += st[k]
            print(f"ep{ep['number']} s{s['index']}: {st['quotes']} quotes, "
                  f"{st['cast_attributed']} cast, "
                  f"{st['narrator_fallback']} narrator "
                  f"({st['disagreements']} disagreements)")
    if totals["quotes"]:
        pct = 100 * totals["cast_attributed"] / totals["quotes"]
        print(f"\nTOTAL: {totals['quotes']} quotes | cast {pct:.0f}% | "
              f"fallback {totals['narrator_fallback']} | "
              f"disagreements {totals['disagreements']}")
        print("Review the scripts/ *.annotated.txt files - every [NAME|note] "
              "tag is a casting decision you can veto before audio exists.")


