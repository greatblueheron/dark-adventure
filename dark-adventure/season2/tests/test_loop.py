import json
from season2.engine.context import narrator_roster, overlay_diff
from season2.engine.loop import validate_diff, parse_json

GROUND = dict(
    roster=[
        dict(id="1", name="Aaron Fischer", is_protagonist=True, ancestry="Human",
             **{"class": "Magic-User"}, alignment="Neutral Evil", level=1, xp=0,
             current_hp=6, max_hp=6, armor_class=9,
             stats=dict(STR=12, INT=18, WIS=9, DEX=15, CON=18, CHA=9),
             spells_known=["Sleep"], conditions=[], status="alive", inventory=[]),
        dict(id="2", name="Voldek", is_protagonist=False, ancestry="Human",
             **{"class": "Magic-User"}, alignment="Chaotic Evil", level=1, xp=0,
             current_hp=3, max_hp=3, armor_class=10,
             stats=dict(STR=13, INT=16, WIS=13, DEX=13, CON=10, CHA=14),
             spells_known=["Push"], conditions=[], status="alive",
             inventory=[dict(name="Dagger", quantity=1, status="held")]),
    ],
    visited={"KEEP-1"},
)


def test_narrator_layer_never_leaks_alignment_or_others_stats():
    view = narrator_roster(GROUND["roster"])
    dumped = json.dumps(view)
    assert "alignment" not in dumped and "Evil" not in dumped
    aaron, voldek = view[0], view[1]
    assert aaron["stats"] is not None          # his own screen
    assert voldek["stats"] is None             # others' sheets invisible
    assert "id" not in dumped.replace("is_narrator", "")


def test_overlay_applies_hp_items_xp_and_location():
    diff = dict(hp_changes=[{"character": "Voldek", "delta": -2}],
                items_gained=[{"character": "Aaron Fischer", "item": "Torch", "quantity": 2}],
                xp_awards=[{"character": "Voldek", "amount": 25}],
                location_change="KEEP-15")
    g2 = overlay_diff(GROUND, diff)
    v = next(r for r in g2["roster"] if r["name"] == "Voldek")
    a = next(r for r in g2["roster"] if r["name"] == "Aaron Fischer")
    assert v["current_hp"] == 1 and v["xp"] == 25
    assert any(i["name"] == "Torch" for i in a["inventory"])
    assert "KEEP-15" in g2["visited"] and g2["current_area"] == "KEEP-15"
    # original untouched (deep copy)
    assert GROUND["roster"][1]["current_hp"] == 3


def test_validate_diff_catches_bad_data():
    areas = {"KEEP-1", "KEEP-15", "RAVINE"}
    ok = dict(hp_changes=[{"character": "Voldek", "delta": -3}],
              deaths=[{"character": "Voldek"}], location_change="RAVINE")
    assert validate_diff(ok, GROUND, areas) == []       # 3-3=0 -> death legal
    bad = dict(hp_changes=[{"character": "Nobody", "delta": -1}],
               deaths=[{"character": "Aaron Fischer"}],          # hp stays 6
               items_gained=[{"character": "Voldek", "item": "x", "quantity": 0}],
               location_change="NARNIA")
    errs = validate_diff(bad, GROUND, areas)
    assert len(errs) == 4


def test_parse_json_strips_fences():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_overlay_tracks_expended_spells_and_narrator_sees_it():
    diff = dict(spells_cast=[{"character": "Aaron Fischer", "spell": "Sleep",
                              "slot_level": 1}])
    g2 = overlay_diff(GROUND, diff)
    a = next(r for r in g2["roster"] if r["name"] == "Aaron Fischer")
    assert a["spells_used"] == ["Sleep"]
    view = narrator_roster(g2["roster"])
    aaron = next(v for v in view if v["is_narrator"])
    assert any("EXPENDED" in sp for sp in aaron["spells"])
    # unexpended spells stay unmarked
    voldek = next(v for v in view if not v["is_narrator"])
    assert all("EXPENDED" not in sp for sp in voldek["spells"])


def test_validate_diff_rejects_null_and_junk_quantities():
    areas = {"KEEP-1"}
    bad = dict(items_lost=[{"character": "Voldek", "item": "torch", "quantity": None}],
               items_gained=[{"character": "Voldek", "item": "rope", "quantity": "two"}])
    errs = validate_diff(bad, GROUND, areas)
    assert len(errs) == 2 and all("bad quantity" in e for e in errs)


def test_drop_to_zero_forces_down_condition():
    # exercised via the same normalisation the loop applies inline; emulate it
    ground = dict(roster=[dict(name="Voldek", current_hp=3)])
    d = dict(hp_changes=[{"character": "Voldek", "delta": -3}],
             deaths=[], conditions_gained=[])
    dead = {x.get("character") for x in d["deaths"]}
    downed = set()
    hp_now = {r["name"]: r["current_hp"] for r in ground["roster"]}
    for ch in d["hp_changes"]:
        nm = ch["character"]
        if hp_now[nm] + ch["delta"] <= 0 and nm not in dead and nm not in downed:
            d["conditions_gained"].append(dict(character=nm, condition="down"))
    assert d["conditions_gained"] == [{"character": "Voldek", "condition": "down"}]


def test_non_roster_entries_would_be_dropped_not_fatal():
    # emulate the extractor's sanitisation pass
    names = {r["name"] for r in GROUND["roster"]}
    d = dict(hp_changes=[{"character": "Male orc 10", "delta": -4},
                         {"character": "Voldek", "delta": -1}],
             deaths=[{"character": "Male orc 10"}],
             conditions_gained=[{"character": "Male orc 1", "condition": "asleep"}])
    for key in ("hp_changes", "deaths", "conditions_gained"):
        d[key] = [e for e in d[key] if e.get("character") in names]
    from season2.engine.loop import validate_diff
    assert validate_diff(d, GROUND, {"KEEP-1"}) == []
    assert d["hp_changes"] == [{"character": "Voldek", "delta": -1}]


def test_cleric_spell_view_shows_prayer_slots_not_empty_list():
    from season2.engine.context import _spell_view
    urgosh = {"class": "Cleric", "spell_slots": {"1": 1}, "spells_used": [],
              "spells_known": []}
    view = _spell_view(urgosh)
    assert view and "1 of 1" in view[0] and "Cure Light Wounds" in view[0]
    urgosh["spells_used"] = ["Cure Light Wounds"]
    view = _spell_view(urgosh)
    assert "0 of 1" in view[0] and any("EXPENDED" in v for v in view)
    mu = {"class": "Magic-User", "spells_known": ["Sleep"], "spells_used": []}
    assert _spell_view(mu) == ["Sleep"]
