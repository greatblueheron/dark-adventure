# Season 2 — Implementation Roadmap

Each phase has a clear "done when" gate. Don't start a phase until the
previous gate passes. Checked boxes reflect actual project state.

## Current status (July 2026)

**Phases 0-1 COMPLETE. Canonical campaign seeded — next up: Phase 3
(recommended) or Phase 2.**

- Canonical campaign: **seed 17**, campaign id `c24063e2-b190-40c5-97d0-a3dcd6586346`
- Protagonist: **Aaron Fischer** — Human Magic-User, INT 18 / CON 18 /
  WIS 9 / CHA 9, reads as **Neutral Evil** (central mystery: is the
  reading true, or an artifact of his arrival?). Spells: Read Magic,
  Sleep, Unseen Servant, Comprehend Languages.
- Party: 5 Magic-Users, 3 Fighters, 1 Thief (Kix), 1 Cleric (Urgosh —
  sole healer). Hidden evils: Aaron, Thessaly (NE Elf Fighter, best
  warrior), Voldek (CE Magic-User). Seraphel (NG) holds Detect Magic +
  Protection from Evil — the party's potential conscience.
- The **database is the source of truth**. Inspect it any time with
  `poetry run python -m season2.db roster`. DEFAULT_NAMES in seed.py is
  bootstrap-only and dead after seeding.

---

## Phase 0 — Foundations ✅ DONE
- [x] Repo structure: `season2/` inside `dark-adventure` (Poetry 2.x
      project; run poetry commands from inside `season2/`).
- [x] Supabase project created; `migrations/schema.sql` applied (v2:
      OSRIC ruleset default; party_sheet includes ancestry + alignment).
      NB: with "auto-expose new tables" disabled, service_role needed
      explicit GRANTs — done, plus default privileges for future objects.
- [x] `.env` populated (Supabase URL + sb_secret key, ANTHROPIC_API_KEY,
      model names). `poetry run python -m season2.db check` connects.

## Phase 1 — Rules engine + seed party ✅ DONE
Pure Python rules (LLM used only for cosmetic naming, human-approved).

