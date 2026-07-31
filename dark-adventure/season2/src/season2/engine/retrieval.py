"""Module-chunk retrieval (Phase 2). Given where the party is / what is
happening, return the relevant chunks: vector hits + adjacency expansion.

Requires migrations/phase2.sql (embedding column at Voyage dims, metadata
column, match_module_chunks() function, ivfflat index after load).
"""
from __future__ import annotations

import os

EMBED_MODEL = os.getenv("EMBED_MODEL", "voyage-3.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))


def _embed_query(query: str) -> list[float]:
    from dotenv import load_dotenv
    load_dotenv()
    import voyageai
    vo = voyageai.Client()
    return vo.embed([query], model=EMBED_MODEL, input_type="query",
                    output_dimension=EMBED_DIM).embeddings[0]


def chunks_for_query(query: str, k: int = 6, module_code: str | None = None) -> list[dict]:
    """Pure vector search via the match_module_chunks SQL function."""
    from ..db import client
    c = client()
    hits = c.rpc("match_module_chunks", dict(
        query_embedding=_embed_query(query), match_count=k,
        filter_module_code=module_code,
    )).execute().data
    return hits or []


def chunks_for_location(area_id: str, query: str | None = None, k: int = 4,
                        module_code: str | None = None) -> list[dict]:
    """The Phase 4 workhorse: the chunk for the CURRENT area, all chunks it
    connects to, plus (optionally) vector hits for what's happening there.
    De-duplicated, current area first."""
    from ..db import client
    c = client()

    def by_area(aid: str) -> list[dict]:
        q = (c.table("documents").select("id, title, content, metadata")
             .eq("kind", "module_chunk").eq("metadata->>area_id", aid))
        return q.execute().data or []

    out: list[dict] = []
    seen: set[str] = set()

    def add(rows: list[dict]):
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)

    current = by_area(area_id)
    add(current)
    for r in current:
        for neighbour in (r.get("metadata") or {}).get("connections", []):
            add(by_area(neighbour))
    if query:
        add([h for h in chunks_for_query(query, k=k, module_code=module_code)])
    return out
