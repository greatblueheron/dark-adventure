"""Phase 3 narrative bootstrap — every narrative artifact is GENERATED
from the roster (the database is the source of truth), at high temperature,
rerollable, and hand-editable.

Artifacts (stored in `documents`, latest row per kind/title wins;
history is kept — every reroll/push inserts a new version):

  protagonist   kind='protagonist_bible'          (Aaron Fischer)
  style         kind='style_guide'                (litRPG conventions)
  characters    kind='character_bible', title=<name>   (the other nine)
  prologue      kind='episode_script', title='Episode 1'

Usage:
  poetry run python -m season2.bootstrap status
  poetry run python -m season2.bootstrap gen all            # missing only, in order
  poetry run python -m season2.bootstrap gen protagonist    # (re)roll one artifact
  poetry run python -m season2.bootstrap gen protagonist --note "make him older, from Chicago"
  poetry run python -m season2.bootstrap gen characters --name Voldek
  poetry run python -m season2.bootstrap show prologue
  poetry run python -m season2.bootstrap pull prologue --out ep1.md   # edit by hand...
  poetry run python -m season2.bootstrap push prologue --file ep1.md  # ...push back as new version

Generation order matters (later artifacts consume earlier ones):
protagonist -> style -> characters -> prologue.

Hidden-knowledge design: character bibles are written in two delimited
sections — PUBLIC PERSONA (what Aaron/the narrator can perceive) and
HIDDEN TRUTH (ground truth incl. alignment). Phase 4's context builder
feeds ONLY the public section to the narrator.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

# ---------------------------------------------------------------- data access

def _client():
    from .db import client
    return client()


def fetch_campaign(c) -> dict:
    rows = c.table("campaigns").select("*").eq("status", "active").execute().data
    if not rows:
        sys.exit("No active campaign — seed one first.")
    return rows[0]


def fetch_roster(c, campaign_id: str) -> list[dict]:
    return (c.table("characters")
            .select("name, is_protagonist, ancestry, class, alignment, level, "
                    "current_hp, max_hp, armor_class, stats, spells_known, "
                    "spell_slots, abilities, status")
            .eq("campaign_id", campaign_id)
            .order("is_protagonist", desc=True).order("name")
            .execute().data)


def latest_doc(c, campaign_id: str, kind: str, title: str | None = None) -> dict | None:
    q = (c.table("documents").select("*")
         .eq("campaign_id", campaign_id).eq("kind", kind))
    if title is not None:
        q = q.eq("title", title)
    rows = q.order("created_at", desc=True).limit(1).execute().data
    return rows[0] if rows else None


def save_doc(c, campaign_id: str, kind: str, title: str, content: str) -> None:
    c.table("documents").insert(dict(
        campaign_id=campaign_id, kind=kind, title=title, content=content,
    )).execute()

# ---------------------------------------------------------------- LLM calling

def default_call(prompt: str, max_tokens: int = 4000) -> str:
    from dotenv import load_dotenv
    load_dotenv()
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=os.getenv("WRITER_MODEL", "claude-opus-4-8"),
        max_tokens=max_tokens,
        temperature=1.0,                      # high temperature: creative rolls
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")

# ---------------------------------------------------------------- prompts

def _roster_json(roster: list[dict]) -> str:
    return json.dumps(roster, indent=1, default=str)


def _nonce() -> int:
    return random.randint(100000, 999999)


def _note_block(note: str | None) -> str:
    return f"\nSHOWRUNNER DIRECTION (must be followed): {note}\n" if note else ""


def build_protagonist_prompt(roster: list[dict], note: str | None = None) -> str:
    p = next(r for r in roster if r["is_protagonist"])
    return f"""You are the head writer of "Whispers in Green Static", a serialized
litRPG audio drama. A real-play AD&D 1e campaign engine generates the events;
your job now is the PROTAGONIST BIBLE — the single document injected into
every scene the show will ever generate. Creative variety seed: {_nonce()}.

The protagonist is a modern person from the real 21st-century world who is
transported into the world of the classic module Keep on the Borderlands.
The dice have already decided everything mechanical about him. Invent
everything else. His character sheet (ground truth, do not contradict):

{json.dumps(p, indent=1, default=str)}

Notes on reading the sheet:
- INT 18 = genuinely brilliant. CON 18 = iron constitution. WIS 9 = poor
  judgment. CHA 9 = little warmth or charm. Invent a modern life that
  PRODUCES this exact profile.
