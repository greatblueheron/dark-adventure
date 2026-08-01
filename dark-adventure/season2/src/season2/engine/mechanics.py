"""Resolve a PLAN scene's encounters and checks with the rules engine.
Output: a labelled mechanics log (list of dicts) — the writer's ground
truth for every number — plus structured results the DIFF step can trust.
"""
from __future__ import annotations

import re

from ..rules.dice import Dice
from ..rules import tables as T
from ..rules.combat import Combatant, resolve_encounter
from ..rules.chargen import _max_die

CLASS_WEAPON = {c: k["weapon"] for c, k in T.STARTING_KITS.items()}


def party_combatant(r: dict) -> Combatant:
    weapon = CLASS_WEAPON[r["class"]]
    return Combatant(
        name=r["name"], side="party", ac=r["armor_class"], hp=r["current_hp"],
        thac0=T.thac0(r["class"], r["level"]), damage=weapon[1].replace("1d", "1d"),
        attack_mod=T.str_hit_adj(r["stats"]), damage_mod=T.str_dmg_adj(r["stats"]),
        character_id=r["id"],
    )


def parse_damage(raw) -> tuple[str, str]:
    """Split a stat-block damage field into (dice, rider). Handles
    '1d6', '1d3 + blood drain', '2-8', 'D 1-4 plus poison', etc.
    Riders (poison, drain...) are narrative: logged, not rolled."""
    text = str(raw or "1d6").strip().lower()
    m = re.search(r"(\d*)d(\d+)\s*([+-]\s*\d+)?", text)
    if m:
        n = m.group(1) or "1"
        mod = (m.group(3) or "").replace(" ", "")
        dice = f"{n}d{m.group(2)}{mod}"
        rider = (text[:m.start()] + text[m.end():]).strip(" +,;")
        return dice, rider
    r = re.search(r"(\d+)\s*-\s*(\d+)", text)          # module range style
    if r:
        lo, hi = int(r.group(1)), int(r.group(2))
        span = max(2, hi - lo + 1)
        dice = f"1d{span}" + (f"+{lo-1}" if lo > 1 else "")
        rider = (text[:r.start()] + text[r.end():]).strip(" +,;")
        return dice, rider
    return "1d6", text if text != "1d6" else ""


def monster_combatant(m: dict, i: int) -> Combatant:
    hd = str(m.get("hd", "1"))
    lvl = max(1, int(re.sub(r"[^0-9]", "", hd.split("+")[0]) or 1))
    dice, _rider = parse_damage(m.get("damage", "1d6"))
    return Combatant(
        name=m.get("name", f"Monster {i+1}"), side="monsters",
        ac=int(m.get("ac", 7)), hp=int(m.get("hp", 4)),
        thac0=max(10, 20 - (lvl - 1)),          # monster matrix approximation
        damage=dice,
        morale=int(m.get("morale", 8)),
    )


SPELL_HEAL = {"cure light wounds": "1d8"}


def _slots_for(r: dict) -> int:
    """Castable level-1 slots. spell_slots jsonb if present, else 1."""
    slots = r.get("spell_slots") or {}
    try:
        return int(slots.get("1", slots.get(1, 1)))
    except Exception:
        return 1


def _cast(dice: Dice, caster: dict, spell: str, target_name: str | None,
          monsters: list[Combatant], roster: list[dict], log: list) -> None:
    """Generic spell ledger: EVERY declared cast is logged; known spells get
    mechanical resolution, the rest are logged as narrated-effect casts."""
    name = spell.strip()
    low = name.lower()
    used = caster.setdefault("spells_used", [])
    if len(used) >= _slots_for(caster):
        log.append(dict(kind="spell_blocked", caster=caster["name"], spell=name,
                        reason="SLOT UNAVAILABLE - already expended; the prose "
                               "must NOT depict this cast succeeding"))
        return
    used.append(name)
    entry = dict(kind="spell", caster=caster["name"], spell=name)
    if low == "sleep":
        affected_hd = dice.roll("2d8", f"Sleep ({caster['name']}) HD affected").total
        put_down = 0
        for m in monsters:
            if m.active and affected_hd > 0:
                m.status = "down"; put_down += 1; affected_hd -= 1
        entry["result"] = f"{put_down} creatures fall asleep (no save)"
    elif low == "magic missile":
        t = next((m for m in monsters if m.active), None)
        if t:
            dmg = dice.roll("1d4", f"Magic Missile ({caster['name']})").total + 1
            t.hp -= dmg
            if t.hp <= 0: t.status = "dead"
            entry.update(target=t.name, damage=dmg,
                         result="slain" if t.hp <= 0 else f"{t.hp} hp left")
        else:
            entry["result"] = "no target in reach"
    elif low in SPELL_HEAL:
        t = next((r for r in roster if r["name"] == target_name), None) or caster
        healed = dice.roll(SPELL_HEAL[low], f"{name} ({caster['name']})").total
        before = t["current_hp"]
        after = min(t["max_hp"], before + healed)
        entry.update(target=t["name"], healed=after - before,
                     result=f"{t['name']} {before} -> {after} hp")
    elif low == "friends":
        boost = dice.roll("2d4", f"Friends ({caster['name']}) CHA boost").total
        entry.update(cha_boost=boost,
                     result=f"caster CHA effectively +{boost} to onlookers who "
                            f"fail a save vs spells; effect is emotional, not command")
    else:
        entry["result"] = "cast logged; effect narrated (no mechanical resolver)"
    log.append(entry)


