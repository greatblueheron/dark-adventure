"""Phase 4 scene loop: plan -> [mechanics -> write -> diff -> validate ->
audit(-> revise)] -> drafted episode; approval applies state + summaries.

Nothing touches campaign state until `approve`. Writer contexts are dumped
to runs/ep{N}-scene{I}-context.txt at generation time so continuity can be
verified by inspecting exactly what the writer saw.
"""
from __future__ import annotations

import json
import os
import re

from ..db import client
from ..bootstrap import latest_doc, fetch_campaign
from ..rules.dice import Dice
from ..rules import xp as XP
from . import context as CTX
from . import prompts as P
from .mechanics import resolve_scene
from . import worldstate as WS

MODELS = dict(plan="AUDITOR_MODEL", scene="WRITER_MODEL", diff="CLERK_MODEL",
              audit="AUDITOR_MODEL", revise="WRITER_MODEL", summary="CLERK_MODEL")
DEFAULTS = dict(AUDITOR_MODEL="claude-sonnet-4-6", WRITER_MODEL="claude-opus-4-8",
                CLERK_MODEL="claude-haiku-4-5-20251001")


def llm(role: str, prompt: str, max_tokens: int) -> str:
    from dotenv import load_dotenv
    load_dotenv()
    import anthropic
    model = os.getenv(MODELS[role], DEFAULTS[MODELS[role]])
    kwargs = dict(model=model, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}])
    if role in ("scene", "plan"):
        kwargs["temperature"] = 1.0        # creative roles only
    try:
        msg = anthropic.Anthropic().messages.create(**kwargs)
    except anthropic.BadRequestError as err:
        if "temperature" in str(err):      # model deprecated the param
            kwargs.pop("temperature", None)
            msg = anthropic.Anthropic().messages.create(**kwargs)
        else:
            raise
    return "".join(b.text for b in msg.content if b.type == "text")


def parse_json(raw: str):
    """Tolerant JSON extraction: strips fences, then decodes the FIRST JSON
    object/array found anywhere in the text (models sometimes preface the
    JSON with prose despite instructions)."""
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        for i, ch in enumerate(cleaned):
            if ch in "{[":
                obj, _ = json.JSONDecoder().raw_decode(cleaned[i:])
                return obj
        raise


# ---------------------------------------------------------------- validation

def valid_area_ids(c) -> set[str]:
    rows = c.table("documents").select("metadata").eq("kind", "module_chunk").execute().data
    return {r["metadata"].get("area_id") for r in rows if r.get("metadata")}


def validate_diff(diff: dict, ground: dict, areas: set[str]) -> list[str]:
    errors = []
    names = {r["name"] for r in ground["roster"]}
    by = {r["name"]: r for r in ground["roster"]}
    for key in ("hp_changes", "deaths", "conditions_gained", "conditions_removed",
                "items_gained", "items_lost", "xp_awards", "spells_cast"):
        for entry in diff.get(key, []):
            if entry.get("character") not in names:
                errors.append(f"{key}: unknown character {entry.get('character')!r}")
    for ch in diff.get("hp_changes", []):
        if not isinstance(ch.get("delta"), int):
            errors.append(f"hp delta not int: {ch}")
    for d in diff.get("deaths", []):
        r = by.get(d.get("character"))
        if r:
            delta = sum(ch["delta"] for ch in diff.get("hp_changes", [])
                        if ch.get("character") == d["character"] and isinstance(ch.get("delta"), int))
            if r["current_hp"] + delta > 0:
                errors.append(f"death of {d['character']} but hp would be "
                              f"{r['current_hp'] + delta} > 0")
    for it in diff.get("items_gained", []) + diff.get("items_lost", []):
        q = it.get("quantity", 1)
        if not isinstance(q, int) or q < 1:
            errors.append(f"bad quantity: {it}")
    for it in diff.get("items_gained", []):
        v = it.get("gp_value")
        if v is not None and (not isinstance(v, int) or v < 0):
            errors.append(f"bad gp_value: {it}")
    for xpa in diff.get("xp_awards", []):
        if not isinstance(xpa.get("amount"), int) or xpa["amount"] < 0:
            errors.append(f"bad xp award: {xpa}")
    loc = diff.get("location_change")
    if loc and loc not in areas:
        errors.append(f"unknown location_change {loc!r}")
    return errors


