"""render.py — deterministic JSON → HTML report (EPIC-04). No LLM. Conflict map is the headline.

Pure function of the brief: the same brief renders byte-identical HTML (ADR-0005). The conflict map
leads (before the analysis sections), carries the attack-bias disclosure (reliability-spec §4), and
surfaces stripped/uncited figures. A render-time guard asserts no BUY/SELL/HOLD rating ever ships.
"""
from __future__ import annotations
import html as _h
import re

_VERDICT = {
    "Holds": ("#0a7d33", "#e7f6ec", "Holds"),
    "Contested": ("#b06a00", "#fdf3e3", "Contested"),
    "Breaks": ("#b3261e", "#fbe9e7", "Breaks"),
}
_SEV = {"high": ("#b3261e", "⚡⚡⚡"), "medium": ("#b06a00", "⚡⚡"), "low": ("#5f6368", "⚡")}
_RATING = re.compile(r"\b(BUY|SELL|HOLD)\b")   # the rating convention must never appear (AC-3)


def _esc(s) -> str:
    return _h.escape(str(s if s is not None else ""))


def _claim_text(claims, cid):
    for c in claims:
        if c.get("id") == cid:
            return c.get("claim", cid)
    return cid


def _attack_bias_html(ab: dict) -> str:
    """The §4 disclosure: cited-contradicted vs uncited-vulnerable, with a low-conviction flag."""
    if not ab:
        return ""
    ratio = ab.get("ratio")
    ratio_txt = f"ratio {ratio}" if ratio is not None else "ratio n/a"
    flag = ('<span class="lc">low-conviction — all-vulnerable, no cited contradiction</span>'
            if ab.get("low_conviction") else "")
    return (f'<div class="bias">attack-bias: '
            f'<b>{_esc(ab.get("cited_contradicted", 0))}</b> cited-contradicted vs '
            f'<b>{_esc(ab.get("uncited_vulnerable", 0))}</b> uncited-vulnerable · {ratio_txt} {flag}</div>')


def _cracks_html(cmap, claims) -> str:
    out = ""
    for c in cmap:
        sc, ze = _SEV.get(c["severity"], ("#5f6368", "⚡"))
        cites = " ".join(f"<span class=cite>{_esc(x)}</span>" for x in c.get("citations", [])) \
            or "<span class=nocite>no citation — unsupported</span>"
        flag = ('<span class="figflag">⚠ figure unverified — stripped</span>'
                if c.get("figure_flagged") else "")
        out += f"""
        <div class="crack" style="border-left-color:{sc}">
          <div class="crackhead">
            <span class="sev" style="color:{sc}">{ze} {c['severity'].upper()}</span>
            <span class="ctype">{_esc(c['crack_type'])}</span>
            <span class="lenses">{_esc(', '.join(c.get('lenses', [])))}</span>
            {flag}
          </div>
          <div class="point">{_esc(c['point'])}</div>
          <div class="claim">tests load-bearing claim: <em>{_esc(_claim_text(claims, c['claim_id']))}</em></div>
          <div class="resolve"><b>What would resolve it:</b> {_esc(c.get('what_would_resolve_it'))}</div>
          <div class="cites">evidence: {cites} &middot; raised by {_esc(', '.join(c.get('stances', [])))}</div>
        </div>"""
    return out


def _lens_coverage_html(active_lenses, sources) -> str:
    """Every active lens is shown; a lens with no retrieved evidence renders as `thin` (never omitted)."""
    with_ev = {s.get("lens") for s in (sources or [])}
    chips = ""
    for lens in (active_lenses or []):
        thin = lens not in with_ev
        cls = "lens-thin" if thin else "lens-ok"
        label = f"{_esc(lens)} · thin" if thin else _esc(lens)
        chips += f'<span class="{cls}">{label}</span> '
    return chips or '<span class=sub>no lenses active</span>'


