"""Phase 6 renderer: span files -> segmented, cached, stitched audio.

  audio script N     annotated scripts + span files for episode N
                     (episode 1 is ingested from its approved document)
  audio render N     spans -> per-scene mp3 -> renders/epN.mp3
                     [--scene I] one scene   [--estimate] no API calls

Spans are the authority: hand-edit scripts/*.spans.jsonl before rendering
and the correction is what gets voiced. Segments are cached by content
hash under renders/cache/ - re-renders only pay for what changed.
Speakers without a voice_id fall back to the narrator (Aaron reads them).
"""
from __future__ import annotations

import hashlib
import json
import os
import re

from ..db import client
from ..bootstrap import fetch_campaign, latest_doc
from ..engine.attribution import NARRATOR

API = "https://api.elevenlabs.io/v1"
FFMPEG = "ffmpeg"
MODEL = os.getenv("ELEVEN_MODEL", "eleven_multilingual_v2")
GAP_TURN_MS = 160
GAP_SCENE_MS = 900


# ---------------------------------------------------------------- segmentation

def segment_scene(text: str, spans: list[dict]) -> list[dict]:
    """Interleave narrator flow with cast-voiced quotes.
    Cast spans cut the text; fallback spans dissolve into narration; the
    cast segment speaks the quote's inner text; adjacent narration merges."""
    segs: list[dict] = []
    buf, last = [], 0
    for sp in spans:
        if sp.get("fallback") is None and sp["speaker"] != NARRATOR:
            buf.append(text[last:sp["start"]])
            narration = "".join(buf).strip()
            if narration:
                segs.append(dict(speaker=NARRATOR, text=narration,
                                 delivery=None))
            buf = []
            segs.append(dict(speaker=sp["speaker"], text=sp["quote"].strip(),
                             delivery=sp.get("delivery") or None))
            last = sp["end"]
        else:
            buf.append(text[last:sp["end"]])
            last = sp["end"]
    buf.append(text[last:])
    tail = "".join(buf).strip()
    if tail:
        segs.append(dict(speaker=NARRATOR, text=tail, delivery=None))
    return [s for s in segs if s["text"]]


def strip_markdown(text: str) -> str:
    """Episode 1 lives as a markdown document; keep only speakable prose."""
    lines = [l for l in text.splitlines()
             if not l.lstrip().startswith("#") and l.strip() != "---"]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ---------------------------------------------------------------- voices & tts

def voice_map(c, camp) -> dict:
    out = {}
    for t in ("characters", "npcs"):
        for r in (c.table(t).select("name, voice_id")
                  .eq("campaign_id", camp["id"]).execute().data):
            if r.get("voice_id"):
                out[r["name"]] = r["voice_id"]
    return out


def narrator_voice(vmap: dict) -> str:
    vid = vmap.get("Aaron Fischer")
    assert vid, "cast Aaron Fischer first (voices set/accept) - he narrates"
    return vid


def _cache_path(voice_id: str, text: str, delivery: str | None) -> str:
    h = hashlib.sha256(f"{MODEL}|{voice_id}|{delivery}|{text}".encode()).hexdigest()[:24]
    return f"renders/cache/{h}.mp3"


def tts(voice_id: str, text: str, delivery: str | None,
        prev: str, nxt: str) -> str:
    """Render one segment (cached). Returns the mp3 path."""
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    path = _cache_path(voice_id, text, delivery)
    if os.path.exists(path):
        return path
    os.makedirs("renders/cache", exist_ok=True)
    speak = text
    if delivery and "v3" in MODEL:
        speak = f"[{delivery}] {text}"          # v3 audio-tag direction
    body = dict(text=speak, model_id=MODEL,
                previous_text=prev[-300:] or None,
                next_text=nxt[:300] or None)
    r = requests.post(f"{API}/text-to-speech/{voice_id}",
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
                      json={k: v for k, v in body.items() if v is not None},
                      timeout=300)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return path


# ---------------------------------------------------------------- stitching

def _run(cmd: list[str]) -> None:
    import subprocess
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"ffmpeg failed: {r.stderr[-400:]}"


def _require_ffmpeg() -> None:
    import shutil
    assert shutil.which(FFMPEG), (
        "ffmpeg not found on PATH - install it (winget install Gyan.FFmpeg) "
        "and reopen the terminal")


def silence(ms: int) -> str:
    """Cached mp3 of silence, codec-matched to the segments."""
    path = f"renders/cache/silence-{ms}.mp3"
    if not os.path.exists(path):
        os.makedirs("renders/cache", exist_ok=True)
        _run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
              "-t", f"{ms/1000:.3f}", "-c:a", "libmp3lame", "-b:a", "128k",
              path])
    return path


def concat_list(paths: list[str], gap_path: str) -> str:
    """ffmpeg concat-demuxer list: every segment followed by the gap."""
    lines = []
    for p in paths:
        lines.append(f"file '{os.path.abspath(p)}'")
        lines.append(f"file '{os.path.abspath(gap_path)}'")
    return "\n".join(lines) + "\n"


