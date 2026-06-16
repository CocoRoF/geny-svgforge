"""색·간격 토큰. 첨부 예시의 팔레트를 라이트 테마로 재현하고, 다크 테마도 제공."""
from __future__ import annotations

LIGHT = {
    "bg": "#ffffff",
    "card_stroke": "#e6e8f0",
    "title": "#1e2340",
    "subtitle": "#6b7280",
    "row_label": "#3b4252",
    "pos_label": "#9aa0ad",
    "caption": "#9aa0ad",
    "connector_accent": "#f5a623",
    "connector_blue": "#5b8def",
    "connector_gray": "#9aa0ad",
    "connector_good": "#22a06b",
    "col_label": "#6b7280",
    "note_bg": "#f7f8fc",
    "note_stroke": "#e6e8f0",
    "note_title": "#1e2340",
    "note_text": "#6b7280",
    # 박스 variant: (fill, stroke, text)
    "token_default": ("#eef2fe", "#9db8f0", "#2b3a67"),
    "token_accent": ("#f1ecfe", "#b9a6f0", "#4a3a7a"),
    "token_highlight": ("#fff7ec", "#f5a623", "#b06d12"),
    "token_muted": ("#f3f4f7", "#d7dae2", "#8a8f98"),
    "token_good": ("#eafaf0", "#7fcf9f", "#1f7a4d"),
}

DARK = {
    "bg": "#15172a",
    "card_stroke": "#2a2d4a",
    "title": "#eef0ff",
    "subtitle": "#a6acc4",
    "row_label": "#c7cce0",
    "pos_label": "#8086a0",
    "caption": "#8086a0",
    "connector_accent": "#f5a623",
    "connector_blue": "#6f9bf0",
    "connector_gray": "#8086a0",
    "connector_good": "#34d399",
    "col_label": "#a6acc4",
    "note_bg": "#1c1f36",
    "note_stroke": "#2a2d4a",
    "note_title": "#eef0ff",
    "note_text": "#a6acc4",
    "token_default": ("#23284a", "#3f4a82", "#cdd6f7"),
    "token_accent": ("#2c2550", "#5a4a9a", "#d7cdf7"),
    "token_highlight": ("#3a2e1c", "#f5a623", "#f3c98a"),
    "token_muted": ("#222539", "#363a55", "#8086a0"),
    "token_good": ("#1e3a2c", "#3f7a5a", "#bfe8cf"),
}


def get_theme(name: str) -> dict:
    return DARK if name == "dark" else LIGHT
