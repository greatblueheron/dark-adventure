"""Phase 2 module ingestion — turn the actual B2 PDF into retrievable,
location-keyed chunks in the `documents` table.

Pipeline (each step reviewable before the next):

  1. extract   PDF -> plain text            (pypdf; or skip and paste text yourself)
  2. chunk     text -> chunks.jsonl         (Claude segments by keyed area,
                                             emits metadata: area ids, names,
                                             sections, connections)
     -> REVIEW chunks.jsonl by hand: fix boundaries, area ids, connections.
  3. load      chunks.jsonl -> Supabase     (Voyage embeddings; creates the
                                             module row; sets campaign's
                                             current module if unset)
  4. search    query -> top chunks          (the Phase 2 gate test)

Usage:
  poetry run python -m season2.ingest extract b2.pdf --out b2.txt
  poetry run python -m season2.ingest chunk b2.txt --module B2 --out b2-chunks.jsonl
  poetry run python -m season2.ingest load b2-chunks.jsonl --module B2 \\
      --title "The Keep on the Borderlands" --levels 1-3
  poetry run python -m season2.ingest search "party at the Caves of Chaos entrance"

Requires VOYAGE_API_KEY in .env (Anthropic's recommended embeddings
provider; Anthropic itself has no embeddings API). Run
migrations/phase2.sql in Supabase BEFORE `load`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

EMBED_MODEL = os.getenv("EMBED_MODEL", "voyage-3.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

# ---------------------------------------------------------------- step 1: extract

def extract(pdf_path: str, out: str) -> None:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(pages)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Extracted {len(reader.pages)} pages -> {out} ({len(text)} chars).")
    print("Skim the file: if keyed areas look garbled, fix by hand before `chunk`.")

# ---------------------------------------------------------------- step 2: chunk

CHUNK_PROMPT = """You are preparing the CLASSIC MODULE text below for a
retrieval system that feeds a Dungeon-Master AI one location at a time.
Segment it into chunks and return ONLY a JSON array (no fences, no prose).

Each chunk object:
{{
 "area_id":   short stable key, e.g. "KEEP-12", "CAVES-B3", "WILDERNESS",
              "RUMORS", "WANDERING-CAVES", "INTRO", "KEEP-OVERVIEW"
 "area_name": human name, e.g. "Tavern", "Kobold Lair - Guard Room"
 "section":   one of "intro" | "keep" | "wilderness" | "caves" | "tables" | "appendix"
 "content":   the chunk text, VERBATIM from the source (do not summarise,
              do not rewrite; preserve stat blocks and boxed text exactly)
 "connections": array of area_ids physically adjacent/connected (doors,
              passages, "to area X" references). Empty array if unknown.
}}

Rules:
- One chunk per keyed/numbered location. Small related sub-areas (e.g.
  "3a") may share their parent's chunk.
- Rumor tables and wandering-monster tables get their OWN chunks with
  section "tables" (the game engine will roll on them).
- Overview/read-aloud text for a region (the Keep generally, a cave mouth
  area) gets its own "-OVERVIEW" chunk.
- Aim for chunks of roughly 150-800 words; merge tiny fragments into their
  parent location rather than emitting slivers.
- Cover ALL substantive game content in the text you were given. DM-advice
  essays may be compressed into one "appendix" chunk or skipped if pure
  how-to-referee pedagogy.