- His alignment is what the world's magic READS him as. He is from a world
  without cosmic alignment. Decide in the bible whether the reading is
  true, false, or unresolved — and whether HE knows about it yet.
- His four known spells should resonate with who he was.

Write the bible with these sections, in markdown:
# Identity  (name is Aaron Fischer; age, city, occupation, life situation)
# Before  (his modern life — specific, textured, unglamorous)
# The Crossing  (the moment of transition; sensory; partially unexplained —
  it should connect somehow to audio/static/signal, honouring the show's
  title, but remain a mystery with room to grow for 100+ episodes)
# Voice  (first-person narration style: rhythms, register, humour, what he
  notices first in a room; 3 short SAMPLE narration passages)
# Speech quirks  (verbal tics, modern references he reaches for, swearing
  habits, phrases to use and phrases to NEVER use)
# What he knows about D&D  (decide: none / played as a kid / lapsed
  grognard — and how that shapes his reactions to living inside it)
# The Reading  (the alignment question, handled per the above)
# Arc seeds  (5-8 long-range threads the show can pull on)
# Hard canon  (bullet list of facts that must never be contradicted)
{_note_block(note)}
Length: 1200-1800 words. Make him specific, flawed, and worth a hundred
hours of listening. Output ONLY the bible, no preamble."""


def build_style_prompt(roster: list[dict], protagonist_bible: str,
                       note: str | None = None) -> str:
    return f"""You are the head writer of "Whispers in Green Static", a serialized
litRPG audio drama generated from a real AD&D 1e campaign engine. Write the
STYLE GUIDE — the document that governs every scene's prose. Creative
variety seed: {_nonce()}.

The protagonist bible (already canon — the style must fit this voice):
---
{protagonist_bible}
---

The party roster (for ensemble texture):
{_roster_json(roster)}

Write the style guide in markdown with these sections:
# POV & tense  (first-person Aaron, tense choice with rationale)
# litRPG conventions  (how stat screens, HP, XP, level-ups, and dice
  outcomes surface in prose; CRITICAL RULE: all numbers come from the
  engine's mechanics log — the prose NEVER invents numbers; how Aaron
  perceives the "System" and whether anyone else can)
# Audio-first prose rules  (this is heard, not read: sentence rhythm,
  dialogue attribution, no visual-only formatting, how stat screens are
  VOICED)
# Tone  (the blend: dread, wonder, gallows humour; what the show never
  does)
# Ensemble handling  (rotating spotlight across ten characters; keeping
  nine NPCs distinct in audio; the narrator only knows what he perceives)
# Violence & death  (this campaign kills characters permanently; how
  deaths land in prose)
# Episode shape  (cold open? recap? cliffhanger discipline; target length
  in words for a 25-35 minute episode)
# Forbidden list  (clichés, anachronism-handling rules, things the prose
  must never do)
{_note_block(note)}
Length: 800-1200 words. Output ONLY the guide, no preamble."""


def build_character_prompt(roster: list[dict], target: dict, protagonist_bible: str,
                           style_guide: str, note: str | None = None) -> str:
    return f"""You are the head writer of "Whispers in Green Static" (litRPG audio
drama from a real AD&D 1e engine). Write the CHARACTER BIBLE for one party
member. Creative variety seed: {_nonce()}.

The character (sheet is ground truth; invent everything else):
{json.dumps(target, indent=1, default=str)}

The full party (for relationships):
{_roster_json(roster)}

The protagonist bible (canon):
---
{protagonist_bible}
---
Style guide (canon):
---
{style_guide}
---

Structure the bible EXACTLY as two top-level sections:

# PUBLIC PERSONA
What Aaron (the narrator) and the party can perceive: appearance, manner,
voice for TTS casting (pitch/pace/accent in plain words), speech patterns
with 3 sample lines, stated backstory (what they CLAIM), habits, how they
treat Aaron, one running bit the show can reuse.

# HIDDEN TRUTH
Ground truth only the engine knows: their real alignment ({target['alignment']})
and what it means for this person, true motives, secrets, what they make of
Aaron, how their hidden nature will LEAK in small perceivable ways (give
3-5 concrete tells the writer can plant without stating the truth), and a
betrayal/revelation arc seed if their alignment warrants one.

