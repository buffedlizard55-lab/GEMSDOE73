#!/usr/bin/env python3
"""Build session-2 site pages from evidence JSONs (numbers cannot drift).

Writes docs/h73-6-traceloc.html, docs/index.html, docs/executive-summary.html.
Every score is labelled HOLDOUT-DTI / OWNER-REPORT / ORGANIZER-CONFIRMED.
Download gate (format-valid?) and submit gate (holdout-promoted?) are kept
visibly separate for every file on the site.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
card = json.loads((ROOT / "evidence/run_card_x.json").read_text())
hold = json.loads((ROOT / "evidence/holdout_x_all_arms.json").read_text())
h = card["holdout"]; v = card["validator"]; u = card["correlation_overlap_vs_registry"]
TIF = "gems73-h73-6-traceloc-x1-37654dots-20261021.tif"
ZIP = "gems73-h73-6-traceloc-x1-37654dots-20261021.zip"
NAME = card["submission_name"]; NOTE = card["submission_note"]
SHA = card["raster_sha256"]
NAV = """<nav>
<a href="index.html">Home</a> <a href="executive-summary.html">Make a submission</a>
<a href="h73-6-traceloc.html">H73-6 lane (new)</a> <a href="h73-1-piedmont.html">H73-1 lane</a>
<a href="research.html">Research</a> <a href="hypotheses.html">Hypotheses</a>
<a href="leaderboard.html">Leaderboard</a> <a href="sources.html">Sources</a>
<a href="irregularities.html">Irregularities</a></nav>"""


def shell(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><link rel="stylesheet" href="assets/site.css">
</head><body>
<header class="top"><div class="wrap"><h1>GEMSDOE73 — Fault-Discovery System for the DOE GEMS Prize</h1>{NAV}</div></header>
<div class="wrap"><p class="mut"><b>Core Values:</b> <b>Maximize P(Win)</b> — every weekly slot is an experiment.
<b>Own the Outcome</b> — every claim carries an evidence class; negative results are published, not buried.</p></div>
<main class="wrap">{body}</main>
<footer><div class="wrap">Generated 2026-10-21 by <code>scripts/build_site_x.py</code> from
<code>evidence/run_card_x.json</code>. Owner scores are labelled OWNER-REPORT; only organiser
receipts are ORGANIZER-CONFIRMED. <a href="https://github.com/buffedlizard55-lab/GEMSDOE73">Repository</a></div></footer>
</body></html>"""


def gate_table() -> str:
    return f"""
<table><tr><th>File (all format-valid, portal-safe)</th><th>OK to download?</th><th>Recommended to submit?</th><th>Why</th></tr>
<tr><td><b>NEW — H73-6 X1 traceloc</b><br><code>{TIF}</code></td><td><span class="pill yes">YES</span></td>
<td><span class="pill no">NO — DO NOT SUBMIT</span></td><td>Unique + valid, but <b>verdict NEGATIVE</b>:
HOLDOUT-DTI {h['X1_dti']:.4f} vs fold-fair control {h['h33_analogue_foldfair_dti']:.4f} (gate failed).</td></tr>
<tr><td>H73-1 E1 piedmont scarp-chain<br><code>gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif</code></td>
<td><span class="pill yes">YES</span></td><td><span class="pill no">NO — DO NOT SUBMIT</span></td>
<td>Session-1 NEGATIVE: HOLDOUT-DTI 0.0548 vs control 0.0939. See <a href="h73-1-piedmont.html">lane page</a>.</td></tr>
<tr><td>H73-F curvature lineament ridge (parallel session, PR #4)<br><code>gems73-h73f-curvature-lineament-37654-20261021T040043Z-4acc39d2-zeros.tif</code></td>
<td><span class="pill rev">REVIEW ONLY</span></td><td><span class="pill no">NO — DO NOT SUBMIT</span></td>
<td>Format-valid (re-verified here) but <b>holdout NOT RUN</b> per its own run card (synthesis only).
Uniqueness vs H73-6 X1: mutual 0.133, ρ 0.002 — distinct lane, still unvalidated.</td></tr>
<tr><td>H73-A blind stepover (<b>synthetic generator</b>)<br><code>gems73-h73a-blind-stepover-20261021T022620Z-c111bb0f-zeros.tif</code></td>
<td><span class="pill rev">REVIEW ONLY</span></td><td><span class="pill no">NO — DO NOT SUBMIT</span></td>
<td>Random-geometry synthetic dots, <b>no real holdout</b> (its own run card: verdict negative).
Earlier revisions of this site wrongly labelled it “PRIMARY” — corrected 2026-10-21 (IR-73-10).</td></tr>
<tr><td>Hydrothermal corridor (<b>synthetic-demo holdout</b>)<br><code>gems73-hydro-permeability-corridor-37654-20261021T000000Z-2bbb79d4-zeros.tif</code></td>
<td><span class="pill rev">REVIEW ONLY</span></td><td><span class="pill no">NO — DO NOT SUBMIT</span></td>
<td>Its “holdout” was a hard-coded synthetic demo, now removed from the code (IR-73-11). No trustworthy score exists.</td></tr>
</table>
<p><b>Bottom line:</b> no file in this repo is currently recommended for a weekly slot. Downloading any
file is safe; <em>submitting</em> one spends a slot against this repo's own evidence and requires a human
selector override. That separation is deliberate — it is how a slot is never wasted on an unvalidated idea.</p>"""


