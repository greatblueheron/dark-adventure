"""AD&D 1e character generation — fully dice-driven ("the dice cast the show").

Every character, protagonist included, is generated the same way:
1. Race is rolled on a weighted table (humans most common, per 1e
   demographics) — except the protagonist, who is always Human (they are
   a modern person from our world).
2. Stats are 5d6-drop-the-two-lowest rolled strictly IN ORDER (STR, INT,
   WIS, DEX, CON, CHA) — a heroic house rule. No arrange-to-taste. Racial
   adjustments apply after.
3. Class EMERGES from the stats: among the classes this race may take and
   these stats legally qualify for, the one whose prime requisites the
   character is best at. Nobody chooses; the rolls decide who exists.

House rules:
- HP: rolled; minimum 3 at level 1 (MIN_START_HP) so nobody starts at 1 hp.
- The PROTAGONIST gets maximum possible level-1 HP for their emergent
  class (+ CON adjustment) — plot armour, deliberately.
- OSRIC racial ability min/maxes are not enforced (only class minimums and
  race/class legality) — a rolled dwarf with CON 9 simply exists.
- Alignment is ROLLED on a weighted nine-point table (good/neutral-heavy,
  evil corners live) and clamped to class constraints (Paladin LG, Druid
  TN, Ranger any Good, Thief non-LG/CG). The protagonist's rolled
  alignment is what the world's magic READS them as — a modern person has
  no cosmic stamp, so treat it as a mystery hook in the bible.
"""
from __future__ import annotations

from .dice import Dice
from . import tables as T

MIN_START_HP = 3
ABILITIES = ["STR", "INT", "WIS", "DEX", "CON", "CHA"]

# Weighted race table (d100): humans dominate, exotic races are rare.
RACE_TABLE = [
    (50, "Human"), (62, "Dwarf"), (72, "Elf"), (82, "Half-elf"),
    (90, "Halfling"), (95, "Gnome"), (100, "Half-orc"),
]


def roll_race(dice: Dice, name: str) -> str:
    roll = dice.roll("1d100", f"{name} race").total
    for ceiling, race in RACE_TABLE:
        if roll <= ceiling:
            return race
    return "Human"


def roll_5d6_drop_two(dice: Dice, label: str) -> int:
    """5d6, drop the two lowest (house rule — heroic cast)."""
    r = dice.roll("5d6", label)
    return r.total - sum(sorted(r.rolls)[:2])


def natural_stats(dice: Dice, name: str) -> dict[str, int]:
    """5d6-drop-two-lowest rolled IN ORDER — the dice decide who this is."""
    return {a: roll_5d6_drop_two(dice, f"{name} {a}") for a in ABILITIES}


def apply_racial_adjustments(stats: dict[str, int], race: str) -> dict[str, int]:
    out = dict(stats)
    for ability, adj in T.RACIAL_ADJUSTMENTS[race].items():
        out[ability] = max(3, min(18, out[ability] + adj))
    return out


def meets(cls: str, stats: dict[str, int]) -> bool:
    return all(stats[a] >= v for a, v in T.CLASS_REQUIREMENTS[cls].items())


def emergent_class(stats: dict[str, int], race: str) -> str:
    """Among legally qualified classes for this race, the one whose prime
    requisites the character is best at. Fighter breaks ties (it is the
    common calling) and is the floor if nothing qualifies (near-impossible
    with 4d6-drop-lowest)."""
    candidates = [c for c in T.RACE_CLASSES[race] if meets(c, stats)]
    if not candidates:
        return "Fighter"
    def score(c):
        primes = T.PRIME_REQUISITES[c] or ["INT"]   # illusionists list none
        return (sum(stats[a] for a in primes) / len(primes), c == "Fighter")
    return max(candidates, key=score)


def roll_alignment(dice: Dice, name: str, cls: str) -> str:
    """Weighted nine-point alignment roll, re-rolled until it satisfies the
    class's constraint (Paladin->LG, Druid->TN, Ranger->Good, Thief->non-
    LG/CG). Re-rolling (rather than snapping to a fixed value) keeps the
    permitted spread: a Ranger can be any flavour of Good."""
    allowed = T.ALIGNMENT_CONSTRAINTS.get(cls, set(T.ALIGNMENTS))
    for _ in range(50):
        roll = dice.roll("1d100", f"{name} alignment").total
        alignment = next(a for ceiling, a in T.ALIGNMENT_TABLE if roll <= ceiling)
        if alignment in allowed:
            return alignment
    return sorted(allowed)[0]           # deterministic fallback, unreachable


