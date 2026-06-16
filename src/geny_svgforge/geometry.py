"""기하 primitive + 렌더 element.

레이아웃 엔진은 spec 을 받아 절대 좌표가 박힌 El 리스트와 캔버스 크기를 만든다.
렌더러는 El 리스트만 SVG 문자열로 직렬화한다(렌더러는 레이아웃을 모른다).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def intersects(self, other: "Rect", pad: float = 0.0) -> bool:
        return not (
            self.right + pad <= other.x
            or other.right + pad <= self.x
            or self.bottom + pad <= other.y
            or other.bottom + pad <= self.y
        )


# ── 렌더 element ────────────────────────────────────────────────
@dataclass
class El:
    """draw element 베이스. bbox() 로 점유 영역을 보고(린트가 사용)."""

    def bbox(self) -> Optional[Rect]:
        return None


@dataclass
class RectEl(El):
    x: float
    y: float
    w: float
    h: float
    rx: float = 0.0
    fill: str = "none"
    stroke: str = "none"
    stroke_width: float = 1.0
    role: str = ""  # "box" 등 — 린트가 충돌 검사 대상 식별에 사용

    def bbox(self) -> Rect:
        return Rect(self.x, self.y, self.w, self.h)


@dataclass
class TextEl(El):
    x: float
    y: float  # baseline y
    text: str
    size: float
    fill: str = "#000"
    weight: Literal["normal", "bold"] = "normal"
    anchor: Literal["start", "middle", "end"] = "start"
    # 텍스트가 차지하는 폭(실측) — 린트/bbox 용
    width: float = 0.0

    def bbox(self) -> Rect:
        if self.anchor == "middle":
            x0 = self.x - self.width / 2
        elif self.anchor == "end":
            x0 = self.x - self.width
        else:
            x0 = self.x
        # baseline 기준 위로 ~0.8em, 아래로 ~0.2em
        return Rect(x0, self.y - self.size * 0.8, self.width, self.size)


@dataclass
class PathEl(El):
    d: str
    stroke: str = "#000"
    stroke_width: float = 2.0
    fill: str = "none"
    # 경로의 대략 bbox (라우팅 시 알고 있음). 린트 정보용.
    approx: Optional[Rect] = None
    dashed: bool = False

    def bbox(self) -> Optional[Rect]:
        return self.approx


@dataclass
class Scene:
    width: float
    height: float
    elements: list[El] = field(default_factory=list)
    bg: str = "#ffffff"
