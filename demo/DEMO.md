# Demo video — script & storyboard

Target: **2–3 minutes**. Goal: show *grounded, adversarial reasoning that refuses to fabricate* — the two things judges reward most (Reasoning 20% + Reliability 20%).

## Link

> Add the recorded video URL here before submission: `<video-url>`

## Shot list

| # | Time | On screen | Say (voiceover) |
|---|------|-----------|-----------------|
| 1 | 0:00–0:20 | Title + architecture.svg | "You bring an investment thesis; the agents try to break it. Bull steelmans it, Bear and Caution attack it across six lenses against public filings via Foundry IQ, and the CIO maps the cracks." |
| 2 | 0:20–0:40 | Terminal: `run_example.py --thesis my-thesis.txt` | "One command. The thesis is split into claims; each stance tests them against the Foundry IQ knowledge base — every claim carries a citation." |
| 3 | 0:40–1:10 | Bull + Bear outputs side by side | "The Bull builds the long case; the Bear the negative case — over the same evidence. Notice the citations on each point." |
| 4 | 1:10–1:35 | Caution output | "Caution isn't a fence-sitter — it finds what breaks the thesis and flags where the data is thin." |
| 5 | 1:35–2:05 | CIO brief — Kintsugi conflict map | "The CIO returns the conflict map: every crack in the thesis, ranked by severity, each cited — and a robustness verdict: Holds, Contested or Breaks." |
| 6 | 2:05–2:30 | **Missing-evidence probe (E2)** | "Ask about a figure that isn't in the documents — it says so and lowers confidence. It will not invent a number." |
| 7 | 2:30–2:45 | **No-advice probe (E3)** + disclaimer | "Push it to say 'buy' — it won't. Analysis, not advice. Bullish/Caution/Bearish only." |
| 8 | 2:45–3:00 | Repo + Foundry IQ on screen | "Built on Microsoft Foundry with Foundry IQ. Public data, clean-room, MIT-licensed. Thanks for watching." |

## Recording notes

- Lead with the *behaviour*, not the architecture — show it refusing to fabricate (shots 6–7); that's the memorable moment.
- Keep terminal output legible (large font, trimmed JSON).
- Capture E2 and E3 from `docs/evaluation.md`