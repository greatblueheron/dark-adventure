"""B/X combat resolution. Pure: takes Combatants, returns a mechanics log.

The log (list of dicts) is the ground truth handed to the writer model and
the diff extractor. State application to the DB happens elsewhere.

House rule (README Phase 1 decision): DEATH_RULE controls what 0 HP means.
- "instant": 0 HP = dead (classic B/X).
- "deaths_door": 0 HP = dying/unconscious; a further hit while down = dead.
  Better for serialized fiction: near-deaths are drama, and true deaths
  still happen when nobody can reach the fallen in time.
Default: deaths_door. Flip to "instant" if you want the meat grinder.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dice import Dice
from . import tables as T

DEATH_RULE = "deaths_door"


@dataclass
class Combatant:
    name: str
    side: str                  # "party" | "monsters"
    ac: int                    # descending
    hp: int
    thac0: int
    damage: str                # e.g. "1d8"
    attack_mod: int = 0        # STR/DEX mods, magic weapon bonus
    damage_mod: int = 0
    morale: int = 12           # 2d6 roll-under; party never checks morale
    character_id: str | None = None   # DB id for party members
    status: str = "up"         # up | down | dead | fled

    @property
    def active(self) -> bool:
        return self.status == "up"


def attack(dice: Dice, a: Combatant, t: Combatant) -> dict:
    roll = dice.d20(f"{a.name} attacks {t.name}", modifier=a.attack_mod)
    needed = a.thac0 - t.ac
    natural = roll.rolls[0]
    hit = natural != 1 and (natural == 20 or roll.total >= needed)
    entry = dict(
        type="attack", actor=a.name, target=t.name,
        roll=roll.total, natural=natural, needed=needed, hit=hit,
    )
    if hit:
        dmg = max(1, dice.roll(a.damage, f"{a.name} damage").total + a.damage_mod)
        was_up = t.status == "up"
        t.hp -= dmg
        if t.hp <= 0:
            if DEATH_RULE == "instant" or not was_up or t.side == "monsters":
                t.status, t.hp = "dead", 0
            else:
                t.status, t.hp = "down", 0
        entry.update(damage=dmg, target_hp_after=t.hp, target_status=t.status)
    return entry


def morale_check(dice: Dice, group: list[Combatant], trigger: str) -> dict:
    score = max((c.morale for c in group if c.active), default=12)
    roll = dice.roll("2d6", f"morale ({trigger})")
    holds = roll.total <= score
    if not holds:
        for c in group:
            if c.active:
                c.status = "fled"
    return dict(type="morale", trigger=trigger, roll=roll.total, score=score,
                result="holds" if holds else "flees")


def resolve_encounter(dice: Dice, party: list[Combatant], monsters: list[Combatant],
                      max_rounds: int = 20) -> list[dict]:
    """Simple full-auto resolution: side initiative each round, everyone
    attacks the first active enemy. Monsters check morale at first death
    and at half strength. Returns the mechanics log.

    (Later, the PLAN step can inject tactics — focus fire, spells, retreat —
    by pre-processing the combatant lists or interleaving spell events.)
    """
    log: list[dict] = []
    checked = set()

    def side_active(cs): return [c for c in cs if c.active]

    for rnd in range(1, max_rounds + 1):
        p_init = dice.d6(label=f"round {rnd} party initiative").total
        m_init = dice.d6(label=f"round {rnd} monster initiative").total
        log.append(dict(type="initiative", round=rnd, party=p_init, monsters=m_init))
        order = [party, monsters] if p_init >= m_init else [monsters, party]

        for side in order:
            foes = monsters if side is party else party
            for c in side_active(side):
                targets = side_active(foes)
                if not targets:
                    break
                log.append(attack(dice, c, targets[0]))

        m_up = side_active(monsters)
        m_dead = [c for c in monsters if c.status == "dead"]
        if m_up and m_dead and "first_death" not in checked:
            checked.add("first_death")
            log.append(morale_check(dice, monsters, "first death"))
        if m_up and len(side_active(monsters)) * 2 <= len(monsters) and "half" not in checked:
            checked.add("half")
            log.append(morale_check(dice, monsters, "half strength"))

        if not side_active(monsters) or not side_active(party):
            break

    log.append(dict(
        type="encounter_end",
        party=[dict(name=c.name, hp=c.hp, status=c.status, character_id=c.character_id) for c in party],
        monsters=[dict(name=c.name, hp=c.hp, status=c.status) for c in monsters],
    ))
    return log
