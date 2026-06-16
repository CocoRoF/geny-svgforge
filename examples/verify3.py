"""세 가지 대표 다이어그램을 node-graph 로 렌더해 라우팅/레이아웃을 검증."""
import pathlib

from geny_svgforge import render
from geny_svgforge.api import to_png

HERE = pathlib.Path(__file__).parent


def cols(texts, row, variant=None, sub=None, idp=None):
    out = []
    for c, t in enumerate(texts):
        n = {"text": t, "row": row, "col": c}
        if variant:
            n["variant"] = variant
        if sub:
            n["sublabel"] = sub[c]
        if idp:
            n["id"] = f"{idp}{c}"
        out.append(n)
    return out


EMBEDDING = {
    "type": "node-graph",
    "title": "Token embedding + positional encoding",
    "subtitle": "각 토큰 위치마다 같은 hidden size 벡터를 더해 transformer 입력을 만든다",
    "row_labels": {0: "token", 1: "token embedding", 2: "position vector", 3: "input vector"},
    "nodes": [
        *cols(["나는", "밥을", "먹었다"], 0, sub=["0", "1", "2"], idp="t"),
        *cols(["E[나는]", "E[밥을]", "E[먹었다]"], 1, variant="accent", idp="e"),
        *cols(["PE[0]", "PE[1]", "PE[2]"], 2, variant="highlight", idp="p"),
        *cols(["x0 = E + PE", "x1 = E + PE", "x2 = E + PE"], 3, idp="x"),
    ],
    "edges": (
        [{"from": f"t{c}", "to": f"e{c}", "color": "gray", "arrow": True} for c in range(3)]
        + [{"from": f"e{c}", "to": f"x{c}", "color": "blue", "arrow": True} for c in range(3)]
        + [{"from": f"p{c}", "to": f"x{c}", "color": "accent", "arrow": True} for c in range(3)]
    ),
    "note": {"title": "shape", "lines": [
        "token embedding: [seq_len, hidden_size]",
        "positional encoding: [seq_len, hidden_size]",
        "result: [seq_len, hidden_size]",
    ]},
    "caption": "token embedding과 positional encoding은 같은 hidden size를 가지며 같은 위치끼리 element-wise add된다.",
}

SINUSOIDAL = {
    "type": "node-graph",
    "title": "Sinusoidal positional encoding matrix",
    "subtitle": "한 position은 빠른 파장과 느린 파장의 sin, cos 값을 함께 가진다",
    "row_labels": {0: "position 0", 1: "position 1", 2: "position 2", 3: "position 3"},
    "col_labels": {0: "dim 0", 1: "dim 1", 2: "dim 2", 3: "dim 3"},
    "nodes": [
        *cols(["sin = 0", "cos = 1", "sin = 0", "cos = 1"], 0,
              sub=["fast sin", "fast cos", "slow sin", "slow cos"], idp="r0c"),
        *cols(["0.84", "0.54", "0.05", "0.99"], 1,
              sub=["fast sin", "fast cos", "slow sin", "slow cos"], idp="r1c"),
        *cols(["0.91", "-0.42", "0.09", "0.99"], 2,
              sub=["fast sin", "fast cos", "slow sin", "slow cos"], idp="r2c"),
        *cols(["0.14", "-0.99", "0.14", "0.99"], 3,
              sub=["fast sin", "fast cos", "slow sin", "slow cos"], idp="r3c"),
    ],
    "edges": [{"from": f"r{r}c2", "to": f"r{r+1}c2", "color": "blue"} for r in range(3)],
    "note": {"title": "읽는 법", "lines": [
        "앞쪽 차원은 가까운 위치 변화에 민감하다",
        "뒤쪽 차원은 더 느리게 변한다",
        "여러 주파수가 한 위치 벡터 안에 섞인다",
    ]},
    "caption": "각 position은 여러 주파수의 sin, cos 값을 hidden dimension 방향으로 가진다.",
}

ABSPOS = {
    "type": "node-graph",
    "title": "Absolute position shifts, relative pattern remains",
    "subtitle": "문장 앞에 토큰이 들어오면 position은 밀리지만 주변 토큰 관계는 유지된다",
    "row_labels": {0: "문장 A", 1: "관계 A", 2: "문장 B", 3: "관계 B"},
    "nodes": [
        {"text": "나는", "row": 0, "col": 0, "sublabel": "0"},
        {"text": "오늘", "row": 0, "col": 1, "sublabel": "1"},
        {"text": "밥을", "row": 0, "col": 2, "sublabel": "2", "id": "aobj"},
        {"text": "먹었다", "row": 0, "col": 3, "sublabel": "3", "variant": "good", "id": "averb"},
        {"text": "밥을", "row": 1, "col": 0, "sublabel": "object", "variant": "accent", "id": "raobj"},
        {"text": "다음", "row": 1, "col": 1, "sublabel": "+1", "variant": "muted"},
        {"text": "먹었다", "row": 1, "col": 2, "sublabel": "verb", "variant": "good", "id": "raverb"},
        {"text": "나는", "row": 2, "col": 0, "sublabel": "0"},
        {"text": "정말", "row": 2, "col": 1, "sublabel": "1", "variant": "accent"},
        {"text": "오늘", "row": 2, "col": 2, "sublabel": "2"},
        {"text": "밥을", "row": 2, "col": 3, "sublabel": "3", "id": "bobj"},
        {"text": "먹었다", "row": 2, "col": 4, "sublabel": "4", "variant": "good", "id": "bverb"},
        {"text": "밥을", "row": 3, "col": 0, "sublabel": "object", "variant": "accent", "id": "rbobj"},
        {"text": "다음", "row": 3, "col": 1, "sublabel": "+1", "variant": "muted"},
        {"text": "먹었다", "row": 3, "col": 2, "sublabel": "verb", "variant": "good", "id": "rbverb"},
    ],
    "edges": [
        {"from": "aobj", "to": "averb", "color": "accent"},
        {"from": "raobj", "to": "raverb", "color": "gray", "arrow": True},
        {"from": "bobj", "to": "bverb", "color": "accent"},
        {"from": "rbobj", "to": "rbverb", "color": "gray", "arrow": True},
    ],
    "note": {"title": "모델이 배워야 하는 것", "lines": [
        "절대 position 번호만 외우면 일반화가 약하다",
        "언어 패턴은 주변 토큰과의 거리에서 자주 드러난다",
        "sin과 cos는 offset 관계를 선형 연산으로 다루기 좋다",
    ]},
    "caption": "앞에 토큰이 끼어들면 절대 position은 바뀌지만, 가까운 토큰 사이의 상대 관계는 유지된다.",
}

for name, spec in [("embedding", EMBEDDING), ("sinusoidal", SINUSOIDAL), ("abspos", ABSPOS)]:
    r = render(spec)
    (HERE / f"{name}.png").write_bytes(to_png(spec, scale=2.0))
    print(f"{name}: {r.width:.0f}x{r.height:.0f}  warnings={r.warnings}")
