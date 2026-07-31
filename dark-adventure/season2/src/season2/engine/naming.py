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


# Common real first names (mixed) and surnames for the protagonist —
# chosen in CODE with a true random draw, never by the model (LLMs converge
# on favourites like "Marcus Webb").
# The protagonist is male (production decision); the name is drawn from
# the male list. FEMALE_FIRST_NAMES is retained for any future use.
MALE_FIRST_NAMES = [
    "James", "David", "Michael", "Daniel", "Matthew", "Chris", "Andrew", "Ryan",
    "Kevin", "Brian", "Jason", "Eric", "Tyler", "Brandon", "Aaron", "Nathan",
    "Adam", "Zach", "Sean", "Kyle", "Derek", "Trevor", "Colin", "Grant",
    "Wesley", "Marcus", "Omar", "Victor", "Raj", "Dmitri", "Kenji", "Steve",
    "Paul", "Mark", "Greg", "Scott", "Todd", "Jeff", "Craig", "Doug",
    "Alan", "Neil", "Ian", "Owen", "Cole", "Wade", "Ross", "Lars",
]
FEMALE_FIRST_NAMES = [
    "Sarah", "Emily", "Jessica", "Ashley", "Amanda", "Megan", "Lauren", "Rachel",
    "Nicole", "Katie", "Hannah", "Alyssa", "Kayla", "Brooke", "Erin", "Molly",
    "Paige", "Claire", "Jenna", "Holly", "Dana", "Tara", "Robin", "Priya",
    "Elena", "Maya", "Nina", "Sofia", "Ingrid", "Leila",
]
FIRST_NAMES = MALE_FIRST_NAMES + FEMALE_FIRST_NAMES   # legacy alias
LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Taylor", "Anderson", "Thomas", "Jackson",
    "White", "Harris", "Martin", "Thompson", "Robinson", "Clark", "Lewis",
    "Walker", "Hall", "Young", "King", "Wright", "Scott", "Green", "Baker",
    "Adams", "Nelson", "Hill", "Campbell", "Mitchell", "Carter", "Phillips",
    "Evans", "Turner", "Parker", "Collins", "Edwards", "Stewart", "Morris",
    "Murphy", "Cook", "Rogers", "Reed", "Bailey", "Bell", "Cooper", "Ward",
    "Nguyen", "Patel", "Kim", "Garcia", "Martinez", "Chen", "Kowalski",
    "O'Brien", "MacLeod", "Fischer", "Novak", "Lindqvist", "Tanaka", "Haddad",
]


def random_protagonist_name(gender: str = "male") -> str:
    import random as _random
    pool = MALE_FIRST_NAMES if gender == "male" else FEMALE_FIRST_NAMES
    return f"{_random.choice(pool)} {_random.choice(LAST_NAMES)}"


PROMPT = """You are naming the cast of a serialized AD&D 1st-edition audio drama.
Below is the rolled party as JSON. Propose one name per character.

Rules:
- Names must fit race and class (dwarven names for dwarfs, etc.), feel like
  classic late-70s/early-80s fantasy, and be phonetically DISTINCT from each
  other (they'll be spoken aloud in audio — no two names may share a first
  syllable or rhyme).
- Look at the stats for flavour: a CHA 7 cleric might have a dour name; a
  DEX 17 gnome something quick and clever.
- The character marked "is_protagonist": true will be named separately by
  the production; return the exact placeholder string "PROTAGONIST" in
  their position.
- AVOID the stock fantasy names you would reach for first — be inventive,
  draw on varied real-world linguistic inspirations (Norse, Welsh, Slavic,
  Basque, Finnish, etc., filtered through a fantasy lens). Variety seed:
  {nonce} — let it push you toward different choices than previous runs.
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
    import random as _random
    raw = call_fn(PROMPT.format(roster=json.dumps(roster, indent=1),
                                nonce=_random.randint(100000, 999999)))
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    names = json.loads(cleaned)
    if not (isinstance(names, list) and len(names) == len(party)
            and all(isinstance(n, str) and n.strip() for n in names)):
        raise ValueError(f"Bad naming response: {raw[:200]}")
    names = [n.strip() for n in names]
    chosen = protagonist_name or random_protagonist_name()
    for i, e in enumerate(party):
        if e["character"]["is_protagonist"]:
            names[i] = chosen
    return names


def apply_names(party: list[dict], names: list[str]) -> None:
    for entry, name in zip(party, names):
        entry["character"]["name"] = name
