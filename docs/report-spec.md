# Report spec — interactive HTML brief

The cited brief, rendered as a **self-contained interactive HTML report**. Produced **deterministically** from the validated CIO output (`output-schema.md`) by `src/render.py` — **no LLM, no model call** (see ADR-0005). This is what guarantees that not a single figure changes between the CIO and the screen.

Sample / mockup: [`report.sample.html`](report.sample.html) (MSFT, illustrative data).

## Why deterministic (not a formatting agent)

- **Preserves cite-or-silence** — a template can't paraphrase a number or drop a citation; an LLM formatter could.
- **Free and fast** — rendering is templating, not reasoning; no tokens, no latency.
- **No extra failure surface** mid-demo.

## Input

The validated brief object: `thesis`, `entity`, `thesis_robustness`, `equity_lean`, `confidence`, `thesis_summary`, `weighed_stances`, `conflict_map`, `domain_findings`, `run`, `citations`, `data_completeness`, `disclaimer`. See [`output-schema.md`](output-schema.md).

## Sections (top to bottom)

1. **Mockup banner** — present only when rendering sample data; omitted for live runs.
2. **Header** — ticker + company; **thesis under test**; **robustness badge** (Holds / Contested / Breaks) + an equity-lean chip; **confidence** and **data-completeness** meters; **date generated** + run id; **stance-weight bar**; a holds/breaks summary.
3. **Agent run · health** — run metadata (run id, timestamp, model, retrieval effort, total time, total retrievals, lenses-with-evidence) and a **per-agent table** (status, latency, retrievals, confidence). A failed/degraded agent is shown (amber/red dot), not hidden.
4. **Analysis** — a **view switch**:
   - **Debate · by stance** — Bull / Bear / Caution tabs; each point shows lens tag, confidence, and an expandable citation (quote + locator).
   - **By domain · 6 lenses** — collapsible panel per lens with a **net-lean** chip, source count, a one-line **finding**, the contributing stance points, and expandable citations. Lenses with no evidence show **"thin data"**, not omission.
5. **Kintsugi conflict map (headline — rendered directly after the header)** — each crack shows severity (⚡ high / medium / low), crack type (contradicted / unsupported / vulnerable), the claim under test, an expandable citation, and *what would resolve it*. Ranked by severity; never omitted for tidiness.
6. **Sources** — the documents used, with provenance.
7. **Footer** — analysis-not-advice disclaimer; verdict family; data-quality caveat.

## Interactions

View switch (stance ↔ domain), stance tabs, domain accordions, citation expanders, conflict accordions. Vanilla JS only; **no localStorage / sessionStorage**; single file, no server, no external JS.

## Branding

Cream `#faf7f2`, teal accent `#1f8a8a`; Instrument Serif headlines, Manrope body, JetBrains Mono for ids/metrics. Verdict colours: Bullish green, Bearish red, Caution amber.

## Determinism & invariants (enforced in `render.py`)

- Every figure shown traces to a citation in the input; uncited figures are stripped or flagged.
- The strings BUY / SELL / HOLD never appear.
- A lens with no evidence renders as `thin`, contributing to lower data-completeness — never silently dropped.
- The mockup banner appears **only** when `entity.sample == true`.

## Invocation

```bash
python scripts/run_example.py --thesis examples/thesis.txt --html out/report.html
# 