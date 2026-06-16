"""geny-svgforge — AI가 의미(spec)만 내면 결정론적 레이아웃으로 깨끗한 다이어그램 SVG를 만든다."""
from __future__ import annotations

from .api import RenderResult, render, to_png, validate_spec
from .spec import (
    Connector,
    GEdge,
    GNode,
    NodeGraphSpec,
    Note,
    Row,
    Token,
    TokenSequenceSpec,
    json_schema,
)

try:
    from importlib.metadata import version as _version

    __version__ = _version("geny-svgforge")
except Exception:  # noqa: BLE001
    __version__ = "0.0.0"
__all__ = [
    "render",
    "to_png",
    "validate_spec",
    "RenderResult",
    "json_schema",
    "NodeGraphSpec",
    "GNode",
    "GEdge",
    "TokenSequenceSpec",
    "Row",
    "Token",
    "Connector",
    "Note",
]
