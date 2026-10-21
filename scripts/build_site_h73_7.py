#!/usr/bin/env python3
"""Rebuild the GEMSDOE73 site front pages from evidence/run_card_h73-7.json.

Originally wrote docs/index.html + docs/executive-summary.html + the lane page
on this lane's branch. After the parallel-lane merge onto main, the home and
executive pages are maintained there (with an H73-7 co-candidate section
inserted at merge time), so this builder now regenerates ONLY
docs/h73-7-hardfault.html. The index/exec bodies below are retained as the
branch-time record; do not re-enable those writes without re-merging.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
card = json.loads((ROOT / "evidence/run_card_h73-7.json").read_text())
hold = json.loads((ROOT / "evidence/holdout_h73-7.json").read_text())
h = card["holdout"]
sc = hold["scores"]
u = card["correlation_overlap_vs_registry"]
NAME = card["submission_name"]
TIF = f"{NAME}.tif"
ZIP = f"{NAME}.zip"
NOTE = card["submission_note"]
SHA = card["raster_sha256"]
promote = card["verdict"] == "promote"


def f4(x):
    return f"{x:.4f}"


def ci(v):
    return f"[{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]"


NAV = """<nav>
<a href="index.html">Home</a>
<a href="executive-summary.html">Make a submission</a>
<a href="h73-7-hardfault.html">H73-7 lane</a>
<a href="h73-1-piedmont.html">H73-1 lane</a>
<a href="research.html">Research</a>
<a href="hypotheses.html">Hypotheses</a>
<a href="leaderboard.html">Leaderboard</a>
<a href="sources.html">Sources</a>
<a href="irregularities.html">Irregularities</a>
</nav>"""


def page(title: str, body: str, active: str = "") -> str:
    nav = NAV.replace(f'href="{active}"', f'href="{active}" class="active"') if active else NAV
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="assets/site.css">
<style>.pill{{display:inline-block;padding:2px 10px;border-radius:99px;font-weight:700;color:#fff}}
.yes{{background:#16a34a}}.no{{background:#dc2626}}.sel{{background:#d97706}}
.badbox{{border:2px solid #dc2626;border-radius:10px;padding:14px;margin:16px 0}}
.goodbox{{border:2px solid #16a34a;border-radius:10px;padding:14px;margin:16px 0}}
img.fig{{max-width:100%;border-radius:8px}}</style>
</head><body>
<header class="top"><div class="wrap">
<h1>GEMSDOE73 — Fault-Discovery System for the DOE GEMS Prize</h1>
{nav}
</div></header>
<div class="values"><div class="wrap"><b>Core Values:</b> <b>Maximize P(Win)</b> — every weekly slot is an experiment. <b>Own the Outcome</b> — every claim carries an evidence class; defects are measured, published, replaced.</div></div>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">Scores are labelled <b>HOLDOUT-DTI</b> (local hide-and-recover) or <b>OWNER-REPORT / ORGANIZER-CONFIRMED</b> (external). A projection is never written as a score. <a href="https://github.com/buffedlizard55-lab/GEMSDOE73">Repository</a> · <a href="downloads/run_card_h73-7.json">H73-7 run card (JSON)</a></div></footer>
</body></html>
"""


GATE_TABLE = f"""
<table>
<tr><th>Gate 1 — OK to download?</th><td><span class="pill yes">YES</span> Format-valid on re-read bytes (single-band float32, EPSG:32611, 3730×3292, all 12,279,160 cells finite in [0,1], 0 NaN, <code>nodata=None</code> — the portal error “Predicted values must be in range [0, 1]” cannot trigger), registry-unique under the operative gates. Safe to download.</td></tr>
<tr><th>Gate 2 — Recommended to submit?</th><td><span class="pill sel">SELECTOR DECISION — passed its preregistered gate</span> <b>Verdict: PROMOTE (to selector).</b> This is the first lane in this repo to beat the fold-fair champion analogue on the shared holdout instrument (HOLDOUT-DTI {f4(h['selected_dti'])} vs {f4(h['h33_analogue_foldfair_control_dti'])}; details below). This repo spends <b>no</b> weekly slot: a human selector must still check the weekly cap on the DrivenData submission page and weigh the transfer caveat before submitting. If you are the selector and accept the caveats, this is the file to submit — see the <a href="executive-summary.html">executive summary</a>.</td></tr>
</table>"""

