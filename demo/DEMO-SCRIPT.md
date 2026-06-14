# DEMO-SCRIPT.md — 2–3 min recording script (runs from a SAVED run)

**This demo is recorded from a pre-recorded saved run — it is NOT live.** It replays
[`demo/saved-run.json`](./saved-run.json) (the real 2026-06-13 Foundry IQ run on the NVDA bull
thesis), so judges see deterministic, reproducible behaviour with zero spend and zero risk of a
live-call wobble on stage. The companion storyboard with timestamps is [`demo/DEMO.md`](./DEMO.md).

> **Recording instructions (human):** capture screen + voiceover to **`demo/demo.mp4`**, target
> **110–200 s** (2–3 min). Keep terminal text large; trim JSON to the cited cracks. Do not run the
> live pipeline on camera — drive everything from `demo/saved-run.json` / `out/saved-report.html`.

## The money moment — lead with this

The headline is the **refuse-to-fabricate** behaviour and a **cited `contradicted` crack flipping
the verdict**, not the architecture. Open on the result, then explain how it got there.

- **Verdict flip:** the saved run returns **`Breaks`** — the thesis does **not** survive. It breaks on
  load-bearing claim **c3** ("continued access to the large China market"): NVIDIA's own 10-K says it
  is *"already effectively foreclosed from the China market by U.S. export controls"* — a **cited
  `contradicted` crack** (`S10, S8, S9`), China revenue **$25.0B → $19.7B**. A real objection, drawn
  from the public record, flips a confident bull thesis. That is the product.
- **E6 — faithfulness (strip the unverifiable figure):** show that a figure absent from the cited
  extract is **stripped and flagged** (`[figure unverified]`), never echoed with a borrowed citation.
- **E9 — anti-fabrication (reject the fabricated quote):** show that a crack whose quote appears in
  **no** retrieved extract is **rejected entirely** — the system would rather say less than make
  something up. Cite-or-silence.

These three beats (contradicted-crack flip → E6 → E9) are the first 60 seconds. Everything else is
support.

## Shot list (drives from the saved run)

| # | Time | On screen | Say (voiceover) |
|---|------|-----------|-----------------|
| 1 | 0:00–0:20 | `out/saved-report.html` — verdict **Breaks** + Kintsugi conflict map | "You bring an investment thesis. The agents try to break it. This NVIDIA bull thesis **Breaks** — and here's the crack that did it." |
| 2 | 0:20–0:50 | The **c3 China** cited contradicted crack (`S10, S8, S9`) | "NVIDIA's *own* 10-K says it's already foreclosed from China by export controls — China revenue fell $25.0B to $19.7B. A cited contradiction, from the public record, flips the thesis." |
| 3 | 0:50–1:20 | **E6** faithfulness — stripped `[figure unverified]` | "When a figure isn't in the cited document, it's stripped and flagged — never echoed with a borrowed citation." |
| 4 | 1:20–1:45 | **E9** anti-fabrication — rejected fabricated quote | "Paste in a quote that isn't in any retrieved extract and the whole crack is rejected. It refuses to fabricate." |
| 5 | 1:45–2:15 | Bull / Bear / Caution + CIO map | "Bull steelmans, Bear and Caution attack across lenses against public filings via **Foundry IQ**, the CIO ranks every crack by severity — Holds, Contested, or **Breaks**." |
| 6 | 2:15–2:40 | **E3** no-advice probe + disclaimer | "Push it to say 'buy' — it won't. Analysis, not advice." |
| 7 | 2:40–3:00 | Repo + Foundry IQ | "Grounded in Microsoft Foundry IQ. Public data, clean-room. Determinism, eval evidence in `evals/`. Thanks for watching." |

## Why this is honest

Every figure on screen is in [`demo/saved-run.json`](./saved-run.json) and carries an `Sx` citation
resolving to a retrieved Foundry IQ extract. The verdict is computed deterministically (the LLM
narrates but cannot change it), so the same saved run renders the same verdict every time — proven by
eval **E8** (see [`evals/EVIDENCE.md`](../evals/EVIDENCE.md)).
