"""AD&D 1e reference tables — VERIFIED against OSRIC (fetched from the
OSRIC SRD, July 2026; OSRIC is the open-licensed restatement of 1e).

Encoded to level 14 — covers the classic module chain through Queen of the
Demonweb Pits (levels 10-14). OSRIC's XP progressions intentionally differ
slightly from the original 1e PHB (legal reasons); they are the canonical
numbers for this engine.

Conventions:
- Descending AC (unarmoured = 10)
- Race and class are separate; single-class only (multiclass = later)
- Exceptional Strength for warriors at STR 18 (d% stored as STR_percentile)
- Saves use OSRIC's five categories:
  R = aimed magic items (rod/staff/wand), B = breath weapon,
  D = death/paralysis/poison, T = petrifaction/polymorph, S = spells
"""

RACES = ["Human", "Dwarf", "Elf", "Half-elf", "Halfling", "Gnome", "Half-orc"]
CLASSES = ["Fighter", "Ranger", "Paladin", "Cleric", "Druid",
           "Magic-User", "Illusionist", "Thief"]
WARRIORS = {"Fighter", "Ranger", "Paladin"}

MAX_LEVEL_ENCODED = 14
HARD_LEVEL_CAP = {"Druid": 14}          # OSRIC: druids cannot exceed 14

# ---- racial ability adjustments (OSRIC; clamped 3-18 after) ----
RACIAL_ADJUSTMENTS = {
    "Dwarf":    {"CON": 1, "CHA": -1},
    "Elf":      {"DEX": 1, "CON": -1},
    "Halfling": {"DEX": 1, "STR": -1},
    "Half-orc": {"STR": 1, "CON": 1, "CHA": -2},
    "Human": {}, "Half-elf": {}, "Gnome": {},
}

# ---- permitted single classes per race (OSRIC lists; assassin excluded) ----
RACE_CLASSES = {
    "Human":    set(CLASSES),
    "Dwarf":    {"Fighter", "Cleric", "Thief"},
    "Elf":      {"Fighter", "Cleric", "Magic-User", "Thief"},
    "Half-elf": {"Fighter", "Ranger", "Cleric", "Magic-User", "Thief"},
    "Halfling": {"Fighter", "Thief"},
    "Gnome":    {"Fighter", "Cleric", "Illusionist", "Thief"},
    "Half-orc": {"Fighter", "Cleric", "Thief"},
}

# ---- class minimum scores (OSRIC, all six abilities) ----
CLASS_REQUIREMENTS = {
    "Fighter":    dict(STR=9, DEX=6, CON=7, INT=3, WIS=6, CHA=6),
    "Ranger":     dict(STR=13, DEX=6, CON=14, INT=13, WIS=14, CHA=6),
    "Paladin":    dict(STR=12, DEX=6, CON=9, INT=9, WIS=13, CHA=17),
    "Cleric":     dict(STR=6, DEX=3, CON=6, INT=6, WIS=9, CHA=6),
    "Druid":      dict(STR=6, DEX=6, CON=6, INT=6, WIS=12, CHA=15),
    "Magic-User": dict(STR=3, DEX=6, CON=6, INT=9, WIS=6, CHA=6),
    "Illusionist": dict(STR=6, DEX=16, CON=3, INT=15, WIS=6, CHA=6),
    "Thief":      dict(STR=6, DEX=9, CON=6, INT=6, WIS=3, CHA=6),
}

# ---- stat-assignment priority ("arrange to taste") per class ----
STAT_PRIORITIES = {
    "Fighter":    ["STR", "CON", "DEX", "WIS", "CHA", "INT"],
    "Ranger":     ["WIS", "CON", "STR", "INT", "DEX", "CHA"],
    "Paladin":    ["CHA", "WIS", "STR", "CON", "INT", "DEX"],
    "Cleric":     ["WIS", "CON", "STR", "DEX", "INT", "CHA"],
    "Druid":      ["WIS", "CHA", "CON", "DEX", "STR", "INT"],
    "Magic-User": ["INT", "DEX", "CON", "WIS", "CHA", "STR"],
    "Illusionist": ["DEX", "INT", "CON", "WIS", "CHA", "STR"],
    "Thief":      ["DEX", "STR", "CON", "INT", "WIS", "CHA"],
}

