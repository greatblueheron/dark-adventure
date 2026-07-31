from season2.bootstrap import (
    build_protagonist_prompt, build_style_prompt, build_character_prompt,
    build_prologue_prompt, _split_public)

ROSTER = [
    dict(name="Aaron Fischer", is_protagonist=True, ancestry="Human",
         **{"class": "Magic-User"}, alignment="Neutral Evil", level=1,
         current_hp=6, max_hp=6, armor_class=9,
         stats=dict(STR=12, INT=18, WIS=9, DEX=15, CON=18, CHA=9),
         spells_known=["Read Magic", "Sleep"], spell_slots={}, abilities=[],
         status="alive"),
    dict(name="Voldek", is_protagonist=False, ancestry="Human",
         **{"class": "Magic-User"}, alignment="Chaotic Evil", level=1,
         current_hp=3, max_hp=3, armor_class=10,
         stats=dict(STR=13, INT=16, WIS=13, DEX=13, CON=10, CHA=14),
         spells_known=["Read Magic", "Push"], spell_slots={}, abilities=[],
         status="alive"),
]


def test_protagonist_prompt_grounds_in_sheet_and_note():
    p = build_protagonist_prompt(ROSTER, note="he is from Chicago")
    assert "Aaron Fischer" in p and '"INT": 18' in p
    assert "Neutral Evil" in p           # alignment mystery is in scope
    assert "he is from Chicago" in p     # showrunner note propagates
    assert "Keep on the Borderlands" in p


def test_character_prompt_demands_two_layer_structure():
    p = build_character_prompt(ROSTER, ROSTER[1], "PB", "SG")
    assert "# PUBLIC PERSONA" in p and "# HIDDEN TRUTH" in p
    assert "Chaotic Evil" in p           # ground truth given to the bible


def test_prologue_prompt_gets_public_personas_only():
    p = build_prologue_prompt(ROSTER, "PB", "SG",
                              {"Voldek": "a cheerful wanderer"})
    assert "a cheerful wanderer" in p
    assert "hidden truths" in p          # explicit no-reveal instruction
    assert "KEEP ON THE BORDERLANDS" in p


def test_split_public_strips_hidden_truth():
    bible = "# PUBLIC PERSONA\nNice fellow.\n\n# HIDDEN TRUTH\nSecretly evil."
    pub = _split_public(bible)
    assert "Nice fellow." in pub and "Secretly evil" not in pub


def test_style_prompt_carries_bible_and_audio_rules():
    p = build_style_prompt(ROSTER, "THE-BIBLE-TEXT")
    assert "THE-BIBLE-TEXT" in p
    assert "NEVER invents numbers" in p
