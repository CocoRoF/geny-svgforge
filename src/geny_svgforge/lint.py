"""시각 결함 린트 — 결정론적 안전망.

레이아웃 엔진이 올바르면 경고는 0건이어야 한다. 경고가 나오면 엔진 버그이거나
극단적 입력이라는 신호이고, AI 에이전트에게 그대로 돌려줘 spec 을 고치게 할 수 있다.
"""
from __future__ import annotations

from .geometry import RectEl, Scene


def lint(scene: Scene) -> list[str]:
    warnings: list[str] = []

    # 1) 토큰 박스끼리 겹침
    boxes = [(el.bbox(), i) for i, el in enumerate(scene.elements)
             if isinstance(el, RectEl) and el.role == "box"]
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            ra, rb = boxes[a][0], boxes[b][0]
            if ra.intersects(rb, pad=-0.5):
                warnings.append(
                    f"token box overlap: box#{boxes[a][1]} ∩ box#{boxes[b][1]}"
                )

    # 2) 캔버스 밖으로 넘치는 요소 (클리핑 위험)
    tol = 1.0
    for i, el in enumerate(scene.elements):
        bb = el.bbox()
        if bb is None:
            continue
        if (bb.x < -tol or bb.y < -tol
                or bb.right > scene.width + tol
                or bb.bottom > scene.height + tol):
            warnings.append(
                f"element#{i} overflows canvas "
                f"(bbox={bb.x:.0f},{bb.y:.0f},{bb.right:.0f},{bb.bottom:.0f} "
                f"canvas={scene.width:.0f}x{scene.height:.0f})"
            )
    return warnings
