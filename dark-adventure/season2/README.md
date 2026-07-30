# Season 2 — Implementation Roadmap

Drop this directory into `dark_adventure/season2/`. Each phase has a clear
"done when" gate. Don't start a phase until the previous gate passes.

---

## Phase 0 — Foundations (an evening)
- [ ] Restructure repo: `season1/`, `season2/`, plan for `shared/` later.
- [ ] `cd season2 && poetry install` — this scaffold installs.
      (Note: if `season2/` lives inside a repo that already has a root
      pyproject.toml, that's fine — Poetry treats this as its own project;
      just run poetry commands from inside `season2/`.)
- [ ] Supabase: create a **new project** (or a dedicated schema in your
      existing one — new project is cleaner; season 1 data stays untouched).
      Run `migrations/schema.sql` in the SQL editor.
- [ ] Copy `.env.example` → `.env`, fill in Supabase URL + service key,
      Anthropic API key. `poetry run python -m season2.db check` connects.

**Done when:** `poetry run pytest` passes and
`poetry run python -m season2.db check` prints OK.

## Phase 1 — Rules engine + seed party (a weekend or two)
Pure Python. No LLM calls. This is the layer everything trusts.
- [ ] `rules/dice.py` — done (implemented + tested in this scaffold).
- [ ]`rules/tables.py` — transcribe B/X (via OSE SRD, which is free and
      clearly licensed) tables: attack matrices/THAC0, saves, XP thresholds,
      class HD, morale, reaction.
- [ ] `rules/chargen.py` — roll a level-1 character (3d6 in order or your
      house rule), pick class legally, roll HP, starting gear, gold.
- [ ] `rules/combat.py` — initiative, attack resolution, damage, morale
      checks, death at 0 HP (decide house rule: instant vs. death's door).
- [ ] `rules/xp.py` — XP from monsters + treasure (B/X is gold-for-XP —
      decide if you keep that; it drives litRPG-friendly loot numbers),
      level-up processing: new HP, spells, abilities.
- [ ] `python -m season2.seed` — rolls the 10-character party, inserts
      campaign + characters + starting inventory into Supabase. Mark one
      as protagonist (their sheet gets rolled but their *personality* comes
      from Phase 3).

**Done when:** seed script produces a party you can read out of the
`party_sheet` view, and combat unit tests resolve a scripted fight
deterministically under a fixed RNG seed.

## Phase 2 — Content prep (a weekend, plus a decision)
- [ ] **Decide the IP posture** before digitizing anything: verbatim module
      adaptation vs. renamed/remixed "in the style of." (Remix strongly
      recommended for a public feed; mechanics via OSE are safe either way.)
- [ ] Chunk your module content (room/area-level chunks, ~300-800 tokens,
      with location IDs) into `documents` rows, `kind='module_chunk'`.
- [ ] Embed chunks (any embedding API; match `vector(1536)` dims or alter
      the column) and build the ivfflat index (commented line in schema).
- [ ] `engine/retrieval.py` — given current location, fetch its chunk +
      adjacent areas by similarity/metadata.

**Done when:** "party is at the Caves of Chaos entrance" retrieves the right
chunks and nothing irrelevant.

## Phase 3 — Narrative bootstrap (fun part; human-in-the-loop)
- [ ] Write/generate the **protagonist bible** (`documents`,
      kind='protagonist_bible'): modern-world backstory, voice, speech
      quirks, what they know about D&D, arrival mystery. Iterate by hand —
      this document is injected into every future writer call.
- [ ] **Style guide** doc: litRPG conventions (stat screens, [System]
      notifications if you want them, chapter cadence), tone, POV rules.
- [ ] Generate the **isekai prologue / Episode 1** as a one-off script,
      editing prompts until the voice sings. Do NOT automate yet.

**Done when:** you read Episode 1 aloud and love it.

## Phase 4 — The scene loop (the core build, 2-4 weekends)
- [ ] `engine/context.py` — build_planning_context / build_scene_context
      exactly per generation-loop.md's token budget.
- [ ] `engine/prompts.py` — PLAN, SCENE, DIFF, AUDIT, REVISE, SUMMARIZE.
- [ ] `engine/loop.py` — the 2a-2e loop: mechanics → write → extract diff →
      validate → commit (single Postgres transaction per scene).
- [ ] Human review gate: episode lands as `status='drafted'`; you approve
      (or edit) before state is considered canon — cheap insurance early on.

**Done when (THE milestone):** two consecutive text-only episodes where
episode 2 provably references an HP change, an item pickup, and an NPC from
episode 1 — all sourced from the DB, verified by grepping the context you
sent, not by luck.

## Phase 5 — Campaign machinery
- [ ] Summary roll-ups (scene→episode→arc→campaign) after each episode.
- [ ] XP/level-up processing wired into post-episode step; level-up events
      surface in the next episode's prose.
- [ ] Protagonist-death check → finale-arc mode.
- [ ] Module selector: propose 2-3 level-appropriate classics with
      reasoning; you approve; bridge scene generated.

## Phase 6 — Audio (port, don't rewrite)
- [ ] Extract season 1's TTS/mixing/Suno/Transistor code into `shared/`.
- [ ] TTS bake-off: render the same Episode 1 scene on Fish Audio, Inworld,
      and your existing ElevenLabs voices; compare cost × quality by ear.
- [ ] Voice map: `characters.voice_id` per party member + narrator
      (= protagonist) voice. Fewer full cast voices than season 1 is fine —
      first-person litRPG carries most dialogue in the narrator's voice.
- [ ] `audio/render.py` — compile speaker-tagged script → episode audio.

## Phase 7 — Ops
- [ ] Cost logging per episode (tokens + TTS chars) into a small table.
- [ ] Idempotent regen: re-render audio or re-write a scene WITHOUT
      re-applying state diffs (state application is a one-time commit).
- [ ] Backups: Supabase PITR or scheduled dumps — this DB *is* the campaign.

---

## Working rhythm
Build Phase 1 completely before touching prompts. The temptation is to jump
to Phase 3-4 because prose is the fun part — but every hour in the rules
engine pays back tenfold in continuity you never have to prompt for.