IMPORTANT: if the character's alignment is Good or their persona is honest,
HIDDEN TRUTH may be short — hidden depth, not necessarily deception. If
they are Evil, the persona must be genuinely likeable enough that the
audience will be wounded later.
{_note_block(note)}
Length: 500-800 words. Output ONLY the bible, no preamble."""


def build_prologue_prompt(roster: list[dict], protagonist_bible: str,
                          style_guide: str, public_personas: dict[str, str],
                          note: str | None = None) -> str:
    personas = "\n\n".join(f"## {name}\n{p}" for name, p in public_personas.items())
    return f"""You are the head writer of "Whispers in Green Static". Write EPISODE 1
— the isekai prologue — as finished first-person prose per the style guide.
Creative variety seed: {_nonce()}.

CANON DOCUMENTS:

Protagonist bible:
---
{protagonist_bible}
---
Style guide (follow it exactly, including episode shape and length):
---
{style_guide}
---
Party roster (mechanical ground truth):
{_roster_json(roster)}

Party PUBLIC personas (all the narrator may know about them — you do NOT
have access to any hidden truths and must not invent revelations):
---
{personas}
---

EPISODE 1 REQUIREMENTS:
- Aaron's last ordinary moments in the modern world; the Crossing as the
  bible describes it; arrival; first contact with the party (they are
  strangers to him — devise the natural reason these ten are travelling
  together toward the KEEP ON THE BORDERLANDS, which may be named);
  end at or within sight of the Keep's gates. Do not enter the Caves.
- The litRPG layer awakens for Aaron during this episode per the style
  guide: his first stat screen must use ONLY these true numbers from his
  sheet, voiced as the guide prescribes.
- Introduce at most 4-5 party members with real focus; the rest are
  present but backgrounded (a ten-hander cold open is audio soup).
- Keep description of the Keep itself light — deeper module detail arrives
  in later episodes.
