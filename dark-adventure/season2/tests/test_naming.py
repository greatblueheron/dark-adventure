import json
import pytest
from season2.engine.naming import name_party, apply_names
from season2.rules.chargen import generate_party
from season2.rules.dice import Dice

NAMES10 = ["Thordak", "Brannis", "Elowen", "Kazrik", "Maelis",
           "Ondra", "Piprin", "Quorra", "Sturm", "Vex"]


def fake_call(prompt):
    roster = json.loads(prompt.split("Party:\n", 1)[1])
    assert len(roster) == 10 and roster[0]["is_protagonist"]
    return json.dumps(NAMES10)


def fake_call_fenced(prompt):
    return "```json\n" + json.dumps(NAMES10) + "\n```"


def test_name_party_and_apply():
    party = generate_party(Dice(seed=7), [f"PC{i}" for i in range(10)])
    names = name_party(party, call_fn=fake_call)
    assert names[1:] == NAMES10[1:]        # slot 0 is code-side random
    apply_names(party, names)
    assert party[3]["character"]["name"] == "Kazrik"


def test_markdown_fences_stripped():
    party = generate_party(Dice(seed=7), [f"PC{i}" for i in range(10)])
    assert name_party(party, call_fn=fake_call_fenced)[1:] == NAMES10[1:]


def test_protagonist_override():
    party = generate_party(Dice(seed=7), [f"PC{i}" for i in range(10)])
    names = name_party(party, call_fn=fake_call, protagonist_name="Dana Kowalski")
    assert names[0] == "Dana Kowalski" and names[1:] == NAMES10[1:]


def test_protagonist_random_name_from_code_lists():
    from season2.engine import naming
    party = generate_party(Dice(seed=7), [f"PC{i}" for i in range(10)])
    names = name_party(party, call_fn=fake_call)   # no override supplied
    first, last = names[0].split(" ", 1)
    assert first in naming.MALE_FIRST_NAMES and last in naming.LAST_NAMES
    # and it is drawn randomly, not fixed: many draws should vary
    draws = {naming.random_protagonist_name() for _ in range(50)}
    assert len(draws) > 10


def test_bad_response_raises():
    party = generate_party(Dice(seed=7), [f"PC{i}" for i in range(10)])
    with pytest.raises(Exception):
        name_party(party, call_fn=lambda p: "Sure! Here are some names: Bob, Alice")
