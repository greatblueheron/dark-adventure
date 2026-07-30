"""B/X reference tables (Phase 1). Transcribe from the OSE SRD.

Everything here is DATA, not logic. Keep it boring and auditable.
TODO(Phase 1): fill in real values for all classes/levels you'll reach.
"""

# XP thresholds per class per level, e.g. {"Fighter": [0, 2000, 4000, ...]}
XP_THRESHOLDS: dict[str, list[int]] = {}

# Hit dice per class, e.g. {"Fighter": "1d8", "Magic-User": "1d4"}
HIT_DICE: dict[str, str] = {}

# Attack: B/X uses THAC0-style matrices. {"Fighter": {1: 19, 4: 17, ...}}
THAC0: dict[str, dict[int, int]] = {}

# Saving throws: {class: {level_band: {"death": 12, "wands": 13, ...}}}
SAVES: dict[str, dict[int, dict[str, int]]] = {}

# Morale (2d6 roll-under), reaction table (2d6), etc.