def resolve_scene(dice: Dice, plan_beat: dict, roster: list[dict]) -> dict:
    """Run all encounters and checks for one planned scene."""
    log: list[dict] = []
    casualties: list[dict] = []
    monster_xp_total = 0

    alive = [r for r in roster if r["status"] == "alive"]

    beat_spells = list(plan_beat.get("spells", []))
    encounters = plan_beat.get("encounters", [])
    if beat_spells and encounters:
        # scene-level casts belong to the scene's combat: merge into the
        # first encounter so offensive spells reach real monsters (a
        # beat-level Sleep once rolled into an empty room - ep6 scene 3)
        encounters[0].setdefault("spells", [])
        encounters[0]["spells"] = beat_spells + encounters[0]["spells"]
    else:
        for sp in beat_spells:
            caster = next((r for r in alive if r["name"] == sp.get("caster")), None)
            if caster:
                _cast(dice, caster, sp.get("spell", ""), sp.get("target"),
                      [], alive, log)

    for enc in plan_beat.get("encounters", []):
        party = [party_combatant(r) for r in alive]
        expanded = []
        for m in enc.get("monsters", []):
            for k in range(int(m.get("count", 1))):
                mm = dict(m)
                if m.get("count", 1) and int(m.get("count", 1)) > 1:
                    mm["name"] = f"{m.get('name', 'Monster')} {k+1}"
                expanded.append(mm)
        monsters = [monster_combatant(m, i) for i, m in enumerate(expanded)]
        specials = {mm.get("name", "?"): parse_damage(mm.get("damage"))[1]
                    for mm in enc.get("monsters", [])}
        specials = {k: v for k, v in specials.items() if v}
        log.append(dict(kind="encounter_start", name=enc.get("name", "encounter"),
                        monsters=[dict(name=m.name, ac=m.ac, hp=m.hp) for m in monsters],
                        special_abilities=specials or None))
        # casts are DECLARED (scene spells[] or encounter spells[]),
        # never inferred from tactics prose - inference mis-attributed
        # reserve-holding as casting (ep6 scene 2)
        for sp in enc.get("spells", []):
            caster = next((r for r in alive if r["name"] == sp.get("caster")), None)
            if caster:
                _cast(dice, caster, sp.get("spell", ""), sp.get("target"),
                      monsters, alive, log)
        intent = (enc.get("intent") or "fight").lower()
        rounds = {"skirmish": 3, "drive_off": 4}.get(intent, 20)
        log.extend(resolve_encounter(dice, party, monsters, max_rounds=rounds))
        if intent in ("skirmish", "drive_off"):
            fled = [m.name for m in monsters if m.active]
            for m in monsters:
                if m.active:
                    m.status = "fled"
            if fled:
                log.append(dict(kind="disengage", intent=intent, fled=fled,
                                note="encounter objective reached; remaining "
                                     "creatures withdraw rather than die"))
        for p in party:      # copy outcomes back
            r = next(x for x in alive if x["name"] == p.name)
            delta = p.hp - r["current_hp"]
            if delta != 0:
                casualties.append(dict(character=p.name, delta=delta))
            if p.status in ("down", "dead"):
                log.append(dict(kind="party_status", character=p.name, status=p.status))
        slain_hd = sum(1 for m in monsters if m.status in ("dead", "down"))
        monster_xp_total += slain_hd * 10      # ~10xp/HD at these levels (1e-ish)
        log.append(dict(kind="encounter_end", name=enc.get("name"),
                        monsters_remaining=sum(1 for m in monsters if m.active)))
        log.append(dict(kind="encounter_summary", area=plan_beat.get("location"),
                        results=[dict(name=m.name, status=m.status)
                                 for m in monsters]))

    for chk in plan_beat.get("checks", []):
        r = next((x for x in alive if x["name"] == chk.get("character")), None)
        if not r:
            continue
        kind, detail = chk.get("kind"), chk.get("detail", "")
        if kind == "save":
            cat = {"poison": "D", "death": "D", "wand": "R", "rod": "R", "breath": "B",
                   "petrif": "T", "polymorph": "T"}.get(
                next((k for k in ["poison", "death", "wand", "rod", "breath",
                                  "petrif", "polymorph"] if k in detail.lower()), ""), "S")
            target = T.saves(r["class"], r["level"])[cat]
            roll = dice.roll("1d20", f"{r['name']} save ({detail})").total
            log.append(dict(kind="check", check="save", character=r["name"],
                            detail=detail, roll=roll, target=target,
                            success=roll >= target))
        elif kind == "thief_skill":
            skills = T.thief_skills(r["level"], r["stats"]["DEX"], r["ancestry"])
            key = next((k for k in skills if k in detail.lower().replace(" ", "")
                        or detail.lower().split()[0][:4] in k), "move")
            roll = dice.roll("1d100", f"{r['name']} {detail}").total
            log.append(dict(kind="check", check="thief_skill", character=r["name"],
                            detail=detail, roll=roll, target=skills[key],
                            success=roll <= skills[key]))
        elif kind == "chance":
            m = re.search(r"(\d)\s*-?\s*in\s*-?\s*6", chk.get("detail", "").lower())
            x = int(m.group(1)) if m else 3
            roll = dice.roll("1d6", f"chance {chk.get('detail','')}").total
            log.append(dict(kind="check", check="chance", character=r["name"],
                            detail=chk.get("detail", ""), roll=roll, target=x,
                            success=roll <= x))
        else:
            stat = next((s for s in ["STR", "INT", "WIS", "DEX", "CON", "CHA"]
                         if s.lower() in detail.lower()), "DEX")
            roll = dice.roll("1d20", f"{r['name']} {stat} check").total
            log.append(dict(kind="check", check="ability", character=r["name"],
                            detail=detail, roll=roll, target=r["stats"][stat],
                            success=roll <= r["stats"][stat]))

    return dict(log=log, hp_deltas=casualties, monster_xp=monster_xp_total)
