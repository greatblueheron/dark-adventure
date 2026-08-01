-- Phase 6: audio. Voice assignments for cast and recurring NPCs.
alter table characters add column if not exists voice_id text;
alter table npcs       add column if not exists voice_id text;
