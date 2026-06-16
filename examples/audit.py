"""까다로운 입력으로 약점을 찾는 감사 스크립트."""
import traceback

from geny_svgforge import render

CASES = {
    "long_text": {
        "type": "node-graph",
        "nodes": [
            {"text": "이것은 한 박스 안에 들어가기에는 지나치게 긴 설명 문장이라서 자동 줄바꿈이 없으면 박스가 끔찍하게 넓어진다", "row": 0, "col": 0},
            {"text": "짧음", "row": 0, "col": 1},
        ],
    },
    "cycle": {
        "type": "flow",
        "nodes": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}, {"id": "c", "text": "C"}],
        "edges": [{"from": "a", "to": "b", "arrow": True}, {"from": "b", "to": "c", "arrow": True},
                  {"from": "c", "to": "a", "arrow": True, "color": "gray", "label": "retry"}],
    },
    "self_loop": {
        "type": "flow",
        "nodes": [{"id": "a", "text": "시작"}, {"id": "b", "text": "polling", "shape": "diamond"}, {"id": "c", "text": "끝"}],
        "edges": [{"from": "a", "to": "b", "arrow": True}, {"from": "b", "to": "b", "arrow": True, "label": "wait"},
                  {"from": "b", "to": "c", "arrow": True, "label": "done"}],
    },
    "single": {"type": "flow", "nodes": [{"id": "a", "text": "혼자", "shape": "pill"}], "edges": []},
    "right_dir": {
        "type": "flow", "direction": "right",
        "nodes": [{"id": "a", "text": "입력"}, {"id": "b", "text": "처리", "shape": "diamond"},
                  {"id": "c", "text": "출력", "variant": "good"}, {"id": "d", "text": "에러", "variant": "muted"}],
        "edges": [{"from": "a", "to": "b", "arrow": True}, {"from": "b", "to": "c", "arrow": True, "label": "ok"},
                  {"from": "b", "to": "d", "arrow": True, "label": "fail"}],
    },
    "wide_fanout": {
        "type": "flow",
        "nodes": [{"id": "root", "text": "router", "shape": "diamond", "variant": "highlight"},
                  *[{"id": f"c{i}", "text": f"handler {i}"} for i in range(6)]],
        "edges": [{"from": "root", "to": f"c{i}", "arrow": True} for i in range(6)],
    },
}

for name, spec in CASES.items():
    try:
        r = render(spec)
        flag = ""
        if r.warnings:
            flag = f"  ⚠ warnings={r.warnings}"
        if r.width > 900:
            flag += f"  ⚠ very wide ({r.width:.0f})"
        print(f"[{name:12}] {r.width:.0f}x{r.height:.0f}{flag}")
    except Exception as e:  # noqa: BLE001
        print(f"[{name:12}] EXCEPTION: {e}")
        traceback.print_exc()