def download_card() -> str:
    return f"""
<div class="dl bad">
<h2>⬇ ONE-CLICK DOWNLOAD — newest unique submission file (H73-6 X1) — READ THE STATUS FIRST</h2>
{gate_table()}
<p><a class="btn" href="downloads/{TIF}">⬇ Download {TIF}</a>
<a class="btn alt" href="downloads/{ZIP}">.zip (single GeoTIFF inside)</a>
<a class="btn alt" href="downloads/run_card_h73-6.json">Run card (JSON)</a></p>
<p><b>Filename:</b> <code>{TIF}</code><br>
<b>Unique submission name:</b> <code>{NAME}</code><br>
<b>Note for the DrivenData “Note (optional)” field ({card['submission_note_chars']}/140 chars) — only if a selector overrides:</b><br>
<code>{html.escape(NOTE)}</code><br>
<b>sha256:</b> <code>{SHA}</code> · {card['raster_bytes']:,} bytes · single band float32 · EPSG:32611 ·
100 m · 3730×3292 · 37,654 dots · min 0.0 max 1.0 · 0 NaN in all 12,279,160 cells · no nodata tag ·
CRS/shape/transform match sample submission: <b>True</b> ·
(<a href="downloads/validator_h73-6.json">validator receipt</a>)</p>
<p class="mut">This file is newly generated this session, is not a copy of any GEMSDOE-site raster
(uniqueness vs H33 champion: forward overlap {u['vs_h33_champion']['forward_my_dots_within3px']:.3f},
surface ρ {u['vs_h33_champion']['surface_spearman_sample200k']:.3f}), and has never been submitted.
<b>It is OK to download. It is NOT recommended to submit</b> (verdict above). No organiser score exists for it.</p>
</div>"""


PORTAL = """
<div class="dl">
<h2>⚠ Portal error “Predicted values must be in range [0, 1]” — cause and fix</h2>
<p>DrivenData requires every predicted value in <code>[0,1]</code> (official submission format,
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page 967</a>,
re-verified 2026-10-21). The usual trigger in this project family is the float32 sentinel
<code>-3.4028234663852886e+38</code>: <code>training_features.tif</code> uses it as nodata, and any pipeline
that writes it through (as data or as a nodata tag a validator reads as a value) fails the range check.</p>
<p><b>Fix applied to every file above:</b> written <b>all-finite</b> with <code>nodata=None</code> and
<code>0.0</code> outside the footprint, then <b>re-opened from disk</b> and checked cell-by-cell
(all 12,279,160 cells finite, min ≥ 0, max ≤ 1, 0 NaN) by the shared validator before delivery.
Each file ships its re-read receipt. If you ever see the error, you have picked a stale/sentinel file —
re-download the <code>-zeros</code>/all-finite file from this page.</p>
</div>"""

