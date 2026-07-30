from season2.rules.combat import Combatant, resolve_encounter, attack
from season2.rules.dice import Dice


def fighter(name, side="party"):
    return Combatant(name=name, side=side, ac=4, hp=8, thac0=19, damage="1d8",
                     attack_mod=1, damage_mod=1, character_id=f"id-{name}")


def goblin(name):
    return Combatant(name=name, side="monsters", ac=6, hp=4, thac0=19,
                     damage="1d6", morale=7)


def test_encounter_deterministic_and_terminates():
    log1 = resolve_encounter(Dice(seed=11), [fighter("A"), fighter("B")],
                             [goblin("g1"), goblin("g2"), goblin("g3")])
    log2 = resolve_encounter(Dice(seed=11), [fighter("A"), fighter("B")],
                             [goblin("g1"), goblin("g2"), goblin("g3")])
    assert log1 == log2
    assert log1[-1]["type"] == "encounter_end"


def test_attack_math():
    d = Dice(seed=3)
    a, t = fighter("A"), goblin("g")
    entry = attack(d, a, t)
    assert entry["needed"] == 19 - 6  # thac0 - AC
    if entry["hit"]:
        assert entry["damage"] >= 1


def test_party_member_goes_down_not_dead_first():
    # deaths_door rule: a party member at 0 goes 'down'; monsters die outright
    d = Dice(seed=1)
    weak = Combatant(name="W", side="party", ac=9, hp=1, thac0=19, damage="1d4")
    ogre = Combatant(name="ogre", side="monsters", ac=5, hp=30, thac0=17,
                     damage="1d10", morale=10)
    for _ in range(30):
        e = attack(d, ogre, weak)
        if e.get("hit"):
            assert weak.status == "down"
            break
    else:
        raise AssertionError("ogre never hit in 30 swings; check rng/thac0")


def test_morale_can_break_monsters():
    # many weak monsters vs strong party: expect morale check in the log
    party = [fighter(f"P{i}") for i in range(4)]
    mobs = [goblin(f"g{i}") for i in range(6)]
    log = resolve_encounter(Dice(seed=8), party, mobs)
    assert any(e["type"] == "morale" for e in log)
