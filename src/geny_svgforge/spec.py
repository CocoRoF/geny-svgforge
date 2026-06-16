"""선언적 다이어그램 spec.

AI 에이전트는 좌표를 한 줄도 쓰지 않고, '무엇을 그릴지'만 이 spec(JSON)으로 기술한다.
레이아웃·좌표·충돌 회피는 전부 엔진(layout.py)이 결정론적으로 계산한다.

pydantic 모델이라 JSON Schema 자동 생성 + 입력 검증이 공짜로 따라온다.
"""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

TokenVariant = Literal["default", "accent", "highlight", "muted"]


class Token(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., description="박스 안에 표시할 텍스트")
    pos: Optional[str] = Field(None, description="박스 아래 작은 라벨 (예: 'pos 0')")
    id: Optional[str] = Field(None, description="connector 가 가리킬 고유 id")
    variant: TokenVariant = Field("default", description="색상 변형")


class Row(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Optional[str] = Field(None, description="행 왼쪽 위 라벨 (예: 'sentence A')")
    tokens: list[Token] = Field(..., min_length=1)


class Connector(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(..., alias="from", description="시작 토큰 id")
    to: str = Field(..., description="끝 토큰 id")
    style: Literal["arc"] = "arc"
    color: Literal["accent", "blue", "gray"] = "accent"
    arrow: bool = Field(False, description="끝에 화살표 머리 표시")
    label: Optional[str] = None


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    lines: list[str] = Field(default_factory=list)


class TokenSequenceSpec(BaseModel):
    """위치 라벨이 달린 토큰 박스의 행들과, 행 사이를 잇는 커넥터·옆 노트·캡션.

    첨부된 'Absolute position changes, relative pattern remains' 예시가 이 타입이다.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["token-sequence"]
    title: Optional[str] = None
    subtitle: Optional[str] = None
    rows: list[Row] = Field(..., min_length=1)
    connectors: list[Connector] = Field(default_factory=list)
    note: Optional[Note] = None
    caption: Optional[str] = None
    theme: Literal["light", "dark"] = "light"
    font_size: int = Field(15, ge=8, le=40, description="본문 토큰 글자 크기(px)")


# 향후 타입 추가 시 Union 으로 확장 (discriminated on `type`)
DiagramSpec = Union[TokenSequenceSpec]


def json_schema() -> dict:
    """AI 에이전트가 형식을 학습할 수 있는 JSON Schema."""
    return TokenSequenceSpec.model_json_schema()
