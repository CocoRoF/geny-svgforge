"""레이아웃 엔진.

spec(node-graph) → 절대 좌표가 박힌 El 리스트 + 캔버스 크기(Scene).

일반화된 그리드 모델: 노드를 (row, col) 그리드에 놓고, 같은 col 은 세로로 정렬한다.
edge 는 두 노드의 마주보는 면(anchor)을 골라 **경계 내부로 한정된 cubic** 으로 잇는다
→ 곡선이 끝점이 만드는 사각형 밖으로 절대 튀어나가지 않는다(overshoot/박스 관통 불가).
모든 요소의 bbox 로 캔버스를 확정하므로 클리핑도 불가능하다.
"""
from __future__ import annotations

from .fonts import FontMetrics, default_fonts
from .geometry import PathEl, Rect, RectEl, Scene, TextEl
from .spec import NodeGraphSpec, TokenSequenceSpec
from .themes import get_theme

PAD = 28
BOX_PAD_X = 16
BOX_MIN_W = 52
COL_GAP = 24
BOX_RX = 9
NOTE_W = 248
NOTE_PAD = 18
SIDE_GAP = 40


def _wrap(text: str, max_w: float, fm: FontMetrics, size: float) -> list[str]:
    if fm.text_width(text, size) <= max_w:
        return [text]
    out: list[str] = []
    cur = ""
    for w in text.split(" "):
        trial = w if not cur else cur + " " + w
        if fm.text_width(trial, size) <= max_w:
            cur = trial
            continue
        if cur:
            out.append(cur)
            cur = ""
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


def _arrow_head(x: float, y: float, dir_: str, color: str, s: float = 5.0) -> PathEl:
    if dir_ == "down":
        d = f"M {x-s:.1f} {y-s*1.7:.1f} L {x+s:.1f} {y-s*1.7:.1f} L {x:.1f} {y:.1f} Z"
    elif dir_ == "up":
        d = f"M {x-s:.1f} {y+s*1.7:.1f} L {x+s:.1f} {y+s*1.7:.1f} L {x:.1f} {y:.1f} Z"
    elif dir_ == "right":
        d = f"M {x-s*1.7:.1f} {y-s:.1f} L {x-s*1.7:.1f} {y+s:.1f} L {x:.1f} {y:.1f} Z"
    else:  # left
        d = f"M {x+s*1.7:.1f} {y-s:.1f} L {x+s*1.7:.1f} {y+s:.1f} L {x:.1f} {y:.1f} Z"
    return PathEl(d, color, 0.0, color, Rect(x - s * 1.7, y - s * 1.7, s * 3.4, s * 3.4))