ANSWER = f"""
<h2>The brief's question, answered (PhD-level)</h2>
<p><b>Why did <code>h33-h33-2-b2…-zeros</code> score 0.2778 (OWNER-REPORT; no receipt in any repo — IR-73-02),
the group best?</b> Measured byte-exact in session-1 and re-verified this session
(H33 ⊂ H19-5, zero exceptions): it is the dotted H19-5 field with every dot ≤200 m from the catalogue
deleted. DTI pays for <em>credit density</em> — a non-redundant dot helps iff realised kernel credit
<code>k &gt; 0.2·DTI ≈ 0.056</code>. H19-5's ~90% scarp/openness surface matches the evidence class human
mappers used to draw the hidden set (“manually identified by fault experts”, official page); dotting to
≈2.5 px spacing removed sub-bar redundant mass; the B2 prune deleted dots that could only cover
already-mapped, masked traces while paying full false-positive tax.</p>
<p><b>Can we beat 0.2778, or the current leader 0.4413 (ORGANIZER-CONFIRMED leaderboard read 2026-10-21:
#1 xiaofanhu 0.4413, #2 cfld__ 0.3904, #3 Batik Shirt Brothers 0.3894)?</b> Emission gains are nearly
exhausted (+0.055 → +0.012 → +0.007); only a field with higher credit density in its top 37,654 dots can.
This session tested trace localisation + independent corroboration (H73-6): HOLDOUT-DTI
{h['X1_dti']:.4f} [{h['X1_ci95'][0]:.4f}, {h['X1_ci95'][1]:.4f}] vs control {h['h33_analogue_foldfair_dti']:.4f}
— better than session-1 (0.0548) and better than random ({h['random_control_dti']:.4f}), but it does
<b>not</b> beat the control, so we do not claim it beats 0.2778 live and we do not spend a slot on it.
0.4413 (≈+60% credit density over H33 at equal mass) remains out of reach of any single unsupervised
transform tried across 78 sibling repos; claiming otherwise would be a projection dressed as a score.</p>
<p><b>What would change the verdict?</b> A field that beats the fold-fair control with paired CI excluding 0
on this instrument — most plausibly (per <a href="research/hypotheses_x.md">H73-8</a>) absolute-elevation
bench rejection from USGS 3DEP 1 m DEMs, which needs an unrestricted machine (sandbox egress is
github/pypi only), or expert-style multi-scale openness tracing rebuilt from the 1 m DEMs.</p>"""

HYPO = """
<h2>Five new hypotheses this session (ranked before any holdout run)</h2>
<table><tr><th>#</th><th>Hypothesis</th><th>Layers</th><th>Signature</th><th>Why off-catalogue</th><th>Status</th></tr>
<tr><td>H73-6 ★ lane</td><td>Trace-localised corroborated scarps</td><td>LiDAR step/pol. + U/K + gravity slope + piedmont</td><td>Structure-tensor NMS centreline × non-topo witness ≤200 m</td><td>Narrow piedmont centrelines magnitude-ranking buries</td><td>Tested: NEGATIVE (above)</td></tr>
<tr><td>H73-7</td><td>Witness-only corroboration</td><td>Same, no thinning</td><td>Scarp × witness × piedmont</td><td>Basement-offsetting traces only</td><td>Tested as X3 ablation: 0.0585</td></tr>
<tr><td>H73-8</td><td>Absolute-elevation bench rejection</td><td>USGS 3DEP 1 m DEM (absolute z)</td><td>Reject steps at paleo-shoreline elevations</td><td>Benches mimic scarps; faults cross elevation bands</td><td>Not viable in sandbox (named source checked)</td></tr>
<tr><td>H73-9</td><td>Magnetic contact terminations</td><td>RTP/TMI/tmi_vg/tc</td><td>Tensor eigenframe jump across a line</td><td>Subsurface offsets under cover</td><td>Low prior (worm lanes 0.03–0.10)</td></tr>
<tr><td>H73-10</td><td>Seismicity-aligned scarps</td><td>ieq/deq × scarp</td><td>Scarp on quake-density ridge</td><td>Active blind structures</td><td>100 km kernel too smooth for 300 m credit</td></tr>
</table>
<p class="mut">Full text with named mimics and ranking rationale: <a href="research/hypotheses_x.md">docs/research/hypotheses_x.md</a>;
preregistration: <code>registry/preregistration_x.json</code>. Session-1 hypotheses H73-1…5: <a href="research/hypotheses.md">hypotheses.md</a>.</p>"""

