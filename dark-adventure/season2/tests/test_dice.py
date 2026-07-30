from season2.rules.dice import Dice


def test_notation_parsing_and_bounds():
    d = Dice(seed=42)
    r = d.roll("3d6+2", "stat roll")
    assert len(r.rolls) == 3
    assert all(1 <= x <= 6 for x in r.rolls)
    assert r.total == sum(r.rolls) + 2


def test_deterministic_under_seed():
    a = [Dice(seed=7).roll("1d20").total for _ in range(1)]
    b = [Dice(seed=7).roll("1d20").total for _ in range(1)]
    assert a == b


def test_log_and_drain():
    d = Dice(seed=1)
    d.d20("attack", modifier=2)
    d.d6(2, "damage")
    log = d.drain_log()
    assert len(log) == 2 and d.log == []
    assert "attack" in str(log[0])
