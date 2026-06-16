"""Scene(El 리스트) -> SVG 문자열. 렌더러는 레이아웃을 모르고 직렬화만 한다."""
from __future__ import annotations

from xml.sax.saxutils import escape

from .fonts import FONT_FAMILY
from .geometry import PathEl, RectEl, Scene, TextEl


def _fmt(n: float) -> str:
    return f"{n:.2f}".rstrip("0").rstrip(".")


def _shape_svg(el: RectEl) -> str:
    """RectEl.shape 에 맞는 SVG 도형 문자열."""
    x, y, w, h = el.x, el.y, el.w, el.h
    cx, cy = x + w / 2, y + h / 2
    paint = f'fill="{el.fill}" stroke="{el.stroke}" stroke-width="{_fmt(el.stroke_width)}"'
    s = el.shape

    if s in ("rect", "pill"):
        rx = h / 2 if s == "pill" else el.rx
        return (f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" height="{_fmt(h)}" '
                f'rx="{_fmt(rx)}" {paint}/>')
    if s == "ellipse":
        return (f'<ellipse cx="{_fmt(cx)}" cy="{_fmt(cy)}" rx="{_fmt(w/2)}" ry="{_fmt(h/2)}" '
                f'{paint}/>')
    if s == "diamond":
        d = (f"M {_fmt(cx)} {_fmt(y)} L {_fmt(x+w)} {_fmt(cy)} "
             f"L {_fmt(cx)} {_fmt(y+h)} L {_fmt(x)} {_fmt(cy)} Z")
        return f'<path d="{d}" {paint} stroke-linejoin="round"/>'
    if s == "hexagon":
        ins = min(w * 0.18, h * 0.5)
        d = (f"M {_fmt(x+ins)} {_fmt(y)} L {_fmt(x+w-ins)} {_fmt(y)} L {_fmt(x+w)} {_fmt(cy)} "
             f"L {_fmt(x+w-ins)} {_fmt(y+h)} L {_fmt(x+ins)} {_fmt(y+h)} L {_fmt(x)} {_fmt(cy)} Z")
        return f'<path d="{d}" {paint} stroke-linejoin="round"/>'
    if s == "parallelogram":
        sk = min(w * 0.18, 24.0)
        d = (f"M {_fmt(x+sk)} {_fmt(y)} L {_fmt(x+w)} {_fmt(y)} "
             f"L {_fmt(x+w-sk)} {_fmt(y+h)} L {_fmt(x)} {_fmt(y+h)} Z")
        return f'<path d="{d}" {paint} stroke-linejoin="round"/>'
    if s == "cylinder":
        ry = min(h * 0.16, 13.0)
        body = (f"M {_fmt(x)} {_fmt(y+ry)} C {_fmt(x)} {_fmt(y)} {_fmt(x+w)} {_fmt(y)} "
                f"{_fmt(x+w)} {_fmt(y+ry)} L {_fmt(x+w)} {_fmt(y+h-ry)} "
                f"C {_fmt(x+w)} {_fmt(y+h)} {_fmt(x)} {_fmt(y+h)} {_fmt(x)} {_fmt(y+h-ry)} Z")
        top = (f"M {_fmt(x)} {_fmt(y+ry)} C {_fmt(x)} {_fmt(y+2*ry)} {_fmt(x+w)} {_fmt(y+2*ry)} "
               f"{_fmt(x+w)} {_fmt(y+ry)}")
        return (f'<path d="{body}" {paint}/>'
                f'<path d="{top}" fill="none" stroke="{el.stroke}" stroke-width="{_fmt(el.stroke_width)}"/>')
    # fallback
    return (f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(w)}" height="{_fmt(h)}" '
            f'rx="{_fmt(el.rx)}" {paint}/>')


def render_svg(scene: Scene, font_family: str = FONT_FAMILY, font_faces_css: str = "") -> str:
    w, h = scene.width, scene.height
    aria = f' aria-label="{escape(scene.title)}"' if scene.title else ' aria-hidden="false"'
    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_fmt(w)} {_fmt(h)}" width="{_fmt(w)}" height="{_fmt(h)}" '
        f'role="img"{aria} font-family="{font_family}">',
    ]
    if scene.title:
        out.append(f"<title>{escape(scene.title)}</title>")
    if scene.desc:
        out.append(f"<desc>{escape(scene.desc)}</desc>")
    out.append(f"<style>{font_faces_css}text{{font-family:{font_family};}}</style>")

    for el in scene.elements:
        if isinstance(el, RectEl):
            out.append(_shape_svg(el))
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