DOWNLOAD_BOX = f"""
<p><a class="btn" href="downloads/{TIF}">⬇ Download {TIF}</a>
<a class="btn alt" href="downloads/{ZIP}">.zip (same single GeoTIFF inside)</a></p>
<p><b>Unique submission name:</b> <code>{NAME}</code><br>
<b>Note to paste into the form's <em>Note (optional)</em> field ({card['submission_note_chars']}/140 chars):</b><br>
<code>{html.escape(NOTE)}</code></p>
<p class="mut">37,654 dots · 0 within 2 px of the USGS/INGENIOUS catalogue · sha256 <code>{SHA}</code> · <a href="downloads/{NAME}.json">validator receipt (independent re-read)</a> · <a href="downloads/run_card_h73-7.json">run card</a></p>"""

HOLDOUT_TABLE = f"""
<table>
<tr><th>Arm (same instrument, same budget 37,654, same allowed mask)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr>
<tr><td><b>E1 — hard-weighted PU-HGB, 41 physical channels (selected)</b></td><td><b>{f4(sc['E1']['dti'])}</b></td><td>{ci(sc['E1'])}</td></tr>
<tr><td>E2 — same, unweighted (ablation)</td><td>{f4(sc['E2']['dti'])}</td><td>{ci(sc['E2'])}</td></tr>
<tr><td>E3 — hard-weighted, no scarp-family features (ablation)</td><td>{f4(sc['E3']['dti'])}</td><td>{ci(sc['E3'])}</td></tr>
<tr><td>Fold-fair H33-analogue control (H19-5 support re-dotted fold-fairly)</td><td>{f4(sc['h33_analogue_foldfair']['dti'])}</td><td>{ci(sc['h33_analogue_foldfair'])}</td></tr>
<tr><td>Random dots (control)</td><td>{f4(sc['random_control']['dti'])}</td><td>{ci(sc['random_control'])}</td></tr>
<tr><td>H33 champion scored statically (expected ≈0: its B=2 prune deletes catalogue-covering dots)</td><td>{f4(sc['h33_static_reference']['dti'])}</td><td>{ci(sc['h33_static_reference'])}</td></tr>
</table>
<p>Evidence class for every number above: <b>HOLDOUT-DTI</b>, evaluator <code>gems57-pooled-hide-v2</code>,
{h['withheld_positive_pixels']:,} withheld catalogue pixels (whole components, buffered, quadrant folds NW/NE/SW/SE),
pooled DTI (α=0.2, β=0.8, 300 m triangular kernel), paired 20 km spatial-cluster bootstrap (1,000 draws).
Paired Δ E1 − control = <b>+{h['paired_delta_vs_control']['delta']:.4f} [{h['paired_delta_vs_control']['ci95'][0]:.4f}, {h['paired_delta_vs_control']['ci95'][1]:.4f}]</b> — excludes 0.
<b>Instrument integrity:</b> the control, rebuilt identically to the merged H73-1 lane, reproduced its published 0.093861 exactly (random and static controls also exact) — one unchanged instrument, comparable numbers.
Full data: <a href="https://github.com/buffedlizard55-lab/GEMSDOE73/blob/main/evidence/holdout_h73-7.json">evidence/holdout_h73-7.json</a>.</p>"""

CAVEATS = f"""
<div class="badbox"><h3 style="margin-top:0">Read before spending a slot — three honest caveats</h3>
<ol>
<li><b>Transfer is unproven.</b> {html.escape(h['transfer_caveat'])}</li>
<li><b>The named mechanism was not the active ingredient on this instrument.</b> {html.escape(h['mechanism_reading'])}</li>
<li><b>Literal one-way overlap (IR-73-15).</b> Under the brief's literal forward rule (&gt;70% of my dots within 3 px of one registry raster), this file “fails” against four dense/union rasters (forward 0.71–0.99, worst the 206,895-dot lattice whose halo covers any dot field — IR-73-01). Under the shared tool's operative gates it passes clearly: surface Spearman max {u['stage_A_surface_spearman_max_sample200k']:.4f}, dots Spearman max {u['stage_B_dots_spearman_max_full']:.4f}, worst <em>mutual</em> overlap {u['dots_mutual_overlap_max']:.4f} (vs the H33 champion: mutual {u['vs_h33_champion'][0]['mutual']:.4f}, forward {u['vs_h33_champion'][0]['forward']:.4f}). Full table in the run card — the selector decides with eyes open.</li>
</ol></div>"""