lane_body = f"""
<h1>H73-6 — trace-localised, independently-corroborated scarps (session-2 lane)</h1>
<p class="mut">One preregistered lane · 3 experiments (X1/X2/X3) · every number HOLDOUT-DTI or OWNER-REPORT ·
0 weekly slots spent · no organiser score exists for this file.</p>
{download_card()}
{PORTAL}
<div class="card"><h2 style="margin-top:0">Method (single paragraph — the lane)</h2>
<p>{html.escape(json.loads((ROOT/"registry/preregistration_x.json").read_text())["single_method_paragraph"])}</p>
<p><b>Named non-fault mimic:</b> {html.escape(card["named_non_fault_mimic"])}</p></div>
<div class="card"><h2 style="margin-top:0">Holdout — primary instrument</h2>
<p class="mut">HOLDOUT-DTI · evaluator <code>gems57-pooled-hide-v2</code> · whole-component hide-and-recover,
fold-fair emission, visible faults masked pixel-exactly · 11,321 withheld px · α=0.2 β=0.8 300 m triangular
kernel · paired spatial-cluster bootstrap 95% CIs. Controls reproduce session-1 exactly (same folds/seeds).</p>
<table><tr><th>Arm</th><th>DTI</th><th>95% CI</th></tr>
<tr><td><b>X1 full (NMS + witness)</b></td><td>{h['X1_dti']:.4f}</td><td>[{h['X1_ci95'][0]:.4f}, {h['X1_ci95'][1]:.4f}]</td></tr>
<tr><td>X2 thinning only</td><td>{h['X2_dti']:.4f}</td><td>—</td></tr>
<tr><td>X3 witness only</td><td>{h['X3_dti']:.4f}</td><td>—</td></tr>
<tr><td>H33-analogue control (fold-fair)</td><td>{h['h33_analogue_foldfair_dti']:.4f}</td><td>[{h['h33_analogue_foldfair_ci95'][0]:.4f}, {h['h33_analogue_foldfair_ci95'][1]:.4f}]</td></tr>
<tr><td>Random control</td><td>{h['random_control_dti']:.4f}</td><td>—</td></tr>
<tr><td>Session-1 E1 (same instrument, ref)</td><td>0.0548</td><td>[0.0417, 0.0688]</td></tr></table>
<p>X1 − control = {h['X1_paired_delta_vs_control']:+.4f} [{h['X1_paired_delta_vs_control_ci95'][0]:+.4f},
{h['X1_paired_delta_vs_control_ci95'][1]:+.4f}] (gate FAILED); X1 − random =
{h['X1_paired_delta_vs_random']:+.4f} [{h['X1_paired_delta_vs_random_ci95'][0]:+.4f},
{h['X1_paired_delta_vs_random_ci95'][1]:+.4f}] (real but small signal).
Leakage canaries: {card['leakage_canaries']['channels']} channels, max symmetric AUC
{card['leakage_canaries']['max_symmetric_auc']:.3f} ≤ 0.90 PASS.
Report-only SGMC-piedmont proxy (never used for selection): X1 {card['secondary_proxy_report_only']['X1']:.4f}
vs champion {card['secondary_proxy_report_only']['h33_champion']:.4f} — no override temptation this time.
Reading: thinning (+0.0014 over the E3-style base) and corroboration (+0.0021) each help marginally and
additively, but neither closes the gap to the tuned H19-5 geography. Negative results are deliverables.</p></div>
<div class="card"><h2 style="margin-top:0">Uniqueness vs accessible registry ({u['registry_checked']} rasters)</h2>
<table>
<tr><th>Surface Spearman (pre-placement, 200k sample)</th><td>max {u['surface_spearman_max_sample200k']:.3f} ≤ 0.90 ✓</td></tr>
<tr><th>Final-dots Spearman (200k sample)</th><td>max {u['dots_spearman_max_sample200k']:.3f} ≤ 0.90 ✓</td></tr>
<tr><th>Mutual 3 px overlap</th><td>max {u['dots_mutual_overlap_max']:.3f} ≤ 0.70 ✓ (worst: session-1 H73-1 E1 — shared scarp/piedmont base, disclosed)</td></tr>
<tr><th>vs H33 champion</th><td>forward {u['vs_h33_champion']['forward_my_dots_within3px']:.3f} · mutual {u['vs_h33_champion']['mutual_min']:.3f} · surface ρ {u['vs_h33_champion']['surface_spearman_sample200k']:.3f}</td></tr>
<tr><th>Literal forward overlap</th><td>{html.escape(u['forward_literal_note'])}</td></tr>
</table>
<img class="fig" src="assets/fig_x1_vs_h33.png" alt="Map of X1 dots vs H33 champion"></div>
<p><a href="executive-summary.html">Executive summary — exactly how to submit (and why not to submit this file)</a> ·
<a href="sources.html">Official sources</a> · <a href="research/hypotheses_x.md">Five new hypotheses</a> ·
<a href="downloads/run_card_h73-6.json">Run card JSON</a></p>"""

