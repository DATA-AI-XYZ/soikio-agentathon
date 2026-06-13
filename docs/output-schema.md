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
      "severity": "high",                       // high