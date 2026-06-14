"""TESTPLAN-03.1.01 — citations.py faithfulness gate (reliability-spec §1).

quote-contains-figure (E6, strip+flag, crack survives), quote-in-extract (E9, reject), the
strip-vs-reject distinction for contradicted cracks, the doc-level severity cap, and the
attack-bias disclosure (§4). Pure-logic with inline fixtures, fully offline. Test names embed the
-k selectors."""
import citations


def test_e6_strip_figure_crack_survives():
    """AC-1 (E6) · a prose figure absent from the quote is stripped + flagged; the crack survives
    because it keeps valid cited support (quote IS in the extract)."""
    points = [{
        "claim_id": "c1", "crack_type": "contradicted", "stance": "bear", "lens": "risk",
        "point": "Gross margin fell to 44% on export controls.",
        "quote": "gross margin compression on export controls",
        "citations": ["S1"],
    }]
    extracts = {"S1": "the 10-K notes gross margin compression on export controls hit the segment"}
    out = citations.faithful(points, {"S1"}, extracts)
    assert len(out) == 1                          # crack survives
    assert "44%" not in out[0]["point"]           # unverifiable figure stripped
    assert out[0]["figure_flagged"] is True
    assert "44%" in out[0]["stripped_figures"]


def test_e9_reject_fabricated_quote():
    """AC-2 (E9) · a quote that is not a substring of the retrieved extract is a fabricated citation
    → the whole crack is rejected."""
    points = [{
        "claim_id": "c1", "crack_type": "contradicted", "stance": "bear",
        "point": "China revenue collapses 30%.",
        "quote": "the company will permanently lose all china revenue",
        "citations": ["S1"],
    }]
    extracts = {"S1": "china export controls may reduce data-center revenue in some quarters"}
    out = citations.faithful(points, {"S1"}, extracts)
    assert out == []                              # fabricated → not displayed


def test_contradicted_suppressed_only_on_extract_fail():
    """AC-3 · a contradicted crack is absent ONLY on quote-in-extract failure; a quote-contains-figure
    failure leaves the crack present (figure stripped)."""
    survives = {
        "claim_id": "c1", "crack_type": "contradicted", "stance": "bear",
        "point": "Margin compressed by 44%.",                       # figure-fail only
        "quote": "the filing reports margin compression in the period",
        "citations": ["S1"],
    }
    rejected = {
        "claim_id": "c2", "crack_type": "contradicted", "stance": "bear",
        "point": "Revenue zeroed out.",
        "quote": "revenue will go to absolute zero forever",         # extract-fail
        "citations": ["S2"],
    }
    extracts = {
        "S1": "the filing reports margin compression in the period",
        "S2": "revenue grew modestly with some headwinds",
    }
    out = citations.faithful([survives, rejected], {"S1", "S2"}, extracts)
    kept = {p["claim_id"] for p in out}
    assert kept == {"c1"}                          # figure-fail kept, extract-fail dropped
    kept_point = next(p for p in out if p["claim_id"] == "c1")
    assert "44%" not in kept_point["point"] and kept_point["figure_flagged"] is True


def test_doc_level_cap():
    """AC-4 · a crack pinned only to a doc-level locator is capped at medium severity; a pinpoint
    locator is left untouched. The gate also annotates `severity_cap` on a doc-level point."""
    assert citations.cap_severity("high", "doc-level") == "medium"
    assert citations.cap_severity("high", "p.42") == "high"        # pinpoint not capped
    assert citations.cap_severity("medium", "doc-level") == "medium"
    assert citations.cap_severity("low", "doc-level") == "low"     # nothing to cap below medium

    points = [{
        "claim_id": "c1", "crack_type": "contradicted", "stance": "bear",
        "point": "Demand is softening.", "quote": "demand is softening",
        "citations": ["S1"], "locator": "doc-level",
    }]
    out = citations.faithful(points, {"S1"}, {"S1": "the report says demand is softening"})
    assert out[0]["severity_cap"] == "medium"


def test_attack_bias_ratio():
    """AC-5 · the gate exposes cited-contradicted vs uncited-vulnerable counts + ratio; an
    all-vulnerable / no-contradicted set is flagged low_conviction."""
    mixed = [
        {"crack_type": "contradicted", "citations": ["S1"]},
        {"crack_type": "vulnerable", "citations": []},
        {"crack_type": "vulnerable", "citations": []},
    ]
    bias = citations.attack_bias(mixed)
    assert bias["cited_contradicted"] == 1
    assert bias["uncited_vulnerable"] == 2
    assert bias["ratio"] == 0.5
    assert bias["low_conviction"] is False        # a real contradicted crack exists

    all_vulnerable = [
        {"crack_type": "vulnerable", "citations": []},
        {"crack_type": "vulnerable", "citations": ["S3"]},
    ]
    assert citations.attack_bias(all_vulnerable)["low_conviction"] is True
