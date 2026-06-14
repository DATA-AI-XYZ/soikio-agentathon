# Output schema

The CIO emits one JSON object — the cited brief, headlined by the Kintsugi conflict map. Stance agents emit a simpler shape (their points/cracks + assumptions + stance confidence). Validate with `pydantic` (`src/`).

## Thesis input

The user submits the thesis under test; a claim-extraction step turns it into testable claims:

```json
"thesis": {
  "entity": { "ticker": "MSFT", "name": "Microsoft Corp" },
  "text": "Cloud-led margin expansion makes MSFT durably undervalued ...",
  "claims": [
    { "id": "c1", "claim": "Cloud margins keep expanding", "horizon": "medium" },
    { "id": "c2", "claim": "Premium valuation is justified", "horizon": "medium" }
  ]
}
```

## Citation object

Every material claim references one of these:

```json
{
  "source_id": "doc-msft-10k-2025",
  "locator": "Item 7, MD&A, p.42",
  "quote": "Operating margin expanded to 44% from 42% ...",
  "knowledge_source": "blob://public-docs/msft-10k-2025.pdf"
}
```

## Stance output (Bull / Bear / Caution)

```json
{
  "stance": "bull",
  "points": [
    {
      "lens": "fundamental",
      "claim": "Margins expanded year over year.",
      "citations": [ { "source_id": "doc-msft-10k-2025", "locator": "Item 7" } ],
      "confidence": 0.78
    }
  ],
  "key_assumptions": ["Cloud growth sustains current margin trajectory"],
  "data_gaps": ["No guidance document in the knowledge base"],
  "stance_confidence": 0.66
}
```

## CIO brief (final output)

```json
{
  "entity": { "ticker": "MSFT", "name": "Microsoft Corp" },
  "thesis_robustness": "Contested",           // Holds | Contested | Breaks  (HEADLINE verdict)
  "equity_lean": "Bullish",                    // Bullish | Caution | Bearish (secondary context)
  "confidence": 0.62,                          // 0.0–1.0
  "thesis_summary": "Where the thesis holds and where it breaks, every figure cited.",
  "weighed_stances": {
    "bull": { "weight": 0.45, "strongest_point": "...", "citations": ["doc-..."] },
    "bear": { "weight": 0.30, "strongest_point": "...", "citations": ["doc-..."] },
    "caution": { "weight": 0.25, "key_risk": "...", "citations": ["doc-..."] }
  },
  "conflict_map": [                            // the Kintsugi headline: cracks ranked by severity
    {
      "claim_under_test": "Cloud margins keep expanding",
      "crack_type": "vulnerable",              // contradicted | unsupported | vulnerable
      "severity": "high",                       // high | medium | low (computed in code)
      "what_would_resolve_it": "Forward margin guidance in the next 10-Q",
      "citations": [ { "source_id": "doc-msft-10k-2025", "locator": "Item 7" } ]
    }
  ],
  "domain_findings": [                         // per-lens grounded evidence (six specialists)
    { "lens": "fundamental", "summary": "...", "citations": ["doc-..."], "data_gap": false }
  ],
  "run": {
    "run_id": "sk-2026-06-14-msft-01",
    "created_at": "2026-06-14T14:32:00+01:00",
    "corpus_version": "public-docs@2026-06-12",
    "model": "claude-sonnet-4-6"
  },
  "citations": [ /* deduped union of every citation referenced above */ ]
}
```

## Review block (Reviewer agent)

Attached by the Reviewer, which runs *after* the CIO and compares this brief to the user's stored run history (`src/memory.py`). Deltas are **computed in code** (`src/reviewer.py` → `compute_deltas`); the agent writes only the narrative and feedback. Cracks are keyed by `(claim_under_test, crack_type)`.

```json
"review": {
  "vs_prior_run": {
    "had_prior": true,
    "prior_run_id": "sk-2026-06-11-msft-03",
    "prior_verdict": "Breaks",
    "current_verdict": "Contested",
    "verdict_change": "improved",              // improved | deteriorated | unchanged
    "cracks_healed":     ["Cloud margins keep expanding [vulnerable]"],
    "cracks_new":        [],
    "cracks_persisting": ["Premium valuation is justified [contradicted]"],
    "confidence_delta": 0.07,
    "note": "..."
  },
  "vs_history": {
    "runs_considered": 12,
    "runs_this_entity": 3,
    "verdict_mix": { "Holds": 4, "Contested": 6, "Breaks": 2 },
    "recurring_crack_themes": ["valuation"],
    "pattern_note": "..."
  },
  "calibration": {
    "status": "tracking",                      // insufficient_history | tracking | calibrated
    "note": "Consistency and drift are measured from stored runs. Predictive calibration requires outcome capture over time."
  },
  "feedback": [ "actionable bullet", "..." ]
}
```