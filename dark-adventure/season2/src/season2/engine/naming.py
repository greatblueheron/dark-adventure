"""Name the rolled party using Claude, based on actual class/race/stats.

Design notes:
- Naming happens AFTER the dice roll the party (names depend on who the
  dice produced) and BEFORE the Supabase insert (names propagate into
  every event row, episode, and TTS voice tag — rename-late is painful).
- The API call is injected (call_fn) so tests run without network/keys.
- The protagonist gets a modern real-world name (they're from our world);
  pass --protagonist-name to override with your own choice.
"""
from __future__ import annotations

import json
import os
import re


def _default_call(prompt: str) -> str:
    from dotenv import load_dotenv
    load_dotenv()
    import anthropic
    client = anthropic.Anthropic()          # uses ANTHROPIC_API_KEY from env
    msg = client.messages.create(
        model=os.getenv("CLERK_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


PROMPT = """You are naming the cast of a serialized AD&D 1st-edition audio drama.
Below is the rolled party as JSON. Propose one name per character.

Rules:
- Names must fit race and class (dwarven names for dwarfs, etc.), feel like
  classic late-70s/early-80s fantasy, and be phonetically DISTINCT from each
  other (they'll be spoken aloud in audio — no two names may share a first
  syllable or rhyme).
- Look at the stats for flavour: a CHA 7 cleric might have a dour name; a
  DEX 17 gnome something quick and clever.
- The character marked "is_protagonist": true is a modern person from the
  real 21st-century world transported into the game world. Give them an
  ordinary, believable modern first+last name (e.g. the kind of name a
  podcast producer or IT worker might have), NOT a fantasy name.
- Reply with ONLY a JSON array of strings, in the same order as the input,
  no other text, no markdown fences.

Party:
{roster}
"""


def name_party(party: list[dict], call_fn=None, protagonist_name: str | None = None
               ) -> list[str]:
    """Return proposed names, one per party entry, in order."""
    call_fn = call_fn or _default_call
    roster = [
        dict(index=i, is_protagonist=e["character"]["is_protagonist"],
             race=e["character"]["ancestry"], cls=e["character"]["class"],
             stats=e["character"]["stats"])
        for i, e in enumerate(party)
    ]
    raw = call_fn(PROMPT.format(roster=json.dumps(roster, indent=1)))
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    names = json.loads(cleaned)
    if not (isinstance(names, list) and len(names) == len(party)
            and all(isinstance(n, str) and n.strip() for n in names)):
        raise ValueError(f"Bad naming response: {raw[:200]}")
    names = [n.strip() for n in names]
    if protagonist_name:
        for i, e in enumerate(party):
            if e["character"]["is_protagonist"]:
                names[i] = protagonist_name
    return names


def apply_names(party: list[dict], names: list[str]) -> None:
    for entry, name in zip(party, names):
        entry["character"]["name"] = name
