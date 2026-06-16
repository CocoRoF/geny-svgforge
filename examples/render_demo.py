"""예시 spec 을 깨끗한 SVG 로 렌더하고(PNG 도) 린트 결과를 출력."""
import json
import pathlib
import sys

from geny_svgforge import render
from geny_svgforge.api import to_png

HERE = pathlib.Path(__file__).parent
spec_path = HERE / (sys.argv[1] if len(sys.argv) > 1 else "token_sequence_positions.json")
spec = json.loads(spec_path.read_text(encoding="utf-8"))

# 프로덕션 SVG (폰트 임베드 — 브라우저/resvg 에서 완전 이식)
result = render(spec)
out_svg = HERE / "out.svg"
out_svg.write_text(result.svg, encoding="utf-8")
print(f"canvas: {result.width:.0f} x {result.height:.0f}")
print(f"lint warnings ({len(result.warnings)}):")
for w in result.warnings:
    print("  -", w)
print(f"wrote {out_svg} ({len(result.svg)} bytes)")

try:
    out_png = HERE / "out.png"
    out_png.write_bytes(to_png(spec, scale=2.0))
    print(f"wrote {out_png}")
except Exception as e:  # noqa: BLE001
    print(f"(png skip: {e})")
