import json
import pytest
from season2.ingest import parse_chunks, _windows, CHUNK_PROMPT


def test_parse_chunks_validates_and_defaults():
    raw = json.dumps([dict(area_id="KEEP-12", area_name="Tavern",
                           section="keep", content="A smoky room.")])
    chunks = parse_chunks(raw)
    assert chunks[0]["connections"] == []


def test_parse_chunks_strips_fences_and_rejects_bad():
    raw = "```json\n" + json.dumps([dict(area_id="A", area_name="B",
                                         section="caves", content="C",
                                         connections=["D"])]) + "\n```"
    assert parse_chunks(raw)[0]["connections"] == ["D"]
    with pytest.raises(Exception):
        parse_chunks(json.dumps([dict(area_id="", area_name="X",
                                      section="keep", content="y")]))


def test_windows_split_on_paragraphs_and_cover_everything():
    text = ("para " * 200 + "\n\n") * 100          # ~100k chars
    ws = _windows(text, max_chars=30000)
    assert len(ws) > 1
    assert "".join(ws) == text
    assert all(len(w) <= 30000 for w in ws)


def test_chunk_prompt_demands_verbatim_and_tables():
    p = CHUNK_PROMPT.format(part="part 1 of 1", text="XYZ")
    assert "VERBATIM" in p and '"tables"' in p and "XYZ" in p
