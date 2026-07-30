"""B/X reference tables (per the OSE SRD restatement of B/X).

Everything here is DATA, not logic. Values were transcribed from memory of
the OSE SRD — VERIFY against https://oldschoolessentials.necroticgnome.com/srd/
before your first published episode. Tables cover levels 1-6; extend before
the party outgrows them (the engine raises loudly if data is missing).

B/X conventions used throughout:
- Descending AC (unarmored = 9, plate+shield = 2)
- Race-as-class (Dwarf/Elf/Halfling are classes)
- Attack via THAC0 bands; saves via level bands
"""

CLASSES = ["Fighter", "Cleric", "Magic-User", "Thief", "Dwarf", "Elf", "Halfling"]

# ---- ability score modifiers (3-18) ----
def ability_mod(score: int) -> int:
    if score <= 3: return -3
    if score <= 5: return -2
    if score <= 8: return -1
    if score <= 12: return 0
    if score <= 15: return 1
    if score <= 17: return 2
    return 3

PRIME_REQUISITES = {
    "Fighter": ["STR"], "Cleric": ["WIS"], "Magic-User": ["INT"],
    "Thief": ["DEX"], "Dwarf": ["STR"], "Elf": ["INT", "STR"], "Halfling": ["STR", "DEX"],
}

def prime_req_xp_bonus(cls: str, stats: dict[str, int]) -> int:
    """Percent XP modifier from prime requisite(s). Simplified: uses the
    average of prime reqs; -20/-10/0/+5/+10 bands per B/X."""
    avg = sum(stats[a] for a in PRIME_REQUISITES[cls]) / len(PRIME_REQUISITES[cls])
    if avg <= 5: return -20
    if avg <= 8: return -10
    if avg <= 12: return 0
    if avg <= 15: return 5
    return 10

# ---- class requirements (minimum scores) ----
CLASS_REQUIREMENTS = {"Dwarf": {"CON": 9}, "Elf": {"INT": 9}, "Halfling": {"DEX": 9, "CON": 9}}

# ---- hit dice ----
HIT_DICE = {
    "Fighter": "1d8", "Cleric": "1d6", "Magic-User": "1d4", "Thief": "1d4",
    "Dwarf": "1d8", "Elf": "1d6", "Halfling": "1d6",
}

# ---- XP thresholds: XP required to BE each level (index 0 = level 1) ----
XP_THRESHOLDS = {
    "Fighter":    [0, 2000, 4000, 8000, 16000, 32000],
    "Cleric":     [0, 1500, 3000, 6000, 12000, 25000],
    "Magic-User": [0, 2500, 5000, 10000, 20000, 40000],
    "Thief":      [0, 1200, 2400, 4800, 9600, 20000],
    "Dwarf":      [0, 2200, 4400, 8800, 17000, 35000],
    "Elf":        [0, 4000, 8000, 16000, 32000, 64000],
    "Halfling":   [0, 2000, 4000, 8000, 16000, 32000],
}
MAX_LEVEL_ENCODED = 6

# ---- attack (THAC0 by level band; melee/missile add ability mods) ----
THAC0_BANDS = {
    "Fighter":    [(1, 3, 19), (4, 6, 17)],
    "Cleric":     [(1, 4, 19), (5, 6, 17)],
    "Magic-User": [(1, 5, 19), (6, 6, 17)],
    "Thief":      [(1, 4, 19), (5, 6, 17)],
    "Dwarf":      [(1, 3, 19), (4, 6, 17)],
    "Elf":        [(1, 3, 19), (4, 6, 17)],
    "Halfling":   [(1, 3, 19), (4, 6, 17)],
}

def thac0(cls: str, level: int) -> int:
    for lo, hi, val in THAC0_BANDS[cls]:
        if lo <= level <= hi:
            return val
    raise KeyError(f"THAC0 not encoded for {cls} level {level} — extend tables.py")

# ---- saving throws (D=death/poison, W=wands, P=paralysis, B=breath, S=spells) ----
SAVE_BANDS = {
    "Fighter":    [(1, 3, dict(D=12, W=13, P=14, B=15, S=16)), (4, 6, dict(D=10, W=11, P=12, B=13, S=14))],
    "Cleric":     [(1, 4, dict(D=11, W=12, P=14, B=16, S=15)), (5, 6, dict(D=9,  W=10, P=12, B=14, S=12))],
    "Magic-User": [(1, 5, dict(D=13, W=14, P=13, B=16, S=15)), (6, 6, dict(D=11, W=12, P=11, B=14, S=12))],
    "Thief":      [(1, 4, dict(D=13, W=14, P=13, B=16, S=15)), (5, 6, dict(D=12, W=13, P=11, B=14, S=13))],
    "Dwarf":      [(1, 3, dict(D=8,  W=9,  P=10, B=13, S=12)), (4, 6, dict(D=6,  W=7,  P=8,  B=10, S=10))],
    "Elf":        [(1, 3, dict(D=12, W=13, P=13, B=15, S=15)), (4, 6, dict(D=10, W=11, P=11, B=13, S=13))],
    "Halfling":   [(1, 3, dict(D=8,  W=9,  P=10, B=13, S=12)), (4, 6, dict(D=6,  W=7,  P=8,  B=10, S=10))],
}

