"""선언적 다이어그램 spec.

AI 에이전트는 좌표를 한 줄도 쓰지 않고 '무엇을 그릴지'만 이 spec(JSON)으로 기술한다.
좌표·정렬·커넥터 라우팅·캔버스 크기는 전부 엔진(layout.py)이 결정론적으로 계산한다.

핵심 타입은 일반화된 **node-graph**: 그리드(row/col)에 노드를 놓고, 임의의 노드 사이를
견고하게 라우팅되는 edge 로 연결한다. token-sequence 는 node-graph 로 변환되는 sugar.
"""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Variant = Literal["default", "accent", "highlight", "muted", "good"]
EdgeColor = Literal["accent", "blue", "gray", "good"]
Shape = Literal["rect", "pill", "ellipse", "diamond", "cylinder", "hexagon", "parallelogram"]


# ── 일반 node-graph ────────────────────────────────────────────
class GNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="박스 안 텍스트 (\\n 로 줄바꿈 가능)")
    row: int = Field(..., ge=0, description="그리드 행 (0=맨 위)")
    col: int = Field(..., ge=0, description="그리드 열 (0=맨 왼쪽). 같은 col 은 세로로 정렬됨")
    id: Optional[str] = Field(None, description="edge 가 가리킬 고유 id")
    variant: Variant = Field("default", description="색상 변형")
    shape: Shape = Field("rect", description="노드 도형")
    sublabel: Optional[str] = Field(None, description="박스 아래 작은 라벨 (예: 'pos 0', 'fast sin')")


class GEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(..., alias="from", description="시작 노드 id")
    to: str = Field(..., description="끝 노드 id")
    color: EdgeColor = "gray"
    arrow: bool = Field(False, description="끝에 화살표 머리")
    dashed: bool = False
    label: Optional[str] = None


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    lines: list[str] = Field(default_factory=list)


class NodeGraphSpec(BaseModel):
    """그리드에 놓인 노드 + 임의의 edge 로 구성된 일반 다이어그램.

    박스-화살표 도식 대부분(임베딩 흐름, 행렬, 파이프라인 등)을 표현한다.
    같은 col 의 노드는 세로로 정렬되고, edge 는 박스를 뚫지 않게 라우팅된다.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["node-graph"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    nodes: list[GNode] = Field(..., min_length=1)
    edges: list[GEdge] = Field(default_factory=list)
    # 행/열 헤더. 키는 row/col 인덱스(JSON 에선 문자열 키도 자동 정수 변환).
    row_labels: dict[int, str] = Field(default_factory=dict, description="행 왼쪽 라벨 {row: text}")
    col_labels: dict[int, str] = Field(default_factory=dict, description="열 위 라벨 {col: text}")
    note: Optional[Note] = None
    caption: Optional[str] = None
    theme: Literal["light", "dark"] = "light"
    font_size: int = Field(15, ge=8, le=40)


# ── flow (자동 레이어 배치) ────────────────────────────────────
class FNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="고유 id (edge 가 가리킴)")
    text: str
    variant: Variant = "default"
    shape: Shape = "rect"
    sublabel: Optional[str] = None


class FlowSpec(BaseModel):
    """플로우차트. row/col 을 직접 주지 않고 edge 그래프 구조로 자동 배치한다.

    layer(노드) = 시작 노드로부터의 최장 경로. direction='down' 이면 layer 가 행,
    'right' 면 열이 된다. 같은 layer 안의 순서는 이웃 위치 기준으로 자동 정렬(교차 감소).
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["flow"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    direction: Literal["down", "right"] = "down"
    nodes: list[FNode] = Field(..., min_length=1)
    edges: list[GEdge] = Field(default_factory=list)
    note: Optional[Note] = None
    caption: Optional[str] = None
    theme: Literal["light", "dark"] = "light"
    font_size: int = Field(15, ge=8, le=40)


# ── token-sequence (sugar) ─────────────────────────────────────
class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    pos: Optional[str] = None
    id: Optional[str] = None
    variant: Variant = "default"


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = None
    tokens: list[Token] = Field(..., min_length=1)


class Connector(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(..., alias="from")
    to: str = Field(...)
    style: Literal["arc"] = "arc"
    color: EdgeColor = "accent"
    arrow: bool = False
    label: Optional[str] = None


class TokenSequenceSpec(BaseModel):
    """위치 라벨 토큰 박스의 행들. 내부적으로 node-graph 로 변환되어 렌더된다."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["token-sequence"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    rows: list[Row] = Field(..., min_length=1)
    connectors: list[Connector] = Field(default_factory=list)
    note: Optional[Note] = None
    caption: Optional[str] = None
    theme: Literal["light", "dark"] = "light"
    font_size: int = Field(15, ge=8, le=40)

    def to_node_graph(self) -> NodeGraphSpec:
        nodes: list[GNode] = []
        row_labels: dict[int, str] = {}
        for ri, row in enumerate(self.rows):
            if row.label:
                row_labels[ri] = row.label
            for ci, tok in enumerate(row.tokens):
                nodes.append(GNode(
                    text=tok.text, row=ri, col=ci, id=tok.id,
                    variant=tok.variant, sublabel=tok.pos,
                ))
        edges = [
            GEdge.model_validate({"from": c.from_, "to": c.to, "color": c.color, "arrow": c.arrow, "label": c.label})
            for c in self.connectors
        ]
        return NodeGraphSpec(
            type="node-graph", title=self.title, subtitle=self.subtitle,
            nodes=nodes, edges=edges, row_labels=row_labels,
            note=self.note, caption=self.caption, theme=self.theme, font_size=self.font_size,
        )


DiagramSpec = Union[NodeGraphSpec, FlowSpec, TokenSequenceSpec]


def json_schema() -> dict:
    """AI 에이전트가 형식을 학습할 JSON Schema."""
    return {
        "oneOf": [
            NodeGraphSpec.model_json_schema(),
            FlowSpec.model_json_schema(),
            TokenSequenceSpec.model_json_schema(),
        ],
        "$comment": (
            "Pick by type: 'flow' = auto-laid-out flowchart (just nodes+edges, no row/col); "
            "'node-graph' = explicit grid placement; 'token-sequence' = sugar."
        ),
    }
