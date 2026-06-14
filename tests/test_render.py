"""TESTPLAN-04.1.01 — render.py deterministic HTML.

Conflict-map headline, citation traceability (stripped/uncited figures), BUY/SELL/HOLD absence,
attack-bias note (§4), thin-lens rendering + mockup-banner gating, and byte-deterministic output.
Fixture-driven, fully offline. Test names embed the -k selectors."""
import copy
import json
import os

import render

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "brief.json")


def _brief():
    return json.load(open(_FIXTURE, encoding="utf-8"))


def test_conflict_map_headline():
    """AC-1 · the conflict-map section renders before the analysis sections."""
    out = render.html(_brief())
    cm = out.index("Conflict map")
    assert cm < out.index("CIO brief")
    assert cm < out.index("The thesis under test")
    assert cm < out.index("Evidence")


def test_uncited_stripped():
    """AC-2 · a flagged/stripped figure shows the unverified marker (not the raw number); an
    uncited crack shows the no-citation marker."""
    out = render.html(_brief())
    assert "figure unverified" in out          # the stripped-figure flag is surfaced
    assert "44%" not in out                     # the unverifiable figure never reaches the page
    assert "no citation" in out                 # the uncited unsupported crack is marked


def test_no_advice_strings():
    """AC-3 · the rendered HTML contains none of BUY/SELL/HOLD (render-time guard passes)."""
    out = render.html(_brief())
    for tok in ("BUY", "SELL", "HOLD"):
        assert tok not in out


def test_thin_lens_and_banner():
    """AC-4 · a lens with no evidence renders as `thin`; the mockup banner appears only when sample."""
    out = render.html(_brief())
    assert "esg · thin" in out                  # esg is active but has no retrieved evidence
    assert "SAMPLE / MOCKUP RUN" not in out     # sample == false → no banner

    sample = copy.deepcopy(_brief())
    sample["entity"]["sample"] = True
    assert "SAMPLE / MOCKUP RUN" in render.html(sample)


def test_byte_deterministic():
    """AC-5 · the same brief renders byte-identical HTML."""
    assert render.html(_brief()) == render.html(_brief())


def test_attack_bias_note_rendered():
    """AC-1/§4 · the attack-bias ratio renders near the conflict map; an all-vulnerable map shows
    the low-conviction flag."""
    out = render.html(_brief())
    assert "attack-bias" in out and "ratio 2.0" in out

    low = copy.deepcopy(_brief())
    low["attack_bias"] = {"cited_contradicted": 0, "uncited_vulnerable": 3, "contradicted": 0,
                          "vulnerable": 3, "ratio": 0.0, "low_conviction": True}
    assert "low-conviction" in render.html(low)