# ---- ability adjustments (OSRIC Chapter I tables) ----
def str_hit_adj(stats: dict) -> int:
    s, pct = stats["STR"], stats.get("STR_percentile", 0)
    if s == 3: return -3
    if s <= 5: return -2
    if s <= 7: return -1
    if s <= 16: return 0
    if s == 17: return 1
    # 18 and 18/xx (00 = STR 19 in OSRIC)
    if pct == 100: return 3
    if pct >= 51: return 2
    return 1

def str_dmg_adj(stats: dict) -> int:
    s, pct = stats["STR"], stats.get("STR_percentile", 0)
    if s <= 5: return -1
    if s <= 15: return 0
    if s <= 17: return 1
    if pct == 0: return 2
    if pct <= 75: return 3
    if pct <= 90: return 4
    if pct <= 99: return 5
    return 6

def dex_ac_adj(dex: int) -> int:
    """Added to descending AC (negative = better)."""
    if dex == 3: return 4
    if dex == 4: return 3
    if dex == 5: return 2
    if dex == 6: return 1
    if dex <= 14: return 0
    return -(min(dex, 18) - 14)          # 15:-1 16:-2 17:-3 18:-4

def dex_missile_adj(dex: int) -> int:
    if dex == 3: return -3
    if dex == 4: return -2
    if dex == 5: return -1
    if dex <= 15: return 0
    return min(dex, 18) - 15             # 16:+1 17:+2 18:+3

def con_hp_adj(con: int, cls: str) -> int:
    if con == 3: return -2
    if con <= 6: return -1
    if con <= 14: return 0
    if con == 15: return 1
    if con == 16: return 2
    return (3 if con == 17 else 4) if cls in WARRIORS else 2

# ---- XP bonus: +10% if ALL listed abilities are 16+ (OSRIC per class) ----
PRIME_REQUISITES = {
    "Fighter": ["STR"], "Ranger": ["STR", "INT", "WIS"], "Paladin": ["STR", "WIS"],
    "Cleric": ["WIS"], "Druid": ["WIS", "CHA"], "Magic-User": ["INT"],
    "Illusionist": [], "Thief": ["DEX"],     # illusionists get no XP bonus
}

def prime_req_xp_bonus(cls: str, stats: dict) -> int:
    primes = PRIME_REQUISITES[cls]
    return 10 if primes and all(stats[a] >= 16 for a in primes) else 0

# ---- hit dice (die, cap level, flat hp/level after cap) ----
# After the cap, CON adjustments no longer apply (OSRIC).
HIT_DICE = {
    "Fighter":    ("1d10", 9, 3),
    "Ranger":     ("1d8", 11, 2),        # 2d8 at level 1, see FIRST_LEVEL_HD
    "Paladin":    ("1d10", 9, 3),
    "Cleric":     ("1d8", 9, 2),
    "Druid":      ("1d8", 14, 0),
    "Magic-User": ("1d4", 11, 1),
    "Illusionist": ("1d4", 10, 1),
    "Thief":      ("1d6", 10, 2),
}
FIRST_LEVEL_HD = {"Ranger": "2d8"}

# ---- XP required to BE each level (index 0 = level 1), OSRIC exact ----
XP_THRESHOLDS = {
    "Fighter":    [0, 1900, 4250, 7750, 16000, 35000, 75000, 125000, 250000,
                   500000, 750000, 1000000, 1250000, 1500000],
    "Ranger":     [0, 2250, 4500, 9500, 20000, 40000, 90000, 150000, 225000,
                   325000, 650000, 975000, 1300000, 1625000],
    "Paladin":    [0, 2550, 5500, 12500, 25000, 45000, 95000, 175000, 325000,
                   600000, 1000000, 1350000, 1700000, 2050000],
    "Cleric":     [0, 1550, 2900, 6000, 13250, 27000, 55000, 110000, 220000,
                   450000, 675000, 900000, 1125000, 1350000],
    "Druid":      [0, 2000, 4000, 8000, 12000, 20000, 35000, 60000, 90000,
                   125000, 200000, 300000, 750000, 1500000],
    "Magic-User": [0, 2400, 4800, 10250, 22000, 40000, 60000, 80000, 140000,
                   250000, 375000, 750000, 1125000, 1500000],
    "Illusionist": [0, 2500, 4750, 9000, 18000, 35000, 60250, 95000, 144500,
                    220000, 440000, 660000, 880000, 1100000],
    "Thief":      [0, 1250, 2500, 5000, 10000, 20000, 40000, 70000, 110000,
                   160000, 220000, 440000, 660000, 880000],
}

