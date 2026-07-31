-- ============================================================
-- Whispers in Green Static — Season 2 ("Borderlands" campaign)
-- Persistent AD&D 1e campaign state engine — Supabase/Postgres schema
-- (v2: ruleset default -> OSRIC; party_sheet includes ancestry+alignment)
-- Run in Supabase SQL editor. Assumes service-role access from
-- your pipeline (single-operator backend; RLS left disabled).
-- ============================================================

create extension if not exists vector;      -- pgvector, for module-text retrieval
create extension if not exists pgcrypto;    -- gen_random_uuid()

-- ---------- enums ----------
create type campaign_status  as enum ('active', 'completed', 'abandoned');
create type module_status    as enum ('planned', 'active', 'completed', 'skipped');
create type char_status      as enum ('alive', 'dead', 'retired', 'missing');
create type item_status      as enum ('held', 'stored', 'lost', 'destroyed', 'sold', 'given_away');
create type episode_status   as enum ('planned', 'outlined', 'drafted', 'audited', 'audio_rendered', 'published');
create type event_type       as enum (
  'death', 'level_up', 'xp_award', 'item_gained', 'item_lost',
  'injury', 'condition_gained', 'condition_removed',
  'npc_met', 'npc_died', 'quest_started', 'quest_completed',
  'location_discovered', 'party_decision', 'milestone', 'other'
);
create type summary_scope    as enum ('scene', 'episode', 'module_arc', 'campaign');
create type doc_kind         as enum (
  'protagonist_bible', 'character_bible', 'style_guide',
  'module_chunk', 'house_rules', 'world_lore', 'commercial_brief',
  'episode_script'
);

-- ---------- core ----------
create table campaigns (
  id                uuid primary key default gen_random_uuid(),
  name              text not null,
  status            campaign_status not null default 'active',
  ruleset           text not null default 'AD&D 1e (OSRIC)',   -- which rules the engine implements
  current_module_id uuid,                                -- FK added after modules
  in_world_date     text,                                -- freeform campaign calendar
  created_at        timestamptz not null default now()
);

create table modules (
  id            uuid primary key default gen_random_uuid(),
  campaign_id   uuid not null references campaigns(id) on delete cascade,
  code          text not null,               -- 'B2', 'X1', 'G1' ...
  title         text not null,
  level_min     int,
  level_max     int,
  status        module_status not null default 'planned',
  order_index   int,                         -- play order once chosen
  selection_notes text,                      -- why the selector picked it
  created_at    timestamptz not null default now()
);

alter table campaigns
  add constraint fk_current_module
  foreign key (current_module_id) references modules(id);

-- ---------- party ----------
create table characters (
  id              uuid primary key default gen_random_uuid(),
  campaign_id     uuid not null references campaigns(id) on delete cascade,
  name            text not null,
  is_protagonist  boolean not null default false,
  class           text not null,             -- 'Fighter', 'Magic-User', ...
  ancestry        text,                      -- race/ancestry per ruleset
  alignment       text,
  level           int not null default 1,
  xp              int not null default 0,
  max_hp          int not null,
  current_hp      int not null,
  armor_class     int not null,
  stats           jsonb not null,            -- {"STR":13,"INT":9,"WIS":11,"DEX":16,"CON":12,"CHA":10}
  saves           jsonb,                     -- per-ruleset save table snapshot
  abilities       jsonb not null default '[]'::jsonb,  -- class abilities, thief skills, etc.
  spells_known    jsonb not null default '[]'::jsonb,
  spell_slots     jsonb not null default '{}'::jsonb,  -- {"1": {"max":2,"used":0}}
  conditions      jsonb not null default '[]'::jsonb,  -- ["lost two fingers (L hand)", "cursed: ..."]
  status          char_status not null default 'alive',
  death_event_id  uuid,                      -- FK added after events
  voice_id        text,                      -- TTS voice mapping
  personality     text,                      -- short voice/behavior sketch for prompts
  created_at      timestamptz not null default now()
);
create index idx_characters_campaign on characters(campaign_id, status);

create table inventory_items (
  id              uuid primary key default gen_random_uuid(),
  campaign_id     uuid not null references campaigns(id) on delete cascade,
  character_id    uuid references characters(id),       -- null = party pool / mule
  name            text not null,
  description     text,
  quantity        int not null default 1,
  is_magical      boolean not null default false,
  is_identified   boolean not null default true,
  properties      jsonb not null default '{}'::jsonb,   -- {"bonus":"+1","charges":7}
  status          item_status not null default 'held',
  acquired_event_id uuid,
  lost_event_id     uuid,
  created_at      timestamptz not null default now()
);
create index idx_items_owner on inventory_items(character_id, status);

