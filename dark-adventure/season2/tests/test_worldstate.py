from season2.engine.worldstate import derive_area_updates, treasure_gp, npc_records
from season2.engine.context import overlay_diff


def test_area_updates_fold_kills_and_flights():
    log = [dict(kind="encounter_start"),
           dict(kind="encounter_summary", area="CAVES-7",
                results=[dict(name="Orc guard 1", status="dead"),
                         dict(name="Orc guard 2", status="fled"),
                         dict(name="Orc guard 3", status="fled")]),
           dict(kind="disengage", fled=["Orc guard 4"])]
    st = derive_area_updates("CAVES-7", log, None)
    assert st["monsters_slain"] == ["Orc guard 1"]
    assert set(st["monsters_fled"]) == {"Orc guard 2", "Orc guard 3", "Orc guard 4"}
    assert st["alerted"] is True
    # folding again with a prior state de-duplicates and a kill beats a flight
    log2 = [dict(kind="encounter_summary", area="CAVES-7",
                 results=[dict(name="Orc guard 2", status="dead")])]
    st2 = derive_area_updates("CAVES-7", log2, st)
    assert "Orc guard 2" in st2["monsters_slain"]
    assert "Orc guard 2" not in st2["monsters_fled"]


def test_no_encounters_means_no_state_write():
    assert derive_area_updates("KEEP-13", [dict(kind="check")], None) is None
    assert derive_area_updates(None, [], None) is None


def test_treasure_gp_sums_only_stated_values():
    diff = dict(items_gained=[
        dict(character="Thessaly", item="electrum coins", gp_value=25),
        dict(character="Kix", item="silver chain", gp_value=None),
        dict(character="Brennos", item="belt-knife")])
    assert treasure_gp(diff) == 25


def test_npc_records_filter_generics_and_carry_episode():
    diff = dict(npcs_met=[
        dict(name="Corporal", role="watch officer", disposition="neutral"),
        dict(name="A very long descriptive non-name entry here", role="x"),
        dict(name="", role="y")])
    recs = npc_records(diff, 6)
    assert len(recs) == 1 and recs[0]["first_seen_episode"] == 6


def test_overlay_rest_clears_expended_slots():
    ground = dict(roster=[dict(name="Aaron Fischer", current_hp=3, max_hp=6,
                               spells_used=["Sleep"], inventory=[], xp=0)],
                  visited=set())
    g2 = overlay_diff(ground, dict(party_rested=True))
    assert g2["roster"][0]["spells_used"] == []


def test_npc_records_exclude_party_members():
    diff = dict(npcs_met=[dict(name="Brennos", role="spokesman"),
                          dict(name="Corporal", role="watch officer")])
    recs = npc_records(diff, 2, party_names={"Brennos", "Urgosh"})
    assert [r["name"] for r in recs] == ["Corporal"]