- End on the hook that makes a listener need Episode 2.
{_note_block(note)}
Output ONLY the episode prose, no preamble, no headers except any the
style guide prescribes."""

# ---------------------------------------------------------------- operations

ORDER = ["protagonist", "style", "characters", "prologue"]
KINDS = {"protagonist": "protagonist_bible", "style": "style_guide",
         "characters": "character_bible", "prologue": "episode_script"}


def _split_public(bible: str) -> str:
    """Return only the PUBLIC PERSONA section of a character bible."""
    marker = "# HIDDEN TRUTH"
    return bible.split(marker)[0].replace("# PUBLIC PERSONA", "").strip()


def _need(c, camp_id, kind, title, what):
    doc = latest_doc(c, camp_id, kind, title)
    if not doc:
        sys.exit(f"Missing prerequisite: {what} — run `bootstrap gen {what}` first.")
    return doc["content"]


def gen(artifact: str, note: str | None, name: str | None, only_missing: bool,
        call_fn=default_call) -> None:
    c = _client()
    camp = fetch_campaign(c)
    roster = fetch_roster(c, camp["id"])

    def _protagonist():
        content = call_fn(build_protagonist_prompt(roster, note), 4000)
        save_doc(c, camp["id"], "protagonist_bible", "Aaron Fischer", content)
        print(f"protagonist bible written ({len(content)} chars). `show protagonist` to read.")

    def _style():
        pb = _need(c, camp["id"], "protagonist_bible", None, "protagonist")
        content = call_fn(build_style_prompt(roster, pb, note), 4000)
        save_doc(c, camp["id"], "style_guide", "Style Guide", content)
        print(f"style guide written ({len(content)} chars).")

    def _characters():
        pb = _need(c, camp["id"], "protagonist_bible", None, "protagonist")
        sg = _need(c, camp["id"], "style_guide", None, "style")
        targets = [r for r in roster if not r["is_protagonist"]]
        if name:
            targets = [r for r in targets if r["name"].lower() == name.lower()]
            if not targets:
                sys.exit(f"No party member named {name!r}.")
        for t in targets:
            if only_missing and latest_doc(c, camp["id"], "character_bible", t["name"]):
                print(f"  {t['name']}: exists, skipping")
                continue
            content = call_fn(build_character_prompt(roster, t, pb, sg, note), 2500)
            save_doc(c, camp["id"], "character_bible", t["name"], content)
            print(f"  {t['name']}: bible written ({len(content)} chars)")

    def _prologue():
        pb = _need(c, camp["id"], "protagonist_bible", None, "protagonist")
        sg = _need(c, camp["id"], "style_guide", None, "style")
        personas = {}
        for r in roster:
            if r["is_protagonist"]:
                continue
            doc = latest_doc(c, camp["id"], "character_bible", r["name"])
            if not doc:
                sys.exit(f"Missing character bible for {r['name']} — run `gen characters`.")
            personas[r["name"]] = _split_public(doc["content"])
        content = call_fn(build_prologue_prompt(roster, pb, sg, personas, note), 16000)
        save_doc(c, camp["id"], "episode_script", "Episode 1", content)
        print(f"Episode 1 written ({len(content)} chars, ~{len(content.split())} words).")

    steps = dict(protagonist=_protagonist, style=_style,
                 characters=_characters, prologue=_prologue)
    if artifact == "all":
        for step in ORDER:
            if only_missing and step != "characters" and latest_doc(
                    c, camp["id"], KINDS[step],
                    None if step != "prologue" else "Episode 1"):
                print(f"{step}: exists, skipping")
                continue
            print(f"== {step} ==")
            steps[step]()
    else:
        steps[artifact]()


def status() -> None:
    c = _client()
    camp = fetch_campaign(c)
    roster = fetch_roster(c, camp["id"])
    print(f"Campaign: {camp['name']}  ({camp['id']})")
    for step in ORDER:
        if step == "characters":
            for r in roster:
                if r["is_protagonist"]:
                    continue
                doc = latest_doc(c, camp["id"], "character_bible", r["name"])
                mark = "x" if doc else " "
                when = f"  ({doc['created_at'][:19]})" if doc else ""
                print(f"  [{mark}] character bible: {r['name']}{when}")
        else:
            title = "Episode 1" if step == "prologue" else None
            doc = latest_doc(c, camp["id"], KINDS[step], title)
            mark = "x" if doc else " "
            when = f"  ({doc['created_at'][:19]})" if doc else ""
            print(f"[{mark}] {step}{when}")


def _resolve(artifact: str, name: str | None) -> tuple[str, str | None]:
    kind = KINDS[artifact]
    if artifact == "characters":
        if not name:
            sys.exit("--name required for character bibles.")
        return kind, name
    return kind, ("Episode 1" if artifact == "prologue" else None)


def show(artifact: str, name: str | None) -> None:
    c = _client()
    camp = fetch_campaign(c)
    kind, title = _resolve(artifact, name)
    doc = latest_doc(c, camp["id"], kind, title)
    if not doc:
        sys.exit("Not generated yet.")
    print(doc["content"])


def pull(artifact: str, name: str | None, out: str) -> None:
    c = _client()
    camp = fetch_campaign(c)
    kind, title = _resolve(artifact, name)
    doc = latest_doc(c, camp["id"], kind, title)
    if not doc:
        sys.exit("Not generated yet.")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc["content"])
    print(f"Wrote {out}. Edit it, then `bootstrap push {artifact} --file {out}`"
          + (f" --name {name}" if name else ""))


def push(artifact: str, name: str | None, file: str) -> None:
    c = _client()
    camp = fetch_campaign(c)
    kind, title = _resolve(artifact, name)
    with open(file, encoding="utf-8") as f:
        content = f.read()
    save_doc(c, camp["id"], kind, title or {"protagonist_bible": "Aaron Fischer",
                                            "style_guide": "Style Guide"}[kind], content)
    print(f"Pushed {file} as new latest version of {artifact}"
          + (f" ({name})" if name else "") + ".")


def main() -> None:
    ap = argparse.ArgumentParser(prog="bootstrap")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    g = sub.add_parser("gen")
    g.add_argument("artifact", choices=ORDER + ["all"])
    g.add_argument("--note", default=None, help="showrunner direction for this roll")
    g.add_argument("--name", default=None, help="single character (for `characters`)")
    g.add_argument("--missing-only", action="store_true",
                   help="skip artifacts that already exist (default for `all`)")
    for cmd in ("show", "pull", "push"):
        p = sub.add_parser(cmd)
        p.add_argument("artifact", choices=ORDER)
        p.add_argument("--name", default=None)
        if cmd == "pull":
            p.add_argument("--out", required=True)
        if cmd == "push":
            p.add_argument("--file", required=True)
    a = ap.parse_args()
    if a.cmd == "status":
        status()
    elif a.cmd == "gen":
        only_missing = a.missing_only or a.artifact == "all"
        gen(a.artifact, a.note, a.name, only_missing)
    elif a.cmd == "show":
        show(a.artifact, a.name)
    elif a.cmd == "pull":
        pull(a.artifact, a.name, a.out)
    elif a.cmd == "push":
        push(a.artifact, a.name, a.file)


if __name__ == "__main__":
    main()