ARCHIVE = """
<h2>Previous lanes in this repo — archive (download for review only)</h2>
<div class="badbox">
<p><span class="pill no">DO NOT SUBMIT</span> <b>H73-A blind stepover</b> (<code>gems73-h73a-blind-stepover-…-zeros.tif</code>, 30,762 dots) and
<span class="pill no">DO NOT SUBMIT</span> <b>hydrothermal permeability corridor</b> (<code>gems73-hydro-permeability-corridor-…-zeros.tif</code>, 37,654 dots):
both are <em>synthetic-generator</em> artifacts that were never scored on the real holdout instrument.
An earlier version of this site promoted them as “one-click submission” files — that was wrong and is corrected here.
The hydro lane's card quoted “HOLDOUT-DTI 0.1112” from a hard-coded demo function; that verdict is void (IR-73-11,
<code>evidence/run_card_hydro_addendum_2026-10-21.json</code>), and the shared tool that produced it now refuses to invent numbers.
Both files remain in <code>docs/downloads/</code> for audit; submitting either would spend a slot against this repo's own evidence.</p>
<p><span class="pill no">DO NOT SUBMIT</span> <b>H73-1 piedmont micro-scarp chain</b> — properly measured, verdict NEGATIVE
(HOLDOUT-DTI 0.0548 [0.0417, 0.0688] vs control 0.0939). See its <a href="h73-1-piedmont.html">lane page</a>. Negative results are deliverables.</p>
</div>"""

WHY_H33 = """
<h2>Why did GEMSDOE32's <code>h33-h33-2-b2</code> score 0.2778 — and can it be beaten?</h2>
<p><i>Score class: 0.2778 is <b>OWNER-REPORT</b> (project ledger; no organizer receipt in any inspected repo — IR-73-02).
Everything below about the file's construction is <b>MEASURED-HERE</b> from its bytes (sha256 <code>c55bafc470…</code>), re-verified this session.</i></p>
<ol>
<li><b>Exact lineage:</b> H33-2-B2 (37,654 dots) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131), zero exceptions. H33-2-B2 is D2.8 with <b>every dot within 2.0 px of the catalogue deleted — 6,436 dots</b> (minimum retained distance 2.236 px). <i>(This site previously printed “1,152 dots from ~38,800” — wrong, corrected; IR-73-16.)</i></li>
<li><b>Dotting raises credit density:</b> DTI = T / (0.2·(T+F) + 0.8·|G|). A non-redundant dot helps only if its kernel credit k &gt; 0.2·DTI ≈ 0.056 at DTI 0.2778. Thinning 121,131 px to ~2.5–2.8 px-spaced dots keeps trace coverage (k ≥ ~0.58 on a covered trace) while paying the 0.2 FP tax once per ~6 px of trace: OWNER-REPORT ladder 0.1922 → 0.2477/0.2600.</li>
<li><b>The B=2 prune is free:</b> hidden truth excludes the catalogue, so dots ≤200 m from known traces mostly cover masked, zero-credit traces at full FP cost. Deleting 6,436 of them cost no hidden recall: 0.2600 → 0.2778 family step.</li>
<li><b>The field matched the hidden set's likely construction:</b> H19-5 is ~90% scarp/openness-weighted — the same LiDAR-scarp population expert re-mapping adds. Corollary (MEASURED-HERE): the champion scores DTI 0.0067 against the full catalogue, below random — any non-fold-fair catalogue holdout ranks it last (IR-73-06).</li>
</ol>
<p><b>Can 0.2778 be beaten? 0.4413?</b> At fixed mass the only lever is mean credit per dot; emission tricks are exhausted (ladder gains +0.0555, +0.0123, +0.0070). Beating 0.2778 needs a better <em>field</em>; 0.4413 (live #1, ORGANIZER-CONFIRMED public leaderboard read 2026-10-21) needs ≈+60% credit density over H33 — not claimed here. H73-7's measured claim is narrower and real: on the shared fold-fair instrument its field beats the champion-analogue control by +46% relative. Whether that transfers to the expert hidden set is the open question one slot would answer.</p>"""

