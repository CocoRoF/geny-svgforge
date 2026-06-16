# geny-svgforge

**AI가 좌표 대신 '의미(spec)'만 내면, 결정론적 레이아웃 엔진이 겹침·클리핑 없는 깨끗한 다이어그램 SVG를 만든다.**

LLM에게 `<svg>`를 직접 쓰게 하면 텍스트 폭·박스 경계·곡선 경로·viewBox를 수치로 못 맞춰 요소가 겹치고 글자가 잘린다. geny-svgforge는 그 사이에 레이아웃 계층을 둔다. AI는 *"두 문장의 토큰 시퀀스, posN 라벨, A의 2번과 B의 3번을 곡선으로 연결, 우측 노트, 하단 캡션"* 이라는 JSON spec만 내고, 라이브러리가 폰트를 실측해 좌표를 계산하고 전체 bbox로 캔버스를 확정한다. → **겹침·오버플로가 구조적으로 불가능.**

> edit2ppt(AI가 PPT 구조를 내고 엔진이 렌더)·Contextifier(문서 구조 보존)와 같은 계보.

---

## 설치

```bash
pip install geny-svgforge            # 코어 (SVG)
pip install 'geny-svgforge[png]'     # + PNG 내보내기 (cairosvg)
pip install 'geny-svgforge[mcp]'     # + MCP 서버
```

## 빠른 시작 (Python)

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
    "note": {"title": "모델이 배워야 하는 것",
             "lines": ["절대 position만 외우면 문장 길이 변화에 약하다.",
                       "상대 거리와 주변 패턴을 attention에서 같이 다룬다."]},
    "caption": "절대 위치가 바뀌어도 상대 토큰 관계가 유지되는 문장 예시",
}

result = render(spec)        # 폰트 임베드된 이식성 SVG
print(result.warnings)       # []  ← 겹침/클리핑 없음(린트 통과)
open("out.svg", "w").write(result.svg)
```

## CLI

```bash
geny-svgforge render spec.json -o out.svg
geny-svgforge render spec.json -o out.png      # PNG ([png] 필요)
geny-svgforge validate spec.json               # 렌더 전 검증
geny-svgforge schema -o schema.json            # JSON Schema 덤프
```

## MCP (AI 에이전트 직결)

```bash
python -m geny_svgforge.mcp_server
```
제공 툴: `render_diagram(spec)` → `{svg, width, height, warnings[]}`, `validate_diagram_spec(spec)`, `get_diagram_schema()`. 에이전트는 schema로 형식을 배우고, spec만 내고, warnings가 있으면 고쳐 다시 호출한다.

---

## 동작 원리

3-Layer: **Spec(JSON Schema) → Layout Engine → Renderer**.

- **폰트 실측** — `fontTools`로 glyph advance를 직접 합산해 텍스트 폭을 px로 계산(브라우저·헤드리스 무의존). 측정에 쓴 폰트를 그대로 SVG에 넣으므로 **측정 == 렌더**.
- **결정론적 레이아웃** — 박스는 텍스트 폭에 맞춰 sizing, 커넥터는 행 사이 띠에 충돌 회피로 라우팅, 마지막에 모든 요소 bbox로 viewBox·패딩을 확정 → 클리핑 불가.
- **폰트 임베드** — 사용된 글자만 subset해 base64 `@font-face`로 넣어 어디서든(브라우저·resvg) 동일 렌더. PNG는 설치 폰트로 cairosvg 렌더(`raster_safe`).
- **린트** — 박스 겹침·캔버스 초과를 사후 검사. 0이어야 정상이며, AI에게 그대로 돌려줄 수 있는 안전망.

## 다이어그램 타입

| 타입 | 설명 |
|---|---|
| `token-sequence` | 위치 라벨 토큰 박스의 행 + 행 간 커넥터 + 옆 노트 + 캡션 |

(향후 `flow`, `grid`, `stack`, `callout` 등 추가 예정 — spec은 `type`으로 확장.)

## 로드맵
- 충돌 자동 해소(제약/force), 시각 자기검수 루프(render→raster→멀티모달 판정→spec 수정→재렌더)
- 다이어그램 타입·테마·템플릿 확장, 접근성(`title`/`desc`/aria)

## 라이선스
MIT. 폰트는 사용 환경의 폰트(예: SIL OFL의 Noto Sans CJK)를 측정·임베드한다 — 임베드 시 해당 폰트 라이선스를 따른다.
