-- Phase 4: scene loop support
alter type episode_status add value if not exists 'approved';
alter table campaigns add column if not exists current_area text;
