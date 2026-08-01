"""Dialogue attribution (Phase 6): detect quoted spans, attribute each to a
speaker via two independent model passes, and apply the precision-first
policy — a cast voice only when both passes agree with high confidence;
everything else falls back to the narrator (diegetically clean: it is
Aaron's memoir).

Pure parts (detection, policy, annotation) are deterministic and tested;
model calls are injected.
"""
from __future__ import annotations

import json
import re

NARRATOR = "NARRATOR"

QUOTE_RE = re.compile(r'[“"]([^”"]+)[”"]')


def detect_quotes(text: str) -> list[dict]:
    """Every quoted span, in order: {id, start, end, quote}."""
    out = []
    for i, m in enumerate(QUOTE_RE.finditer(text), 1):
        out.append(dict(id=f"Q{i}", start=m.start(), end=m.end(),
                        quote=m.group(1)))
    return out


ATTRIBUTION = """Attribute each quoted line in this scene to its speaker.

The scene is first-person memoir narrated by Aaron Fischer; a line may
only be attributed to a LEGAL SPEAKER. If the speaker is ambiguous, is
remembered/hypothetical speech, is read aloud from writing, or you are
not certain, attribute it to NARRATOR.

LEGAL SPEAKERS: {speakers}

SCENE with quotes numbered:
{numbered}

Return ONLY a JSON array, one object per quote id:
[{{"id": "Q1", "speaker": "exact legal name or NARRATOR",
   "confidence": "high"|"low",
   "delivery": "2-6 word performance note (tone, pace)"}}]"""


def numbered_text(text: str, quotes: list[dict]) -> str:
    """Scene text with [Qn] markers inserted before each quote."""
    out, last = [], 0
    for q in quotes:
        out.append(text[last:q["start"]])
        out.append(f"[{q['id']}] ")
        out.append(text[q["start"]:q["end"]])
        last = q["end"]
    out.append(text[last:])
    return "".join(out)


def parse_pass(raw: str, quotes: list[dict], legal: set[str]) -> dict:
    """Model output -> {qid: (speaker, confidence, delivery)}; illegal or
    missing entries resolve to NARRATOR/low."""
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        i = cleaned.find("[")
        data = json.loads(cleaned[i:]) if i >= 0 else []
    got = {}
    for e in data if isinstance(data, list) else []:
        sp = e.get("speaker", NARRATOR)
        if sp not in legal:
            sp = NARRATOR
        got[e.get("id")] = (sp, e.get("confidence", "low"),
                            (e.get("delivery") or "").strip()[:60])
    return {q["id"]: got.get(q["id"], (NARRATOR, "low", "")) for q in quotes}


def resolve(p1: dict, p2: dict, quotes: list[dict]) -> list[dict]:
    """Precision-first: cast voice only on agreement + high confidence from
    both passes; otherwise NARRATOR with the reason recorded."""
    spans = []
    for q in quotes:
        s1, c1, d1 = p1[q["id"]]
        s2, c2, _ = p2[q["id"]]
        if s1 == s2 and s1 != NARRATOR and c1 == "high" and c2 == "high":
            spans.append(dict(**q, speaker=s1, delivery=d1, fallback=None))
        else:
            reason = ("disagreement" if s1 != s2
                      else "low_confidence" if s1 != NARRATOR else "narration")
            spans.append(dict(**q, speaker=NARRATOR, delivery=d1,
                              fallback=reason))
    return spans


def annotate(text: str, spans: list[dict]) -> str:
    """Human-reviewable script: [SPEAKER|delivery] tags before each quote."""
    out, last = [], 0
    for s in spans:
        out.append(text[last:s["start"]])
        tag = s["speaker"] + (f"|{s['delivery']}" if s["delivery"] else "")
        out.append(f"[{tag}] ")
        out.append(text[s["start"]:s["end"]])
        last = s["end"]
    out.append(text[last:])
    return "".join(out)


def stats(spans: list[dict]) -> dict:
    cast = [s for s in spans if s["fallback"] is None]
    return dict(quotes=len(spans), cast_attributed=len(cast),
                narrator_fallback=len(spans) - len(cast),
                disagreements=sum(1 for s in spans
                                  if s["fallback"] == "disagreement"),
                by_speaker={s["speaker"]: sum(1 for x in spans
                                              if x["speaker"] == s["speaker"])
                            for s in spans})
