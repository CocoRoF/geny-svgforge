"""레이아웃 엔진 (token-sequence).

spec -> 절대 좌표가 박힌 El 리스트 + 캔버스 크기(Scene).
모든 좌표는 폰트 실측으로 계산하고, 마지막에 전체 내용의 bbox 로 캔버스를 확정하므로
요소 겹침/캔버스 클리핑이 구조적으로 발생할 수 없다.
"""
from __future__ import annotations

from .fonts import FontMetrics, default_fonts
from .geometry import PathEl, Rect, RectEl, Scene, TextEl
from .spec import TokenSequenceSpec
from .themes import get_theme

PAD = 28          # 카드 안쪽 외곽 여백
BOX_PAD_X = 16
BOX_MIN_W = 52
TOKEN_GAP = 14
BOX_RX = 9
NOTE_W = 248
NOTE_PAD = 18
COL_GAP = 40      # 행 블록과 노트 사이
ARC_DIP = 10      # 커넥터가 아래로 굽는 깊이


def _wrap(text: str, max_w: float, fm: FontMetrics, size: float) -> list[str]:
    """단어 단위로 줄바꿈. 한 단어가 너무 길면 글자 단위로 끊는다."""
    if fm.text_width(text, size) <= max_w:
        return [text]
    out: list[str] = []
    words = text.split(" ")
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if fm.text_width(trial, size) <= max_w:
            cur = trial
            continue
        if cur:
            out.append(cur)
            cur = ""
        # 단어 자체가 너무 길면 글자 단위
        if fm.text_width(w, size) > max_w:
            piece = ""
            for ch in w:
                if fm.text_width(piece + ch, size) <= max_w:
                    piece += ch
                else:
                    out.append(piece)
                    piece = ch
            cur = piece
        else:
            cur = w
    if cur:
        out.append(cur)
    return out