# ---------------------------------------------------------------- pipeline

def plan_episode(number: int) -> None:
    c = client()
    camp = fetch_campaign(c)
    ground = CTX.fetch_ground(c, camp["id"])
    plan_ctx = CTX.build_plan_context(c, camp, ground, number)
    os.makedirs("runs", exist_ok=True)
    with open(f"runs/ep{number}-plan-context.txt", "w", encoding="utf-8") as f:
        f.write(plan_ctx)
    prompt = P.PLAN.format(context=plan_ctx, episode=number)
    raw = llm("plan", prompt, 12000)
    try:
        plan = parse_json(raw)
    except Exception as err:
        print(f"  plan JSON invalid ({err}); retrying with compactness demand...")
        raw = llm("plan", prompt + "\n\nYOUR PREVIOUS ATTEMPT WAS TRUNCATED OR "
                  "MALFORMED. Return the COMPLETE JSON object only, more compactly: "
                  "3-4 scenes max, beats as short phrases, one stat line per "
                  "monster GROUP (use a 'count' field) rather than per individual.",
                  12000)
        plan = parse_json(raw)
    assert plan.get("scenes"), "plan has no scenes"
    existing = (c.table("episodes").select("id").eq("campaign_id", camp["id"])
                .eq("number", number).execute().data)
    if existing:
        c.table("episodes").update(dict(outline=plan, title=plan.get("title"),
                                        status="outlined")).eq("id", existing[0]["id"]).execute()
    else:
        c.table("episodes").insert(dict(
            campaign_id=camp["id"], module_id=camp.get("current_module_id"),
            number=number, title=plan.get("title"), status="outlined",
            outline=plan)).execute()
    print(f"Episode {number} planned: {plan.get('title')!r}, "
          f"{len(plan['scenes'])} scenes.")
    for s in plan["scenes"]:
        print(f"  {s['index']}. [{s.get('location')}] {s.get('goal')}")


