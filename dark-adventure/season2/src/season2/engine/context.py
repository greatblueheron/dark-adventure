"""Phase 4 context builders — the two-layer knowledge model.

GROUND LAYER (planner / mechanics / auditor / validator):
  full roster incl. alignments, full character bibles incl. HIDDEN TRUTH,
  module chunks for current + adjacent areas (the DM's screen).

NARRATOR LAYER (the SCENE writer, i.e. Aaron's voice):
  roster as Aaron perceives it (no alignments anywhere — his own "reading"
  is governed by his bible, not his sheet), PUBLIC personas only, module
  content only for the current location and previously visited areas.
  Unvisited content reaches the writer only through the plan's beats and
  the mechanics log — i.e., only as it happens.

During episode generation, scene diffs are applied to an in-memory
overlay so scene N+1 sees scene N's consequences; nothing touches the
database until the episode is APPROVED.
"""
from __future__ import annotations

import copy
import json

from ..bootstrap import latest_doc, _split_public


# ---------------------------------------------------------------- ground state

def fetch_ground(c, campaign_id: str) -> dict:
    roster = (c.table("characters")
              .select("id, name, is_protagonist, ancestry, class, alignment, level, xp, "
                      "current_hp, max_hp, armor_class, stats, saves, abilities, "
                      "spells_known, spell_slots, spells_used, conditions, status")
              .eq("campaign_id", campaign_id).execute().data)
    inv = (c.table("inventory_items").select("id, character_id, name, quantity, status")
           .eq("status", "held").execute().data)
    for r in roster:
        r["inventory"] = [i for i in inv if i["character_id"] == r["id"]]
    visited = set()
    for e in (c.table("events").select("data").eq("campaign_id", campaign_id)
              .eq("type", "location_discovered").execute().data):
        if e["data"].get("area_id"):
            visited.add(e["data"]["area_id"])
    states = {r["area_id"]: r["state"] for r in
              (c.table("area_state").select("area_id, state")
               .eq("campaign_id", campaign_id).execute().data)}
    npcs = (c.table("npcs").select("name, role, disposition, status, notes")
            .eq("campaign_id", campaign_id).execute().data)
    return dict(roster=roster, visited=visited, area_state=states, npcs=npcs)


def overlay_diff(ground: dict, diff: dict) -> dict:
    """Apply a validated scene diff to an in-memory copy of ground state."""
    g = copy.deepcopy(ground)
    by = {r["name"]: r for r in g["roster"]}
    for ch in diff.get("hp_changes", []):
        r = by[ch["character"]]
        r["current_hp"] = max(0, min(r["max_hp"], r["current_hp"] + ch["delta"]))
    for d in diff.get("deaths", []):
        by[d["character"]]["status"] = "dead"
    for cnd in diff.get("conditions_gained", []):
        by[cnd["character"]].setdefault("conditions", []).append(cnd["condition"])
    for cnd in diff.get("conditions_removed", []):
        r = by[cnd["character"]]
        r["conditions"] = [x for x in r.get("conditions", []) if x != cnd["condition"]]
    for it in diff.get("items_gained", []):
        by[it["character"]]["inventory"].append(
            dict(name=it["item"], quantity=it.get("quantity", 1), status="held"))
    for it in diff.get("items_lost", []):
        inv = by[it["character"]]["inventory"]
        for entry in inv:
            if entry["name"].lower() == it["item"].lower():
                entry["quantity"] -= it.get("quantity", 1)
        by[it["character"]]["inventory"] = [e for e in inv if e["quantity"] > 0]
    for xp in diff.get("xp_awards", []):
        by[xp["character"]]["xp"] += xp["amount"]
    for sp in diff.get("spells_cast", []):
        if sp.get("character") in by:
            by[sp["character"]].setdefault("spells_used", []).append(sp["spell"])
    if diff.get("party_rested"):
        for r in g["roster"]:
            r["spells_used"] = []
    if diff.get("location_change"):
        g["visited"].add(diff["location_change"])
        g["current_area"] = diff["location_change"]
    return g


# ---------------------------------------------------------------- narrator layer