def layout_token_sequence(spec: TokenSequenceSpec) -> Scene:
    reg, bold = default_fonts()
    th = get_theme(spec.theme)
    fs = float(spec.font_size)

    title_sz = round(fs * 1.5)
    subtitle_sz = max(11, round(fs - 2))
    rowlabel_sz = max(11, round(fs - 2))
    pos_sz = max(10, round(fs - 4))
    caption_sz = max(11, round(fs - 2))
    note_title_sz = round(fs)
    note_text_sz = max(11, round(fs - 2))
    box_h = round(fs + 20)

    els: list = []

    # 세로 커서. 좌표는 (0,0) 기준 임시 배치 후, 마지막에 캔버스 확정.
    y = PAD

    if spec.title:
        w = bold.text_width(spec.title, title_sz)
        els.append(TextEl(PAD, y + title_sz * 0.82, spec.title, title_sz,
                          th["title"], "bold", "start", w))
        y += title_sz * 1.25
    if spec.subtitle:
        w = reg.text_width(spec.subtitle, subtitle_sz)
        els.append(TextEl(PAD, y + subtitle_sz * 0.82, spec.subtitle, subtitle_sz,
                          th["subtitle"], "normal", "start", w))
        y += subtitle_sz * 1.7

    y += fs * 0.8  # 헤더와 첫 행 사이

    rows_top = y
    id_to_box: dict[str, Rect] = {}
    rows_right = PAD

    has_pos = any(t.pos for r in spec.rows for t in r.tokens)

    for ri, row in enumerate(spec.rows):
        # 행 라벨 (박스 위, 왼쪽)
        if row.label:
            w = reg.text_width(row.label, rowlabel_sz)
            els.append(TextEl(PAD, y + rowlabel_sz * 0.82, row.label, rowlabel_sz,
                              th["row_label"], "normal", "start", w))
            y += rowlabel_sz * 1.55

        box_top = y
        x = PAD
        boxes_this_row: list[tuple[Rect, str]] = []
        for tok in row.tokens:
            tw = reg.text_width(tok.text, fs)
            bw = max(BOX_MIN_W, tw + BOX_PAD_X * 2)
            r = Rect(x, box_top, bw, box_h)
            fill, stroke, txt = th[f"token_{tok.variant}"]
            els.append(RectEl(r.x, r.y, r.w, r.h, BOX_RX, fill, stroke, 1.6, role="box"))
            els.append(TextEl(r.cx, r.cy + fs * 0.34, tok.text, fs, txt,
                              "normal", "middle", tw))
            if tok.id:
                id_to_box[tok.id] = r
            boxes_this_row.append((r, tok.pos or ""))
            x += bw + TOKEN_GAP

        rows_right = max(rows_right, x - TOKEN_GAP)
        y = box_top + box_h

        # pos 라벨 (박스 아래, 가운데)
        if has_pos:
            y += pos_sz + 6
            for r, pos in boxes_this_row:
                if pos:
                    w = reg.text_width(pos, pos_sz)
                    els.append(TextEl(r.cx, y, pos, pos_sz, th["pos_label"],
                                      "normal", "middle", w))
            y += 4

        # 행 사이 간격 (커넥터가 그려질 띠)
        if ri < len(spec.rows) - 1:
            y += fs * 2.2

    rows_bottom = y

    # ── 커넥터 (행 사이 띠에 그림) ──
    for c in spec.connectors:
        a = id_to_box.get(c.from_)
        b = id_to_box.get(c.to)
        if not a or not b:
            continue
        # 위/아래 박스 판별
        top_box, bot_box = (a, b) if a.cy <= b.cy else (b, a)
        x1, y1 = top_box.cx, top_box.bottom
        x2, y2 = bot_box.cx, bot_box.y
        # pos 라벨 영역을 피해 살짝 내려서 시작
        y1o = y1 + (pos_sz + 10 if has_pos else 6)
        midy = (y1o + y2) / 2 + ARC_DIP
        d = f"M {x1:.1f} {y1o:.1f} C {x1:.1f} {midy:.1f}, {x2:.1f} {midy:.1f}, {x2:.1f} {y2:.1f}"
        col = th[f"connector_{c.color}"]
        lo_x, hi_x = min(x1, x2), max(x1, x2)
        approx = Rect(lo_x, y1o, hi_x - lo_x, max(1.0, midy - y1o))
        els.append(PathEl(d, col, 2.4, "none", approx))
        if c.arrow:
            # 끝점에 작은 삼각형
            s = 5
            tri = f"M {x2-s:.1f} {y2-s*1.6:.1f} L {x2+s:.1f} {y2-s*1.6:.1f} L {x2:.1f} {y2:.1f} Z"
            els.append(PathEl(tri, col, 0.0, col, Rect(x2 - s, y2 - s * 1.6, 2 * s, s * 1.6)))

    # ── 노트 (오른쪽 사이드바) ──
    content_bottom = rows_bottom
    if spec.note:
        inner = NOTE_W - NOTE_PAD * 2
        wrapped: list[tuple[str, float, str, str]] = []  # (text, size, color, weight)
        if spec.note.title:
            wrapped.append((spec.note.title, note_title_sz, th["note_title"], "bold"))
        for ln in spec.note.lines:
            for piece in _wrap(ln, inner, reg, note_text_sz):
                wrapped.append((piece, note_text_sz, th["note_text"], "normal"))
        # 높이 계산
        h = NOTE_PAD
        line_ys: list[float] = []
        for i, (_t, sz, _c, _w) in enumerate(wrapped):
            h += sz * (1.7 if i else 1.0)
            line_ys.append(h)
        h += NOTE_PAD - note_text_sz * 0.2
        note_w = NOTE_W
        note_x = rows_right + COL_GAP
        note_y = rows_top + max(0, (rows_bottom - rows_top - h) / 2)
        els.append(RectEl(note_x, note_y, note_w, h, 14, th["note_bg"],
                          th["note_stroke"], 1.4))
        for (t, sz, c, weight), ly in zip(wrapped, line_ys):
            fm = bold if weight == "bold" else reg
            w = fm.text_width(t, sz)
            els.append(TextEl(note_x + NOTE_PAD, note_y + ly, t, sz, c, weight, "start", w))
        content_bottom = max(content_bottom, note_y + h)
        right_edge = note_x + note_w
    else:
        right_edge = rows_right

    # ── 캡션 (맨 아래, 가운데) ──
    # 캔버스 폭을 먼저 잠정 확정 (캡션 가운데 정렬에 필요)
    title_w = els[0].bbox().right if (spec.title and els) else 0
    canvas_w = max(right_edge, title_w) + PAD
    canvas_w = max(canvas_w, PAD * 2 + 200)

    y = content_bottom
    if spec.caption:
        y += fs * 1.4
        w = reg.text_width(spec.caption, caption_sz)
        els.append(TextEl(canvas_w / 2, y, spec.caption, caption_sz, th["caption"],
                          "normal", "middle", w))
        y += caption_sz * 0.4

    canvas_h = y + PAD

    # 카드 배경을 맨 뒤에 삽입
    card = RectEl(0.5, 0.5, canvas_w - 1, canvas_h - 1, 18, th["bg"],
                  th["card_stroke"], 1.0)
    return Scene(canvas_w, canvas_h, [card, *els], bg=th["bg"])


def build_scene(spec: TokenSequenceSpec) -> Scene:
    if spec.type == "token-sequence":
        return layout_token_sequence(spec)
    raise ValueError(f"지원하지 않는 다이어그램 타입: {spec.type}")
