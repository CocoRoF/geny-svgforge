"""공개 API. AI 에이전트/서버/CLI 가 쓰는 진입점."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from .fonts import EMBED_FAMILY, FONT_FAMILY, default_fonts, subset_b64
from .geometry import TextEl
from .layout import build_scene
from .lint import lint
from .render import render_svg
from .spec import TokenSequenceSpec


@dataclass
class RenderResult:
    svg: str
    width: float
    height: float
    warnings: list[str] = field(default_factory=list)


def _coerce(spec: Union[dict, TokenSequenceSpec]) -> TokenSequenceSpec:
    if isinstance(spec, TokenSequenceSpec):
        return spec
    return TokenSequenceSpec.model_validate(spec)


def _embed_css(scene) -> tuple[str, str]:
    """사용된 글자만 subset 해 base64 @font-face 로 임베드.

    측정에 쓴 폰트를 그대로 임베드하므로 어떤 렌더러에서도 측정==렌더가 성립한다(완전 이식성).
    반환: (font_faces_css, font_family).
    """
    reg, bold = default_fonts()
    reg_chars: set[str] = set()
    bold_chars: set[str] = set()
    for el in scene.elements:
        if isinstance(el, TextEl):
            (bold_chars if el.weight == "bold" else reg_chars).update(el.text)
    css = ""
    if reg_chars:
        b = subset_b64(reg.path, reg.ttc_index, reg_chars)
        if b:
            css += (f"@font-face{{font-family:'{EMBED_FAMILY}';font-weight:400;"
                    f"src:url(data:font/ttf;base64,{b}) format('truetype');}}")
    if bold_chars:
        b = subset_b64(bold.path, bold.ttc_index, bold_chars)
        if b:
            css += (f"@font-face{{font-family:'{EMBED_FAMILY}';font-weight:700;"
                    f"src:url(data:font/ttf;base64,{b}) format('truetype');}}")
    real = default_fonts()[0].family_name
    family = f"'{EMBED_FAMILY}', '{real}', {FONT_FAMILY}" if css else FONT_FAMILY
    return css, family


def render(
    spec: Union[dict, TokenSequenceSpec],
    embed_font: bool = True,
    raster_safe: bool = False,
) -> RenderResult:
    """spec(dict or model) -> 깨끗한 SVG + 린트 경고.

    잘못된 spec 은 pydantic ValidationError 를 던진다(렌더 전 차단).
    - embed_font=True: 사용된 글자를 subset 해 @font-face 로 임베드(브라우저·resvg 에서 완전 이식).
    - raster_safe=True: 임베드 대신 실제 설치 폰트 family 를 우선 지정(cairosvg 등 @font-face 미지원
      래스터라이저에서 CJK 가 깨지지 않게). PNG 내보내기에 사용.
    """
    model = _coerce(spec)
    scene = build_scene(model)
    warnings = lint(scene)
    if raster_safe:
        real = default_fonts()[0].family_name
        svg = render_svg(scene, font_family=f"'{real}', {FONT_FAMILY}")
    elif embed_font:
        css, family = _embed_css(scene)
        svg = render_svg(scene, font_family=family, font_faces_css=css)
    else:
        svg = render_svg(scene)
    return RenderResult(svg=svg, width=scene.width, height=scene.height, warnings=warnings)


def to_png(spec: Union[dict, TokenSequenceSpec], scale: float = 2.0) -> bytes:
    """PNG 바이트. cairosvg 필요(optional dep 'png'). @font-face 미지원 래스터라이저를 위해
    실제 설치 폰트로 렌더한다(설치 폰트가 없으면 resvg + 임베드 SVG 사용 권장)."""
    import cairosvg

    res = render(spec, raster_safe=True)
    return cairosvg.svg2png(
        bytestring=res.svg.encode("utf-8"), output_width=int(res.width * scale)
    )


def validate_spec(spec: dict) -> dict[str, Any]:
    """렌더 없이 spec 만 검증. {ok, errors[], warnings[]}."""
    from pydantic import ValidationError

    try:
        model = _coerce(spec)
    except ValidationError as e:
        return {"ok": False, "errors": e.errors(include_url=False), "warnings": []}
    scene = build_scene(model)
    return {"ok": True, "errors": [], "warnings": lint(scene)}