def _spell_view(r: dict) -> list[str]:
    """Casting state as perceivable. MUs list known spells; clerics/druids
    pray from the whole class list against slots, so represent the SLOT."""
    used = r.get("spells_used") or []
    if r["class"] in ("Cleric", "Druid"):
        slots = r.get("spell_slots") or {}
        try:
            total = int(slots.get("1", slots.get(1, 1)))
        except Exception:
            total = 1
        left = max(0, total - len(used))
        base = (f"{left} of {total} first-level prayer(s) available "
                f"(any cleric spell, e.g. Cure Light Wounds)")
        return [base] + [f"{sp} (EXPENDED)" for sp in used]
    return [(f"{sp} (EXPENDED - cannot cast again until rest)"
             if sp in used else sp) for sp in r.get("spells_known", [])]


def narrator_roster(roster: list[dict]) -> list[dict]:
    """The party as Aaron perceives it: no alignments, no hidden anything.
    HP is perceivable (litRPG: he sees the numbers); ids stripped."""
    out = []
    for r in roster:
        out.append(dict(
            name=r["name"], race=r["ancestry"], cls=r["class"], level=r["level"],
            hp=f"{r['current_hp']}/{r['max_hp']}", ac=r["armor_class"],
            status=r["status"], conditions=r.get("conditions", []),
            stats=r["stats"] if r["is_protagonist"] else None,  # own screen only
            spells=_spell_view(r),
            notable_gear=[i["name"] for i in r.get("inventory", [])][:6],
            is_narrator=r["is_protagonist"],
        ))
    return out


def personas_for(c, campaign_id: str, roster: list[dict], focal: list[str]) -> dict:
    """PUBLIC persona text for focal characters; one-liner for the rest."""
    out = {}
    for r in roster:
        if r["is_protagonist"]:
            continue
        doc = latest_doc(c, campaign_id, "character_bible", r["name"])
        if not doc:
            continue
        public = _split_public(doc["content"])
        out[r["name"]] = public if r["name"] in focal else public.split(".")[0][:220] + "."
    return out


def hidden_bibles(c, campaign_id: str, roster: list[dict]) -> dict:
    """GROUND layer: full bibles including HIDDEN TRUTH (planner/auditor only)."""
    out = {}
    for r in roster:
        if r["is_protagonist"]:
            continue
        doc = latest_doc(c, campaign_id, "character_bible", r["name"])
        if doc:
            out[r["name"]] = doc["content"]
    return out


# ---------------------------------------------------------------- summaries

def recap(c, campaign_id: str, last_n_episodes: int = 3) -> dict:
    camp_sum = (c.table("summaries").select("content").eq("campaign_id", campaign_id)
                .eq("scope", "campaign").order("created_at", desc=True)
                .limit(1).execute().data)
    ep_sums = (c.table("summaries").select("content, created_at")
               .eq("campaign_id", campaign_id).eq("scope", "episode")
               .order("created_at", desc=True).limit(last_n_episodes).execute().data)
    return dict(campaign=(camp_sum[0]["content"] if camp_sum else ""),
                episodes=[e["content"] for e in reversed(ep_sums)])


# ---------------------------------------------------------------- module layer

def area_chunks(c, area_ids: list[str]) -> list[dict]:
    out = []
    for aid in area_ids:
        rows = (c.table("documents").select("title, content, metadata")
                .eq("kind", "module_chunk").eq("metadata->>area_id", aid)
                .execute().data)
        out.extend(rows)
    return out


def dm_module_context(c, area_id: str) -> dict:
    """GROUND: current area + everything it connects to, full text."""
    current = area_chunks(c, [area_id])
    neighbours = []
    for ch in current:
        neighbours.extend((ch.get("metadata") or {}).get("connections", []))
    return dict(current=current, adjacent=area_chunks(c, list(dict.fromkeys(neighbours))))


def narrator_module_context(c, area_id: str, visited: set[str]) -> dict:
    """NARRATOR: full text ONLY for current + visited neighbours; unvisited
    neighbours appear as bare exit labels."""
    current = area_chunks(c, [area_id])
    exits, seen = [], []
    for ch in current:
        for n in (ch.get("metadata") or {}).get("connections", []):
            (seen if n in visited else exits).append(n)
    return dict(current=current,
                visited_adjacent=area_chunks(c, list(dict.fromkeys(seen))),
                unvisited_exits=list(dict.fromkeys(exits)))