create table npcs (
  id            uuid primary key default gen_random_uuid(),
  campaign_id   uuid not null references campaigns(id) on delete cascade,
  module_id     uuid references modules(id),
  name          text not null,
  role          text,                        -- 'Castellan of the Keep'
  disposition   text,                        -- 'friendly', 'hostile', 'owes party a favor'
  status        char_status not null default 'alive',
  notes         text,
  first_seen_episode int,
  created_at    timestamptz not null default now()
);

-- ---------- episodes & narrative ----------
create table episodes (
  id             uuid primary key default gen_random_uuid(),
  campaign_id    uuid not null references campaigns(id) on delete cascade,
  module_id      uuid references modules(id),
  number         int not null,
  title          text,
  status         episode_status not null default 'planned',
  outline        jsonb,                      -- planned scene list
  script_path    text,                       -- Supabase Storage path to full script
  audio_path     text,
  transistor_id  text,
  published_at   timestamptz,
  created_at     timestamptz not null default now(),
  unique (campaign_id, number)
);

create table scenes (
  id           uuid primary key default gen_random_uuid(),
  episode_id   uuid not null references episodes(id) on delete cascade,
  index        int not null,
  location     text,
  full_text    text,                         -- generated prose (or Storage path if huge)
  mechanics_log jsonb,                       -- dice engine transcript fed to the writer
  state_diff   jsonb,                        -- extracted diff, pre-application
  audited      boolean not null default false,
  created_at   timestamptz not null default now(),
  unique (episode_id, index)
);

-- Append-only campaign log: the single source of truth for "what happened".
create table events (
  id            uuid primary key default gen_random_uuid(),
  campaign_id   uuid not null references campaigns(id) on delete cascade,
  episode_id    uuid references episodes(id),
  scene_id      uuid references scenes(id),
  type          event_type not null,
  character_id  uuid references characters(id),
  npc_id        uuid references npcs(id),
  description   text not null,               -- human-readable, prompt-ready one-liner
  data          jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now()
);
create index idx_events_campaign on events(campaign_id, created_at);
create index idx_events_character on events(character_id);

alter table characters
  add constraint fk_death_event foreign key (death_event_id) references events(id);
alter table inventory_items
  add constraint fk_acquired_event foreign key (acquired_event_id) references events(id),
  add constraint fk_lost_event     foreign key (lost_event_id) references events(id);

-- ---------- summaries (hierarchical memory) ----------
create table summaries (
  id           uuid primary key default gen_random_uuid(),
  campaign_id  uuid not null references campaigns(id) on delete cascade,
  scope        summary_scope not null,
  scene_id     uuid references scenes(id),
  episode_id   uuid references episodes(id),
  module_id    uuid references modules(id),
  content      text not null,
  token_count  int,
  version      int not null default 1,
  created_at   timestamptz not null default now()
);
create index idx_summaries_scope on summaries(campaign_id, scope);

-- ---------- reference documents & retrieval ----------
create table documents (
  id           uuid primary key default gen_random_uuid(),
  campaign_id  uuid not null references campaigns(id) on delete cascade,
  kind         doc_kind not null,
  module_id    uuid references modules(id),   -- for module_chunk
  title        text,
  content      text not null,
  embedding    vector(1536),                  -- match your embedding model dims
  created_at   timestamptz not null default now()
);
create index idx_documents_kind on documents(campaign_id, kind);
-- similarity search index (ivfflat; build after inserting chunks)
-- create index idx_documents_embedding on documents
--   using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ---------- convenience views ----------
create view party_sheet as
select c.name, c.is_protagonist, c.class, c.ancestry, c.alignment,
       c.level, c.xp, c.current_hp, c.max_hp, c.armor_class, c.status,
       c.conditions,
       coalesce(json_agg(json_build_object('item', i.name, 'qty', i.quantity))
                filter (where i.id is not null and i.status = 'held'), '[]') as inventory
from characters c
left join inventory_items i on i.character_id = c.id
group by c.id
order by c.is_protagonist desc, c.name;

create view campaign_log as
select e.created_at, ep.number as episode, e.type, c.name as character,
       n.name as npc, e.description
from events e
left join episodes ep on ep.id = e.episode_id
left join characters c on c.id = e.character_id
left join npcs n on n.id = e.npc_id
order by e.created_at;
