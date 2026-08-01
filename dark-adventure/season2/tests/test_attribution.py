from season2.engine.attribution import (detect_quotes, numbered_text,
                                        parse_pass, resolve, annotate, stats,
                                        NARRATOR)

TEXT = ('Brennos counted us twice. "Nine," he said, and the word had teeth. '
        'I kept my voice level. "Count again." '
        'Somewhere behind us Thessaly murmured, "He won\u2019t like the answer."')


def test_detect_quotes_straight_and_curly():
    qs = detect_quotes(TEXT)
    assert [q["quote"] for q in qs] == ["Nine,", "Count again.",
                                       "He won\u2019t like the answer."]
    curly = detect_quotes('\u201cHold the line,\u201d she said.')
    assert curly[0]["quote"] == "Hold the line,"


def test_numbered_text_marks_every_quote():
    qs = detect_quotes(TEXT)
    n = numbered_text(TEXT, qs)
    assert "[Q1]" in n and "[Q3]" in n


def test_policy_requires_double_high_agreement():
    qs = detect_quotes(TEXT)
    legal = {"Brennos", "Aaron Fischer", "Thessaly", NARRATOR}
    p1 = {"Q1": ("Brennos", "high", "grim"),
          "Q2": ("Aaron Fischer", "high", "level"),
          "Q3": ("Thessaly", "low", "soft")}
    p2 = {"Q1": ("Brennos", "high", ""),
          "Q2": ("Thessaly", "high", ""),        # disagreement
          "Q3": ("Thessaly", "high", "")}        # low on pass 1
    spans = resolve(p1, p2, qs)
    assert spans[0]["speaker"] == "Brennos" and spans[0]["fallback"] is None
    assert spans[1]["speaker"] == NARRATOR and spans[1]["fallback"] == "disagreement"
    assert spans[2]["speaker"] == NARRATOR and spans[2]["fallback"] == "low_confidence"
    st = stats(spans)
    assert st["cast_attributed"] == 1 and st["disagreements"] == 1


def test_parse_pass_rejects_illegal_speakers_and_fills_gaps():
    qs = detect_quotes(TEXT)
    legal = {"Brennos", NARRATOR}
    raw = '[{"id": "Q1", "speaker": "Sauron", "confidence": "high"}]'
    p = parse_pass(raw, qs, legal)
    assert p["Q1"][0] == NARRATOR and p["Q3"][0] == NARRATOR


def test_annotate_inserts_reviewable_tags():
    qs = detect_quotes(TEXT)
    legal = {"Brennos", NARRATOR}
    p = {q["id"]: ("Brennos", "high", "grim") for q in qs}
    spans = resolve(p, p, qs)
    out = annotate(TEXT, spans)
    assert "[Brennos|grim] " in out and out.count("[Brennos") == 3
