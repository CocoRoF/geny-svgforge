"""레이아웃 엔진.

spec → 절대 좌표가 박힌 El 리스트 + 캔버스 크기(Scene).

- node-graph: 노드를 (row, col) 그리드에 놓는다(align="grid": 같은 col 세로 정렬).
- flow: edge 그래프로 layer 를 자동 산출해 배치한다(align="center": layer 마다 가운데 정렬).
edge 는 두 노드의 마주보는 면을 골라 **끝점이 만드는 사각형 내부로 한정된 cubic** 으로 잇는다
→ overshoot / 박스 관통 불가. 여러 행을 건너뛰는 edge 는 빈 열-갭 레인으로 우회한다.
모든 요소의 bbox 로 캔버스를 확정하므로 클리핑도 불가능하다.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from .fonts import FontMetrics, default_fonts
from .geometry import PathEl, Rect, RectEl, Scene, TextEl
from .spec import FlowSpec, GNode, NodeGraphSpec, TokenSequenceSpec
from .themes import get_theme

PAD = 28
BOX_PAD_X = 16
BOX_MIN_W = 52
MAX_NODE_W = 240   # 노드 텍스트가 이보다 넓으면 자동 줄바꿈
COL_GAP = 24
BOX_RX = 9
NOTE_W = 248
NOTE_PAD = 18
SIDE_GAP = 40
GROUP_PAD = 15


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


def _shape_metrics(shape: str, w: float, h: float) -> tuple[float, float]:
    """도형 안에 텍스트가 들어가도록 외곽 박스 크기를 보정."""
    if shape == "pill":
        return w + 12, h
    if shape == "ellipse":
        return w * 1.35, h * 1.28
    if shape == "diamond":
        return w * 1.5, h * 1.5
    if shape == "hexagon":
        return w * 1.25, h + 6
    if shape == "parallelogram":
        return w + min(w * 0.4, 48), h
    if shape == "cylinder":
        return w, h + 22
    return w, h


def _parse_hex(c: str):
    if not c.startswith("#"):
        return None
    h = c[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _contrast_text(c: str) -> str:
    rgb = _parse_hex(c)
    if not rgb:
        return "#15172a"
    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
    return "#15172a" if lum > 0.6 else "#ffffff"


def _darken(c: str, f: float = 0.72) -> str:
    rgb = _parse_hex(c)
    if not rgb:
        return c
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v * f))) for v in rgb)


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


def layout_node_graph(spec: NodeGraphSpec, align: str = "grid") -> Scene:
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

    # 노드 측정 (도형 보정 포함)
    cell: dict[tuple[int, int], dict] = {}
    for n in nodes:
        lines: list[str] = []
        for raw in n.text.split("\n"):
            lines.extend(_wrap(raw, MAX_NODE_W, reg, fs) if raw else [""])
        tw = max((reg.text_width(ln, fs) for ln in lines), default=0)
        w = max(BOX_MIN_W, tw + BOX_PAD_X * 2)
        h = box_h0 + (len(lines) - 1) * line_h
        w, h = _shape_metrics(n.shape, w, h)
        cell[(n.row, n.col)] = {"node": n, "lines": lines, "w": w, "h": h, "shape": n.shape}

    row_h = [float(box_h0)] * nrows
    row_has_sub = [False] * nrows
    for (r, c), info in cell.items():
        row_h[r] = max(row_h[r], info["h"])
        if info["node"].sublabel:
            row_has_sub[r] = True

    rl_w = 0.0
    if spec.row_labels:
        rl_w = max(reg.text_width(t, rl_sz) for t in spec.row_labels.values()) + 16

    groups = list(getattr(spec, "groups", []) or [])
    group_inset = GROUP_PAD if groups else 0.0
    grid_x0 = PAD + group_inset + rl_w

    # 열 좌표 산출 — grid: col 정렬 / center: 행마다 가운데 정렬
    if align == "grid":
        col_w = [BOX_MIN_W] * ncols
        for (r, c), info in cell.items():
            col_w[c] = max(col_w[c], info["w"])
        col_x = []
        x = grid_x0
        for c in range(ncols):
            col_x.append(x)
            x += col_w[c] + COL_GAP
        grid_right = x - COL_GAP
        content_w = grid_right - grid_x0
    else:
        row_pack: dict[int, float] = {}
        for r in range(nrows):
            ws = [cell[(r, c)]["w"] for c in range(ncols) if (r, c) in cell]
            row_pack[r] = sum(ws) + COL_GAP * max(0, len(ws) - 1)
        content_w = max(row_pack.values()) if row_pack else BOX_MIN_W
        grid_right = grid_x0 + content_w

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
    if groups:
        y += GROUP_PAD + slab_sz   # 그룹 상단 테두리 + 라벨 공간 확보

    # 열 라벨 (위) — grid 모드만
    if align == "grid" and spec.col_labels:
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
    ROW_GAP = fs * 2.0

    node_start_idx = len(els)   # 그룹 박스를 노드 뒤에 삽입할 위치
    cur = y
    for r in range(nrows):
        row_top[r] = cur
        bh = row_h[r]
        if r in spec.row_labels:
            w = reg.text_width(spec.row_labels[r], rl_sz)
            els.append(TextEl(PAD, cur + bh / 2 + rl_sz * 0.34, spec.row_labels[r], rl_sz, th["row_label"], "normal", "start", w))
        present = sorted(c for (rr, c) in cell if rr == r)
        if align == "center":
            xcur = grid_x0 + (content_w - row_pack[r]) / 2
        for c in present:
            info = cell[(r, c)]
            n, lines, w, h, shape = info["node"], info["lines"], info["w"], info["h"], info["shape"]
            if align == "grid":
                bx = col_x[c] + (col_w[c] - w) / 2
            else:
                bx = xcur
                xcur += w + COL_GAP
            box = Rect(bx, cur + (bh - h) / 2, w, h)
            if n.color:
                fill, stroke, txt = n.color, _darken(n.color), (n.text_color or _contrast_text(n.color))
            else:
                fill, stroke, txt = th[f"token_{n.variant}"]
                if n.text_color:
                    txt = n.text_color
            els.append(RectEl(box.x, box.y, box.w, box.h, BOX_RX, fill, stroke, 1.6, role="box", shape=shape))
            n_lines = len(lines)
            ty_off = 6 if shape == "cylinder" else 0
            for li, ln in enumerate(lines):
                lw = reg.text_width(ln, fs)
                ly = box.cy - (n_lines - 1) * line_h / 2 + li * line_h + fs * 0.34 + ty_off
                els.append(TextEl(box.cx, ly, ln, fs, txt, "normal", "middle", lw))
            if n.id:
                id_rect[n.id] = box
                id_row[n.id] = r
            if n.sublabel:
                sw = reg.text_width(n.sublabel, slab_sz)
                els.append(TextEl(box.cx, cur + bh + slab_sz + 2, n.sublabel, slab_sz, th["pos_label"], "normal", "middle", sw))
        row_bottom[r] = cur + bh + (slab_zone if row_has_sub[r] else 0)
        cur = row_bottom[r] + ROW_GAP
    grid_bottom = cur - ROW_GAP

    # ── 그룹 컨테이너 (멤버 노드 bbox 를 감싸 노드 뒤에 삽입) ──
    if groups:
        gels: list = []
        for grp in groups:
            rects = [id_rect[n] for n in grp.nodes if n in id_rect]
            if not rects:
                continue
            minx = min(r.x for r in rects)
            miny = min(r.y for r in rects)
            maxx = max(r.right for r in rects)
            maxy = max(r.bottom for r in rects)
            gx, gy = minx - GROUP_PAD, miny - GROUP_PAD
            gw, gh = (maxx - minx) + 2 * GROUP_PAD, (maxy - miny) + 2 * GROUP_PAD
            _f, gstroke, glab = th[f"token_{grp.variant}"]
            gels.append(RectEl(gx, gy, gw, gh, 14, th["group_bg"], gstroke, 1.4))
            if grp.label:
                lw = reg.text_width(grp.label, slab_sz)
                gels.append(RectEl(gx + 12, gy - slab_sz * 0.66, lw + 12, slab_sz + 4, 0, th["bg"], "none", 0.0))
                gels.append(TextEl(gx + 18, gy + slab_sz * 0.34, grp.label, slab_sz, glab, "bold", "start", lw))
        els[node_start_idx:node_start_idx] = gels

    # ── edges (경계 내부 한정 라우팅 + 라벨) ──
    def _edge_label(lx: float, ly: float, label: str) -> None:
        lw = reg.text_width(label, slab_sz)
        els.append(RectEl(lx - lw / 2 - 5, ly - slab_sz * 0.72, lw + 10, slab_sz + 5,
                          (slab_sz + 5) / 2, th["bg"], "none", 0.0))
        els.append(TextEl(lx, ly + slab_sz * 0.30, label, slab_sz, th["row_label"], "normal", "middle", lw))

    # 같은 노드쌍을 잇는 다중 엣지 → 서로 겹치지 않게 평행 오프셋
    pair_count: dict[tuple[str, str], int] = defaultdict(int)
    for e in spec.edges:
        pair_count[(e.from_, e.to)] += 1
    pair_seen: dict[tuple[str, str], int] = defaultdict(int)

    for e in spec.edges:
        a = id_rect.get(e.from_)
        b = id_rect.get(e.to)
        if not a or not b:
            continue
        col = th[f"connector_{e.color}"]

        # 자기 루프 — 노드 오른쪽에 작은 고리
        if e.from_ == e.to:
            sx, sy = a.right, a.y + a.h * 0.30
            ex, ey = a.right, a.y + a.h * 0.70
            bulge = a.right + 24
            d = f"M {sx:.1f} {sy:.1f} C {bulge:.1f} {sy-4:.1f}, {bulge:.1f} {ey+4:.1f}, {ex:.1f} {ey:.1f}"
            els.append(PathEl(d, col, 2.2, "none", Rect(a.right, sy - 4, bulge - a.right + 2, (ey - sy) + 8), dashed=e.dashed))
            if e.arrow:
                els.append(_arrow_head(ex, ey, "left", col))
            if e.label:
                _edge_label(bulge + 6 + reg.text_width(e.label, slab_sz) / 2, (sy + ey) / 2, e.label)
            continue

        key = (e.from_, e.to)
        pair_seen[key] += 1
        cnt = pair_count[key]
        off = ((pair_seen[key] - 1) - (cnt - 1) / 2) * 13.0 if cnt > 1 else 0.0

        dx = b.cx - a.cx
        dy = b.cy - a.cy
        rs, rt = id_row.get(e.from_, 0), id_row.get(e.to, 0)
        lane = None
        if abs(dy) >= abs(dx):  # 세로
            if dy >= 0:
                sx, sy = a.cx + off, row_bottom[rs]
                ex, ey = b.cx + off, b.y
                end_dir = "down"
            else:
                sx, sy = a.cx + off, a.y
                ex, ey = b.cx + off, row_bottom[rt]
                end_dir = "up"
            if abs(rt - rs) >= 2:
                lane = max(a.right, b.right) + COL_GAP * 0.5 + off
                seg = ey - sy
                d = (f"M {sx:.1f} {sy:.1f} "
                     f"C {sx:.1f} {sy + 24:.1f}, {lane:.1f} {sy + 8:.1f}, {lane:.1f} {sy + 34:.1f} "
                     f"L {lane:.1f} {ey - 34:.1f} "
                     f"C {lane:.1f} {ey - 8:.1f}, {ex:.1f} {ey - 24:.1f}, {ex:.1f} {ey:.1f}") \
                    if seg > 80 else \
                    f"M {sx:.1f} {sy:.1f} C {lane:.1f} {sy:.1f}, {lane:.1f} {ey:.1f}, {ex:.1f} {ey:.1f}"
                lx, ly = lane, (sy + ey) / 2
            else:
                my = (sy + ey) / 2
                d = f"M {sx:.1f} {sy:.1f} C {sx:.1f} {my:.1f}, {ex:.1f} {my:.1f}, {ex:.1f} {ey:.1f}"
                lx, ly = (sx + ex) / 2, my
        else:                   # 가로
            if dx >= 0:
                sx, sy = a.right, a.cy + off
                ex, ey = b.x, b.cy + off
                end_dir = "right"
            else:
                sx, sy = a.x, a.cy + off
                ex, ey = b.right, b.cy + off
                end_dir = "left"
            mx = (sx + ex) / 2
            d = f"M {sx:.1f} {sy:.1f} C {mx:.1f} {sy:.1f}, {mx:.1f} {ey:.1f}, {ex:.1f} {ey:.1f}"
            lx, ly = mx, (sy + ey) / 2

        # 엣지 스타일 — straight/orthogonal 은 곡선 d 를 덮어씀 (lane 우회는 곡선 유지)
        if e.style == "straight":
            d = f"M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}"
        elif e.style == "orthogonal" and lane is None:
            if abs(dy) >= abs(dx):
                my = (sy + ey) / 2
                d = (f"M {sx:.1f} {sy:.1f} L {sx:.1f} {my:.1f} "
                     f"L {ex:.1f} {my:.1f} L {ex:.1f} {ey:.1f}")
            else:
                mx2 = (sx + ex) / 2
                d = (f"M {sx:.1f} {sy:.1f} L {mx2:.1f} {sy:.1f} "
                     f"L {mx2:.1f} {ey:.1f} L {ex:.1f} {ey:.1f}")

        xs = [sx, ex] + ([lane] if lane is not None else [])
        approx = Rect(min(xs), min(sy, ey), max(1.0, max(xs) - min(xs)), max(1.0, abs(ey - sy)))
        els.append(PathEl(d, col, 2.4, "none", approx, dashed=e.dashed))
        if e.arrow:
            els.append(_arrow_head(ex, ey, end_dir, col))
        if e.label:
            _edge_label(lx, ly, e.label)

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

    # ── 범례 (콘텐츠 아래 한 줄) ──
    legend = list(getattr(spec, "legend", []) or [])
    if legend:
        prov_bottom = max((el.bbox().bottom for el in els if el.bbox() is not None), default=grid_bottom)
        ly = prov_bottom + fs * 1.3
        lx = PAD
        sw = slab_sz + 3
        for item in legend:
            fill, stroke, _t = th[f"token_{item.variant}"]
            els.append(RectEl(lx, ly - sw, sw, sw, 4, fill, stroke, 1.4))
            lw = reg.text_width(item.label, slab_sz)
            els.append(TextEl(lx + sw + 6, ly - sw * 0.2, item.label, slab_sz, th["row_label"], "normal", "start", lw))
            lx += sw + 6 + lw + 20

    # 캔버스 = 모든 요소 bbox 의 합집합 + 여백 (자기루프·레인·라벨·노트·헤더·범례 전부 포함)
    bboxes = [el.bbox() for el in els if el.bbox() is not None]
    content_right = max((bb.right for bb in bboxes), default=grid_right)
    content_bottom = max((bb.bottom for bb in bboxes), default=grid_bottom)

    cap_w = reg.text_width(spec.caption, caption_sz) if spec.caption else 0.0
    canvas_w = max(content_right + PAD, cap_w + 2 * PAD, PAD * 2 + 200)

    y = content_bottom
    if spec.caption:
        y += fs * 1.4
        els.append(TextEl(canvas_w / 2, y, spec.caption, caption_sz, th["caption"], "normal", "middle", cap_w))
        y += caption_sz * 0.4
    canvas_h = y + PAD

    card = RectEl(0.5, 0.5, canvas_w - 1, canvas_h - 1, 18, th["bg"], th["card_stroke"], 1.0)
    desc = spec.subtitle or spec.caption or ""
    return Scene(canvas_w, canvas_h, [card, *els], bg=th["bg"], title=spec.title or "", desc=desc)


def _layer_flow(spec: FlowSpec) -> NodeGraphSpec:
    """flow → layer 자동 산출 후 node-graph 로 변환 (longest-path layering + barycenter 정렬)."""
    by_id = {n.id: n for n in spec.nodes}
    order_idx = {n.id: i for i, n in enumerate(spec.nodes)}
    # self-edge 는 layering 에서 제외(자기 루프로 렌더), 나머지로 그래프 구성
    raw = [(e.from_, e.to) for e in spec.edges
           if e.from_ in by_id and e.to in by_id and e.from_ != e.to]
    succ: dict[str, list[str]] = defaultdict(list)
    for u, v in raw:
        succ[u].append(v)

    # 반복적 DFS 로 back edge(조상으로 향하는 엣지) 분류 → layering 에서 제외 → cycle 안전.
    state: dict[str, int] = {nid: 0 for nid in by_id}  # 0 white · 1 gray · 2 black
    back: set[tuple[str, str]] = set()
    for root in by_id:
        if state[root] != 0:
            continue
        state[root] = 1
        stack = [(root, iter(succ[root]))]
        while stack:
            u, it = stack[-1]
            for v in it:
                sv = state.get(v, 0)
                if sv == 1:
                    back.add((u, v))
                elif sv == 0:
                    state[v] = 1
                    stack.append((v, iter(succ[v])))
                    break
            else:
                state[u] = 2
                stack.pop()

    dag = [(u, v) for (u, v) in raw if (u, v) not in back]
    preds: dict[str, list[str]] = defaultdict(list)
    for u, v in dag:
        preds[v].append(u)

    layer = {nid: 0 for nid in by_id}
    for _ in range(len(by_id) + 1):
        changed = False
        for u, v in dag:
            if layer[v] < layer[u] + 1:
                layer[v] = layer[u] + 1
                changed = True
        if not changed:
            break

    succ_dag: dict[str, list[str]] = defaultdict(list)
    for u, v in dag:
        succ_dag[u].append(v)

    max_layer = max(layer.values()) if layer else 0
    by_layer: dict[int, list[str]] = defaultdict(list)
    for nid in by_id:
        by_layer[layer[nid]].append(nid)
    for L in by_layer:
        by_layer[L].sort(key=lambda nid: order_idx[nid])

    # 교차 최소화 — median heuristic 을 위/아래로 번갈아 sweep (Sugiyama 식).
    def _order(L: int, adj: int, neigh: dict[str, list[str]]) -> None:
        posmap = {nid: i for i, nid in enumerate(by_layer.get(adj, []))}
        keyed = []
        for j, nid in enumerate(by_layer[L]):
            ps = sorted(posmap[x] for x in neigh[nid] if x in posmap)
            m = statistics.median(ps) if ps else j  # 이웃 없으면 현재 위치 유지
            keyed.append((m, j, nid))
        keyed.sort(key=lambda t: (t[0], t[1]))
        by_layer[L] = [nid for _, _, nid in keyed]

    for it in range(4):
        if it % 2 == 0:
            for L in range(1, max_layer + 1):
                _order(L, L - 1, preds)
        else:
            for L in range(max_layer - 1, -1, -1):
                _order(L, L + 1, succ_dag)

    gnodes: list[GNode] = []
    for L in range(max_layer + 1):
        for o, nid in enumerate(by_layer[L]):
            n = by_id[nid]
            row, col = (o, L) if spec.direction == "right" else (L, o)
            gnodes.append(GNode(text=n.text, row=row, col=col, id=n.id,
                                variant=n.variant, shape=n.shape, sublabel=n.sublabel,
                                color=n.color, text_color=n.text_color))
    return NodeGraphSpec(
        type="node-graph", title=spec.title, subtitle=spec.subtitle,
        nodes=gnodes, edges=spec.edges, groups=spec.groups, legend=spec.legend,
        note=spec.note, caption=spec.caption,
        theme=spec.theme, font_size=spec.font_size,
    )


def build_scene(spec) -> Scene:
    """타입별 디스패치 (새 타입은 여기에 분기 추가)."""
    if isinstance(spec, TokenSequenceSpec):
        return layout_node_graph(spec.to_node_graph(), align="grid")
    if isinstance(spec, FlowSpec):
        return layout_node_graph(_layer_flow(spec), align="center")
    if isinstance(spec, NodeGraphSpec):
        return layout_node_graph(spec, align="grid")
    raise ValueError(f"지원하지 않는 다이어그램 타입: {getattr(spec, 'type', spec)}")