MODULE TEXT ({part}):
---
{text}
---"""


def _windows(text: str, max_chars: int = 60000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    out, rest = [], text
    while rest:
        if len(rest) <= max_chars:
            out.append(rest)
            break
        cut = rest.rfind("\n\n", 0, max_chars)
        cut = cut if cut > max_chars // 2 else max_chars
        out.append(rest[:cut])
        rest = rest[cut:]
    return out


def default_call(prompt: str, max_tokens: int = 32000) -> str:
    from dotenv import load_dotenv
    load_dotenv()
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.getenv("WRITER_MODEL", "claude-opus-4-8"),
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def parse_chunks(raw: str) -> list[dict]:
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    data = json.loads(cleaned)
    assert isinstance(data, list)
    for ch in data:
        for key in ("area_id", "area_name", "section", "content"):
            assert isinstance(ch.get(key), str) and ch[key].strip(), f"bad chunk: {ch.get('area_id')}"
        ch.setdefault("connections", [])
        assert isinstance(ch["connections"], list)
    return data


def chunk(text_path: str, module_code: str, out: str, call_fn=default_call) -> None:
    with open(text_path, encoding="utf-8") as f:
        text = f.read()
    windows = _windows(text)
    chunks: list[dict] = []
    for i, w in enumerate(windows, 1):
        print(f"Chunking window {i}/{len(windows)} ({len(w)} chars)...")
        raw = call_fn(CHUNK_PROMPT.format(part=f"part {i} of {len(windows)}", text=w))
        chunks.extend(parse_chunks(raw))
    # de-duplicate area_ids across windows (later wins, warn)
    seen: dict[str, int] = {}
    for idx, ch in enumerate(chunks):
        if ch["area_id"] in seen:
            print(f"  WARNING: duplicate area_id {ch['area_id']} — keeping both; "
                  f"resolve during review.")
        seen[ch["area_id"]] = idx
    with open(out, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")
    words = sum(len(ch["content"].split()) for ch in chunks)
    print(f"{len(chunks)} chunks -> {out} ({words} words total).")
    print("REVIEW THE FILE before `load`: check boundaries, area ids, connections.")

# ---------------------------------------------------------------- step 3: load

def _embed(texts: list[str]) -> list[list[float]]:
    from dotenv import load_dotenv
    load_dotenv()
    import voyageai
    vo = voyageai.Client()          # uses VOYAGE_API_KEY
    out: list[list[float]] = []
    for i in range(0, len(texts), 64):
        batch = texts[i:i + 64]
        res = vo.embed(batch, model=EMBED_MODEL, input_type="document",
                       output_dimension=EMBED_DIM)
        out.extend(res.embeddings)
    return out


def load(jsonl_path: str, module_code: str, title: str, levels: str) -> None:
    from .db import client
    c = client()
    camp = c.table("campaigns").select("*").eq("status", "active").execute().data[0]

    existing = (c.table("modules").select("*").eq("campaign_id", camp["id"])
                .eq("code", module_code).execute().data)
    if existing:
        module = existing[0]
    else:
        lo, hi = (levels.split("-") + [levels])[:2]
        module = c.table("modules").insert(dict(
            campaign_id=camp["id"], code=module_code, title=title,
            level_min=int(lo), level_max=int(hi), status="active", order_index=1,
        )).execute().data[0]
        print(f"Module row created: {module_code} — {title}")
    if not camp.get("current_module_id"):
        c.table("campaigns").update({"current_module_id": module["id"]}).eq(
            "id", camp["id"]).execute()
        print("Campaign current module set.")

    with open(jsonl_path, encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    print(f"Embedding {len(chunks)} chunks with {EMBED_MODEL} ({EMBED_DIM}d)...")
    # Embed name+content so area names weigh into similarity.
    vectors = _embed([f"{ch['area_name']}\n{ch['content']}" for ch in chunks])

    rows = [dict(
        campaign_id=camp["id"], kind="module_chunk", module_id=module["id"],
        title=f"{module_code}:{ch['area_id']} {ch['area_name']}",
        content=ch["content"], embedding=vec,
        metadata=dict(area_id=ch["area_id"], area_name=ch["area_name"],
                      section=ch["section"], connections=ch["connections"],
                      module_code=module_code),
    ) for ch, vec in zip(chunks, vectors)]
    for i in range(0, len(rows), 50):
        c.table("documents").insert(rows[i:i + 50]).execute()
    print(f"Loaded {len(rows)} chunks. Now build the index (see migrations/phase2.sql "
          f"post-load section), then run `ingest search` to test the gate.")

# ---------------------------------------------------------------- step 4: search

def search(query: str, k: int = 6) -> None:
    from .engine.retrieval import chunks_for_query
    hits = chunks_for_query(query, k=k)
    if not hits:
        print("No hits — has `load` run and the match function been created?")
        return
    for h in hits:
        print(f"[{h['similarity']:.3f}] {h['title']}  "
              f"(section={h['metadata'].get('section')}, "
              f"connects={h['metadata'].get('connections')})")
        print(f"    {h['content'][:160].replace(chr(10), ' ')}...")

# ---------------------------------------------------------------- CLI

def main() -> None:
    ap = argparse.ArgumentParser(prog="ingest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("pdf"); e.add_argument("--out", required=True)
    ch = sub.add_parser("chunk"); ch.add_argument("text"); ch.add_argument("--module", required=True)
    ch.add_argument("--out", required=True)
    lo = sub.add_parser("load"); lo.add_argument("jsonl"); lo.add_argument("--module", required=True)
    lo.add_argument("--title", required=True); lo.add_argument("--levels", default="1-3")
    se = sub.add_parser("search"); se.add_argument("query"); se.add_argument("-k", type=int, default=6)
    a = ap.parse_args()
    if a.cmd == "extract":
        extract(a.pdf, a.out)
    elif a.cmd == "chunk":
        chunk(a.text, a.module, a.out)
    elif a.cmd == "load":
        load(a.jsonl, a.module, a.title, a.levels)
    elif a.cmd == "search":
        search(a.query, a.k)


if __name__ == "__main__":
    main()
