"""Phase 6 voice casting — design custom ElevenLabs voices per character
from their PUBLIC attributes, audition them, accept or reroll.

  poetry run python -m season2.voices design Thessaly [--note "colder"]
  poetry run python -m season2.voices accept Thessaly --preview 2
  poetry run python -m season2.voices set "Aaron Fischer" --voice-id XYZ
  poetry run python -m season2.voices list

`design` writes auditions/<name>-preview{1..N}.mp3 — LISTEN, then accept
one (saves it to your ElevenLabs library and records voice_id in the DB)
or run design again to reroll. Rejected preview ids are reported to the
API on accept (their tuning signal). Requires ELEVENLABS_API_KEY in .env.

Voice descriptions are built from the PUBLIC persona only — a voice is a
perceivable attribute; hidden truths must not leak into casting.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from .db import client
from .bootstrap import fetch_campaign, latest_doc, _split_public
from .engine.loop import llm

API = "https://api.elevenlabs.io/v1"


def _headers() -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    key = os.environ.get("ELEVENLABS_API_KEY")
    assert key, "set ELEVENLABS_API_KEY in .env"
    return {"xi-api-key": key, "Content-Type": "application/json"}


def _character(c, camp, name: str) -> dict:
    """Party first, then recurring NPCs; result carries _table for writes."""
    for table in ("characters", "npcs"):
        rows = (c.table(table).select("*").eq("campaign_id", camp["id"])
                .ilike("name", f"%{name}%").execute().data)
        if len(rows) > 1:
            raise AssertionError(f"ambiguous: {[r['name'] for r in rows]}")
        if rows:
            rows[0]["_table"] = table
            rows[0].setdefault("ancestry", "human")
            rows[0].setdefault("class", rows[0].get("role") or "commoner")
            return rows[0]
    raise AssertionError(f"no character or npc matching {name!r}")


DESCRIBE = """Write an ElevenLabs voice-design description (60-400 chars,
plain prose, no names) for this fantasy audio-drama character. Cover:
apparent age and gender of the voice, race colouration ({race}), timbre,
pace, accent flavour, and emotional default. Use ONLY the public persona
below - perceivable qualities, no secrets.