# ---- to-hit: THAC0 (score needed vs AC 0), from OSRIC matrices ----
# Simplification: needed = thac0 - target AC; natural 20 always hits,
# natural 1 always misses. (The matrices' "repeating 20s" vs very low ACs
# are approximated by the natural-20 rule.)
_FIGHTER_THAC0 = {lv: 21 - lv for lv in range(1, 15)}   # 1:20 ... 14:7
THAC0_TABLE = {
    "Fighter": _FIGHTER_THAC0, "Ranger": _FIGHTER_THAC0, "Paladin": _FIGHTER_THAC0,
    "Cleric": {1: 20, 2: 20, 3: 20, 4: 18, 5: 18, 6: 18, 7: 16, 8: 16, 9: 16,
               10: 14, 11: 14, 12: 14, 13: 12, 14: 12},
    "Druid":  {1: 20, 2: 20, 3: 20, 4: 18, 5: 18, 6: 18, 7: 16, 8: 16, 9: 16,
               10: 14, 11: 14, 12: 14, 13: 12, 14: 12},
    "Magic-User": {**{lv: 20 for lv in range(1, 6)}, **{lv: 19 for lv in range(6, 11)},
                   **{lv: 17 for lv in range(11, 15)}},
    "Illusionist": {**{lv: 20 for lv in range(1, 6)}, **{lv: 19 for lv in range(6, 11)},
                    **{lv: 17 for lv in range(11, 15)}},
    "Thief": {**{lv: 20 for lv in range(1, 5)}, **{lv: 19 for lv in range(5, 9)},
              **{lv: 16 for lv in range(9, 13)}, **{lv: 14 for lv in range(13, 15)}},
}

def thac0(cls: str, level: int) -> int:
    try:
        return THAC0_TABLE[cls][level]
    except KeyError:
        raise KeyError(f"THAC0 not encoded for {cls} level {level} — extend tables.py")

# ---- saving throws (OSRIC exact, by level band) ----
SAVE_BANDS = {
    "Fighter": [(1, 2, dict(R=16, B=17, D=14, T=15, S=17)),
                (3, 4, dict(R=15, B=16, D=13, T=14, S=16)),
                (5, 6, dict(R=13, B=13, D=11, T=12, S=14)),
                (7, 8, dict(R=12, B=12, D=10, T=11, S=13)),
                (9, 10, dict(R=10, B=9, D=8, T=9, S=11)),
                (11, 12, dict(R=9, B=8, D=7, T=8, S=10)),
                (13, 14, dict(R=7, B=5, D=5, T=6, S=8))],
    "Paladin": [(1, 2, dict(R=14, B=15, D=12, T=13, S=15)),
                (3, 4, dict(R=13, B=14, D=11, T=12, S=14)),
                (5, 6, dict(R=11, B=11, D=9, T=10, S=12)),
                (7, 8, dict(R=10, B=10, D=8, T=9, S=11)),
                (9, 10, dict(R=8, B=7, D=6, T=7, S=9)),
                (11, 12, dict(R=7, B=6, D=5, T=6, S=8)),
                (13, 14, dict(R=5, B=3, D=3, T=4, S=6))],
    "Cleric":  [(1, 3, dict(R=14, B=16, D=10, T=13, S=15)),
                (4, 6, dict(R=13, B=15, D=9, T=12, S=14)),
                (7, 9, dict(R=11, B=13, D=7, T=10, S=12)),
                (10, 12, dict(R=10, B=12, D=6, T=9, S=11)),
                (13, 15, dict(R=9, B=11, D=5, T=8, S=10))],
    "Magic-User": [(1, 5, dict(R=11, B=15, D=14, T=13, S=12)),
                   (6, 10, dict(R=9, B=13, D=13, T=11, S=10)),
                   (11, 15, dict(R=7, B=11, D=11, T=9, S=8))],
    "Thief":   [(1, 4, dict(R=14, B=16, D=13, T=12, S=15)),
                (5, 8, dict(R=12, B=15, D=12, T=11, S=13)),
                (9, 12, dict(R=10, B=14, D=11, T=10, S=11)),
                (13, 16, dict(R=8, B=13, D=10, T=9, S=9))],
}
SAVE_GROUP = {"Fighter": "Fighter", "Ranger": "Fighter", "Paladin": "Paladin",
              "Cleric": "Cleric", "Druid": "Cleric",
              "Magic-User": "Magic-User", "Illusionist": "Magic-User",
              "Thief": "Thief"}

