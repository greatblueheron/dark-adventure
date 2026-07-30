"""Combat resolution (Phase 1).

TODO(Phase 1):
- initiative (side-based 1d6 in B/X)
- attack(attacker, target, dice) -> hit/miss via THAC0, damage roll
- morale_check(monster_group, dice)
- apply_damage -> emits structured facts: hp_after, death flags
- resolve_encounter(party, monsters, tactics, dice) -> mechanics log
  (list of dicts) suitable for the writer prompt + state diff
Death house rule decision goes here (0 HP = dead vs death's door).
"""