def _max_die(notation: str) -> int:
    """Maximum possible roll for 'NdM' notation ('2d8' -> 16)."""
    n, m = notation.lower().split("d")
    return int(n or 1) * int(m)


def _random_spells(dice, name, spell_list, count, exclude=frozenset()):
    pool = [sp for sp in spell_list if sp not in exclude]
    out = []
    for i in range(count):
        idx = dice.roll(f"1d{len(pool)}", f"{name} starting spell {i+1}").total - 1
        out.append(pool.pop(idx))
    return out


def make_character(dice: Dice, name: str, race: str | None = None,
                   is_protagonist: bool = False) -> dict:
    """Roll one level-1 character, fully dice-driven. Race is rolled unless
    given; the protagonist is always Human."""
    if is_protagonist:
        race = "Human"
    elif race is None:
        race = roll_race(dice, name)

    stats = apply_racial_adjustments(natural_stats(dice, name), race)
    cls = emergent_class(stats, race)
    alignment = roll_alignment(dice, name, cls)

    if cls in T.WARRIORS and stats["STR"] == 18:
        stats["STR_percentile"] = dice.roll("1d100", f"{name} exceptional STR").total

    hd = T.FIRST_LEVEL_HD.get(cls, T.HIT_DICE[cls][0])
    rolled = dice.roll(hd, f"{name} HP").total     # consumed even for the
    if is_protagonist:                             # protagonist, preserving
        rolled = _max_die(hd)                      # the seed's dice stream
    hp_roll = rolled + T.con_hp_adj(stats["CON"], cls)
    max_hp = max(MIN_START_HP, hp_roll)

    kit = T.STARTING_KITS[cls]
    armor_ac = kit["armor"][1] + T.dex_ac_adj(stats["DEX"])
    gold = dice.roll("3d6", f"{name} starting gold").total * 10

    spells: list[str] = []
    slots: dict[str, dict] = {}
    if cls in ("Cleric", "Druid", "Magic-User", "Illusionist"):
        base = list(T.SPELL_SLOTS[cls][1])
        if cls in ("Cleric", "Druid"):              # wisdom bonus spells (OSRIC)
            for i, n in enumerate(T.wis_bonus_spells(stats["WIS"])):
                if i < len(base):
                    base[i] += n
                else:
                    base.append(n)
        slots = {str(i): {"max": n, "used": 0} for i, n in enumerate(base, start=1)}
        if cls == "Magic-User":
            # OSRIC: starts knowing 4 spells — Read Magic + 3 others
            spells = ["Read Magic"] + _random_spells(
                dice, name, T.FIRST_LEVEL_ARCANE, 3, exclude={"Read Magic"})
        elif cls == "Illusionist":
            # OSRIC: 4 spells, no Read Magic (phantasmal script)
            spells = _random_spells(dice, name, T.FIRST_LEVEL_ILLUSION, 4)

    abilities = list(T.CLASS_ABILITIES[cls]) + list(T.RACE_ABILITIES[race])
    if cls == "Thief":
        abilities.append(f"Thief skills: {T.thief_skills(1, stats['DEX'], race)}")

    character = dict(
        name=name, is_protagonist=is_protagonist,
        **{"class": cls}, ancestry=race, alignment=alignment,
        level=1, xp=0, max_hp=max_hp, current_hp=max_hp,
        armor_class=armor_ac, stats=stats, saves=T.saves(cls, 1),
        abilities=abilities, spells_known=spells, spell_slots=slots,
        conditions=[], status="alive",
    )
    items = (
        [dict(name=kit["weapon"][0], properties={"damage": kit["weapon"][1]}, quantity=1),
         dict(name=kit["armor"][0], properties={"base_ac": kit["armor"][1]}, quantity=1)]
        + [dict(name=g, properties={}, quantity=1) for g in kit["gear"]]
        + [dict(name="Gold pieces", properties={}, quantity=gold)]
    )
    return dict(character=character, starting_items=items)


def generate_party(dice: Dice, names: list[str], protagonist_index: int = 0) -> list[dict]:
    return [
        make_character(dice, n, is_protagonist=(i == protagonist_index))
        for i, n in enumerate(names)
    ]
