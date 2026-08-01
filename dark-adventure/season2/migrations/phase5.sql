-- Phase 5 tranche 2: the world that remembers
create table if not exists area_state (
  id          uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references campaigns(id) on delete cascade,
  area_id     text not null,
  state       jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now(),
  unique (campaign_id, area_id)
);
grant all on area_state to service_role;

-- expended spells persist across episodes now (reset by a night's rest)
alter table characters add column if not exists spells_used jsonb not null default '[]'::jsonb;
