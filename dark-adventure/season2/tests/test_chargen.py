from season2.rules.chargen import (
    generate_party, make_character, meets, emergent_class)
from season2.rules.dice import Dice
from season2.rules import tables as T

NAMES = [f"PC{i}" for i in range(10)]


def test_party_shape_and_validity():
    party = generate_party(Dice(seed=99), NAMES, protagonist_index=0)
    assert len(party) == 10
    assert sum(e["character"]["is_protagonist"] for e in party) == 1
    for e in party:
        c = e["character"]
        assert c["class"] in T.CLASSES
        assert c["ancestry"] in T.RACES
        assert c["class"] in T.RACE_CLASSES[c["ancestry"]]   # legal combo
        assert c["level"] == 1 and c["xp"] == 0
        assert c["max_hp"] >= 3
        base = {a: c["stats"][a] for a in ["STR", "INT", "WIS", "DEX", "CON", "CHA"]}
        assert all(3 <= v <= 18 for v in base.values())
        assert set(c["saves"]) == {"R", "B", "D", "T", "S"}
        assert any(i["name"] == "Gold pieces" for i in e["starting_items"])


def test_every_character_is_emergent_and_qualified():
    for seed in range(15):
        for e in generate_party(Dice(seed=seed), NAMES):
            c = e["character"]
            assert c["class"] == emergent_class(c["stats"], c["ancestry"])
            assert meets(c["class"], c["stats"]) or c["class"] == "Fighter"


def test_race_distribution_varies():
    races = {e["character"]["ancestry"]
             for seed in range(12)
             for e in generate_party(Dice(seed=seed), NAMES)}
    assert "Human" in races and len(races) >= 4   # weighted table produces variety


def test_protagonist_always_human():
    for seed in range(15):
        p = generate_party(Dice(seed=seed), NAMES, protagonist_index=0)[0]["character"]
        assert p["ancestry"] == "Human" and p["is_protagonist"]


def test_exceptional_strength_only_for_warriors_at_18():
    found = False
    for seed in range(300):
        c = make_character(Dice(seed=seed), "X", race="Human")["character"]
        if "STR_percentile" in c["stats"]:
            assert c["class"] in T.WARRIORS and c["stats"]["STR"] == 18
            assert 1 <= c["stats"]["STR_percentile"] <= 100
            found = True
            break
    assert found


def test_casters_get_slots_and_spells():
    seen_mu = False
    for seed in range(120):
        c = make_character(Dice(seed=seed), "M", race="Human")["character"]
        if c["class"] == "Magic-User":
            assert c["spell_slots"]["1"]["max"] == 1
            assert "Read Magic" in c["spells_known"] and len(c["spells_known"]) == 4
            seen_mu = True
            break
    assert seen_mu


def test_deterministic():
    assert generate_party(Dice(seed=5), NAMES) == generate_party(Dice(seed=5), NAMES)


def test_protagonist_gets_max_hp():
    party = generate_party(Dice(seed=31), NAMES, protagonist_index=0)
    p = party[0]["character"]
    die_max = {"Fighter": 10, "Paladin": 10, "Ranger": 16, "Cleric": 8, "Druid": 8,
               "Thief": 6, "Magic-User": 4, "Illusionist": 4}[p["class"]]
    assert p["max_hp"] == max(3, die_max + T.con_hp_adj(p["stats"]["CON"], p["class"]))
    assert party == generate_party(Dice(seed=31), NAMES, protagonist_index=0)


def test_alignment_rolled_and_class_legal():
    seen = set()
    for seed in range(25):
        for e in generate_party(Dice(seed=seed), NAMES):
            c = e["character"]
            assert c["alignment"] in T.ALIGNMENTS
            allowed = T.ALIGNMENT_CONSTRAINTS.get(c["class"], set(T.ALIGNMENTS))
            assert c["alignment"] in allowed
            seen.add(c["alignment"])
    assert len(seen) >= 6           # weighted table produces real spread
    assert any("Evil" in a for a in seen)   # the evil corners are live


def test_alignment_table_covers_d100():
    ceilings = [c for c, _ in T.ALIGNMENT_TABLE]
    assert ceilings == sorted(ceilings) and ceilings[-1] == 100
