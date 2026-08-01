"""Pure world-state derivation (Phase 5): monster attrition, treasure
valuation, NPC promotion. No I/O — the loop applies these at approval."""
from __future__ import annotations


def derive_area_updates(area_id: str | None, mechanics_log: list,
                        prior: dict | None) -> dict | None:
    """Fold a scene's mechanics log into an area's persistent state."""
    if not area_id:
        return None
    state = dict(prior or {})
    slain = list(state.get("monsters_slain", []))
    fled = list(state.get("monsters_fled", []))
    touched = False
    for e in mechanics_log or []:
        if e.get("kind") == "encounter_summary":
            for r in e.get("results", []):
                touched = True
                if r.get("status") in ("dead", "down"):
                    slain.append(r.get("name"))
                elif r.get("status") == "fled":
                    fled.append(r.get("name"))
        elif e.get("kind") == "disengage":
            touched = True
            fled.extend(e.get("fled", []))
        elif e.get("kind") == "encounter_start":
            touched = True
    if not touched:
        return None
    state["monsters_slain"] = sorted(set(filter(None, slain)))
    state["monsters_fled"] = sorted(set(filter(None, fled)) - set(state["monsters_slain"]))
    state["alerted"] = True
    return state


def treasure_gp(diff: dict) -> int:
    """Stated treasure value in a scene diff (gold-for-XP economy)."""
    total = 0
    for it in (diff or {}).get("items_gained", []):
        v = it.get("gp_value")
        if isinstance(v, int) and v > 0:
            total += v
    return total


def npc_records(diff: dict, episode_number: int,
                party_names: set[str] | None = None) -> list[dict]:
    """npcs_met entries worth promoting, minus party members and generics."""
    party = {p.lower() for p in (party_names or set())}
    out = []
    for n in (diff or {}).get("npcs_met", []):
        name = (n.get("name") or "").strip()
        if not name or len(name.split()) > 4 or name.lower() in party:
            continue
        out.append(dict(name=name, role=n.get("role"),
                        disposition=n.get("disposition"),
                        first_seen_episode=episode_number))
    return out
