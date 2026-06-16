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

The general type is **`node-graph`**: place nodes on a `(row, col)` grid (same `col` aligns vertically) and connect any nodes with edges. The engine sizes boxes, routes edges around obstacles, and fits the canvas.

```python
from geny_svgforge import render

spec = {
    "type": "node-graph",
    "title": "Token embedding + positional encoding",
    "row_labels": {0: "token", 1: "embedding", 2: "position", 3: "input"},
    "nodes": [
        {"text": "나는", "row": 0, "col": 0, "id": "t0", "sublabel": "0"},
        {"text": "밥을", "row": 0, "col": 1, "id": "t1", "sublabel": "1"},
        {"text": "E[나는]", "row": 1, "col": 0, "id": "e0", "variant": "accent"},
        {"text": "E[밥을]", "row": 1, "col": 1, "id": "e1", "variant": "accent"},
        {"text": "PE[0]", "row": 2, "col": 0, "id": "p0", "variant": "highlight"},
        {"text": "PE[1]", "row": 2, "col": 1, "id": "p1", "variant": "highlight"},
        {"text": "x0 = E + PE", "row": 3, "col": 0, "id": "x0"},
        {"text": "x1 = E + PE", "row": 3, "col": 1, "id": "x1"},
    ],
    "edges": [
        {"from": "t0", "to": "e0", "color": "gray", "arrow": True},
        {"from": "e0", "to": "x0", "color": "blue", "arrow": True},   # spans the position row → routed around it
        {"from": "p0", "to": "x0", "color": "accent", "arrow": True},
        {"from": "t1", "to": "e1", "color": "gray", "arrow": True},
        {"from": "e1", "to": "x1", "color": "blue", "arrow": True},
        {"from": "p1", "to": "x1", "color": "accent", "arrow": True},
    ],
    "caption": "same hidden size, element-wise add at each position",
}

result = render(spec)        # portable SVG with the used glyphs embedded
print(result.warnings)       # []  ← no overlap / no clipping (lint passed)
open("out.svg", "w").write(result.svg)
```

`token-sequence` is also accepted as convenience sugar (rows of tokens with `pos` labels and `connectors`); it is converted to `node-graph` internally.

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
| `flow` | **Auto-layout flowchart.** Just give `nodes` + `edges` (no coordinates); the engine assigns layers (longest-path) and orders each layer to reduce crossings. `direction: down\|right`. Best for pipelines, decision flows. |
| `node-graph` | **Explicit grid.** Nodes at `(row, col)` (same col aligns) + arbitrary edges (auto-anchored, obstacle-avoiding), optional row/col headers, per-node sublabels, side note, caption. Best for matrices, aligned diagrams. |
| `token-sequence` | Convenience sugar over `node-graph` — rows of `pos`-labeled tokens + `connectors`. |

Node `variant`: `default · accent · highlight · muted · good`. Node `shape`: `rect · pill · ellipse · diamond · cylinder · hexagon · parallelogram` (auto-sized to text). Edge `color`: `accent · blue · gray · good`, with optional `arrow`, `dashed`, and `label`.

Wrap nodes in a labeled container (subgraph) with `groups: [{ "label": "...", "nodes": ["id1", "id2"], "variant": "accent" }]` — drawn as a fieldset-style box behind the members. Works in both `flow` and `node-graph`.

```python
# flow: no coordinates — the engine lays it out
render({
    "type": "flow", "title": "RAG pipeline",
    "nodes": [
        {"id": "q", "text": "질문", "shape": "pill", "variant": "accent"},
        {"id": "db", "text": "pgvector", "shape": "cylinder"},
        {"id": "found", "text": "문서 있음?", "shape": "diamond", "variant": "highlight"},
        {"id": "ans", "text": "답변", "shape": "pill", "variant": "good"},
    ],
    "edges": [
        {"from": "q", "to": "db", "arrow": True, "label": "query"},
        {"from": "db", "to": "found", "arrow": True},
        {"from": "found", "to": "ans", "arrow": True, "label": "yes", "color": "good"},
    ],
})
```

### Edge routing
Edges connect the facing sides of two nodes with a cubic strictly **bounded by the rectangle spanning its endpoints** — it can never overshoot or pierce a box. Edges that span intermediate rows are detoured through an empty column-gap lane, so they don't cross the rows in between.

## Roadmap

- Automatic collision resolution (constraint / force based)
- Visual self-repair loop: render → rasterize → multimodal critique → fix spec → re-render
- More diagram types, themes, templates, accessibility (`<title>`/`<desc>`/aria)

## Fonts

The package **bundles NanumGothic (Regular + Bold, SIL OFL)** so it works out of the box in any environment — including minimal Docker images with no system fonts. Text is measured against this font and a glyph subset of it is embedded in the SVG, so layout and rendering match everywhere. Override with the `GENY_SVGFORGE_FONT` / `GENY_SVGFORGE_FONT_BOLD` environment variables (path to a `.ttf`/`.otf`) to use a different font.

## License

MIT for the library code. The bundled font NanumGothic is licensed under the SIL Open Font License 1.1 (`src/geny_svgforge/fonts/OFL.txt`); embedding it in output SVGs is permitted under the OFL.
