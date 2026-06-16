import json
import pathlib

from geny_svgforge import json_schema, render, validate_spec
from geny_svgforge.geometry import PathEl, RectEl
from geny_svgforge.layout import build_scene
from geny_svgforge.spec import TokenSequenceSpec

EX = pathlib.Path(__file__).parent.parent / "examples" / "token_sequence_positions.json"


def _spec() -> dict:
    return json.loads(EX.read_text(encoding="utf-8"))


def test_render_zero_warnings():
    r = render(_spec())
    assert r.svg.startswith("<svg")
    assert r.width > 0 and r.height > 0
    assert r.warnings == []  # 겹침/오버플로 없음


def test_all_elements_inside_canvas():
    scene = build_scene(TokenSequenceSpec.model_validate(_spec()))
    for el in scene.elements:
        bb = el.bbox()
        if bb is None:
            continue
        assert bb.x >= -1 and bb.y >= -1
        assert bb.right <= scene.width + 1 and bb.bottom <= scene.height + 1


def test_token_boxes_and_connector_present():
    scene = build_scene(TokenSequenceSpec.model_validate(_spec()))
    boxes = [e for e in scene.elements if isinstance(e, RectEl) and e.role == "box"]
    paths = [e for e in scene.elements if isinstance(e, PathEl)]
    assert len(boxes) == 9          # sentence A(4) + B(5)
    assert len(paths) >= 1          # a2 -> b3 커넥터


def test_no_box_overlap():
    scene = build_scene(TokenSequenceSpec.model_validate(_spec()))
    boxes = [e.bbox() for e in scene.elements if isinstance(e, RectEl) and e.role == "box"]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not boxes[i].intersects(boxes[j], pad=-0.5)


def test_validation_rejects_empty_tokens():
    res = validate_spec({"type": "token-sequence", "rows": [{"tokens": []}]})
    assert res["ok"] is False
    assert res["errors"]


def test_schema_exposes_fields():
    s = json_schema()
    assert "rows" in s["properties"]
    assert s["properties"]["type"]


def test_embed_font_default_on():
    r = render(_spec())
    assert "@font-face" in r.svg  # 폰트 임베드로 이식성 확보
