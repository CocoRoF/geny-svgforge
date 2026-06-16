"""MCP 서버 — AI 에이전트가 좌표 대신 spec 만 내고 깨끗한 SVG 를 받는다.

실행: python -m geny_svgforge.mcp_server   (의존: pip install 'geny-svgforge[mcp]')
"""
from __future__ import annotations

from typing import Any

from .api import render
from .api import validate_spec as _validate
from .spec import json_schema


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("geny-svgforge")

    @mcp.tool()
    def render_diagram(spec: dict[str, Any]) -> dict[str, Any]:
        """다이어그램 spec(JSON)을 깨끗한 SVG 로 렌더한다.

        좌표는 절대 쓰지 말고 get_diagram_schema 의 형식대로 의미만 기술할 것.
        반환: { svg, width, height, warnings[] }. warnings 가 있으면 spec 을 고쳐 다시 호출.
        """
        r = render(spec)
        return {"svg": r.svg, "width": r.width, "height": r.height, "warnings": r.warnings}

    @mcp.tool()
    def validate_diagram_spec(spec: dict[str, Any]) -> dict[str, Any]:
        """렌더 없이 spec 을 검증한다. { ok, errors[], warnings[] }."""
        return _validate(spec)

    @mcp.tool()
    def get_diagram_schema() -> dict[str, Any]:
        """다이어그램 spec 의 JSON Schema(형식·필드 설명)."""
        return json_schema()

    return mcp


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
