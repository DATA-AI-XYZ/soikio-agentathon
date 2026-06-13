# ADR-0008 — Verification gate + deterministic scoring (the rigour moat)

**Status:** Accepted · **Date:** 2026-06-12

## Context

A design-soundness review found the product *markets* audit-grade rigour it doesn't *enforce*: `citations.py` checked that a citation existed, not that it was true; severity/robustness/confidence were free-text LLM judgements with no rubric; and `unsupported` was indistinguishable from "retrieval missed it". Citation-grounded RAG mis-cites 17–34% of the time and LLM critique invents flaws ~40% of the time — so a sharp judge could click one crack, open the source, and collapse the whole positioning. This is also the only place to build a real technical moat versus a funded look-alike (LinqAlpha) and commodity grounded-RAG.

## Decision

Three enforced mechanisms, specified in `docs/scoring.md` and `docs/reliability-spec.md`:

1. **Deterministic scoring.** Agents *classify* (typed cracks with `claim_id` / `crack_type` / `citations` + `load_bearing` flags from extraction); **code computes** severity, `thesis_robustness` (Holds/Contested/Breaks) and confidence via explicit functions. Same thesis → same verdict (E8).
2. **Citation faithfulness gate.** Before display: the shown figure must appear in its citation `quote`, and the `quote` must be a substring of the actual retrieved extract. Fabricated citations are rejected, not just flagged (E6, E9).
3. **Coverage probe.** `unsupported` may be asserted only when a covering document exists; otherwise it's a `data_gap` that lowers data-completeness, not a crack against the user's thesis (E7).

## Consequences

- **+** Converts "audit-grade" from a claim into a guarantee — a judge clicking a crack confirms it.
- **+** The technical moat: machine-checked adversarial citations are the hardest thing for a verdict-engine to copy.
- **+** Reproducible verdicts; honest about its own limits (attack-bias disclosure).
- **−** More build work (extraction prompt, scorer, faithfulness/coverage checks) under deadline. Mitigated by keeping the scorer small and the corpus curated.

## Related

`docs/scoring.md`, `docs/reliability-spec.md`, `prompts/extract.md`, evaluation E6–E9. Builds on cite-or-silence (ADR-0004) and the Kintsugi conflict map (ADR-0007).
