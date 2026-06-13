# Reliability spec — make the rigour real, not claimed

The product's whole pitch is *disciplined, grounded, audit-grade*. The risk a sharp judge exploits: it currently **checks that a citation exists, not that it is true.** Citation-grounded RAG mis-cites 17–34% of the time; LLM critique invents flaws ~40% of the time. This spec closes that gap so "cite-or-silence" is a guarantee, not a slogan. It is also the **technical moat** (machine-checked adversarial citations — the hardest thing for a verdict-engine competitor to copy).

## 1. Citation faithfulness gate (`src/citations.py`)

Presence ≠ faithfulness. For every figure/claim surfaced in agent or CIO output:

1. **Quote-contains-figure.** The number shown in the prose must appear verbatim in the citation's `quote`. If the prose says "44%" and the quote doesn't contain "44%", the figure is **stripped** (cite-or-silence) and the claim is flagged.
2. **Quote-in-extract.** The citation `quote` must be a substring of the actual Foundry IQ retrieved extract for that `source_id` (you have the extract — agentic retrieval returned it). A quote the model wrote that isn't in the retrieved text is a **fabricated citation** → the whole crack/point is **rejected**, not just the figure.
3. **Locator presence.** If Foundry IQ returns a section/page locator, it is carried through; if it returns only a doc-level ref, `locator` is set to the doc and the crack severity is **capped at medium** (you can't pinpoint it, so it can't break a thesis alone).

A `contradicted` crack that fails (1) or (2) is **never shown**. This is the gate that makes the demo safe: a judge who clicks a crack and opens the source will find the quote actually there.

## 2. Coverage probe — "unsupported" vs "we didn't retrieve it"

The deepest design flaw is that `unsupported` looks identical whether the claim is baseless or the tiny corpus simply lacked the page. Fix:

- Before any agent may assert `crack_type: unsupported` for a claim/lens, run a **coverage query**: does the knowledge base contain ≥1 document plausibly covering this claim/lens? (A topical retrieval, separate from the evidence retrieval.)
- **Coverage present, no supporting evidence found → legitimate `unsupported` crack.**
- **No coverage → it is a `data_gap`, NOT a crack.** It lowers `data_completeness`; it does **not** appear on the conflict map as a flaw in the user's thesis.

This single rule stops the demo corpus from manufacturing false cracks — the most likely way the live demo embarrasses itself.

## 3. BUY/SELL guard — precise, not a blocklist

Block advisory output without false-positives on legitimate prose. Match advisory **intent**, not substrings:
- Block: imperative recommendations to transact — "buy", "sell", "accumulate", "trim", "take profits", "go long/short", "exit", a price target framed as an instruction.
- Allow: descriptive uses — "sell-side consensus", "buyback", "holding period", "buyers returned", "the bull case". Use phrase/context rules, and keep a test fixture of allow/deny examples.

## 4. Attack-bias disclosure (turns a weakness into a differentiator)

LLMs carry a documented **contrarian bias** in investment analysis — a thesis-attacker is structurally prone to manufacturing doubt, and the `vulnerable` crack-type is the easy escape hatch ("fragile" can be asserted about anything). Mitigations, surfaced honestly:
- `vulnerable` cracks **require a citation** (per `scoring.md`); an uncited `vulnerable` claim is rejected as speculation.
- The report shows an **attack-bias note**: the share of cracks that are cited-contradicted vs uncited-vulnerable, so the user can see when the Bear is reaching. A map that is all `vulnerable` and no `contradicted` is flagged low-conviction.

## Evaluation additions (add to `evaluation.md`)

| # | Scenario | Expected | Proves |
|---|----------|----------|--------|
| **E6** | Inject a thesis figure absent from the corpus | It is stripped, not echoed with a borrowed citation; the claim is flagged. | Faithfulness gate (§1). |
| **E7** | Ask about a claim with no covering document | Returns a `data_gap` (lowers data_completeness), **not** an `unsupported` crack. | Coverage probe (§2). |
| **E8** | Run the same thesis 3× | Same `thesis_robustness` and same high-severity cracks each time (modulo retrieval noise). | Deterministic scoring (`scoring.md`). |
| **E9** | Paste a fabricated quote into a crack | The crack is rejected (quote not in retrieved extract). | Anti-fabrication gate (§1.2). |

## Why this is the win-critical work

The judge doesn't attack the architecture — they click one ⚡ crack and open the source. With this spec, that click **confirms** the claim. Without it, one mis-resolving citation collapses the entire "audit-grade" positioning. Faithfulness + coverage are not polish; they are the difference between winning and a public faceplant.
