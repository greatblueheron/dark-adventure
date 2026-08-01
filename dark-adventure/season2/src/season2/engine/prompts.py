"""Phase 4 prompt templates. Contracts:
- PLAN and DIFF return ONLY JSON (no fences, no prose).
- SCENE returns prose only.
- AUDIT returns JSON verdict. SUMMARIZE returns plain text.
"""

PLAN = """You are the showrunner-DM of "Whispers in Green Static", a litRPG
audio drama played strictly under AD&D 1e rules by a deterministic dice
engine. Plan the next episode from the GROUND-TRUTH context below. You see
everything (hidden alignments, unvisited rooms); the narrator does not.

{context}

Design 3-5 scenes advancing the party's expedition. CONTINUATION: the
RECAP describes events the audience has ALREADY SEEN - never re-stage,
re-dramatise, or repeat a summarised event. Episode {episode} begins
strictly AFTER the last summarised moment and moves forward. Referencing
consequences of past events is good; replaying them is a continuity
error. PACING: an audio
drama cannot linger — if recent episodes stayed in one small area, this
one should cover real ground (use the MODULE AREA INDEX). Most episodes
should include at least one encounter, hazard, or dice-worthy risk. Honour the module's
content faithfully (monsters, treasures, NPCs as written). Use hidden
truths for subtext and planted tells, never overt revelation unless the
fiction forces it. Party decisions should follow from established
personalities.

Return ONLY a JSON object:
{{
 "title": "episode title",
 "premise": "1-2 sentences",
 "scenes": [
   {{
    "index": 1,
    "location": "AREA-ID the scene occurs in (e.g. KEEP-15, CAVES-1)",
    "moves_party_to": "AREA-ID if the party ends the scene elsewhere, else null",
    "goal": "what this scene accomplishes dramatically",
    "beats": ["ordered story beats, concrete"],
    "focal_characters": ["at most 4 party names given real focus"],
    "spells": [
      {{"caster": "party member name", "spell": "Cure Light Wounds",
        "target": "recipient name or null"}}
    ],
    -- EVERY spell actually cast this scene MUST be declared here or in an
    -- encounter's own "spells" list (mid-combat casts). The engine rolls
    -- ONLY declared casts; party_tactics never casts anything. --
    "encounters": [
      {{"name": "6 kobold guards", "intent": "fight|skirmish|drive_off",
        "monsters": [{{"name": "Kobold guard 1", "ac": 7, "hd": "1/2",
                       "hp": 3, "damage": "1d4", "morale": 6}}],
        "trigger": "when/why it starts",
        "spells": [{{"caster": "name", "spell": "Sleep", "target": null}}],
        "party_tactics": "who does what (descriptive - casts go in spells)"}}
    ],
    "checks": [
      {{"kind": "save|thief_skill|ability|chance",
        "character": "name", "detail": "e.g. save vs Spells / move quietly",
        "target": "what happens on success/failure"}}
    ],
    "reveals": ["information the party LEARNS this scene (this is how the
                 narrator may learn unvisited content)"]
   }}
 ]
}}
Copy monster ac/hp/damage/morale faithfully from the module text. For
groups of identical monsters, one entry with a "count" field is fine.
Only include encounters/checks the dice must resolve; pure roleplay
scenes may have none. KEEP THE JSON COMPACT — short beat phrases, no
prose padding — the whole object must fit well within the output limit."""

SCENE = """You are the writer of "Whispers in Green Static". Write the next
scene as finished first-person prose in Aaron Fischer's voice, exactly per
the style guide.

{context}

RULES:
- Every number (damage, HP, dice outcomes) must come from the MECHANICS
  LOG. Never invent or alter numbers. If the log shows a miss, it missed.
- Spells marked EXPENDED are gone until the party rests; no character may
  cast one again, and casters feel the empty slot.
- A character with condition "down" is unconscious and dying. They cannot
  walk, speak, or act. If the SCENE PLAN requires them active, the scene
  must FIRST depict their stabilisation/revival on the page (binding, a
  logged healing spell) before they do anything - never skip it.
- You know ONLY what the narrator layer above contains. Do not reveal or
  imply hidden motives/alignments; unentered areas are unknown to you.
- Follow the SCENE PLAN's beats; realise them as drama, don't summarise.
- VARIETY: do not open every scene the same way. Aaron's acoustic
  perception should permeate scenes, not ritually open them - vary entry
  points: mid-dialogue, mid-action, an object, a thought, a person. If
  RECENT SCENE OPENINGS are listed in context, do not echo their
  constructions.
- 600-1100 words. Output ONLY the scene prose."""