- [x] `rules/dice.py` — seedable, labelled, append-only roll log.
- [x] `rules/tables.py` — **verified against the OSRIC SRD** (fetched
      July 2026), encoded to **level 14** (covers the classic chain
      through Queen of the Demonweb Pits). Druid hard-caps at 14.
      Simplifications on record: to-hit is THAC0-at-AC-0 with natural-20
      auto-hit (approximates the matrices' repeating 20s); demihuman
      level limits deliberately NOT enforced; racial ability min/maxes
      not enforced.
- [x] `rules/chargen.py` — fully dice-driven ("the dice cast the show"):
      race rolled on a weighted d100 (humans common), stats **5d6-drop-
      the-two-lowest strictly IN ORDER**, class **emerges** as the best
      legal fit, alignment rolled on a weighted nine-point table with
      class clamps (Paladin LG, Druid TN, Ranger Good, Thief non-LG/CG).
      Protagonist specials: always Human, always male-named, **max
      level-1 HP** (roll consumed to preserve the seed stream). Monk and
      Assassin intentionally excluded.
- [x] `rules/combat.py` — initiative, THAC0 attacks, morale (2d6 house
      rule), **deaths_door** rule chosen: party members go down at 0 HP
      and die only if hit while down; monsters die outright.
- [x] `rules/xp.py` — gold-for-XP kept (1 gp = 1 XP), +10% when all
      prime requisites 16+, OSRIC HD caps with flat HP after (no CON),
      multi-level jumps, MU/Illusionist "new spell on level-up" hook.
- [x] `seed.py` — seeds campaign + party + inventory. `--claude-names`
      has Claude propose audio-distinct fantasy names (protagonist name
      drawn in CODE from real male-name lists — never by the model);
      interactive approval before insert.
- [x] `engine/naming.py` + `db.py roster` command.

**Gate passed:** party seeded and readable via `party_sheet` /
`db roster`; 26 deterministic tests green.

## Phase 2 — Content prep (a weekend, plus a decision)
- [ ] **Decide the IP posture** before digitizing anything: verbatim
      module adaptation vs. renamed/remixed "in the style of." (Remix
      strongly recommended for a public feed; mechanics via OSRIC are
      safe either way.)
- [ ] Chunk module content (room/area-level, ~300-800 tokens, with
      location IDs) into `documents` rows, `kind='module_chunk'`.
- [ ] Embed chunks (match `vector(1536)` dims or alter the column);
      build the ivfflat index (commented line in schema).
- [ ] `engine/retrieval.py` — given current location, fetch its chunk +
      adjacent areas.

**Done when:** "party is at the Caves of Chaos entrance" retrieves the
right chunks and nothing irrelevant.

## Phase 3 — Narrative bootstrap (fun part; human-in-the-loop) ← NEXT
- [ ] **Protagonist bible** (`documents`, kind='protagonist_bible'):
      Aaron Fischer's modern-world backstory, voice, speech quirks, D&D
      familiarity, arrival mystery — including the **Neutral Evil
      reading** and what (if anything) he knows about it. Iterate by
      hand; this document is injected into every future writer call.
- [ ] **Character bibles / party notes**: personalities for the nine
      others; explicitly mark hidden knowledge (Thessaly's and Voldek's
      alignments are ground truth the NARRATOR must not know).
- [ ] **Style guide** doc: litRPG conventions (stat screens rendered
      only from engine-provided numbers, [System] framing if any,
      chapter cadence), tone, first-person POV rules.
- [ ] **Isekai prologue / Episode 1** as a one-off script, edited until
      the voice sings. Do NOT automate yet.

**Done when:** you read Episode 1 aloud and love it.

## Phase 4 — The scene loop (the core build, 2-4 weekends)
- [ ] `engine/context.py` — planning/scene context builders per
      `docs-generation-loop.md` token budget. Must implement the
      **two-layer knowledge model**: ground truth (DB) vs. what the
      protagonist-narrator knows (no leaking hidden alignments).
- [ ] `engine/prompts.py` — PLAN, SCENE, DIFF, AUDIT, REVISE, SUMMARIZE.
- [ ] `engine/loop.py` — mechanics → write → extract diff → validate →
      commit (single transaction per scene).
- [ ] Human review gate: episodes land as `status='drafted'`; you
      approve before state becomes canon.

**Done when (THE milestone):** two consecutive text-only episodes where
episode 2 provably references an HP change, an item pickup, and an NPC
from episode 1 — sourced from the DB, verified by inspecting the sent
context, not by luck.

## Phase 5 — Campaign machinery
- [ ] Summary roll-ups (scene→episode→arc→campaign) after each episode.
- [ ] XP/level-up processing wired into post-episode step; level-ups
      surface in the next episode's prose.
- [ ] Protagonist-death check → finale-arc mode.
- [ ] Module selector: propose 2-3 level-appropriate classics with
      reasoning; you approve; bridge scene generated.

## Phase 6 — Audio (port, don't rewrite)
- [ ] Extract season 1's TTS/mixing/Suno/Transistor code into `shared/`.
- [ ] TTS bake-off: same Episode 1 scene on Fish Audio, Inworld, and
      existing ElevenLabs voices; compare cost × quality by ear.
- [ ] Voice map: `characters.voice_id` per member + narrator (= Aaron).
      First-person litRPG carries most dialogue in the narrator's voice,
      so fewer full cast voices than season 1 is fine.
- [ ] `audio/render.py` — speaker-tagged script → episode audio.

## Phase 7 — Ops
- [ ] Cost logging per episode (tokens + TTS chars) into a small table.
- [ ] Idempotent regen: re-render audio or re-write a scene WITHOUT
      re-applying state diffs (state application is a one-time commit).
- [ ] Backups: Supabase PITR or scheduled dumps — this DB *is* the
      campaign. (Worth enabling NOW that a canonical campaign exists.)

---

## Standing disciplines
- **Schema sync:** any change to what characters/episodes/events ARE
  gets checked in three places — code, live DB, `migrations/schema.sql`.
- **Seed streams:** chargen changes invalidate old seed printouts. The
  canonical campaign is locked; further chargen changes affect future
  campaigns only.
- **Rules before prose:** every hour in the rules engine pays back
  tenfold in continuity you never have to prompt for.
