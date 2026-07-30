# Season 2 Engine — Architecture & Generation Loop

The system is three layers, strictly separated:

1. **Rules engine (code, deterministic)** — dice, combat, XP, level-ups, encumbrance, death. Implements your chosen ruleset (recommend Old-School Essentials' restatement of B/X). The LLM never adjudicates mechanics.
2. **State store (Supabase)** — the schema in `schema.sql`. Single source of truth. The LLM never "remembers"; it is *told*.
3. **Narrative layer (LLMs)** — turns mechanics + state into litRPG prose, extracts state diffs, maintains summaries, audits continuity.

Model roles (suggested):
- **Writer** — Claude Opus 4.8 or Fable 5: scene prose in the protagonist's first-person voice.
- **Clerk** — Haiku/Sonnet tier: state-diff extraction, scene summaries, roll-up summaries.
- **Auditor** — Sonnet tier: checks generated prose against the state sheet before it's accepted.

---

## Per-episode loop

```python
def produce_episode(campaign_id):
    ep = create_episode_row(campaign_id)

    # ---------- 1. PLAN ----------
    ctx = build_planning_context(campaign_id)
    #   - party_sheet view (full current state, protagonist first)
    #   - campaign summary + current module_arc summary
    #   - last 2 episode summaries
    #   - retrieved module chunks: current location + adjacent areas
    #     (pgvector search over documents where kind='module_chunk')
    outline = writer_or_sonnet(PLAN_PROMPT, ctx)   # list of 4-8 scenes w/ goals
    save_outline(ep, outline)

    # ---------- 2. SCENES ----------
    for i, scene_plan in enumerate(outline.scenes):
        # 2a. MECHANICS FIRST (code, not LLM)
        mech = rules_engine.resolve(scene_plan, party_state())
        #   - builds encounters from module data (monster stats, reactions,
        #     morale) with real dice; outputs a structured log:
        #     [{"actor":"Brenna","action":"attack","target":"ogre",
        #       "roll":17,"hit":true,"damage":6,"target_hp_after":4}, ...]
        #   - deaths, HP, spell slot usage, treasure found are FACTS here.

        # 2b. WRITE
        scene_ctx = build_scene_context(campaign_id, ep, i)
        #   - protagonist bible + style guide (always injected verbatim)
        #   - party_sheet, relevant NPC rows, recent events
        #   - previous scene's full text (voice continuity)
        #   - mech log for THIS scene
        prose = writer(SCENE_PROMPT, scene_ctx, mech)
        #   SCENE_PROMPT enforces: first-person protagonist POV, litRPG
        #   stat screens rendered ONLY from provided numbers, no invented
        #   mechanics, no contradicting the state sheet.

        # 2c. EXTRACT DIFF
        diff = clerk(DIFF_PROMPT, prose, mech)
        #   -> structured JSON: hp_changes, items_gained/lost, xp, deaths,
        #      npcs_met, conditions, quests. Mech log is ground truth;
        #      prose may add narrative-only facts (npc_met, party_decision).

        # 2d. VALIDATE
        problems = rules_engine.validate(diff) + auditor(AUDIT_PROMPT, prose, party_sheet)
        #   - diff must not contradict mech log (no resurrections, no
        #     duplicate loot, HP within bounds)
        #   - auditor flags prose contradictions ("Thorn gestured with the
        #     hand he lost in ep 14")
        if problems:
            prose = writer(REVISE_PROMPT, prose, problems)   # one retry, then human flag

        # 2e. COMMIT (transaction)
        apply_diff(diff)              # update characters/items; insert events rows
        save_scene(ep, i, prose, mech, diff)
        save_summary('scene', clerk(SUMMARIZE_PROMPT, prose))

    # ---------- 3. POST-EPISODE ----------
    award_xp_and_process_levelups()   # rules engine; new abilities/HP rolled
    #   level-ups emit 'level_up' events -> next episode's writer is told to
    #   narrate the new ability litRPG-style ("[Sleep] added to spellbook")
    roll_up_summaries()               # scenes -> episode summary; refresh
    #                                 # module_arc + campaign summaries
    check_protagonist()               # dead? -> mark campaign arc ending;
    #                                 # generate finale episode(s), stop.
    if module_complete():
        run_module_selector()         # LLM proposes 2-3 level-appropriate
        #                             # classics w/ reasoning; you approve;
        #                             # writer generates a travel/bridge scene.

    # ---------- 4. AUDIO (your season-1 pipeline, refactored) ----------
    script = compile_script(ep)       # speaker-tagged; narrator = protagonist
    audio  = tts_render(script)       # Fish Audio / Inworld voice map from
    #                                 # characters.voice_id
    publish_to_transistor(mix(audio, suno_music(), commercials()))
```

---

## Context budget per writer call (rough)

| Component                          | ~Tokens |
|------------------------------------|---------|
| Protagonist bible + style guide    | 1.5k    |
| Party sheet (10 → fewer over time) | 1–2k    |
| Campaign summary                   | 1k      |
| Module arc summary + last 2 ep summaries | 1.5k |
| Previous scene full text           | 2–3k    |
| Module chunks (retrieved)          | 2–4k    |
| Mechanics log for scene            | 0.5–1k  |
| **Total input**                    | **~10–14k** |

Comfortably inside any frontier context window forever, regardless of how
long the campaign runs — that's the point of the architecture.

## Build order (recommended)

1. Schema + seed script: campaign, 10 characters (roll them with the rules
   engine!), module row for the starting adventure.
2. Rules engine core: dice, attack resolution, morale, XP, level-up tables.
   Test standalone.
3. Isekai prologue: one-off generation task — protagonist bible first, then
   the arrival story, then Episode 1.
4. Scene loop (2a–2e) end to end for one scene. Read the output. Tune the
   SCENE_PROMPT until the voice is right *before* automating further.
5. Summaries + auditor.
6. Wire in the refactored season-1 audio pipeline last.

Prototype milestone: **one full episode, text only, with real state
persistence across a second episode** — including at least one HP change and
one item pickup that episode 2 provably remembers.
