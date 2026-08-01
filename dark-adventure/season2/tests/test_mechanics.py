from season2.engine.mechanics import parse_damage


def test_parse_damage_splits_dice_from_riders():
    assert parse_damage("1d3 + blood drain") == ("1d3", "blood drain")
    assert parse_damage("1d6") == ("1d6", "")
    assert parse_damage("2-8") == ("1d7+1", "")
    assert parse_damage("1-4 plus poison") == ("1d4", "plus poison")
    assert parse_damage("2d4+1") == ("2d4+1", "")
    assert parse_damage(None) == ("1d6", "")


from season2.rules.dice import Dice
from season2.engine.mechanics import _cast, _slots_for


def _mu(name, spells, hp=3, maxhp=6, used=None):
    return dict(name=name, spells_known=spells, current_hp=hp, max_hp=maxhp,
                spell_slots={"1": 1}, spells_used=list(used or []))


def test_cast_ledger_blocks_second_slot_and_logs_it():
    log = []
    aaron = _mu("Aaron", ["Sleep"])
    _cast(Dice(), aaron, "Sleep", None, [], [aaron], log)
    _cast(Dice(), aaron, "Sleep", None, [], [aaron], log)
    kinds = [e["kind"] for e in log]
    assert kinds.count("spell") >= 1 and "spell_blocked" in kinds
    blocked = next(e for e in log if e["kind"] == "spell_blocked")
    assert "SLOT UNAVAILABLE" in blocked["reason"]


def test_cure_light_wounds_heals_with_dice_and_caps_at_max():
    log = []
    urgosh = _mu("Urgosh", ["Cure Light Wounds"], hp=8, maxhp=8)
    aldrin = _mu("Aldrin", [], hp=1, maxhp=3)
    _cast(Dice(), urgosh, "Cure Light Wounds", "Aldrin", [], [urgosh, aldrin], log)
    e = next(x for x in log if x["kind"] == "spell")
    assert e["target"] == "Aldrin" and 1 <= e["healed"] <= 2   # capped at 3 max
    assert "->" in e["result"]


def test_unknown_spell_still_enters_ledger():
    log = []
    v = _mu("Voldek", ["Push"])
    _cast(Dice(), v, "Push", None, [], [v], log)
    e = log[0]
    assert e["kind"] == "spell" and "narrated" in e["result"]


def test_slots_for_defaults_to_one():
    assert _slots_for(dict(spell_slots=None)) == 1
    assert _slots_for(dict(spell_slots={"1": 2})) == 2


from season2.engine.mechanics import resolve_scene


def _roster2():
    return [dict(id="1", name="Aaron Fischer", **{"class": "Magic-User"},
                 armor_class=9, current_hp=6, max_hp=6, level=1, status="alive",
                 stats=dict(STR=12, INT=18, WIS=9, DEX=15, CON=18, CHA=9),
                 spells_known=["Sleep"], spell_slots={"1": 1}, spells_used=[],
                 ancestry="Human"),
            dict(id="2", name="Aldrin", **{"class": "Magic-User"},
                 armor_class=10, current_hp=3, max_hp=3, level=1, status="alive",
                 stats=dict(STR=10, INT=16, WIS=11, DEX=12, CON=9, CHA=12),
                 spells_known=["Sleep"], spell_slots={"1": 1}, spells_used=[],
                 ancestry="Human")]


def test_casts_come_only_from_declarations_never_tactics_prose():
    # tactics mention BOTH casters and the spell; without a declaration,
    # nothing may be rolled (inference mis-attributed casts in ep6)
    base = dict(name="orcs", monsters=[dict(name="Orc", ac=6, hp=5, hd="1",
                                            damage="1d6", morale=8, count=3)],
                party_tactics="Aaron casts Sleep at the cluster while Aldrin "
                              "holds his Sleep in reserve behind the shields")
    beat = dict(location="CAVES-8", encounters=[dict(base)])
    mech = resolve_scene(Dice(), beat, _roster2())
    assert not [e for e in mech["log"] if e.get("kind") == "spell"]

    declared = dict(base, spells=[dict(caster="Aaron Fischer", spell="Sleep")])
    beat2 = dict(location="CAVES-8", encounters=[declared])
    roster = _roster2()
    mech2 = resolve_scene(Dice(), beat2, roster)
    casts = [e for e in mech2["log"] if e.get("kind") == "spell"]
    assert [c["caster"] for c in casts] == ["Aaron Fischer"]
    aldrin = next(r for r in roster if r["name"] == "Aldrin")
    assert aldrin["spells_used"] == []          # the reserve stays a reserve


def test_beat_level_sleep_reaches_encounter_monsters():
    beat = dict(location="CAVES-9",
                spells=[dict(caster="Aaron Fischer", spell="Sleep")],
                encounters=[dict(name="orcs", monsters=[
                    dict(name="Orc", ac=6, hp=4, hd="1", damage="1d6",
                         morale=8, count=4)])])
    mech = resolve_scene(Dice(), beat, _roster2())
    casts = [e for e in mech["log"] if e.get("kind") == "spell"
             and e["spell"].lower() == "sleep"]
    assert len(casts) == 1
    # 2d8 HD, no save: at least two 1-HD orcs must drop
    assert "0 creatures" not in casts[0]["result"]
