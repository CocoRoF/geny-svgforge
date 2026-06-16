"""v0.3.0 검증: flow 자동 배치 + 도형 + 엣지 라벨."""
import pathlib

from geny_svgforge import render
from geny_svgforge.api import to_png

HERE = pathlib.Path(__file__).parent

FLOW = {
    "type": "flow",
    "title": "RAG pipeline",
    "subtitle": "질문이 들어오면 검색 후 생성, 문서가 없으면 fallback",
    "direction": "down",
    "nodes": [
        {"id": "q", "text": "질문", "shape": "pill", "variant": "accent"},
        {"id": "emb", "text": "임베딩"},
        {"id": "search", "text": "벡터 검색"},
        {"id": "db", "text": "pgvector", "shape": "cylinder", "variant": "muted"},
        {"id": "found", "text": "문서 있음?", "shape": "diamond", "variant": "highlight"},
        {"id": "ctx", "text": "컨텍스트 구성"},
        {"id": "fallback", "text": "기본 응답", "shape": "rect", "variant": "muted"},
        {"id": "llm", "text": "LLM 생성", "variant": "accent"},
        {"id": "ans", "text": "답변", "shape": "pill", "variant": "good"},
    ],
    "edges": [
        {"from": "q", "to": "emb", "arrow": True},
        {"from": "emb", "to": "search", "arrow": True},
        {"from": "search", "to": "db", "arrow": True, "dashed": True, "label": "query"},
        {"from": "db", "to": "found", "arrow": True},
        {"from": "found", "to": "ctx", "arrow": True, "color": "good", "label": "yes"},
        {"from": "found", "to": "fallback", "arrow": True, "color": "gray", "label": "no"},
        {"from": "ctx", "to": "llm", "arrow": True},
        {"from": "llm", "to": "ans", "arrow": True},
        {"from": "fallback", "to": "ans", "arrow": True},
    ],
    "caption": "질문 → 검색 → 생성. 문서가 없으면 fallback 경로로.",
}

SHAPES = {
    "type": "node-graph",
    "title": "Node shapes",
    "row_labels": {0: "기본", 1: "흐름도"},
    "nodes": [
        {"text": "rect", "row": 0, "col": 0, "shape": "rect"},
        {"text": "pill", "row": 0, "col": 1, "shape": "pill", "variant": "accent"},
        {"text": "ellipse", "row": 0, "col": 2, "shape": "ellipse", "variant": "highlight"},
        {"text": "diamond", "row": 0, "col": 3, "shape": "diamond", "variant": "good"},
        {"text": "cylinder", "row": 1, "col": 0, "shape": "cylinder", "variant": "muted"},
        {"text": "hexagon", "row": 1, "col": 1, "shape": "hexagon", "variant": "accent"},
        {"text": "parallelogram", "row": 1, "col": 2, "shape": "parallelogram"},
        {"text": "줄바꿈\\n지원", "row": 1, "col": 3, "shape": "rect", "variant": "good"},
    ],
    "caption": "모든 도형은 텍스트 크기에 맞춰 자동으로 커진다.",
}

for name, spec in [("flow", FLOW), ("shapes", SHAPES)]:
    r = render(spec)
    (HERE / f"{name}.png").write_bytes(to_png(spec, scale=2.0))
    print(f"{name}: {r.width:.0f}x{r.height:.0f}  warnings={r.warnings}  title={'<title>' in r.svg}")
