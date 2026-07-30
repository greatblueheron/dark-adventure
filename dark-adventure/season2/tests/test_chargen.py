from season2.rules.chargen import generate_party, make_character, DEFAULT_COMPOSITION
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
        assert c["level"] == 1 and c["xp"] == 0
        assert c["max_hp"] >= 3  # MIN_START_HP house rule
        assert set(c["stats"]) == {"STR", "INT", "WIS", "DEX", "CON", "CHA"}
        assert all(3 <= v <= 18 for v in c["stats"].values())
        assert set(c["saves"]) == {"D", "W", "P", "B", "S"}
        assert any(i["name"] == "Gold pieces" for i in e["starting_items"])


def test_demihuman_requirements_respected():
    for seed in range(30):
        e = make_character(Dice(seed=seed), "X", preferred_class="Dwarf")
        c = e["character"]
        if c["class"] == "Dwarf":
            assert c["stats"]["CON"] >= 9


def test_casters_get_slots_and_spells():
    for seed in range(50):
        e = make_character(Dice(seed=seed), "M", preferred_class="Magic-User")
        c = e["character"]
        if c["class"] == "Magic-User":
            assert c["spell_slots"]["1"]["max"] == 1
            assert "Read Magic" in c["spells_known"] and len(c["spells_known"]) == 2
            break


def test_deterministic():
    a = generate_party(Dice(seed=5), NAMES)
    b = generate_party(Dice(seed=5), NAMES)
    assert a == b