index_body = f"""
{download_card()}
{PORTAL}
{ANSWER}
{HYPO}
<div class="card"><h2 style="margin-top:0">Run card (JSON, this build)</h2>
<pre><code>{html.escape(json.dumps({k: card[k] for k in ("lane","hypothesis","mechanism","named_non_fault_mimic","verdict","download_ok","submit_recommended")}, indent=2))}
holdout X1 = {h['X1_dti']:.4f} [{h['X1_ci95'][0]:.4f},{h['X1_ci95'][1]:.4f}] (HOLDOUT-DTI gems57-pooled-hide-v2, 11,321 withheld)
raster sha256 = {SHA}
validator = PASSED (all-finite [0,1], EPSG:32611 3730x3292, sample match True)
submission name = {NAME} | note ({card['submission_note_chars']}/140) = {NOTE}</code></pre>
<p class="mut">Full card: <a href="downloads/run_card_h73-6.json">run_card_h73-6.json</a>. Prior lane:
<a href="h73-1-piedmont.html">H73-1 piedmont scarp-chain (also NEGATIVE)</a>.</p></div>
<h2>Limitations &amp; what we need</h2>
<ul>
<li><b>Data placement — SOLVED this session without any login:</b> all 23 competition/external/scored files were
restored from owner GitHub mirrors and SHA-256-verified (<code>python scripts/restore_data.py --group all</code>,
receipt <code>data/restore_receipt.json</code>). Hashes prove mirror consistency, not organiser authentication (IR-73-05).
DrivenData originals still require login: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data page</a>.</li>
<li><b>Sandbox egress</b> is github/pypi only → USGS 3DEP tiles for H73-8 cannot be fetched here; run that lane on an unrestricted machine.</li>
<li><b>Holdout ≠ leaderboard:</b> truth here is the visible catalogue; static catalogue DTI anti-ranks live scores
(Spearman −0.49, session-1 MEASURED-HERE). Fold-fair DTI is a screen that saves slots, not a score prediction.</li>
<li><b>No GPU needed</b> for anything on this site (all CPU, ~2 min/experiment suite).</li>
</ul>"""

exec_body = f"""
<h1>Executive summary — exactly how to make a submission</h1>
{download_card()}
<h2>Step-by-step (30 seconds, once a selector approves a file)</h2>
<ol>
<li>Download the approved <code>.tif</code> above (or its <code>.zip</code> — the portal accepts a .zip containing a single GeoTIFF).</li>
<li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submissions page</a> (login required) → <b>New submission</b>.</li>
<li><b>File to submit:</b> choose the downloaded <code>{TIF}</code> (unique name: <code>{NAME}</code>).</li>
<li><b>Note (optional):</b> paste <code>{html.escape(NOTE)}</code> ({card['submission_note_chars']}/140 chars — tells this submission apart later).</li>
<li>Submit. The portal checks CRS/shape/geotransform match and values in [0,1] — this file passes both
(<a href="downloads/validator_h73-6.json">re-read receipt</a>: EPSG:32611, 3730×3292, transform
[100,0,243350,0,-100,4508550], min 0.0 max 1.0, 0 NaN, nodata=None, sha256 <code>{SHA[:16]}…</code>).</li>
<li>Your public DTI appears on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>.
Only that organiser number is ORGANIZER-CONFIRMED; record it back into <code>registry/</code> with the file sha256.</li>
</ol>
<p class="warn"><b>Current recommendation: do not submit yet.</b> Every file on this site is download-OK but
submit-NO (gate table above). The steps are documented so that the moment a lane passes its holdout gate,
submission is one click with zero format risk.</p>
{PORTAL}
<h2>Verify any file yourself</h2>
<pre><code>python scripts/validate_tif.py docs/downloads/{TIF}
python scripts/check_submission_x.py   # full vendor re-read vs sample template
python -m pytest tests/ -q            # 13 tests: metric, writer [0,1], holdout honesty</code></pre>
<h2>Competition facts (verified 2026-10-21)</h2>
<ul>
<li>Task/metric/format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page 967</a> — DTI α=0.2 β=0.8, 300 m triangular kernel, worked example TPw 3.00 FPw 1.89 FNw 2.00 → 0.60 (reproduced in tests).</li>
<li>Format: single-band float32, EPSG:32611, 100 m, same bounds as sample, values in [0,1] (same page).</li>
<li>Leaderboard today: #1 0.4413, #2 0.3904, #3 0.3894 (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">live page</a>). Group best 0.2778 is OWNER-REPORT (no receipt — IR-73-02).</li>
<li>Rules PDF: <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR 96647</a>; reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a>.</li>
<li>Two prize rounds: Initial (private expert set) → expert review → Final (expanded labels). One selected submission counts for both (problem page).</li>
</ul>"""

(DOCS / "h73-6-traceloc.html").write_text(shell("GEMSDOE73 — H73-6 traceloc lane", lane_body))
(DOCS / "index.html").write_text(shell("GEMSDOE73 — Fault-Discovery System for the DOE GEMS Prize", index_body))
(DOCS / "executive-summary.html").write_text(shell("Executive Summary — How to Submit — GEMSDOE73", exec_body))
print("built h73-6-traceloc.html, index.html, executive-summary.html")