def saves(cls: str, level: int) -> dict[str, int]:
    for lo, hi, table in SAVE_BANDS[cls]:
        if lo <= level <= hi:
            return dict(table)
    raise KeyError(f"Saves not encoded for {cls} level {level} — extend tables.py")

# ---- spell slots by level: {class: {char_level: [slots_lvl1, slots_lvl2, ...]}} ----
SPELL_SLOTS = {
    "Magic-User": {1: [1], 2: [2], 3: [2, 1], 4: [2, 2], 5: [2, 2, 1], 6: [2, 2, 2]},
    "Elf":        {1: [1], 2: [2], 3: [2, 1], 4: [2, 2], 5: [2, 2, 1], 6: [2, 2, 2]},
    "Cleric":     {1: [], 2: [1], 3: [2], 4: [2, 1], 5: [2, 2], 6: [2, 2, 1, 1]},
}

FIRST_LEVEL_ARCANE = [
    "Charm Person", "Detect Magic", "Floating Disc", "Hold Portal", "Light",
    "Magic Missile", "Protection from Evil", "Read Languages", "Read Magic",
    "Shield", "Sleep", "Ventriloquism",
]

# ---- thief skills (% by level), abbreviated ----
THIEF_SKILLS = {
    1: dict(climb=87, traps=10, hear=30, hide=10, locks=15, move=20, pockets=20),
    2: dict(climb=88, traps=15, hear=30, hide=15, locks=20, move=25, pockets=25),
    3: dict(climb=89, traps=20, hear=40, hide=20, locks=25, move=30, pockets=30),
    4: dict(climb=90, traps=25, hear=40, hide=25, locks=30, move=35, pockets=35),
    5: dict(climb=91, traps=30, hear=50, hide=30, locks=35, move=40, pockets=40),
    6: dict(climb=92, traps=35, hear=50, hide=36, locks=45, move=45, pockets=45),
}

# ---- class abilities (narrative-facing tags for the writer) ----
CLASS_ABILITIES = {
    "Fighter": ["Any weapon & armor"],
    "Cleric": ["Turn undead", "Divine spellcasting (from level 2)", "Blunt weapons only"],
    "Magic-User": ["Arcane spellcasting", "Spellbook", "Dagger/staff only, no armor"],
    "Thief": ["Thief skills", "Back-stab (+4, x2 damage)", "Leather armor max"],
    "Dwarf": ["Infravision 60'", "Detect construction tricks", "Any armor, small/normal weapons"],
    "Elf": ["Arcane spellcasting", "Infravision 60'", "Detect secret doors", "Immune to ghoul paralysis"],
    "Halfling": ["+1 missile attacks", "-2 AC vs large foes", "Hide (90% woods / 2-in-6 indoors)"],
}

# ---- starting equipment kits (weapon: (name, damage)) ----
STARTING_KITS = {
    "Fighter": dict(weapon=("Sword", "1d8"), armor=("Chain mail + shield", 4), gear=["Backpack", "Torches (6)", "Rations (7 days)", "Waterskin"]),
    "Cleric": dict(weapon=("Mace", "1d6"), armor=("Chain mail + shield", 4), gear=["Holy symbol", "Backpack", "Torches (6)", "Rations (7 days)"]),
    "Magic-User": dict(weapon=("Dagger", "1d4"), armor=("Robes", 9), gear=["Spellbook", "Backpack", "Lantern", "Oil (2 flasks)", "Rations (7 days)"]),
    "Thief": dict(weapon=("Sword", "1d8"), armor=("Leather", 7), gear=["Thieves' tools", "Backpack", "Rope (50')", "Torches (6)", "Rations (7 days)"]),
    "Dwarf": dict(weapon=("Battle axe", "1d8"), armor=("Chain mail + shield", 4), gear=["Backpack", "Torches (6)", "Rations (7 days)", "Iron spikes (12)"]),
    "Elf": dict(weapon=("Sword", "1d8"), armor=("Chain mail", 5), gear=["Spellbook", "Bow + arrows (20)", "Backpack", "Rations (7 days)"]),
    "Halfling": dict(weapon=("Short sword", "1d6"), armor=("Leather + shield", 6), gear=["Sling + stones (20)", "Backpack", "Rations (7 days)"]),
}

# ---- morale & reactions (2d6) ----
def reaction_result(total: int) -> str:
    if total <= 2: return "hostile_attacks"
    if total <= 5: return "hostile_maybe"
    if total <= 8: return "uncertain"
    if total <= 11: return "indifferent"
    return "friendly"
