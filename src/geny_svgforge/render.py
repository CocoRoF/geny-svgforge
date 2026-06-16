"""Scene(El 리스트) -> SVG 문자열. 렌더러는 레이아웃을 모르고 직렬화만 한다."""
from __future__ import annotations

from xml.sax.saxutils import escape

from .fonts import FONT_FAMILY
from .geometry import PathEl, RectEl, Scene, TextEl


def _fmt(n: float) -> str:
    return f"{n:.2f}".rstrip("0").rstrip(".")


def render_svg(scene: Scene, font_family: str = FONT_FAMILY, font_faces_css: str = "") -> str:
    w, h = scene.width, scene.height
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_fmt(w)} {_fmt(h)}" width="{_fmt(w)}" height="{_fmt(h)}" '
        f'role="img" font-family="{font_family}">',
        f"<style>{font_faces_css}text{{font-family:{font_family};}}</style>",
    ]
    for el in scene.elements:
        if isinstance(el, RectEl):
            out.append(
                f'<rect x="{_fmt(el.x)}" y="{_fmt(el.y)}" width="{_fmt(el.w)}" '
                f'height="{_fmt(el.h)}" rx="{_fmt(el.rx)}" fill="{el.fill}" '
                f'stroke="{el.stroke}" stroke-width="{_fmt(el.stroke_width)}"/>'
            )
        elif isinstance(el, TextEl):
            weight = ' font-weight="700"' if el.weight == "bold" else ""
            out.append(
                f'<text x="{_fmt(el.x)}" y="{_fmt(el.y)}" font-size="{_fmt(el.size)}" '
                f'fill="{el.fill}" text-anchor="{el.anchor}"{weight}>'
                f"{escape(el.text)}</text>"
            )
        elif isinstance(el, PathEl):
            dash = ' stroke-dasharray="6 5"' if el.dashed else ""
            out.append(
                f'<path d="{el.d}" fill="{el.fill}" stroke="{el.stroke}" '
                f'stroke-width="{_fmt(el.stroke_width)}" stroke-linecap="round"{dash}/>'
            )
    out.append("</svg>")
    return "\n".join(out)
