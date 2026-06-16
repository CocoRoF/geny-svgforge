# geny-svgforge

**Give an AI a semantic spec instead of raw coordinates, and a deterministic layout engine produces a clean diagram SVG with zero overlaps or clipping.**

When an LLM writes `<svg>` by hand, it can't reliably reason about text widths, box bounds, curve paths, or the viewBox — so elements overlap and captions get clipped. geny-svgforge inserts a layout layer between the AI and the SVG. The AI emits only a JSON **spec** (*"two rows of labeled tokens, posN labels, connect A's token 2 to B's token 3 with a curve, a side note, a caption"*) — no coordinates. The library measures text with real font metrics, sizes every box, routes connectors around obstacles, and fits the viewBox to the content. **Overlap and overflow become structurally impossible.**

> Same lineage as edit2ppt (AI emits PPT structure, engine renders) and Contextifier (structure-preserving document parsing).

---

## Install

```bash
pip install geny-svgforge            # core (SVG)
pip install 'geny-svgforge[png]'     # + PNG export (cairosvg)
pip install 'geny-svgforge[mcp]'     # + MCP server
```

## Quickstart (Python)

```python
from geny_svgforge import render

spec = {
    "type": "token-sequence",
    "title": "Absolute position changes, relative pattern remains",
    "rows": [
        {"label": "sentence A", "tokens": [
            {"text": "나는", "pos": "pos 0"},
            {"text": "오늘", "pos": "pos 1"},
            {"text": "밥을", "pos": "pos 2", "id": "a2"},
            {"text": "먹었다", "pos": "pos 3", "variant": "highlight"},
        ]},
        {"label": "sentence B", "tokens": [
            {"text": "나는", "pos": "pos 0"},
            {"text": "정말", "pos": "pos 1", "variant": "accent"},
            {"text": "오늘", "pos": "pos 2"},
            {"text": "밥을", "pos": "pos 3", "id": "b3"},
            {"text": "먹었다", "pos": "pos 4", "variant": "highlight"},
        ]},
    ],
    "connectors": [{"from": "a2", "to": "b3", "color": "accent"}],
    "note": {"title": "What the model must learn",
             "lines": ["Memorizing absolute positions is brittle to length changes.",
                       "Relative distance and surrounding patterns are handled in attention."]},
    "caption": "Same relative token relationship survives an absolute shift",
}

result = render(spec)        # portable SVG with the used glyphs embedded
print(result.warnings)       # []  ← no overlap / no clipping (lint passed)
open("out.svg", "w").write(result.svg)
```

## CLI

```bash
geny-svgforge render spec.json -o out.svg
geny-svgforge render spec.json -o out.png      # PNG (requires [png])
geny-svgforge validate spec.json               # validate before rendering
geny-svgforge schema -o schema.json            # dump the JSON Schema
```

## MCP server

geny-svgforge ships an [MCP](https://modelcontextprotocol.io) server over **stdio** so any MCP-compatible agent can request diagrams. After `pip install 'geny-svgforge[mcp]'` the server is launched with:

```bash
geny-svgforge-mcp                 # console script
# or
python -m geny_svgforge.mcp_server
```

### Tools exposed

| Tool | Input | Returns |
|---|---|---|
| `get_diagram_schema` | – | JSON Schema describing the spec (the agent learns the format from this) |
| `validate_diagram_spec` | `spec` | `{ ok, errors[], warnings[] }` — check before rendering |
| `render_diagram` | `spec` | `{ svg, width, height, warnings[] }` — if `warnings` is non-empty, fix the spec and call again |

### Client configuration

Add the server to your MCP client config. The standard shape is an `mcpServers` map keyed by a server name.

**Claude Desktop** (`claude_desktop_config.json`), **Cursor** (`~/.cursor/mcp.json`), or **Claude Code** (`.mcp.json`):

```json
{
  "mcpServers": {
    "geny-svgforge": {
      "command": "geny-svgforge-mcp"
    }
  }
}
```

Zero-install with [uv](https://docs.astral.sh/uv/) (no prior `pip install` needed):

```json
{
  "mcpServers": {
    "geny-svgforge": {
      "command": "uvx",
      "args": ["--from", "geny-svgforge[mcp]", "geny-svgforge-mcp"]
    }
  }
}
```

Claude Code can also add it from the CLI:

```bash
claude mcp add geny-svgforge -- uvx --from 'geny-svgforge[mcp]' geny-svgforge-mcp
```

A typical agent flow: call `get_diagram_schema` once to learn the format → emit a `spec` → call `render_diagram` → if `warnings` is non-empty, repair the spec and retry.

---

## How it works

Three layers: **Spec (JSON Schema) → Layout Engine → Renderer**.

- **Real font metrics** — text width is computed in pixels by summing glyph advances via `fontTools` (no browser, no headless engine). The same font used for measurement is embedded into the SVG, so **measured layout == rendered output**.
- **Deterministic layout** — boxes are sized to their text, connectors are routed through the inter-row band away from boxes, and the viewBox/padding is derived from the bounding box of every element — so nothing can clip.
- **Font embedding** — only the glyphs actually used are subset and inlined as a base64 `@font-face`, so the SVG renders identically everywhere (browsers, resvg). `to_png()` renders via the installed font (`raster_safe`) because cairosvg ignores embedded `@font-face`.
- **Lint** — a post-layout pass flags box overlaps and canvas overflow. It should always be empty; if not, the warnings are returned to the agent so it can fix the spec.

## Diagram types

| Type | Description |
|---|---|
| `token-sequence` | Rows of position-labeled token boxes, with inter-row connectors, a side note, and a caption |

(`flow`, `grid`, `stack`, `callout`, … are planned — the spec is extensible via the `type` field.)

## Roadmap

- Automatic collision resolution (constraint / force based)
- Visual self-repair loop: render → rasterize → multimodal critique → fix spec → re-render
- More diagram types, themes, templates, accessibility (`<title>`/`<desc>`/aria)

## License

MIT. Text is measured against — and a subset is embedded from — a system font (e.g. SIL OFL Noto Sans CJK). When embedding, the embedded font's own license applies.