def layout_node_graph(spec: NodeGraphSpec) -> Scene:
    reg, bold = default_fonts()
    th = get_theme(spec.theme)
    fs = float(spec.font_size)

    title_sz = round(fs * 1.5)
    sub_sz = max(11, round(fs - 2))
    rl_sz = max(11, round(fs - 2))
    col_sz = max(11, round(fs - 2))
    slab_sz = max(10, round(fs - 4))
    caption_sz = max(11, round(fs - 2))
    note_title_sz = round(fs)
    note_text_sz = max(11, round(fs - 2))
    box_h0 = round(fs + 20)
    line_h = fs * 1.25
    slab_zone = slab_sz + 8

    nodes = spec.nodes
    nrows = max(n.row for n in nodes) + 1
    ncols = max(n.col for n in nodes) + 1

    # 노드 측정
    cell: dict[tuple[int, int], dict] = {}
    for n in nodes:
        lines = n.text.split("\n")
        tw = max((reg.text_width(ln, fs) for ln in lines), default=0)
        w = max(BOX_MIN_W, tw + BOX_PAD_X * 2)
        h = box_h0 + (len(lines) - 1) * line_h
        cell[(n.row, n.col)] = {"node": n, "lines": lines, "w": w, "h": h}

    col_w = [BOX_MIN_W] * ncols
    row_h = [float(box_h0)] * nrows
    row_has_sub = [False] * nrows
    for (r, c), info in cell.items():
        col_w[c] = max(col_w[c], info["w"])
        row_h[r] = max(row_h[r], info["h"])
        if info["node"].sublabel:
            row_has_sub[r] = True

    rl_w = 0.0
    if spec.row_labels:
        rl_w = max(reg.text_width(t, rl_sz) for t in spec.row_labels.values()) + 16

    els: list = []
    y = PAD
    if spec.title:
        w = bold.text_width(spec.title, title_sz)
        els.append(TextEl(PAD, y + title_sz * 0.82, spec.title, title_sz, th["title"], "bold", "start", w))
        y += title_sz * 1.25
    if spec.subtitle:
        w = reg.text_width(spec.subtitle, sub_sz)
        els.append(TextEl(PAD, y + sub_sz * 0.82, spec.subtitle, sub_sz, th["subtitle"], "normal", "start", w))
        y += sub_sz * 1.7
    y += fs * 0.6

    grid_x0 = PAD + rl_w
    col_x = []
    x = grid_x0
    for c in range(ncols):
        col_x.append(x)
        x += col_w[c] + COL_GAP
    grid_right = x - COL_GAP

    # 열 라벨 (위)
    if spec.col_labels:
        for c, lbl in spec.col_labels.items():
            if 0 <= c < ncols:
                w = reg.text_width(lbl, col_sz)
                els.append(TextEl(col_x[c] + col_w[c] / 2, y + col_sz * 0.82, lbl, col_sz, th["col_label"], "normal", "middle", w))
        y += col_sz * 1.7

    grid_top = y
    row_top = [0.0] * nrows
    row_bottom = [0.0] * nrows
    id_rect: dict[str, Rect] = {}
    id_row: dict[str, int] = {}
    id_col: dict[str, int] = {}
    ROW_GAP = fs * 2.0

    cur = y
    for r in range(nrows):
        row_top[r] = cur
        bh = row_h[r]
        if r in spec.row_labels:
            w = reg.text_width(spec.row_labels[r], rl_sz)
            els.append(TextEl(PAD, cur + bh / 2 + rl_sz * 0.34, spec.row_labels[r], rl_sz, th["row_label"], "normal", "start", w))
        for c in range(ncols):
            info = cell.get((r, c))
            if not info:
                continue
            n, lines, w, h = info["node"], info["lines"], info["w"], info["h"]
            bx = col_x[c] + (col_w[c] - w) / 2
            box = Rect(bx, cur, w, h)
            fill, stroke, txt = th[f"token_{n.variant}"]
            els.append(RectEl(box.x, box.y, box.w, box.h, BOX_RX, fill, stroke, 1.6, role="box"))
            n_lines = len(lines)
            for li, ln in enumerate(lines):
                lw = reg.text_width(ln, fs)
                ly = box.cy - (n_lines - 1) * line_h / 2 + li * line_h + fs * 0.34
                els.append(TextEl(box.cx, ly, ln, fs, txt, "normal", "middle", lw))
            if n.id:
                id_rect[n.id] = box
                id_row[n.id] = r
                id_col[n.id] = c
            if n.sublabel:
                sw = reg.text_width(n.sublabel, slab_sz)
                els.append(TextEl(box.cx, cur + bh + slab_sz + 2, n.sublabel, slab_sz, th["pos_label"], "normal", "middle", sw))
        row_bottom[r] = cur + bh + (slab_zone if row_has_sub[r] else 0)
        cur = row_bottom[r] + ROW_GAP
    grid_bottom = cur - ROW_GAP

    # ── edges (경계 내부 한정 라우팅) ──
    for e in spec.edges:
        a = id_rect.get(e.from_)
        b = id_rect.get(e.to)
        if not a or not b:
            continue
        col = th[f"connector_{e.color}"]
        dx = b.cx - a.cx
        dy = b.cy - a.cy
        rs, rt = id_row.get(e.from_, 0), id_row.get(e.to, 0)
        lane = None
        if abs(dy) >= abs(dx):  # 세로
            if dy >= 0:  # b 가 아래
                sx, sy = a.cx, row_bottom[rs]
                ex, ey = b.cx, b.y
                end_dir = "down"
            else:        # b 가 위
                sx, sy = a.cx, a.y
                ex, ey = b.cx, row_bottom[rt]
                end_dir = "up"
            if abs(rt - rs) >= 2:
                # 중간 행을 건너뛰는 edge → 열 옆 빈 레인으로 우회 (박스 관통 방지)
                lane = max(a.right, b.right) + COL_GAP * 0.5
                seg = ey - sy
                d = (f"M {sx:.1f} {sy:.1f} "
                     f"C {sx:.1f} {sy + 24:.1f}, {lane:.1f} {sy + 8:.1f}, {lane:.1f} {sy + 34:.1f} "
                     f"L {lane:.1f} {ey - 34:.1f} "
                     f"C {lane:.1f} {ey - 8:.1f}, {ex:.1f} {ey - 24:.1f}, {ex:.1f} {ey:.1f}") \
                    if seg > 80 else \
                    f"M {sx:.1f} {sy:.1f} C {lane:.1f} {sy:.1f}, {lane:.1f} {ey:.1f}, {ex:.1f} {ey:.1f}"
            else:
                my = (sy + ey) / 2
                d = f"M {sx:.1f} {sy:.1f} C {sx:.1f} {my:.1f}, {ex:.1f} {my:.1f}, {ex:.1f} {ey:.1f}"
        else:                   # 가로
            if dx >= 0:
                sx, sy = a.right, a.cy
                ex, ey = b.x, b.cy
                end_dir = "right"
            else:
                sx, sy = a.x, a.cy
                ex, ey = b.right, b.cy
                end_dir = "left"
            mx = (sx + ex) / 2
            d = f"M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ey:.1f}, {ex:.1f} {ey:.1f}"
        xs = [sx, ex] + ([lane] if lane is not None else [])
        lo_x, hi_x = min(xs), max(xs)
        lo_y, hi_y = min(sy, ey), max(sy, ey)
        approx = Rect(lo_x, lo_y, max(1.0, hi_x - lo_x), max(1.0, hi_y - lo_y))
        els.append(PathEl(d, col, 2.4, "none", approx, dashed=e.dashed))
        if e.arrow:
            els.append(_arrow_head(ex, ey, end_dir, col))

    content_bottom = grid_bottom
    right_edge = grid_right

    # ── note 사이드바 ──
    if spec.note:
        inner = NOTE_W - NOTE_PAD * 2
        wrapped: list[tuple[str, float, str, str]] = []
        if spec.note.title:
            wrapped.append((spec.note.title, note_title_sz, th["note_title"], "bold"))
        for ln in spec.note.lines:
            for piece in _wrap(ln, inner, reg, note_text_sz):
                wrapped.append((piece, note_text_sz, th["note_text"], "normal"))
        h = NOTE_PAD
        line_ys = []
        for i, (_t, sz, _c, _w) in enumerate(wrapped):
            h += sz * (1.7 if i else 1.0)
            line_ys.append(h)
        h += NOTE_PAD - note_text_sz * 0.2
        note_x = grid_right + SIDE_GAP
        note_y = grid_top + max(0, (grid_bottom - grid_top - h) / 2)
        els.append(RectEl(note_x, note_y, NOTE_W, h, 14, th["note_bg"], th["note_stroke"], 1.4))
        for (t, sz, c, weight), ly in zip(wrapped, line_ys):
            fm = bold if weight == "bold" else reg
            w = fm.text_width(t, sz)
            els.append(TextEl(note_x + NOTE_PAD, note_y + ly, t, sz, c, weight, "start", w))
        content_bottom = max(content_bottom, note_y + h)
        right_edge = note_x + NOTE_W

    title_w = els[0].bbox().right if (spec.title and els) else 0
    canvas_w = max(right_edge, title_w) + PAD
    canvas_w = max(canvas_w, PAD * 2 + 200)

    y = content_bottom
    if spec.caption:
        y += fs * 1.4
        w = reg.text_width(spec.caption, caption_sz)
        els.append(TextEl(canvas_w / 2, y, spec.caption, caption_sz, th["caption"], "normal", "middle", w))
        y += caption_sz * 0.4
    canvas_h = y + PAD

    card = RectEl(0.5, 0.5, canvas_w - 1, canvas_h - 1, 18, th["bg"], th["card_stroke"], 1.0)
    return Scene(canvas_w, canvas_h, [card, *els], bg=th["bg"])


def build_scene(spec) -> Scene:
    if isinstance(spec, TokenSequenceSpec) or getattr(spec, "type", None) == "token-sequence":
        spec = spec.to_node_graph()
    if isinstance(spec, NodeGraphSpec) or getattr(spec, "type", None) == "node-graph":
        return layout_node_graph(spec)
    raise ValueError(f"지원하지 않는 다이어그램 타입: {getattr(spec, 'type', spec)}")