# ---------------------------------------------------------------- assembly

def _j(x) -> str:
    return json.dumps(x, indent=1, ensure_ascii=False, default=str)


def module_area_index(c) -> list[str]:
    """One line per chunk: the DM's map of everything the module contains."""
    rows = (c.table("documents").select("metadata")
            .eq("kind", "module_chunk").execute().data)
    entries = []
    for r in rows:
        m = r.get("metadata") or {}
        if m.get("area_id"):
            entries.append(f"{m['area_id']} [{m.get('section')}]: {m.get('area_name')}")
    return sorted(set(entries))


def build_plan_context(c, camp: dict, ground: dict, episode_number: int) -> str:
    area = camp.get("current_area") or "START"
    mod = dm_module_context(c, area)
    return "\n".join([
        f"EPISODE TO PLAN: {episode_number}",
        f"PARTY LOCATION: {area}",
        "RECAP:\n" + _j(recap(c, camp["id"])),
        "PARTY (GROUND TRUTH, incl. alignments — the narrator must never see these):\n"
        + _j([{k: r[k] for k in ('name', 'is_protagonist', 'ancestry', 'class',
                                 'alignment', 'level', 'current_hp', 'max_hp',
                                 'armor_class', 'stats', 'spells_known', 'spell_slots', 'spells_used',
                                 'conditions', 'status')} for r in ground["roster"]]),
        "HIDDEN CHARACTER TRUTHS:\n" + _j(hidden_bibles(c, camp["id"], ground["roster"])),
        "MODULE - CURRENT AREA (verbatim):\n" + _j(mod["current"]),
        "MODULE - ADJACENT AREAS (verbatim):\n" + _j(mod["adjacent"]),
        f"AREAS ALREADY VISITED: {sorted(ground['visited'])}",
        "PERSISTENT AREA STATE (slain/fled monsters, alert status — the world "
        "remembers; plan against it):\n" + _j(ground.get("area_state", {})),
        "KNOWN NPCS:\n" + _j(ground.get("npcs", [])),
        "MODULE AREA INDEX (the full map — scenes may be set in and move the "
        "party to ANY of these ids, not just adjacent ones; travel between "
        "distant areas should be earned in the fiction):\n"
        + "\n".join(module_area_index(c)),
    ])


def build_scene_context(c, camp: dict, ground: dict, protagonist_bible: str,
                        style_guide: str, plan_beat: dict, mechanics_log: list,
                        prior_tail: str) -> str:
    area = plan_beat.get("location") or camp.get("current_area") or "START"
    mod = narrator_module_context(c, area, ground["visited"])
    personas = personas_for(c, camp["id"], ground["roster"],
                            focal=plan_beat.get("focal_characters", []))
    return "\n".join([
        "PROTAGONIST BIBLE:\n" + protagonist_bible,
        "STYLE GUIDE:\n" + style_guide,
        "RECAP:\n" + _j(recap(c, camp["id"])),
        "THE PARTY AS THE NARRATOR KNOWS THEM:\n" + _j(narrator_roster(ground["roster"])),
        "PUBLIC PERSONAS:\n" + _j(personas),
        "CURRENT LOCATION (what can be perceived here):\n" + _j(mod["current"]),
        "PREVIOUSLY SEEN ADJACENT AREAS:\n" + _j(mod["visited_adjacent"]),
        "UNENTERED EXITS (labels only - contents unknown to the narrator): "
        + _j(mod["unvisited_exits"]),
        "SCENE PLAN (what happens - from the showrunner):\n" + _j(plan_beat),
        "NPCS THE PARTY HAS MET:\n" + _j(ground.get("npcs", [])),
        "WHAT THE PARTY HAS DONE TO PLACES IT VISITED:\n"
        + _j({a: st for a, st in ground.get("area_state", {}).items()
              if a in ground["visited"]}),
        "MECHANICS LOG (ground truth for every number; the prose must not "
        "contradict or invent dice outcomes):\n" + _j(mechanics_log),
        "END OF PREVIOUS SCENE:\n" + (prior_tail or "(episode opening)"),
    ])