index_body = f"""
<div class="goodbox">
<h2 style="margin-top:0">⬇ Current submission candidate — lane H73-7 (hard-fault PU ranker)</h2>
{GATE_TABLE}
{DOWNLOAD_BOX}
</div>

<h2>The measured result (HOLDOUT-DTI — not a live score)</h2>
{HOLDOUT_TABLE}
{CAVEATS}
<p><img class="fig" src="assets/fig_h73-7_vs_h33.png" alt="H73-7 surface and dots versus the H33 champion and the catalogue"></p>
<p class="mut">Left: H73-7 production surface. Centre: emitted dots — H73-7 only (red), shared with the H33 champion within a 4×4 pool cell (green), champion only (blue): the placements are substantially different dot fields. Right: surface under the mapped catalogue (red) — the ranker indeed learned catalogue-style structure, which is both its holdout strength and its transfer risk.</p>

<h2>How to submit (selector only)</h2>
<p>Exact 30-second procedure, the note text, and the “Predicted values must be in range [0, 1]” fix: <a href="executive-summary.html"><b>executive summary →</b></a></p>

{WHY_H33}

<h2>Hypotheses considered this session (ranked before any run)</h2>
<p>Five candidates with layers, physical signature, why each should catch catalogue-missing faults, the named non-fault mimic, expected ΔDTI and cost — frozen in <a href="https://github.com/buffedlizard55-lab/GEMSDOE73/blob/main/docs/research/hypotheses_h73-7.md">docs/research/hypotheses_h73-7.md</a> and <code>registry/preregistration_h73-7.json</code>. Rank 1 (this lane) was implemented; Rank 2 magnetic contact-termination, Rank 3 radiometric alteration lineaments and Rank 4 drainage deflection remain unimplemented and locally validatable; Rank 5 leaderboard tomography is diagnostic-only and was rejected as unvalidatable. No candidate needed new external data — every layer was already hash-pinned and restored (USGS 3DEP derivatives, USGS GeoDAWN DOI 10.5066/P93LGLVQ derivatives, competition feature stack).</p>

{ARCHIVE}

<h2>Run card (protocol JSON, abridged on page — full file linked)</h2>
<pre><code>{html.escape(json.dumps({k: card[k] for k in ("hypothesis", "mechanism", "named_non_fault_mimic", "raster_sha256", "submission_name", "submission_note", "verdict", "weekly_slots_spent", "organizer_score")}, indent=2))}</code></pre>
<p>Full card with holdout CIs, canaries, uniqueness tables and validator output: <a href="downloads/run_card_h73-7.json">downloads/run_card_h73-7.json</a> · lane page: <a href="h73-7-hardfault.html">H73-7 detail →</a></p>
"""

exec_body = f"""
<h2>Executive summary — exactly how to make a submission</h2>
{GATE_TABLE}
<div class="dl">
<h2>⬇ The file (selector-approved use only)</h2>
{DOWNLOAD_BOX}
</div>
<h2>Steps on DrivenData (≈30 seconds)</h2>
<ol>
<li><b>Selector checks first:</b> confirm a weekly slot is available on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission page</a> (the cap shown there governs; this repo cannot see your account's remaining slots), and read the three caveats on the <a href="index.html">home page</a>.</li>
<li>Download <code>{TIF}</code> above (or the <code>.zip</code> — the portal accepts a single GeoTIFF or a .zip containing one).</li>
<li>On the submission page → <b>New submission</b> → <b>File to submit: Choose File</b> → select the downloaded file.</li>
<li>In <b>Note (optional)</b> paste exactly:<br><code>{html.escape(NOTE)}</code></li>
<li>Click <b>Create</b>. The portal checks CRS/shape/geotransform match against the submission format and that predicted values are in [0, 1]. This file passes by construction and by re-read verification: single-band float32, EPSG:32611, 3730×3292, transform [100, 0, 243350, 0, −100, 4508550], <b>all 12,279,160 cells finite, min 0.0, max 1.0, 0 NaN, no nodata tag</b> (<a href="downloads/{NAME}.json">receipt</a>).</li>
<li>Record the organizer score from the submission page when it appears. Only that receipt is <b>ORGANIZER-CONFIRMED</b>; add it to <code>registry/score_ledger.csv</code> with the file's sha256 (<code>{SHA[:12]}…</code>). Until then this file's only numbers are HOLDOUT-DTI.</li>
</ol>
<h2>About the error “Predicted values must be in range [0, 1]”</h2>
<p>That error fires when any cell (or the nodata sentinel, e.g. <code>-3.4028234663852886e+38</code> from the feature stack) lies outside [0, 1]. This file contains no sentinel and no NaN anywhere: outside-footprint cells are literal <code>0.0</code> and <code>nodata</code> is unset, verified by re-opening the written bytes. If you ever regenerate a candidate, use the zeros policy (<code>vendor/gems57/grid.write_submission(..., mode="zeros")</code> / the fail-closed <code>submission_writer</code>) and re-validate the bytes you actually upload.</p>
<h2>What this file is — and is not</h2>
<ul>
<li><b>Is:</b> a unique, newly generated GeoTIFF (never submitted; sha256 above) from lane H73-7, which beat the fold-fair champion-analogue control on the shared holdout instrument by +{h['paired_delta_vs_control']['delta']:.4f} HOLDOUT-DTI (CI in run card).</li>
<li><b>Is not:</b> a proven live improvement over 0.2778, and not a claim on the 0.4413 leaderboard top. No organizer score exists for it. Submitting it is an experiment whose result — positive or negative — is the deliverable.</li>
<li><b>Do not submit instead:</b> the blind-stepover or hydro-corridor files also present in <code>docs/downloads/</code> (synthetic, unmeasured — see archive box on the home page), nor the NEGATIVE H73-1 piedmont file.</li>
</ul>
<p class="mut">Competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">overview</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description &amp; metric</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> · rules PDF <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR 96647</a>.</p>
"""