def saves(cls: str, level: int) -> dict[str, int]:
    for lo, hi, table in SAVE_BANDS[SAVE_GROUP[cls]]:
        if lo <= level <= hi:
            return dict(table)
    raise KeyError(f"Saves not encoded for {cls} level {level} — extend tables.py")

# ---- spell slots by class level (OSRIC exact, levels 1-14) ----
SPELL_SLOTS = {
    "Cleric": {1: [1], 2: [2], 3: [2, 1], 4: [3, 2], 5: [3, 3, 1], 6: [3, 3, 2],
               7: [3, 3, 2, 1], 8: [3, 3, 3, 2], 9: [4, 4, 3, 2, 1],
               10: [4, 4, 3, 3, 2], 11: [5, 4, 4, 3, 2, 1], 12: [6, 5, 5, 3, 2, 2],
               13: [6, 6, 6, 4, 2, 2], 14: [6, 6, 6, 5, 3, 2]},
    "Druid": {1: [2], 2: [2, 1], 3: [3, 2, 1], 4: [4, 2, 2], 5: [4, 3, 2],
              6: [4, 3, 2, 1], 7: [4, 4, 3, 1], 8: [4, 4, 3, 2],
              9: [5, 4, 3, 2, 1], 10: [5, 4, 3, 3, 2], 11: [5, 5, 3, 3, 2, 1],
              12: [5, 5, 4, 4, 3, 2, 1], 13: [6, 5, 5, 5, 4, 3, 2],
              14: [6, 6, 6, 6, 5, 4, 3]},
    "Magic-User": {1: [1], 2: [2], 3: [2, 1], 4: [3, 2], 5: [4, 2, 1],
                   6: [4, 3, 2], 7: [4, 3, 2, 1], 8: [4, 3, 3, 2],
                   9: [4, 4, 3, 2, 1], 10: [4, 4, 3, 2, 2], 11: [4, 4, 4, 3, 3],
                   12: [5, 4, 4, 3, 3, 1], 13: [5, 5, 4, 3, 3, 2],
                   14: [5, 5, 5, 4, 4, 2, 1]},
    "Illusionist": {1: [1], 2: [2], 3: [2, 1], 4: [3, 2], 5: [4, 3, 1],
                    6: [4, 3, 2], 7: [4, 3, 2, 1], 8: [4, 3, 2, 2],
                    9: [5, 3, 3, 2], 10: [5, 4, 3, 2, 1], 11: [5, 4, 3, 3, 2],
                    12: [5, 5, 4, 3, 2, 1], 13: [5, 5, 4, 3, 2, 2],
                    14: [5, 5, 4, 3, 2, 2, 1]},
    # Rangers (druid + MU spells from level 8) and paladins (cleric spells
    # from level 9) — stored as dicts keyed by list kind.
    "Ranger": {8: {"druid": [1]}, 9: {"druid": [1], "mu": [1]},
               10: {"druid": [2], "mu": [1]}, 11: {"druid": [2], "mu": [2]},
               12: {"druid": [2, 1], "mu": [2]}, 13: {"druid": [2, 1], "mu": [2, 1]},
               14: {"druid": [2, 2], "mu": [2, 1]}},
    "Paladin": {9: [1], 10: [2], 11: [2, 1], 12: [2, 2], 13: [2, 2, 1],
                14: [3, 2, 1]},
}

def wis_bonus_spells(wis: int) -> list[int]:
    """Bonus divine spells per spell level for clerics/druids (OSRIC)."""
    return {13: [1], 14: [2], 15: [2, 1], 16: [2, 2], 17: [2, 2, 1],
            18: [2, 2, 1, 1]}.get(min(wis, 18), [])

FIRST_LEVEL_ARCANE = [
    "Burning Hands", "Charm Person", "Comprehend Languages", "Dancing Lights",
    "Detect Magic", "Enlarge", "Feather Fall", "Find Familiar", "Friends",
    "Hold Portal", "Identify", "Jump", "Light", "Magic Missile", "Mending",
    "Message", "Protection from Evil", "Push", "Read Magic", "Shield",
    "Shocking Grasp", "Sleep", "Spider Climb", "Unseen Servant", "Ventriloquism",
]
FIRST_LEVEL_ILLUSION = [
    "Audible Glamour", "Change Self", "Colour Spray", "Dancing Lights",
    "Darkness", "Detect Illusion", "Detect Invisibility", "Fog Cloud",
    "Gaze Reflection", "Hypnotism", "Light", "Phantasmal Force", "Wall of Fog",
]