CLASS: {cls}   RACE: {race}
PUBLIC PERSONA:
{persona}
{note}
Output ONLY the description text."""

AUDITION = """Write a 150-350 character audition passage this character
would plausibly SAY aloud - 2-3 short in-character lines a listener could
judge the voice by (greeting, an observation, a warning). No stage
directions, no quotes marks. PUBLIC PERSONA:
{persona}
Output ONLY the lines."""


def design(name: str, note: str | None, n_previews: int = 3) -> None:
    import requests
    c = client()
    camp = fetch_campaign(c)
    ch = _character(c, camp, name)
    doc = latest_doc(c, camp["id"], "character_bible", ch["name"])
    persona = _split_public(doc["content"]) if doc else f"a {ch['ancestry']} {ch['class']}"
    desc = llm("summary", DESCRIBE.format(
        cls=ch["class"], race=ch["ancestry"], persona=persona[:2500],
        note=f"DIRECTION FROM THE SHOWRUNNER: {note}" if note else ""), 400).strip()
    desc = desc[:1000] if len(desc) >= 20 else desc + " — a fantasy adventurer's voice."
    audition = llm("summary", AUDITION.format(persona=persona[:2500]), 300).strip()
    audition = (audition + " ")[:1000]
    if len(audition) < 100:
        audition = (audition + " The road was long, and the borderlands are "
                    "longer. Stay close, keep your voice down, and count "
                    "your friends twice.")[:1000]
    print(f"description ({len(desc)} chars): {desc}\n")
    r = requests.post(f"{API}/text-to-voice/design", headers=_headers(),
                      json=dict(voice_description=desc, text=audition),
                      timeout=120)
    r.raise_for_status()
    previews = r.json().get("previews", [])
    assert previews, f"no previews returned: {r.text[:200]}"
    os.makedirs("auditions", exist_ok=True)
    slug = ch["name"].split()[0].lower()
    manifest = dict(character=ch["name"], description=desc, text=audition,
                    previews=[])
    for i, p in enumerate(previews[:n_previews], 1):
        path = f"auditions/{slug}-preview{i}.mp3"
        with open(path, "wb") as f:
            f.write(base64.b64decode(p["audio_base_64"]))
        manifest["previews"].append(dict(n=i, generated_voice_id=p["generated_voice_id"]))
        print(f"  preview {i}: {path}")
    with open(f"auditions/{slug}-manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(f"\nLISTEN, then: voices accept {slug} --preview N   (or design "
          f"again to reroll)")


def accept(name: str, preview: int) -> None:
    import requests
    c = client()
    camp = fetch_campaign(c)
    ch = _character(c, camp, name)
    slug = ch["name"].split()[0].lower()
    with open(f"auditions/{slug}-manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    chosen = next(p for p in manifest["previews"] if p["n"] == preview)
    rejected = [p["generated_voice_id"] for p in manifest["previews"]
                if p["n"] != preview]
    r = requests.post(f"{API}/text-to-voice", headers=_headers(), json=dict(
        voice_name=f"WGS2 - {ch['name']}",
        voice_description=manifest["description"],
        generated_voice_id=chosen["generated_voice_id"],
        played_not_selected_voice_ids=rejected), timeout=120)
    r.raise_for_status()
    voice_id = r.json()["voice_id"]
    c.table(ch["_table"]).update({"voice_id": voice_id}).eq("id", ch["id"]).execute()
    print(f"{ch['name']} cast: voice_id {voice_id} saved to library and DB.")


def set_voice(name: str, voice_id: str) -> None:
    c = client()
    camp = fetch_campaign(c)
    ch = _character(c, camp, name)
    c.table(ch["_table"]).update({"voice_id": voice_id}).eq("id", ch["id"]).execute()
    print(f"{ch['name']}: voice_id set to {voice_id}")


def verify(name: str) -> None:
    """Ask the ElevenLabs API whether the character's saved voice exists
    on the account this API key belongs to."""
    import requests
    c = client()
    camp = fetch_campaign(c)
    ch = _character(c, camp, name)
    vid = ch.get("voice_id")
    assert vid, f"{ch['name']} has no voice_id in the DB - accept a preview first"
    r = requests.get(f"{API}/voices/{vid}", headers=_headers(), timeout=60)
    if r.status_code == 200:
        v = r.json()
        print(f"FOUND on this API key's account: {v.get('name')!r} "
              f"(category={v.get('category')}, voice_id={vid})")
        print("If the dashboard doesn't show it: check My Voices (not Voice "
              "Library), any category filter, and that you're logged into "
              "the SAME account/workspace as this API key.")
    else:
        print(f"NOT FOUND ({r.status_code}): the save didn't stick on this "
              f"account. Re-run accept; if it recurs, show me the output.")


def list_voices() -> None:
    c = client()
    camp = fetch_campaign(c)
    for table, label in (("characters", "party"), ("npcs", "npc")):
        for r in (c.table(table).select("name, voice_id")
                  .eq("campaign_id", camp["id"]).order("name").execute().data):
            print(f"  {r['name']:<20} {label:<6} {r['voice_id'] or '- uncast -'}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="voices")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("design"); d.add_argument("name")
    d.add_argument("--note", default=None)
    a = sub.add_parser("accept"); a.add_argument("name")
    a.add_argument("--preview", type=int, required=True)
    s = sub.add_parser("set"); s.add_argument("name")
    s.add_argument("--voice-id", required=True)
    v = sub.add_parser("verify"); v.add_argument("name")
    sub.add_parser("list")
    args = ap.parse_args()
    if args.cmd == "design":
        design(args.name, args.note)
    elif args.cmd == "accept":
        accept(args.name, args.preview)
    elif args.cmd == "set":
        set_voice(args.name, args.voice_id)
    elif args.cmd == "verify":
        verify(args.name)
    elif args.cmd == "list":
        list_voices()


if __name__ == "__main__":
    main()
