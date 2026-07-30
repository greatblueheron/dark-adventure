"""Dice engine. Deterministic under a seed; every roll is logged.

The roll log is what gets handed to the writer model as ground truth,
so rolls carry human-readable labels.
"""
from __future__ import annotations

import os
import random
import re
from dataclasses import dataclass, field

_DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


@dataclass
class Roll:
    notation: str          # "2d6+1"
    label: str             # "Brenna attack vs ogre"
    rolls: list[int]
    modifier: int
    total: int

    def __str__(self) -> str:
        mod = f"{self.modifier:+d}" if self.modifier else ""
        return f"{self.label}: {self.notation} -> {self.rolls}{mod} = {self.total}"


@dataclass
class Dice:
    """Seedable dice roller with an append-only log per scene."""
    seed: int | None = None
    log: list[Roll] = field(default_factory=list)

    def __post_init__(self) -> None:
        env_seed = os.getenv("DICE_SEED")
        if self.seed is None and env_seed:
            self.seed = int(env_seed)
        self._rng = random.Random(self.seed)

    def roll(self, notation: str, label: str = "") -> Roll:
        m = _DICE_RE.match(notation)
        if not m:
            raise ValueError(f"Bad dice notation: {notation!r}")
        count = int(m.group(1) or 1)
        sides = int(m.group(2))
        modifier = int(m.group(3).replace(" ", "")) if m.group(3) else 0
        rolls = [self._rng.randint(1, sides) for _ in range(count)]
        result = Roll(notation, label, rolls, modifier, sum(rolls) + modifier)
        self.log.append(result)
        return result

    # Convenience wrappers used throughout the rules engine
    def d20(self, label: str = "", modifier: int = 0) -> Roll:
        note = f"1d20{modifier:+d}" if modifier else "1d20"
        return self.roll(note, label)

    def d6(self, count: int = 1, label: str = "") -> Roll:
        return self.roll(f"{count}d6", label)

    def stat_3d6(self, label: str) -> Roll:
        return self.roll("3d6", label)

    def drain_log(self) -> list[Roll]:
        """Return and clear the log (call at end of each scene)."""
        out, self.log = self.log, []
        return out
