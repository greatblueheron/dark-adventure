-- ============================================================
-- Phase 2 migration: module chunks + Voyage embeddings + retrieval
-- Run BEFORE `ingest load`. (Post-load section at the bottom.)
-- ============================================================

-- Voyage models output 1024-d vectors (schema originally sized for 1536).
-- Column is empty at this point, so the alter is trivial.
alter table documents alter column embedding type vector(1024);

-- Chunk metadata (area ids, sections, adjacency).
alter table documents add column if not exists metadata jsonb not null default '{}'::jsonb;
create index if not exists idx_documents_area
  on documents ((metadata->>'area_id')) where kind = 'module_chunk';

-- Vector search entry point used by engine/retrieval.py.
create or replace function match_module_chunks(
  query_embedding vector(1024),
  match_count int default 6,
  filter_module_code text default null
) returns table (id uuid, title text, content text, metadata jsonb, similarity float)
language sql stable as $$
  select d.id, d.title, d.content, d.metadata,
         1 - (d.embedding <=> query_embedding) as similarity
  from documents d
  where d.kind = 'module_chunk'
    and d.embedding is not null
    and (filter_module_code is null
         or d.metadata->>'module_code' = filter_module_code)
  order by d.embedding <=> query_embedding
  limit match_count;
$$;

grant execute on function match_module_chunks to service_role;

-- ---------- run AFTER `ingest load` has inserted the chunks ----------
-- (ivfflat builds better with data present; ~100 lists is fine at this scale)
-- create index if not exists idx_documents_embedding on documents
--   using ivfflat (embedding vector_cosine_ops) with (lists = 100);
-- analyze documents;
