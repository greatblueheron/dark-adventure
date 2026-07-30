from season2.rules.dice import Dice
from season2.rules.xp import award, level_for_xp, process_levelup
from season2.rules.chargen import make_character


def test_award_splits_among_living_with_prime_req():
    chars = [
        dict(name="A", status="alive", xp=0, stats=dict(STR=16, INT=9, WIS=9, DEX=9, CON=9, CHA=9), **{"class": "Fighter"}),
        dict(name="B", status="dead",  xp=0, stats=dict(STR=9, INT=9, WIS=9, DEX=9, CON=9, CHA=9), **{"class": "Thief"}),
        dict(name="C", status="alive", xp=0, stats=dict(STR=9, INT=9, WIS=9, DEX=9, CON=9, CHA=9), **{"class": "Cleric"}),
    ]
    out = award(chars, monster_xp=100, treasure_gp=900)  # 1000 / 2 living = 500
    assert len(out) == 2
    a = next(o for o in out if o["character_name"] == "A")
    c = next(o for o in out if o["character_name"] == "C")
    assert a["xp_gained"] == 550  # +10% prime req
    assert c["xp_gained"] == 500


def test_level_thresholds():
    assert level_for_xp("Thief", 0) == 1
    assert level_for_xp("Thief", 1200) == 2
    assert level_for_xp("Fighter", 1999) == 1
    assert level_for_xp("Fighter", 2000) == 2


def test_levelup_rolls_hp_and_updates():
    e = make_character(Dice(seed=42), "T", preferred_class="Thief")
    c = e["character"]
    assert c["class"] == "Thief"
    c["xp"] = 2500  # thief level 3
    updated, events = process_levelup(Dice(seed=42), c)
    assert updated["level"] == 3
    assert updated["max_hp"] > c["max_hp"]
    assert len(events) == 2  # 1->2 and 2->3
    assert all(ev["type"] == "level_up" for ev in events)
    assert "Thief skills:" in [a.split(" {")[0] + ":" for a in updated["abilities"] if a.startswith("Thief")][0]
