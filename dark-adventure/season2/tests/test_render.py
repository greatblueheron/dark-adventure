from season2.audio.render import segment_scene, strip_markdown, _cache_path
from season2.engine.attribution import detect_quotes, resolve, NARRATOR

TEXT = ('The yard held its breath. "Nine," Brennos said, and nobody laughed. '
        'I answered before thinking. "Count again." '
        'He did. "Nine," he said again, softer.')


def _spans(assignments):
    qs = detect_quotes(TEXT)
    p = {q["id"]: assignments[q["id"]] for q in qs}
    return resolve(p, p, qs)


def test_segment_cast_quotes_cut_and_narration_merges():
    spans = _spans({"Q1": ("Brennos", "high", "grim"),
                    "Q2": ("Aaron Fischer", "high", "level"),
                    "Q3": ("Brennos", "high", "soft")})
    segs = segment_scene(TEXT, spans)
    speakers = [s["speaker"] for s in segs]
    assert speakers == [NARRATOR, "Brennos", NARRATOR, "Aaron Fischer",
                        NARRATOR, "Brennos", NARRATOR]
    assert "softer" in segs[-1]["text"]           # trailing attribution -> Aaron
    assert segs[1]["text"] == "Nine," and '"' not in segs[1]["text"]
    assert "Brennos said" in segs[2]["text"]      # attribution stays narrator


def test_segment_fallback_dissolves_into_narration():
    spans = _spans({"Q1": ("Brennos", "high", ""),
                    "Q2": (NARRATOR, "high", ""),
                    "Q3": (NARRATOR, "low", "")})
    segs = segment_scene(TEXT, spans)
    assert [s["speaker"] for s in segs] == [NARRATOR, "Brennos", NARRATOR]
    assert '"Count again."' in segs[2]["text"]    # quote kept inline for Aaron


def test_strip_markdown_removes_headings_only():
    doc = "# Episode 1\n\nProse line one.\n\n## Scene\n\nProse line two.\n---\n"
    out = strip_markdown(doc)
    assert "Episode 1" not in out and "Prose line one." in out
    assert "Prose line two." in out


def test_cache_key_varies_by_voice_text_and_delivery():
    a = _cache_path("v1", "hello", None)
    assert a == _cache_path("v1", "hello", None)
    assert a != _cache_path("v2", "hello", None)
    assert a != _cache_path("v1", "hello", "whisper")


def test_concat_list_alternates_segments_and_gaps():
    from season2.audio.render import concat_list
    out = concat_list(["a.mp3", "b.mp3"], "gap.mp3")
    lines = out.strip().splitlines()
    assert len(lines) == 4
    assert lines[0].endswith("a.mp3'") and lines[1].endswith("gap.mp3'")
    assert lines[2].endswith("b.mp3'") and lines[3].endswith("gap.mp3'")


def test_stitch_produces_playable_audio(tmp_path):
    import shutil, subprocess, os
    if not shutil.which("ffmpeg"):
        import pytest; pytest.skip("no ffmpeg in test env")
    from season2.audio.render import stitch, silence
    os.makedirs("renders/cache", exist_ok=True)
    tone = str(tmp_path / "tone.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=0.3", "-c:a", "libmp3lame",
                    "-b:a", "128k", tone], capture_output=True)
    out = str(tmp_path / "out.mp3")
    mins = stitch([tone, tone], 160, out)
    assert os.path.getsize(out) > 1000 and mins > 0