lane_body = f"""
<h2>Lane H73-7 — hard-fault Positive-Unlabelled ranker</h2>
{GATE_TABLE}
{DOWNLOAD_BOX}
<h3>Hypothesis &amp; mechanism</h3>
<p>{html.escape(card['hypothesis'])}</p>
<p>{html.escape(card['mechanism'])}</p>
<p><b>Named non-fault mimic:</b> {html.escape(card['named_non_fault_mimic'])}</p>
<h3>Holdout result</h3>
{HOLDOUT_TABLE}
<p>Per-fold E1: NW {f4(hold['per_fold']['E1'][0]['dti'])} · NE {f4(hold['per_fold']['E1'][1]['dti'])} · SW {f4(hold['per_fold']['E1'][2]['dti'])} · SE {f4(hold['per_fold']['E1'][3]['dti'])} (control: NW {f4(hold['per_fold']['h33_analogue_foldfair'][0]['dti'])} · NE {f4(hold['per_fold']['h33_analogue_foldfair'][1]['dti'])} · SW {f4(hold['per_fold']['h33_analogue_foldfair'][2]['dti'])} · SE {f4(hold['per_fold']['h33_analogue_foldfair'][3]['dti'])}).</p>
{CAVEATS}
<h3>Leakage canaries</h3>
<p>All {card['leakage_canaries']['channels_tested']} channels alone: max symmetric AUC {card['leakage_canaries']['max_symmetric_auc']:.4f} ({html.escape(card['leakage_canaries']['worst_channel'])}) ≤ 0.90 gate — PASS. No channel is catalogue-derived; there is no distance-to-catalogue feature. (<code>evidence/canaries_h73-7.json</code>)</p>
<h3>Uniqueness (REGISTRY-MEASUREMENT, accessible scan of {u['registry_unique_rasters_checked']} unique rasters)</h3>
<table>
<tr><th>Check</th><th>Worst value</th><th>Gate</th></tr>
<tr><td>Stage A surface Spearman (200k sample)</td><td>{u['stage_A_surface_spearman_max_sample200k']:.4f} vs {html.escape(u['stage_A_worst'])}</td><td>≤ 0.90 ✓</td></tr>
<tr><td>Stage B dots Spearman (full footprint)</td><td>{u['stage_B_dots_spearman_max_full']:.4f} vs {html.escape(u['stage_B_worst_spearman_submission'])}</td><td>≤ 0.90 ✓</td></tr>
<tr><td>Stage B mutual 3 px overlap</td><td>{u['dots_mutual_overlap_max']:.4f} vs {html.escape(u['dots_mutual_worst_submission'])}</td><td>≤ 0.70 ✓</td></tr>
<tr><td>vs H33 champion</td><td>forward {u['vs_h33_champion'][0]['forward']:.4f} · mutual {u['vs_h33_champion'][0]['mutual']:.4f} · rho {u['vs_h33_champion'][0]['rho']:.4f}</td><td>—</td></tr>
</table>
<p>{html.escape(u['literal_forward_note'])}</p>
<p><img class="fig" src="assets/fig_h73-7_vs_h33.png" alt="H73-7 versus champion map"></p>
<h3>Reproduce</h3>
<pre><code>.venv/bin/python scripts/restore_data.py --group all
.venv/bin/python scripts/run_experiments_h73_7.py
.venv/bin/python scripts/build_submission_h73_7.py
.venv/bin/python scripts/audit_registry_h73_7.py
.venv/bin/python scripts/build_run_card_h73_7.py</code></pre>
<p>Preregistration (frozen before the run): <code>registry/preregistration_h73-7.json</code> · ranked hypotheses: <a href="https://github.com/buffedlizard55-lab/GEMSDOE73/blob/main/docs/research/hypotheses_h73-7.md">docs/research/hypotheses_h73-7.md</a> · validator receipt: <a href="downloads/{NAME}.json">{NAME}.json</a></p>
"""

(DOCS / "h73-7-hardfault.html").write_text(page("H73-7 hard-fault PU lane — GEMSDOE73", lane_body, "h73-7-hardfault.html"))
print("wrote docs/h73-7-hardfault.html (index/executive maintained on main post-merge)")