# ---- thief skills (OSRIC base table 1-14 + DEX and racial adjustments) ----
_THIEF_BASE = {
    #      climb traps hear hide move locks pockets read
    1:  (80, 25, 10, 20, 20, 30, 35, 1),
    2:  (82, 29, 13, 25, 25, 34, 39, 5),
    3:  (84, 33, 16, 30, 30, 38, 43, 10),
    4:  (86, 37, 19, 35, 35, 42, 47, 15),
    5:  (88, 41, 22, 40, 40, 46, 51, 20),
    6:  (90, 45, 25, 45, 45, 50, 55, 25),
    7:  (91, 49, 28, 50, 50, 54, 59, 30),
    8:  (92, 53, 31, 55, 55, 58, 63, 35),
    9:  (93, 57, 34, 60, 60, 62, 67, 40),
    10: (94, 61, 37, 65, 65, 66, 71, 45),
    11: (95, 65, 40, 70, 70, 70, 75, 50),
    12: (96, 69, 43, 75, 75, 74, 79, 55),
    13: (97, 73, 46, 80, 80, 78, 83, 60),
    14: (98, 77, 49, 85, 85, 82, 87, 65),
}
_SKILL_KEYS = ["climb", "traps", "hear", "hide", "move", "locks", "pockets", "read"]

_THIEF_DEX_ADJ = {
    9:  dict(traps=-15, hide=-10, move=-20, locks=-10, pockets=-15),
    10: dict(traps=-10, hide=-5, move=-15, locks=-5, pockets=-10),
    11: dict(traps=-5, move=-10, pockets=-5),
    12: dict(move=-5),
    16: dict(locks=5),
    17: dict(traps=5, hide=5, move=5, locks=10),
    18: dict(traps=10, hide=10, move=10, locks=15, pockets=5),
}
_THIEF_RACE_ADJ = {
    "Dwarf":    dict(climb=-10, traps=15, move=-5, locks=15, read=-5),
    "Elf":      dict(climb=-5, traps=5, hear=5, hide=10, move=5, locks=-5, pockets=5, read=10),
    "Gnome":    dict(climb=-15, hear=5, locks=10),
    "Half-elf": dict(hide=5, pockets=10),
    "Halfling": dict(climb=-15, hear=5, hide=15, move=15, pockets=5, read=-5),
    "Half-orc": dict(climb=5, traps=5, hear=5, locks=5, pockets=-5, read=-10),
    "Human":    dict(climb=5, locks=5),
}

def thief_skills(level: int, dex: int, race: str) -> dict[str, int]:
    if level not in _THIEF_BASE:
        raise KeyError(f"Thief skills not encoded for level {level} — extend tables.py")
    base = dict(zip(_SKILL_KEYS, _THIEF_BASE[level]))
    for k, v in _THIEF_DEX_ADJ.get(min(dex, 18), {}).items():
        base[k] += v
    for k, v in _THIEF_RACE_ADJ.get(race, {}).items():
        base[k] += v
    return {k: max(1, min(99, v)) for k, v in base.items()}

# ---- class + race narrative-facing ability tags (OSRIC summaries) ----
CLASS_ABILITIES = {
    "Fighter": ["Any weapon & armour", "Extra attacks vs sub-1HD foes (1/level)"],
    "Ranger": ["Tracking (90% rural / 65% dungeon)", "+1/level melee damage vs evil humanoids & giants",
               "Surprised only on 1-in-6, surprises on 1-3"],
    "Paladin": ["Detect evil 60'", "Improved saves", "Protection from evil aura 10'",
                "Lay on hands (2 hp/level, 1/day)", "Cure disease 1/week", "Immune to disease",
                "Turn undead (from level 3)", "Warhorse (from level 4)"],
    "Cleric": ["Turn undead", "Divine spellcasting", "Blunt weapons only"],
    "Druid": ["Nature spellcasting", "+2 saves vs fire & lightning", "Druids' cant",
              "Druid's knowledge & trackless step (from level 3)"],
    "Magic-User": ["Arcane spellcasting", "Spellbook", "Dagger/dart/staff only, no armour"],
    "Illusionist": ["Phantasmal spellcasting", "Spellbook (phantasmal script)",
                    "Dagger/dart/staff only, no armour"],
    "Thief": ["Thief skills", "Backstab (+4 to hit, x2 damage; x3 at level 5+)",
              "Thieves' cant", "Leather/studded armour only"],
}
RACE_ABILITIES = {
    "Human": [],
    "Dwarf": ["Infravision 60'", "+1 to hit orcs/goblins/hobgoblins/half-orcs",
              "Save bonus vs magic & poison (+1 per 3.5 CON)",
              "-4 to be hit by giants/ogres/trolls/titans", "Detect stonework tricks"],
    "Elf": ["Infravision 60'", "90% resist sleep/charm", "+1 with bows & swords",
            "Detect secret doors (2-in-6 searching)", "Stealthy (4-in-6 surprise)"],
    "Half-elf": ["Infravision 60'", "30% resist sleep/charm", "Detect secret doors (2-in-6)"],
    "Halfling": ["+3 with bow or sling", "Save bonus vs magic & poison (+1 per 3.5 CON)",
                 "Stealthy (4-in-6 surprise)"],
    "Gnome": ["Infravision 60'", "+1 to hit kobolds & goblins",
              "Save bonus vs magic & poison (+1 per 3.5 CON)",
              "-4 to be hit by bugbears/giants/gnolls/ogres/trolls",
              "Speak with burrowing animals", "Detect slopes/depth underground"],
    "Half-orc": ["Infravision 60'"],
}

