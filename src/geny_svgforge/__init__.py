"""geny-svgforge — AI가 의미(spec)만 내면 결정론적 레이아웃으로 깨끗한 다이어그램 SVG를 만든다."""
from __future__ import annotations

from .api import RenderResult, render, validate_spec
from .spec import (
    Connector,
    Note,
    Row,
    Token,
    TokenSequenceSpec,
    json_schema,
)

__version__ = "0.1.0"
__all__ = [
    "render",
    "validate_spec",
    "RenderResult",
    "json_schema",
    "TokenSequenceSpec",
    "Row",
    "Token",
    "Connector",
    "Note",
]
