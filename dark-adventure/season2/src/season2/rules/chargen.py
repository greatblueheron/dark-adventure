"""Level-1 character generation (B/X via OSE).

House rules implemented here (change them, they're yours):
- Stats: 3d6 in order (classic). A character whose best stat is <= 9 is
  rerolled entirely ("hopeless character" rule) — up to 3 rerolls.
- HP: max HP at level 1 would be modern-soft; classic is a straight roll.
  Compromise default: roll, minimum 3 (a 1-HP magic-user dying to a house
  cat in Episode 1 is bad TV). Set MIN_START_HP = 1 for full B/X cruelty.
- Class: chosen to fit the stats (highest mod wins its class), subject to
  demihuman minimums and a target party composition.
"""
from __future__ import annotations

from .dice import Dice
from . import tables as T

MIN_START_HP = 3
STAT_ORDER = ["STR", "INT", "WIS", "DEX", "CON", "CHA"]

# Target composition for a 10-person party (adjust freely).
DEFAULT_COMPOSITION = [
    "Fighter", "Fighter", "Fighter", "Cleric", "Cleric",
    "Magic-User", "Thief", "Dwarf", "Elf", "Halfling",
]


def roll_stats(dice: Dice, name: str) -> dict[str, int]:
    for attempt in range(4):
        stats = {a: dice.stat_3d6(f"{name} {a}").total for a in STAT_ORDER}
        if max(stats.values()) > 9 or attempt == 3:
            return stats
    return stats  # unreachable


def eligible(cls: str, stats: dict[str, int]) -> bool:
    reqs = T.CLASS_REQUIREMENTS.get(cls, {})
    return all(stats[a] >= v for a, v in reqs.items())


def best_class(stats: dict[str, int], preferred: str | None = None) -> str:
    """Pick preferred class if the stats allow it; otherwise the class whose
    prime requisite the character is best at."""
    if preferred and eligible(preferred, stats):
        return preferred
    candidates = [c for c in T.CLASSES if eligible(c, stats)]
    def score(c: str) -> float:
        return sum(stats[a] for a in T.PRIME_REQUISITES[c]) / len(T.PRIME_REQUISITES[c])
    return max(candidates, key=score)


def make_character(
    dice: Dice, name: str, preferred_class: str | None = None,
    is_protagonist: bool = False,
) -> dict:
    """Roll one level-1 character. Returns a dict matching the `characters`
    table shape plus a 'starting_items' list for `inventory_items`."""
    stats = roll_stats(dice, name)
    cls = best_class(stats, preferred_class)

    hp_roll = dice.roll(T.HIT_DICE[cls], f"{name} HP").total + T.ability_mod(stats["CON"])
    max_hp = max(MIN_START_HP, hp_roll)

    kit = T.STARTING_KITS[cls]
    armor_ac = kit["armor"][1] - T.ability_mod(stats["DEX"])  # descending AC: DEX mod lowers
    gold = dice.roll("3d6", f"{name} starting gold").total * 10

    spells: list[str] = []
    slots: dict[str, dict] = {}
    if cls in T.SPELL_SLOTS:
        for i, n in enumerate(T.SPELL_SLOTS[cls].get(1, []), start=1):
            slots[str(i)] = {"max": n, "used": 0}
        if cls in ("Magic-User", "Elf"):
            idx = dice.roll(f"1d{len(T.FIRST_LEVEL_ARCANE)}", f"{name} starting spell").total - 1
            spells = ["Read Magic", T.FIRST_LEVEL_ARCANE[idx]]

    abilities = list(T.CLASS_ABILITIES[cls])
    if cls == "Thief":
        abilities.append(f"Thief skills: {T.THIEF_SKILLS[1]}")

    character = dict(
        name=name,
        is_protagonist=is_protagonist,
        **{"class": cls},
        ancestry={"Dwarf": "Dwarf", "Elf": "Elf", "Halfling": "Halfling"}.get(cls, "Human"),
        alignment="Neutral",
        level=1, xp=0,
        max_hp=max_hp, current_hp=max_hp,
        armor_class=armor_ac,
        stats=stats,
        saves=T.saves(cls, 1),
        abilities=abilities,
        spells_known=spells,
        spell_slots=slots,
        conditions=[],
        status="alive",
    )
    items = (
        [dict(name=kit["weapon"][0], properties={"damage": kit["weapon"][1]}, quantity=1),
         dict(name=kit["armor"][0], properties={"base_ac": kit["armor"][1]}, quantity=1)]
        + [dict(name=g, properties={}, quantity=1) for g in kit["gear"]]
        + [dict(name="Gold pieces", properties={}, quantity=gold)]
    )
    return dict(character=character, starting_items=items)


def generate_party(
    dice: Dice, names: list[str], protagonist_index: int = 0,
    composition: list[str] | None = None,
) -> list[dict]:
    comp = composition or DEFAULT_COMPOSITION
    assert len(names) == len(comp), "names and composition length mismatch"
    return [
        make_character(dice, n, preferred_class=c, is_protagonist=(i == protagonist_index))
        for i, (n, c) in enumerate(zip(names, comp))
    ]