DIFF = """Extract the mechanical state changes from this scene's prose and
mechanics log. Return ONLY JSON, no fences:

SCENE PROSE:
{prose}

MECHANICS LOG:
{log}

{{
 "hp_changes": [{{"character": "name", "delta": -3, "cause": "kobold spear"}}],
 "deaths": [{{"character": "name", "cause": "..."}}],
 "conditions_gained": [{{"character": "name", "condition": "..."}}],
 "conditions_removed": [{{"character": "name", "condition": "..."}}],
 "items_gained": [{{"character": "name", "item": "...", "quantity": 1,
                    "gp_value": 0}}],
 "items_lost": [{{"character": "name", "item": "...", "quantity": 1}}],
 "xp_awards": [{{"character": "name", "amount": 25, "cause": "..."}}],
 "spells_cast": [{{"character": "name", "spell": "Sleep", "slot_level": 1}}],
 "npcs_met": [{{"name": "...", "role": "...", "disposition": "..."}}],
 "party_rested": false,
 "location_change": "one of {allowed_locations} if the party ends the
                     scene in a different area, else null - NEVER invent
                     location ids",
 "notable_events": ["one-line durable facts worth remembering"]
}}
If the prose depicts a downed character stabilised or revived, RECORD it:
conditions_removed "down" plus any hp_changes the log supports.
Use empty arrays where nothing applies. hp_changes, deaths, conditions,
items, xp_awards and spells_cast are for PARTY MEMBERS ONLY - monster and
NPC outcomes (orcs slain, put to sleep, fled, etc.) belong in
notable_events as prose; the engine tracks monster state separately.
gp_value ONLY when the scene or
module states a value — never estimate. party_rested is true only when a
full night's rest completes within the scene. Character names must match the
party roster exactly. Only include changes that actually occurred."""

AUDIT = """You are the continuity auditor. Compare the scene prose against
the mechanics log, the scene plan, the party state, and the
narrator-knowledge rules.

SCENE PROSE:
{prose}

MECHANICS LOG:
{log}

SCENE PLAN:
{plan}

PARTY STATE (entering this scene):
{roster}

MECHANICS CONVENTIONS (the log's "success" field is computed by a
deterministic rules engine and is AUTHORITATIVE): ability, thief_skill and
chance checks are ROLL-UNDER - success means roll <= target, so 17 vs 18
succeeds. Saves are ROLL-OVER - success means roll >= target. Audit prose
against the log's stated outcomes; never re-derive success yourself.

DICE CONVENTIONS (AD&D 1e): ability checks, thief skills and chance
checks are ROLL-UNDER - success means roll <= target, so e.g. 17 vs 18 is
a SUCCESS. Saving throws are roll-over (roll >= target). The log's
success/failure field is authoritative; NEVER re-adjudicate roll
arithmetic yourself - only compare prose outcomes against the log's
stated verdicts.

FAIL if: prose contradicts or invents dice numbers; a hit/miss/death
differs from the log; a cast marked SLOT UNAVAILABLE is depicted as
succeeding; the narrator reveals hidden alignments/motives or
unvisited room contents not in the plan's reveals; stat-screen numbers
don't match the party state (note: a character at FULL hit points is
healthy and unwounded no matter how low their maximum - do not count
low-max/full-hp characters among the WOUNDED, though prose may correctly
treat a low maximum as tactical FRAGILITY; fragile is not wounded); a
headcount the prose ITSELF flags as anomalous, unexplained or dreadful is
a deliberate story beat and passes - fail only counts asserted as
complete and correct that contradict the party state; a character at 0 hp acts
freely (0 hp means
unconscious and dying; once stabilised they are barely conscious, not
walking, fighting, or standing guard). Style nitpicks are NOT failures.

Return ONLY JSON: {{"verdict": "pass"|"fail", "issues": ["..."]}}"""

REVISE = """Revise the scene to fix ONLY these audit issues, changing as
little else as possible. Keep voice, length and beats.

ISSUES:
{issues}

SCENE:
{prose}

MECHANICS LOG (ground truth):
{log}

Output ONLY the revised scene prose."""

SUMMARIZE_SCENE = """Summarise this scene in 3-5 sentences for the campaign
memory: what happened, mechanical outcomes (HP/items/XP), decisions, and
any planted character beats. Plain text only.

{prose}

DIFF:
{diff}"""

SUMMARIZE_EPISODE = """Write an episode summary (120-180 words) from these
scene summaries, for use in future episode recaps: expedition progress,
state changes that matter, open threads. Plain text only.

{scene_summaries}"""


SUMMARIZE_CAMPAIGN = """Write the running campaign summary (200-250 words)
from these episode summaries, oldest first: where the party stands, what
the world remembers of them, open mysteries and debts. Plain text only.

{episode_summaries}"""
