#!/usr/bin/env python3
"""run_example.py — one-command demo (EPIC-04). thesis → cited Kintsugi brief + HTML report."""
from __future__ import annotations
import os, sys, json, argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))
import agent, render  # noqa: E402

# LLM-generated crack prose can contain Unicode (→, em dashes, curly quotes); the Windows console
# defaults to cp1252 and would crash on print. Force UTF-8 stdout/stderr (BUG-20260614-01).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def main():
    ap = argparse.ArgumentParser(description="Red-team an investment thesis.")
    ap.add_argument("--thesis", required=True, help="path to a thesis .txt")
    ap.add_argument("--html", help="write the HTML report here")
    ap.add_argument("--json", help="write the brief JSON here")
    a = ap.parse_args()

    try:
        thesis = open(a.thesis, encoding="utf-8").read().strip()
    except OSError as e:
        print(f"error: cannot read thesis file '{a.thesis}': {e}", file=sys.stderr)
        sys.exit(2)
    if not thesis:
        print(f"error: thesis file '{a.thesis}' is empty - provide a bull-thesis paragraph", file=sys.stderr)
        sys.exit(2)

    brief = agent.run(thesis)

    print(f"\n=== VERDICT: {brief['thesis_robustness']} "
          f"(confidence {brief['confidence']}, data completeness {brief['data_completeness']}) ===")
    print(f"cracks: {len(brief['conflict_map'])} | equity lean: {brief['equity_lean']} | "
          f"compliance_ok: {brief['compliance_ok']} | {brief['telemetry'].get('total_s')}s")
    for c in brief["conflict_map"][:6]:
        print(f"  [{c['severity']:>6}] {c['crack_type']:<12} {c['claim_id']} {c['citations']} :: {c['point'][:110]}")

    if a.json:
        os.makedirs(os.path.dirname(a.json) or ".", exist_ok=True)
        open(a.json, "w", encoding="utf-8").write(json.dumps(brief, indent=2))
        print(f"brief JSON  -> {a.json}")
    if a.html:
        os.makedirs(os.path.dirname(a.html) or ".", exist_ok=True)
        open(a.html, "w", encoding="utf-8").write(render.html(brief))
        print(f"HTML report -> {a.html}")


if __name__ == "__main__":
    main()
