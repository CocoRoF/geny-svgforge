"""폰트 해석 + 텍스트 폭 실측.

레이아웃 품질의 핵심. LLM 이 못 하는 '텍스트가 실제로 몇 px 인가'를 폰트의 glyph advance 로
정확히 계산한다. 측정에 쓴 폰트를 SVG font-family 로 그대로 지정하므로 측정 == 렌더가 성립한다.

브라우저/헤드리스 의존 없이 fontTools 만으로 동작한다(an-web 계보).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from fontTools.ttLib import TTCollection, TTFont

# 시스템에서 흔히 발견되는 한글 지원 폰트 후보. 첫 번째로 존재하는 것을 쓴다.
# (override: GENY_SVGFORGE_FONT / GENY_SVGFORGE_FONT_BOLD 환경변수)
_REGULAR_CANDIDATES = [
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK KR"),
    ("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf", "Noto Sans KR"),
    ("/System/Library/Fonts/AppleSDGothicNeo.ttc", "Apple SD Gothic Neo"),
    ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "NanumGothic"),
]
_BOLD_CANDIDATES = [
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "Noto Sans CJK KR"),
    ("/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf", "Noto Sans KR"),
]

# SVG 에 들어갈 font-family (측정 폰트 + 안전한 폴백)
FONT_FAMILY = "Noto Sans KR, Noto Sans CJK KR, Apple SD Gothic Neo, NanumGothic, sans-serif"


def _resolve(candidates, env_key) -> tuple[str, str]:
    override = os.environ.get(env_key)
    if override and os.path.exists(override):
        return override, ""
    for path, family in candidates:
        if os.path.exists(path):
            return path, family
    raise FileNotFoundError(
        "한글 지원 폰트를 찾지 못했습니다. GENY_SVGFORGE_FONT 환경변수로 .ttf/.otf 경로를 지정하세요."
    )


def _ttc_index_for_family(path: str, family_hint: str) -> int:
    """TTC 안에서 family 이름이 일치하는(그리고 Mono 가 아닌) subfont 인덱스를 찾는다."""
    if not path.lower().endswith(".ttc"):
        return 0
    coll = TTCollection(path, lazy=True)
    try:
        best = 0
        for i, f in enumerate(coll.fonts):
            name = (f["name"].getDebugName(1) or "")
            if family_hint and family_hint in name and "Mono" not in name:
                return i
        return best
    finally:
        coll.close()


@dataclass
class FontMetrics:
    """주어진 폰트로 텍스트 폭/높이를 실측."""

    path: str
    ttc_index: int
    family_name: str
    _font: TTFont
    _cmap: dict
    _advances: dict
    upm: int
    _fallback_adv: int

    @classmethod
    def load(cls, path: str, family_hint: str = "") -> "FontMetrics":
        idx = _ttc_index_for_family(path, family_hint)
        font = TTFont(path, fontNumber=idx, lazy=True)
        cmap = font.getBestCmap()
        hmtx = font["hmtx"]
        advances = {gname: aw for gname, (aw, _lsb) in hmtx.metrics.items()}
        upm = font["head"].unitsPerEm
        # 글자를 못 찾을 때의 보수적 폭 (CJK 기준 약 1em)
        fallback = advances.get(font.getGlyphName(0), upm)
        family = font["name"].getDebugName(1) or family_hint or "sans-serif"
        return cls(path, idx, family, font, cmap, advances, upm, fallback)

    def text_width(self, text: str, size: float) -> float:
        if not text:
            return 0.0
        total = 0
        cmap = self._cmap
        adv = self._advances
        for ch in text:
            gname = cmap.get(ord(ch))
            total += adv.get(gname, self._fallback_adv) if gname else self._fallback_adv
        return total * size / self.upm

    @property
    def ascent(self) -> float:
        try:
            return self._font["hhea"].ascent / self.upm
        except Exception:
            return 0.8

    @property
    def descent(self) -> float:
        try:
            return abs(self._font["hhea"].descent) / self.upm
        except Exception:
            return 0.2

    def line_height(self, size: float) -> float:
        return (self.ascent + self.descent) * size


def subset_b64(path: str, ttc_index: int, chars: set[str]) -> str:
    """주어진 폰트에서 사용된 글자만 subset 해 base64 TTF 로 반환.

    측정에 쓰는 캐시 폰트를 건드리지 않도록 매번 새로 로드한다(subset 은 in-place).
    """
    if not chars:
        return ""
    from io import BytesIO

    from fontTools.subset import Options, Subsetter

    font = TTFont(path, fontNumber=ttc_index, lazy=False)
    opt = Options()
    opt.glyph_names = False
    opt.notdef_outline = True
    opt.recalc_timestamp = False
    opt.drop_tables += ["FFTM"]
    ss = Subsetter(options=opt)
    ss.populate(unicodes=sorted({ord(c) for c in chars}))
    ss.subset(font)
    buf = BytesIO()
    font.save(buf)
    font.close()
    import base64

    return base64.b64encode(buf.getvalue()).decode("ascii")


EMBED_FAMILY = "GenySVGForge"


@lru_cache(maxsize=4)
def default_fonts() -> tuple[FontMetrics, FontMetrics]:
    """(regular, bold) FontMetrics. bold 가 없으면 regular 로 대체."""
    rpath, rfam = _resolve(_REGULAR_CANDIDATES, "GENY_SVGFORGE_FONT")
    reg = FontMetrics.load(rpath, rfam)
    try:
        bpath, bfam = _resolve(_BOLD_CANDIDATES, "GENY_SVGFORGE_FONT_BOLD")
        bold = FontMetrics.load(bpath, bfam)
    except FileNotFoundError:
        bold = reg
    return reg, bold