def write_episode(number: int, resume: bool = False) -> None:
    c = client()
    camp = fetch_campaign(c)
    ep = (c.table("episodes").select("*").eq("campaign_id", camp["id"])
          .eq("number", number).execute().data)
    assert ep and ep[0].get("outline"), "plan the episode first"
    ep = ep[0]
    existing = {}
    if resume:
        for row in (c.table("scenes").select("*").eq("episode_id", ep["id"])
                    .order("index").execute().data):
            existing[row["index"]] = row
        if existing:
            print(f"resuming: keeping scenes {sorted(existing)}")
    else:
        c.table("scenes").delete().eq("episode_id", ep["id"]).execute()  # fresh rewrite

    ground = CTX.fetch_ground(c, camp["id"])
    ground["current_area"] = camp.get("current_area")
    bible = latest_doc(c, camp["id"], "protagonist_bible")["content"]
    style = latest_doc(c, camp["id"], "style_guide")["content"]
    areas = valid_area_ids(c)
    dice = Dice()
    os.makedirs("runs", exist_ok=True)
    prior_tail = ""
    openings: list[str] = []
    # last approved episode's scene openings feed the variety rule too
    prev = (c.table("episodes").select("id").eq("campaign_id", camp["id"])
            .eq("number", number - 1).execute().data)
    if prev:
        for row in (c.table("scenes").select("full_text").eq("episode_id", prev[0]["id"])
                    .order("index").execute().data):
            first = (row["full_text"] or "").strip().split("\n")[0]
            if first:
                openings.append(first[:160])

    for beat in ep["outline"]["scenes"]:
        i = beat["index"]
        if i in existing:
            row = existing[i]
            ground = CTX.overlay_diff(ground, row["state_diff"] or {})
            prior_tail = " ".join((row["full_text"] or "").split()[-120:])
            first = (row["full_text"] or "").strip().split("\n")[0]
            if first:
                openings.append(first[:160])
            print(f"— scene {i}: kept (resume)")
            continue
        print(f"— scene {i} [{beat.get('location')}]: mechanics...", flush=True)
        mech = resolve_scene(dice, beat, ground["roster"])

        ctx = CTX.build_scene_context(c, camp, ground, bible, style, beat,
                                      mech["log"], prior_tail)
        if openings:
            ctx += ("\nRECENT SCENE OPENINGS (vary your approach - do not echo "
                    "these constructions):\n" + "\n".join(f"- {o}" for o in openings))
        with open(f"runs/ep{number}-scene{i}-context.txt", "w", encoding="utf-8") as f:
            f.write(ctx)
        print(f"  writing ({len(ctx.split())} ctx words)...", flush=True)
        prose = llm("scene", P.SCENE.format(context=ctx), 2500)

        allowed_locs = [x for x in dict.fromkeys(
            [beat.get("location"), beat.get("moves_party_to"),
             ground.get("current_area")]) if x]

        def extract_diff(extra: str = "") -> dict:
            d = parse_json(llm("diff", P.DIFF.format(
                prose=prose + extra, log=json.dumps(mech["log"]),
                allowed_locations=allowed_locs), 1500))
            # normalise clerk nulls/omissions before validation
            for key in ("items_gained", "items_lost"):
                for it in d.get(key, []) or []:
                    if it.get("quantity") is None:
                        it["quantity"] = 1
            for lst in ("hp_changes", "deaths", "conditions_gained",
                        "conditions_removed", "items_gained", "items_lost",
                        "xp_awards", "spells_cast", "npcs_met",
                        "notable_events"):
                if d.get(lst) is None:
                    d[lst] = []
            # party-scoped arrays are for party members ONLY; the engine
            # tracks monster fates via encounter_summary -> area_state, so
            # non-roster entries are dropped, not fatal
            names = {r["name"] for r in ground["roster"]}
            dropped = []
            for key in ("hp_changes", "deaths", "conditions_gained",
                        "conditions_removed", "items_gained", "items_lost",
                        "xp_awards", "spells_cast"):
                keep = []
                for entry in d.get(key, []):
                    if entry.get("character") in names:
                        keep.append(entry)
                    else:
                        dropped.append(f"{key}:{entry.get('character')}")
                d[key] = keep
            if dropped:
                print(f"  note: dropped {len(dropped)} non-party entries from "
                      f"diff (monster state lives in area_state): "
                      f"{sorted(set(dropped))[:4]}...")
            # anyone dropped to 0 without dying is DOWN (deaths-door rule);
            # the clerk sometimes forgets the condition, so enforce it here
            dead = {x.get("character") for x in d["deaths"]}
            downed = {x.get("character") for x in d["conditions_gained"]
                      if x.get("condition") == "down"}
            hp_now = {r["name"]: r["current_hp"] for r in ground["roster"]}
            for ch in d["hp_changes"]:
                nm = ch.get("character")
                if (nm in hp_now and isinstance(ch.get("delta"), int)
                        and hp_now[nm] + ch["delta"] <= 0
                        and nm not in dead and nm not in downed):
                    d["conditions_gained"].append(
                        dict(character=nm, condition="down"))
                    downed.add(nm)
            # the PLAN, not the clerk, is authoritative for movement:
            # sanitise invented ids to null rather than failing the scene
            if d.get("location_change") and d["location_change"] not in areas:
                print(f"  note: clerk invented location "
                      f"{d['location_change']!r} - nulled (plan governs movement)")
                d["location_change"] = None
            return d

        diff = extract_diff()
        errors = validate_diff(diff, ground, areas)
        if errors:
            print("  diff invalid, retrying:", errors)
            diff = extract_diff(f"\n\nPRIOR EXTRACTION ERRORS TO FIX: {errors}")
            errors = validate_diff(diff, ground, areas)
            assert not errors, f"diff still invalid: {errors}"
        if not diff.get("location_change") and beat.get("moves_party_to"):
            diff["location_change"] = beat["moves_party_to"]
        # kill XP comes from the rules engine, not the clerk's prose reading
        if mech.get("monster_xp", 0) > 0 and not diff.get("xp_awards"):
            living = [r["name"] for r in ground["roster"] if r["status"] == "alive"]
            share = max(1, mech["monster_xp"] // max(1, len(living)))
            diff["xp_awards"] = [dict(character=n, amount=share,
                                      cause="monsters overcome (engine award)")
                                 for n in living]

        def run_audit() -> dict:
            nudge = ""
            roster_view = json.dumps(CTX.narrator_roster(ground["roster"]))
            for attempt in range(2):
                try:
                    verdict = parse_json(llm("audit", P.AUDIT.format(
                        prose=prose, log=json.dumps(mech["log"]),
                        plan=json.dumps(beat), roster=roster_view) + nudge, 2500))
                    if not (isinstance(verdict, dict) and "verdict" in verdict):
                        raise ValueError(f"audit shape invalid: {type(verdict).__name__}")
                    return verdict
                except Exception as err:
                    print(f"  audit output unparseable (attempt {attempt+1}): {err}")
                    nudge = ('\n\nYOUR PREVIOUS RESPONSE WAS NOT VALID JSON. '
                             'Respond with ONLY the JSON verdict object, '
                             'starting with the character {.')
            return {"verdict": "unparseable", "issues": []}

        audit = run_audit()
        audited = audit.get("verdict") == "pass"
        if audit.get("verdict") == "fail" and audit.get("issues"):
            print("  audit failed, revising:", audit["issues"])
            prose = llm("revise", P.REVISE.format(issues=json.dumps(audit["issues"]),
                                                  prose=prose,
                                                  log=json.dumps(mech["log"])), 2500)
            audit = run_audit()
            audited = audit.get("verdict") == "pass"
            # the revision changed the prose: the diff must describe the
            # prose that will be stored, so re-extract and re-validate
            diff = extract_diff()
            errors = validate_diff(diff, ground, areas)
            if errors:
                diff = extract_diff(f"\n\nPRIOR EXTRACTION ERRORS TO FIX: {errors}")
                errors = validate_diff(diff, ground, areas)
                assert not errors, f"post-revision diff invalid: {errors}"
            if not diff.get("location_change") and beat.get("moves_party_to"):
                diff["location_change"] = beat["moves_party_to"]
        if audit.get("verdict") == "unparseable":
            print("  WARNING: auditor verdict unavailable - scene stored "
                  "audited=False; give it extra scrutiny at review.")

        c.table("scenes").insert(dict(
            episode_id=ep["id"], index=i, location=beat.get("location"),
            full_text=prose, mechanics_log=mech["log"], state_diff=diff,
            audited=audited)).execute()
        ground = CTX.overlay_diff(ground, diff)
        prior_tail = " ".join(prose.split()[-120:])
        first_line = prose.strip().split("\n")[0]
        if first_line:
            openings.append(first_line[:160])
        print(f"  scene {i} done ({len(prose.split())} words, audited={audited})")

    c.table("episodes").update({"status": "drafted"}).eq("id", ep["id"]).execute()
    print(f"Episode {number} DRAFTED. Review with `episode show {number}`, "
          f"then approve or reject.")


EVENT_MAP = [
    ("deaths", "death", lambda e: f"{e['character']} dies: {e.get('cause', '')}"),
    ("items_gained", "item_gained", lambda e: f"{e['character']} gains {e.get('quantity',1)}x {e['item']}"),
    ("items_lost", "item_lost", lambda e: f"{e['character']} loses {e.get('quantity',1)}x {e['item']}"),
    ("xp_awards", "xp_award", lambda e: f"{e['character']} +{e['amount']} XP ({e.get('cause','')})"),
    ("npcs_met", "npc_met", lambda e: f"Met {e['name']} ({e.get('role','')}): {e.get('disposition','')}"),
    ("notable_events", "other", lambda e: e if isinstance(e, str) else json.dumps(e)),
]


def approve_episode(number: int) -> None:
    c = client()
    camp = fetch_campaign(c)
    ep = (c.table("episodes").select("*").eq("campaign_id", camp["id"])
          .eq("number", number).execute().data)[0]
    scenes = (c.table("scenes").select("*").eq("episode_id", ep["id"])
              .order("index").execute().data)
    assert scenes, "nothing drafted"
    roster = {r["name"]: r for r in (c.table("characters").select("*")
              .eq("campaign_id", camp["id"]).execute().data)}
    dice = Dice()
    scene_summaries = []
    final_area = camp.get("current_area")
    spells_used = {r["name"]: list(r.get("spells_used") or []) for r in roster.values()}
    treasure_total = 0
    rested = False

    for s in scenes:
        diff = s["state_diff"] or {}
        for ch in diff.get("hp_changes", []):
            r = roster[ch["character"]]
            r["current_hp"] = max(0, min(r["max_hp"], r["current_hp"] + ch["delta"]))
            c.table("characters").update({"current_hp": r["current_hp"]}).eq("id", r["id"]).execute()
            c.table("events").insert(dict(campaign_id=camp["id"], episode_id=ep["id"],
                scene_id=s["id"], type="injury", character_id=r["id"],
                description=f"{r['name']} {'+' if ch['delta']>0 else ''}{ch['delta']} hp "
                            f"({ch.get('cause','')}) -> {r['current_hp']}/{r['max_hp']}",
                data=ch)).execute()
        for key, etype, desc in EVENT_MAP:
            for e in diff.get(key, []):
                cid = roster.get(e.get("character") if isinstance(e, dict) else "", {}).get("id")
                c.table("events").insert(dict(campaign_id=camp["id"], episode_id=ep["id"],
                    scene_id=s["id"], type=etype, character_id=cid,
                    description=desc(e), data=e if isinstance(e, dict) else {"note": e})).execute()
        for d in diff.get("deaths", []):
            r = roster[d["character"]]
            c.table("characters").update({"status": "dead", "current_hp": 0}).eq("id", r["id"]).execute()
        for it in diff.get("items_gained", []):
            c.table("inventory_items").insert(dict(
                campaign_id=camp["id"],
                character_id=roster[it["character"]]["id"],
                name=it["item"], quantity=it.get("quantity", 1), properties={},
                status="held")).execute()
        for it in diff.get("items_lost", []):
            cid = roster[it["character"]]["id"]
            rows = (c.table("inventory_items").select("id, name, quantity")
                    .eq("character_id", cid).eq("status", "held").execute().data)
            match = next((r for r in rows
                          if r["name"].lower() == it["item"].lower()
                          or it["item"].lower() in r["name"].lower()), None)
            if not match:
                print(f"  note: items_lost {it['item']!r} for {it['character']} "
                      f"matches no held item - event logged, inventory unchanged")
                continue
            q = match["quantity"] - it.get("quantity", 1)
            if q > 0:
                c.table("inventory_items").update({"quantity": q}).eq("id", match["id"]).execute()
            else:
                c.table("inventory_items").update({"status": "lost"}).eq("id", match["id"]).execute()
        for xpa in diff.get("xp_awards", []):
            r = roster[xpa["character"]]
            r["xp"] += xpa["amount"]
            c.table("characters").update({"xp": r["xp"]}).eq("id", r["id"]).execute()
        if diff.get("location_change"):
            final_area = diff["location_change"]
            c.table("events").insert(dict(campaign_id=camp["id"], episode_id=ep["id"],
                scene_id=s["id"], type="location_discovered",
                description=f"Party enters {final_area}",
                data={"area_id": final_area})).execute()
        # --- the world remembers (Phase 5) ---
        area = s["location"] or final_area
        upd = WS.derive_area_updates(area, s.get("mechanics_log") or [],
                                     None)
        if upd is not None:
            prior = (c.table("area_state").select("id, state")
                     .eq("campaign_id", camp["id"]).eq("area_id", area)
                     .execute().data)
            if prior:
                merged = WS.derive_area_updates(area, s.get("mechanics_log") or [],
                                                prior[0]["state"])
                c.table("area_state").update({"state": merged}).eq(
                    "id", prior[0]["id"]).execute()
            else:
                c.table("area_state").insert(dict(campaign_id=camp["id"],
                    area_id=area, state=upd)).execute()
        for rec in WS.npc_records(diff, number,
                                   party_names=set(roster)):
            hit = (c.table("npcs").select("id").eq("campaign_id", camp["id"])
                   .eq("name", rec["name"]).execute().data)
            if hit:
                c.table("npcs").update({k: rec[k] for k in ("role", "disposition")
                                        if rec.get(k)}).eq("id", hit[0]["id"]).execute()
            else:
                c.table("npcs").insert(dict(campaign_id=camp["id"], **rec)).execute()
        treasure_total += WS.treasure_gp(diff)
        for sp in diff.get("spells_cast", []):
            if sp.get("character") in spells_used:
                spells_used[sp["character"]].append(sp["spell"])
        if diff.get("party_rested"):
            rested = True
            spells_used = {k: [] for k in spells_used}
        summ = llm("summary", P.SUMMARIZE_SCENE.format(
            prose=s["full_text"], diff=json.dumps(diff)), 500)
        c.table("summaries").insert(dict(campaign_id=camp["id"], scope="scene",
            scene_id=s["id"], episode_id=ep["id"], content=summ)).execute()
        scene_summaries.append(summ)

    # treasure XP: the 1e economy — gp recovered, split among the living
    if treasure_total > 0:
        living = [r for r in roster.values() if r["status"] == "alive"]
        share = max(1, treasure_total // max(1, len(living)))
        for r in living:
            r["xp"] += share
            c.table("characters").update({"xp": r["xp"]}).eq("id", r["id"]).execute()
            c.table("events").insert(dict(campaign_id=camp["id"], episode_id=ep["id"],
                type="xp_award", character_id=r["id"],
                description=f"{r['name']} +{share} XP (treasure, {treasure_total} gp total)",
                data={"gp": treasure_total})).execute()
        print(f"  treasure XP: {treasure_total} gp -> {share} XP each")
    # natural healing on a full rest (1d3/day, module rule)
    if rested:
        for r in roster.values():
            if r["status"] == "alive" and r["current_hp"] < r["max_hp"]:
                heal = dice.roll("1d3", f"{r['name']} natural healing").total
                r["current_hp"] = min(r["max_hp"], r["current_hp"] + heal)
                c.table("characters").update({"current_hp": r["current_hp"]}).eq(
                    "id", r["id"]).execute()
                c.table("events").insert(dict(campaign_id=camp["id"],
                    episode_id=ep["id"], type="other", character_id=r["id"],
                    description=f"{r['name']} heals {heal} naturally overnight "
                                f"-> {r['current_hp']}/{r['max_hp']}",
                    data={"heal": heal})).execute()
    # persist expended slots (cleared if rested)
    for nm, used in spells_used.items():
        c.table("characters").update({"spells_used": used}).eq(
            "id", roster[nm]["id"]).execute()

    # level-ups through the real rules engine
    for r in roster.values():
        if r["status"] != "alive":
            continue
        if XP.level_for_xp(r["class"], r["xp"]) > r["level"]:
            updated, events = XP.process_levelup(dice, r)
            c.table("characters").update({k: updated[k] for k in
                ("level", "max_hp", "current_hp", "saves", "spell_slots", "abilities")}
                ).eq("id", r["id"]).execute()
            for ev in events:
                c.table("events").insert(dict(campaign_id=camp["id"], episode_id=ep["id"],
                    type="level_up", character_id=r["id"],
                    description=f"{r['name']} reaches level {updated['level']}: "
                                + "; ".join(ev.get("gained", [])), data=ev)).execute()
            print(f"  LEVEL UP: {r['name']} -> {updated['level']}")

    ep_summary = llm("summary", P.SUMMARIZE_EPISODE.format(
        scene_summaries="\n\n".join(scene_summaries)), 400)
    c.table("summaries").insert(dict(campaign_id=camp["id"], scope="episode",
        episode_id=ep["id"], content=ep_summary)).execute()
    all_eps = (c.table("summaries").select("content, created_at")
               .eq("campaign_id", camp["id"]).eq("scope", "episode")
               .order("created_at").execute().data)
    camp_summary = llm("summary", P.SUMMARIZE_CAMPAIGN.format(
        episode_summaries="\n\n".join(x["content"] for x in all_eps)), 500)
    c.table("summaries").insert(dict(campaign_id=camp["id"], scope="campaign",
        content=camp_summary)).execute()
    c.table("campaigns").update({"current_area": final_area}).eq("id", camp["id"]).execute()
    c.table("episodes").update({"status": "approved"}).eq("id", ep["id"]).execute()
    print(f"Episode {number} APPROVED. State applied; party at {final_area}.")
    for r in roster.values():
        if r["status"] == "alive" and r["current_hp"] <= 0:
            print(f"  *** DEATH'S DOOR: {r['name']} is at 0 hp — unconscious "
                  f"and dying until stabilised. Next episode must address this.")


def reject_episode(number: int) -> None:
    c = client()
    camp = fetch_campaign(c)
    ep = (c.table("episodes").select("id").eq("campaign_id", camp["id"])
          .eq("number", number).execute().data)
    if ep:
        c.table("scenes").delete().eq("episode_id", ep[0]["id"]).execute()
        c.table("episodes").delete().eq("id", ep[0]["id"]).execute()
    print(f"Episode {number} rejected and deleted; state untouched. "
          f"Re-plan or re-write freely.")


def register_ep1() -> None:
    c = client()
    camp = fetch_campaign(c)
    doc = latest_doc(c, camp["id"], "episode_script", "Episode 1")
    assert doc, "no approved Episode 1 script in documents"
    existing = (c.table("episodes").select("id").eq("campaign_id", camp["id"])
                .eq("number", 1).execute().data)
    if not existing:
        c.table("episodes").insert(dict(campaign_id=camp["id"],
            module_id=camp.get("current_module_id"), number=1,
            title="Whispers in Green Static", status="approved",
            script_path="documents:episode_script:Episode 1")).execute()
    summ = llm("summary", P.SUMMARIZE_EPISODE.format(
        scene_summaries=doc["content"][:12000]), 400)
    epid = (c.table("episodes").select("id").eq("campaign_id", camp["id"])
            .eq("number", 1).execute().data)[0]["id"]
    c.table("summaries").insert(dict(campaign_id=camp["id"], scope="episode",
        episode_id=epid, content=summ)).execute()
    for area in ("START", "KEEP-1"):
        c.table("events").insert(dict(campaign_id=camp["id"], episode_id=epid,
            type="location_discovered", description=f"Party at {area}",
            data={"area_id": area})).execute()
    c.table("events").insert(dict(campaign_id=camp["id"], episode_id=epid,
        type="milestone", description="Aaron Fischer crosses over; the party "
        "reaches the Keep's main gate.", data={})).execute()
    c.table("campaigns").update({"current_area": "KEEP-1"}).eq("id", camp["id"]).execute()
    print("Episode 1 registered as canon; party at KEEP-1 (Main Gate).")