# ---- starting equipment kits (1e unarmoured AC = 10) ----
STARTING_KITS = {
    "Fighter": dict(weapon=("Longsword", "1d8"), armor=("Chain mail + shield", 4),
                    gear=["Backpack", "Torches (6)", "Rations (7 days)", "Waterskin"]),
    "Ranger": dict(weapon=("Longsword", "1d8"), armor=("Studded leather", 7),
                   gear=["Longbow + arrows (20)", "Backpack", "Rations (7 days)", "Rope (50')"]),
    "Paladin": dict(weapon=("Longsword", "1d8"), armor=("Chain mail + shield", 4),
                    gear=["Holy symbol", "Backpack", "Rations (7 days)"]),
    "Cleric": dict(weapon=("Mace", "1d6+1"), armor=("Chain mail + shield", 4),
                   gear=["Holy symbol", "Backpack", "Torches (6)", "Rations (7 days)"]),
    "Druid": dict(weapon=("Scimitar", "1d8"), armor=("Leather + wooden shield", 7),
                  gear=["Mistletoe", "Backpack", "Rations (7 days)"]),
    "Magic-User": dict(weapon=("Dagger", "1d4"), armor=("Robes", 10),
                       gear=["Spellbook", "Backpack", "Lantern", "Oil (2 flasks)", "Rations (7 days)"]),
    "Illusionist": dict(weapon=("Dagger", "1d4"), armor=("Robes", 10),
                        gear=["Spellbook", "Backpack", "Lantern", "Rations (7 days)"]),
    "Thief": dict(weapon=("Longsword", "1d8"), armor=("Leather", 8),
                  gear=["Thieves' tools", "Backpack", "Rope (50')", "Torches (6)", "Rations (7 days)"]),
}

# ---- alignment (AD&D nine-point grid) ----
ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil",
]

# Weighted d100 table for rolled alignment: adventurers answering a call to
# defend the Borderlands skew good/neutral, but the evil corners are live —
# a hidden Neutral Evil party member is long-arc drama the dice may seed.
ALIGNMENT_TABLE = [
    (16, "Lawful Good"), (34, "Neutral Good"), (48, "Chaotic Good"),
    (60, "Lawful Neutral"), (70, "True Neutral"), (84, "Chaotic Neutral"),
    (89, "Lawful Evil"), (95, "Neutral Evil"), (100, "Chaotic Evil"),
]

# Class alignment constraints (OSRIC):
#   Paladin: Lawful Good only. Druid: True Neutral only.
#   Ranger: any Good. Thief: any neutral or evil, plus Neutral Good
#   (permitted via its neutral component); LG and CG are barred.
ALIGNMENT_CONSTRAINTS = {
    "Paladin": {"Lawful Good"},
    "Druid": {"True Neutral"},
    "Ranger": {"Lawful Good", "Neutral Good", "Chaotic Good"},
    "Thief": set(ALIGNMENTS) - {"Lawful Good", "Chaotic Good"},
}


# ---- morale & reactions (2d6 house rule; OSRIC/1e use d%) ----
def reaction_result(total: int) -> str:
    if total <= 2: return "hostile_attacks"
    if total <= 5: return "hostile_maybe"
    if total <= 8: return "uncertain"
    if total <= 11: return "indifferent"
    return "friendly"