def stitch(paths: list[str], gap_ms: int, out: str) -> float:
    """Concat segments with gaps; returns duration in minutes."""
    _require_ffmpeg()
    import subprocess
    import tempfile
    gap = silence(gap_ms)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        f.write(concat_list(paths, gap))
        listfile = f.name
    _run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
          "-c:a", "libmp3lame", "-b:a", "128k", out])
    os.unlink(listfile)
    probe = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries",
                            "format=duration", "-of", "csv=p=0", out],
                           capture_output=True, text=True)
    try:
        return float(probe.stdout.strip()) / 60
    except ValueError:
        return 0.0


# ---------------------------------------------------------------- rendering

def load_scene_units(c, camp, number: int) -> list[dict]:
    """[{index, text, spans_path}] for an episode; ep1 from its document."""
    ep = (c.table("episodes").select("id, status").eq("campaign_id", camp["id"])
          .eq("number", number).execute().data)
    assert ep and ep[0]["status"] == "approved", "episode must be approved"
    scenes = (c.table("scenes").select("index, full_text")
              .eq("episode_id", ep[0]["id"]).order("index").execute().data)
    if scenes:
        return [dict(index=s["index"], text=s["full_text"] or "") for s in scenes]
    doc = latest_doc(c, camp["id"], "episode_script", f"Episode {number}")
    assert doc, f"episode {number} has no scenes and no script document"
    return [dict(index=1, text=strip_markdown(doc["content"]))]


def render_episode(number: int, only_scene: int | None,
                   estimate: bool) -> None:
    c = client()
    camp = fetch_campaign(c)
    vmap = voice_map(c, camp)
    narr = None if estimate else narrator_voice(vmap)
    units = load_scene_units(c, camp, number)
    os.makedirs("renders", exist_ok=True)
    scene_files, char_counts, uncast = [], {}, set()

    for u in units:
        if only_scene and u["index"] != only_scene:
            continue
        spans_path = f"scripts/ep{number}-scene{u['index']}.spans.jsonl"
        assert os.path.exists(spans_path), (
            f"missing {spans_path} - run `audio script {number}` first")
        spans = [json.loads(l) for l in open(spans_path, encoding="utf-8")
                 if l.strip()]
        segs = segment_scene(u["text"], spans)
        for i, seg in enumerate(segs):
            spk = seg["speaker"]
            if spk != NARRATOR and spk not in vmap:
                uncast.add(spk)
                seg["speaker"] = NARRATOR      # Aaron reads the uncast
            char_counts[seg["speaker"]] = (char_counts.get(seg["speaker"], 0)
                                           + len(seg["text"]))
        if estimate:
            print(f"scene {u['index']}: {len(segs)} segments, "
                  f"{sum(len(s['text']) for s in segs)} chars")
            continue

        seg_paths = []
        for i, seg in enumerate(segs):
            vid = narr if seg["speaker"] == NARRATOR else vmap[seg["speaker"]]
            prev = segs[i - 1]["text"] if i else ""
            nxt = segs[i + 1]["text"] if i + 1 < len(segs) else ""
            seg_paths.append(tts(vid, seg["text"], seg["delivery"], prev, nxt))
            print(f"  s{u['index']} seg {i+1}/{len(segs)} "
                  f"[{seg['speaker']}] {len(seg['text'])} chars", flush=True)
        out = f"renders/ep{number}-scene{u['index']}.mp3"
        stitch(seg_paths, GAP_TURN_MS, out)
        scene_files.append(out)
        print(f"scene {u['index']} -> {out}")

    if uncast:
        print(f"NOTE: uncast speakers read by narrator: {sorted(uncast)} "
              f"(cast them via `voices` and re-render - cache makes it cheap)")
    if estimate:
        total = sum(char_counts.values())
        print(f"\nESTIMATE ep{number}: {total} chars total")
        for k, v in sorted(char_counts.items(), key=lambda x: -x[1]):
            print(f"  {k:<16} {v:>7} chars")
        return
    if scene_files and not only_scene:
        out = f"renders/ep{number}.mp3"
        mins = stitch(scene_files, GAP_SCENE_MS, out)
        print(f"\nEPISODE ASSEMBLED: {out} ({mins:.1f} min)")


def generate_scripts(number: int) -> None:
    """Annotated scripts + span files for one episode (incl. episode 1)."""
    from .dryrun import attribute_scene, cast_names
    from ..engine import attribution as A
    c = client()
    camp = fetch_campaign(c)
    legal = cast_names(c, camp) | {A.NARRATOR}
    units = load_scene_units(c, camp, number)
    os.makedirs("scripts", exist_ok=True)
    for u in units:
        spans = attribute_scene(u["text"], legal)
        base = f"scripts/ep{number}-scene{u['index']}"
        with open(base + ".annotated.txt", "w", encoding="utf-8") as f:
            f.write(A.annotate(u["text"], spans))
        with open(base + ".spans.jsonl", "w", encoding="utf-8") as f:
            for sp in spans:
                f.write(json.dumps(sp, ensure_ascii=False) + "\n")
        st = A.stats(spans)
        print(f"scene {u['index']}: {st['quotes']} quotes, "
              f"{st['cast_attributed']} cast, "
              f"{st['narrator_fallback']} narrator")
    print(f"Skim scripts/ep{number}-*.annotated.txt; edit the .spans.jsonl "
          f"to correct any tag, then `audio render {number}`.")