def html(brief: dict) -> str:
    ent = brief.get("entity") or {}
    name = ent.get("name") or ent.get("ticker") or "the entity"
    vc, vbg, vlabel = _VERDICT.get(brief["thesis_robustness"], ("#5f6368", "#eee", brief["thesis_robustness"]))
    claims = brief.get("claims", [])
    cmap = brief.get("conflict_map", [])

    banner = ('<div class="banner">⚠ SAMPLE / MOCKUP RUN — illustrative data, not a live retrieval</div>'
              if ent.get("sample") else "")
    cracks_html = _cracks_html(cmap, claims)
    bias_html = _attack_bias_html(brief.get("attack_bias") or {})
    lens_html = _lens_coverage_html(brief.get("active_lenses"), brief.get("sources"))

    claims_html = "".join(
        f"<li>{'<b>★ </b>' if c.get('load_bearing') else ''}{_esc(c.get('claim'))} "
        f"<span class=tag>{_esc(c.get('horizon'))}</span></li>" for c in claims)

    src_html = "".join(
        f"<div class=src><span class=cite>{_esc(s['id'])}</span> <span class=tag>{_esc(s['lens'])}</span> {_esc(s['content'][:400])}…</div>"
        for s in brief.get("sources", [])[:20])

    out = f"""<!doctype html><html lang=en><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Thesis Red-Team — {_esc(name)}</title>
<style>
:root{{--ink:#1a1a1a;--mut:#5f6368;--line:#e3e3e3}}
*{{box-sizing:border-box}}
body{{font:16px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);max-width:820px;margin:0 auto;padding:32px 20px;background:#fafafa}}
h1{{font-size:26px;margin:0 0 2px}} .sub{{color:var(--mut);margin:0 0 20px}}
.banner{{background:#fff7e6;border:1px solid #b06a0044;color:#8a5200;border-radius:10px;padding:10px 14px;margin:0 0 16px;font-size:13px;font-weight:600}}
.verdict{{display:flex;align-items:center;gap:16px;background:{vbg};border:1px solid {vc}33;border-radius:14px;padding:18px 20px;margin:18px 0}}
.vbadge{{font-size:30px;font-weight:800;color:{vc};letter-spacing:-.5px}}
.vmeta{{color:var(--mut);font-size:14px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:30px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.brief{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.bias{{font-size:13px;color:var(--mut);margin:2px 0 12px}}
.bias .lc{{background:#fdf3e3;color:#8a5200;border-radius:6px;padding:1px 8px;margin-left:6px;font-weight:600}}
.crack{{background:#fff;border:1px solid var(--line);border-left:4px solid;border-radius:10px;padding:14px 16px;margin:10px 0}}
.crackhead{{display:flex;gap:12px;align-items:center;font-size:12px;margin-bottom:6px;flex-wrap:wrap}}
.sev{{font-weight:700}} .ctype{{background:#f1f1f1;border-radius:20px;padding:1px 9px;text-transform:uppercase;font-size:11px;letter-spacing:.04em}}
.figflag{{background:#fbe9e7;color:#b3261e;border-radius:6px;padding:1px 8px;font-size:11px;font-weight:600}}
.lenses{{color:var(--mut)}} .point{{font-weight:600;margin:2px 0}} .claim{{color:var(--mut);font-size:14px}}
.resolve{{font-size:14px;margin-top:7px}} .cites{{font-size:12px;color:var(--mut);margin-top:7px}}
.cite{{background:#eef3ff;color:#234;border-radius:5px;padding:1px 6px;font:600 12px ui-monospace,monospace}}
.nocite{{color:#b06a00}}
.lens-ok{{background:#e7f6ec;color:#0a7d33;border-radius:20px;padding:1px 10px;font-size:12px;margin-right:4px}}
.lens-thin{{background:#f1f1f1;color:#8a5200;border-radius:20px;padding:1px 10px;font-size:12px;margin-right:4px}}
ul{{padding-left:20px}} li{{margin:3px 0}} .tag{{background:#f1f1f1;border-radius:20px;padding:0 8px;font-size:11px;color:var(--mut)}}
.src{{font-size:13px;color:#333;border-bottom:1px solid var(--line);padding:8px 0}}
.foot{{margin-top:28px;font-size:12px;color:var(--mut);border-top:1px solid var(--line);padding-top:12px}}
</style>
{banner}<h1>Thesis Red-Team — {_esc(name)}</h1>
<p class=sub>Kintsugi conflict map · grounded in public filings via Microsoft Foundry IQ · cite-or-silence</p>

<div class=verdict>
  <div class=vbadge>{_esc(vlabel)}</div>
  <div class=vmeta>thesis robustness · confidence {_esc(brief.get('confidence'))} · data completeness {_esc(brief.get('data_completeness'))}<br>
  {len(cmap)} crack(s) · equity lean: {_esc(brief.get('equity_lean'))}</div>
</div>

<h2>Conflict map — cracks, ranked by severity</h2>
{bias_html}
{cracks_html or '<p class=sub>No cracks survived the gates.</p>'}

<h2>CIO brief</h2>
<div class=brief>{_esc(brief.get('brief')) or '—'}</div>

<h2>The thesis under test</h2>
<ul>{claims_html}</ul>
<p class=sub style="font-size:13px">★ = load-bearing (the thesis rests on it)</p>

<h2>Lens coverage</h2>
<p>{lens_html}</p>

<h2>Evidence (Foundry IQ retrieved)</h2>
{src_html}

<div class=foot>
<b>Analysis, not advice.</b> This is analytical commentary on the robustness of a user-supplied thesis, grounded only in the cited public documents. It issues no transact recommendation or rating and must not be relied upon for financial decisions. Outputs may be incomplete or wrong.
</div>
</html>"""
    assert not _RATING.search(out), "render-time compliance guard: BUY/SELL/HOLD rating must never ship"
    return out
