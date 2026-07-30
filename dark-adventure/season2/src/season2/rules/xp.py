"""XP and leveling (B/X). Gold-for-XP is IN (1 gp recovered = 1 XP) —
it's what makes B/X pacing work and gives litRPG-friendly loot numbers.

award() mutates nothing: it returns per-character payloads the loop turns
into events + character updates. process_levelup() takes a character dict
(DB shape) and returns the updated dict + level_up event payloads.
"""
from __future__ import annotations

from .dice import Dice
from . import tables as T


def award(characters: list[dict], monster_xp: int, treasure_gp: int) -> list[dict]:
    """Split (monster XP + treasure XP) evenly among living characters,
    then apply each character's prime-requisite % modifier."""
    living = [c for c in characters if c["status"] == "alive"]
    if not living:
        return []
    share = (monster_xp + treasure_gp) // len(living)
    out = []
    for c in living:
        bonus = T.prime_req_xp_bonus(c["class"], c["stats"])
        gained = int(share * (100 + bonus) / 100)
        out.append(dict(character_name=c["name"], xp_gained=gained,
                        xp_total=c["xp"] + gained, prime_req_bonus_pct=bonus))
    return out


def level_for_xp(cls: str, xp: int) -> int:
    thresholds = T.XP_THRESHOLDS[cls]
    level = 1
    for i, needed in enumerate(thresholds, start=1):
        if xp >= needed:
            level = i
    if level == T.MAX_LEVEL_ENCODED:
        # At the ceiling of encoded data. Loud warning so you extend tables
        # BEFORE the party actually needs level 7+.
        import warnings
        warnings.warn(f"{cls} at level {level}: tables.py only encodes to "
                      f"level {T.MAX_LEVEL_ENCODED} — extend soon.")
    return level


def process_levelup(dice: Dice, character: dict) -> tuple[dict, list[dict]]:
    """Check XP against thresholds; if the character levels, roll new HP,
    refresh saves/slots/skills. Returns (updated_character, event_payloads).
    Handles multi-level jumps one level at a time (rare but possible with
    big treasure hauls)."""
    c = dict(character)
    events: list[dict] = []
    target = level_for_xp(c["class"], c["xp"])

    while c["level"] < target:
        c["level"] += 1
        hp_gain = max(1, dice.roll(T.HIT_DICE[c["class"]], f"{c['name']} HP for level {c['level']}").total
                      + T.ability_mod(c["stats"]["CON"]))
        c["max_hp"] += hp_gain
        c["current_hp"] += hp_gain
        c["saves"] = T.saves(c["class"], c["level"])

        gained: list[str] = [f"+{hp_gain} HP"]
        if c["class"] in T.SPELL_SLOTS:
            slots = {str(i): {"max": n, "used": 0}
                     for i, n in enumerate(T.SPELL_SLOTS[c["class"]].get(c["level"], []), start=1)}
            old_total = sum(v["max"] for v in c["spell_slots"].values())
            new_total = sum(v["max"] for v in slots.values())
            c["spell_slots"] = slots
            if new_total > old_total:
                gained.append(f"spell slots now {[v['max'] for v in slots.values()]}")
        if c["class"] == "Thief":
            c["abilities"] = [a for a in c["abilities"] if not a.startswith("Thief skills:")]
            c["abilities"].append(f"Thief skills: {T.THIEF_SKILLS[c['level']]}")
            gained.append("thief skills improved")

        events.append(dict(
            type="level_up", character_name=c["name"], new_level=c["level"],
            description=f"{c['name']} reaches level {c['level']} ({', '.join(gained)})",
            data=dict(hp_gain=hp_gain, gains=gained),
        ))
    return c, events
