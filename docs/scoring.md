# Scoring — making severity, robustness & confidence *derived*, not vibes

The headline outputs (severity, robustness, confidence) must be **computed from typed facts by a deterministic function in `src/cio.py`**, not produced as a free-text LLM judgement. This is what converts the conflict map from "a confident-looking opinion" into an audit-trail the product claims to be. Agents *classify*; code *scores*.

## Inputs the agents must emit (so scoring can be deterministic)

Each crack (from Bear/Caution) carries:
- `claim_id` — which extracted claim it attacks.
- `crack_type` — `contradicted` | `unsupported` | `vulnerable`.
- `citations[]` — for `contradicted`/`vulnerable`, ≥1 faithful citation (see `reliability-spec.md`). For `unsupported`, none — but it must have passed the **coverage probe** (otherwise it's a `data_gap`, not a crack).
- `agent_severity_hint` — the agent's own low/medium/high (advisory only; code may override).

Each claim (from `extract.md`) carries `load_bearing: true|false`.

## 1. Severity — a function, not an opinion

`severity = f(crack_type, load_bearing, citation_strength)`:

| crack_type | load-bearing claim | non-load-bearing |
|------------|--------------------|------------------|
| **contradicted** (cited) | **high ⚡** | medium |
| **unsupported** (coverage-confirmed) | medium | low |
| **vulnerable** (cited) | medium | low |

Adjustment: a `contradicted` crack whose citation is **single-source** is capped at medium until corroborated (avoids one cherry-picked line breaking a thesis). `vulnerable` with no citation is **rejected** (it's speculation, not a crack — see reliability-spec).

## 2. Thesis robustness — derived from the crack set

Computed in code, in order:

1. **Breaks** — any **high-severity** crack on a **load-bearing** claim, OR a load-bearing claim is `unsupported` (coverage-confirmed) with no supporting evidence from Bull.
2. **Contested** — any **medium-severity** crack on a load-bearing claim, OR ≥2 medium cracks total, that remain unresolved.
3. **Holds** — only low-severity cracks survive, and every load-bearing claim has Bull support that outweighs its cracks.

Ties resolve to the **more conservative** rating (Breaks > Contested > Holds). The CIO writes the narrative; the rating itself is the function's output.

## 3. Confidence — capped, not asserted

```
confidence = base
base = mean(citation_strength of surviving evidence)         # 0–1
cap if data_completeness < 0.5         → confidence ≤ 0.5
cap if thesis_robustness == "Breaks"   → confidence ≤ 0.5
cap if any unresolved high-severity    → confidence ≤ 0.45
cap if load-bearing claim has 0 evidence either way → confidence ≤ 0.4
```

A `Breaks` verdict can fire from a load-bearing claim being `unsupported` (a **medium**-severity crack), which would otherwise skip the high-severity cap — so the headline could read "Breaks" at base confidence. The Breaks cap closes that gap: a broken thesis is never reported at high confidence. An evidence-gap Breaks (unsupported load-bearing, no citations) lands at ≤ 0.4; a cited Breaks at ≤ 0.45–0.5.
`data_completeness = lenses_with_usable_evidence / active_lens_count` where `active_lens_count` is the number of lenses actually run for this thesis (**3** for the MVP lens set — fundamental, risk, valuation — or **6** for the full set). A lens is "usable" only if the coverage probe found ≥1 relevant document for it. The denominator is the active lens set, not a hardcoded 6, so a 3-lens MVP run is not penalised for the 3 lenses it never ran.

## 4. Conflict-map dedup & ranking — deterministic

- **Dedup key:** `(claim_id, crack_type)`. Cracks sharing a key are merged; their citations are unioned; the highest severity wins. (Bear and Caution naming the same crack across lenses collapse to one.)
- **Rank:** by severity (high → low), then by number of distinct citations (more-corroborated first), then by `claim_id`.
- **No silent drop:** every merged crack is retained; dedup is recorded (`merged_from: [...]`) so the "never omit for tidiness" invariant holds literally.

## 5. "What would resolve it" — must be concrete & falsifiable

The CIO generates this, but it is **rejected and regenerated** if it is generic ("more disclosure", "next earnings release" with no specifics). It must name: a **specific document/event** and the **observation that would flip the crack** (e.g. "Q3 segment-margin disclosure showing cloud gross margin ≥ prior period" — not "next earnings"). A resolution that doesn't name what observation settles it is not a resolution.

## Why this matters

Two runs on the same thesis must return the **same** robustness rating (modulo retrieval noise). `evaluation.md` E8 tests this. A conflict map whose severity flips on resampling is the fastest way a judge dismisses the "audit-grade" claim — see `reliability-spec.md`.
