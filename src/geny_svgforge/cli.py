"""geny-svgforge CLI: render / validate / schema."""
from __future__ import annotations

import argparse
import json
import sys

from .api import render, to_png, validate_spec
from .spec import json_schema


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="geny-svgforge",
                                description="AI 의미 spec -> 깨끗한 다이어그램 SVG")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="spec(json) -> svg/png")
    r.add_argument("spec")
    r.add_argument("-o", "--out", help="출력 경로 (.svg 또는 .png). 생략 시 stdout(svg)")
    r.add_argument("--no-embed", action="store_true", help="폰트 임베드 비활성")

    v = sub.add_parser("validate", help="spec 검증만")
    v.add_argument("spec")

    s = sub.add_parser("schema", help="JSON Schema 출력")
    s.add_argument("-o", "--out")

    args = p.parse_args(argv)

    if args.cmd == "schema":
        out = json.dumps(json_schema(), ensure_ascii=False, indent=2)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(out)
        else:
            print(out)
        return 0

    if args.cmd == "validate":
        res = validate_spec(_load(args.spec))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 1

    if args.cmd == "render":
        spec = _load(args.spec)
        if args.out and args.out.lower().endswith(".png"):
            open(args.out, "wb").write(to_png(spec))
            print(f"wrote {args.out}", file=sys.stderr)
            return 0
        res = render(spec, embed_font=not args.no_embed)
        for w in res.warnings:
            print(f"warning: {w}", file=sys.stderr)
        if args.out:
            open(args.out, "w", encoding="utf-8").write(res.svg)
            print(f"wrote {args.out}", file=sys.stderr)
        else:
            sys.stdout.write(res.svg)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
