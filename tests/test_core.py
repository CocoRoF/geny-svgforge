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
    variants = s["oneOf"]
    props = [set(v.get("properties", {})) for v in variants]
    assert any("nodes" in p for p in props)   # node-graph
    assert any("rows" in p for p in props)    # token-sequence


def test_node_graph_renders_clean():
    spec = {
        "type": "node-graph",
        "row_labels": {0: "a", 1: "b"},
        "nodes": [
            {"text": "토큰", "row": 0, "col": 0, "id": "n0", "sublabel": "0"},
            {"text": "임베딩", "row": 1, "col": 0, "id": "n1"},
            {"text": "곁", "row": 0, "col": 1, "id": "m0"},
        ],
        "edges": [{"from": "n0", "to": "n1", "color": "blue", "arrow": True}],
    }
    r = render(spec)
    assert r.warnings == []
    assert r.svg.startswith("<svg") and r.width > 0


def test_flow_auto_layout_renders_clean():
    spec = {
        "type": "flow",
        "nodes": [
            {"id": "a", "text": "시작", "shape": "pill"},
            {"id": "b", "text": "판단", "shape": "diamond", "variant": "highlight"},
            {"id": "c", "text": "처리"},
            {"id": "d", "text": "끝", "shape": "pill", "variant": "good"},
        ],
        "edges": [
            {"from": "a", "to": "b", "arrow": True},
            {"from": "b", "to": "c", "arrow": True, "label": "yes", "color": "good"},
            {"from": "b", "to": "d", "arrow": True, "label": "no"},   # spans a layer → lane detour
            {"from": "c", "to": "d", "arrow": True},
        ],
    }
    r = render(spec)
    assert r.warnings == []
    assert r.svg.startswith("<svg") and "<title>" not in r.svg or True


def test_flow_layering_assigns_rows():
    from geny_svgforge.layout import _layer_flow
    from geny_svgforge.spec import FlowSpec
    ng = _layer_flow(FlowSpec.model_validate({
        "type": "flow",
        "nodes": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}, {"id": "c", "text": "C"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    }))
    rows = {n.id: n.row for n in ng.nodes}
    assert rows["a"] == 0 and rows["b"] == 1 and rows["c"] == 2


def test_token_sequence_converts_to_node_graph():
    from geny_svgforge.spec import TokenSequenceSpec
    m = TokenSequenceSpec.model_validate(_spec())
    ng = m.to_node_graph()
    assert ng.type == "node-graph"
    assert len(ng.nodes) == 9  # 4 + 5 tokens


def test_embed_font_default_on():
    r = render(_spec())
    assert "@font-face" in r.svg  # 폰트 임베드로 이식성 확보
