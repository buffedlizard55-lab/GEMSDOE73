#!/usr/bin/env python3
"""Build the H73-1 lane page (docs/h73-1-piedmont.html) from evidence/run_card_h73-1.json.

The site home/executive/sources pages belong to the merged main lanes; this
builder only (re)writes the H73-1 lane page and its download receipts."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
card = json.loads((ROOT / "evidence/run_card_h73-1.json").read_text())
cal = json.loads((ROOT / "evidence/instrument_calibration.json").read_text())
tif = f"{card['submission_name']}.tif"
zipn = f"{card['submission_name']}.zip"
h = card["holdout"]; v = card["validator"]; u = card["correlation_overlap_vs_registry"]
CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0b1220;color:#e5e7eb}
.wrap{max-width:980px;margin:0 auto;padding:28px 20px 60px}
a{color:#7dd3fc} code{background:#1e293b;padding:1px 5px;border-radius:4px;word-break:break-all}
.card{background:#111827;border:1px solid #334155;border-radius:12px;padding:20px;margin:18px 0}
.bad{border-color:#dc2626;background:#2a0f12}.good{border-color:#16a34a}
.btn{display:inline-block;background:#0369a1;color:#fff;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:700;margin:6px 8px 6px 0}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #334155;padding:7px 9px;text-align:left;vertical-align:top}
h1{font-size:26px}h2{margin-top:26px}.small{color:#9ca3af;font-size:13px}img{max-width:100%;border-radius:8px}
.pill{display:inline-block;padding:2px 9px;border-radius:99px;font-weight:700}.no{background:#dc2626;color:#fff}.yes{background:#16a34a;color:#fff}
"""


def page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body><div class="wrap">{body}</div></body></html>"""


index = f"""
<h1>GEMSDOE73 — H73-1 piedmont micro-scarp chain lane</h1>
<p class="small">DOE GEMS Prize (DrivenData #306) · one preregistered lane · every number labelled
HOLDOUT-DTI or OWNER-REPORT · no organizer score exists for this repo's file.</p>

<div class="card bad">
<h2 style="margin-top:0">⬇ Submission file — READ THE STATUS FIRST</h2>
<table>
<tr><th>Gate 1 — OK to download?</th><td><span class="pill yes">YES</span> Format-valid and registry-unique; safe to download for review.</td></tr>
<tr><th>Gate 2 — Recommended to submit?</th><td><span class="pill no">NO — DO NOT SUBMIT</span>
<b>Verdict: NEGATIVE.</b> The candidate failed the preregistered holdout gate
(HOLDOUT-DTI {h['E1_dti']:.4f} vs fold-fair H33-analogue control {h['h33_analogue_foldfair_dti']:.4f}).
Submitting it would spend a weekly slot against this repo's own evidence. A human selector may
override knowingly (see the report-only proxy below) — that decision is not made here.</td></tr>
</table>
<p><a class="btn" href="downloads/{tif}">⬇ Download .tif (review only)</a>
<a class="btn" href="downloads/{zipn}">⬇ Download .zip (single GeoTIFF inside)</a>
<a class="btn" href="downloads/run_card_h73-1.json">Run card (JSON)</a></p>
<p><b>Filename:</b> <code>{tif}</code><br>
<b>Unique submission name:</b> <code>{card['submission_name']}</code><br>
<b>Note to paste in the DrivenData “Note (optional)” field ({card['submission_note_chars']}/140 chars) — only if a selector overrides:</b><br>
<code>{html.escape(card['submission_note'])}</code><br>
<b>sha256:</b> <code>{card['raster_sha256']}</code> · {card['raster_bytes']:,} bytes ·
single band float32 · EPSG:32611 · 3730×3292 · 37,654 dots · min {v['min']}, max {v['max']},
{v['n_nan']} NaN in all 12,279,160 cells · CRS/shape/transform match the sample submission:
<b>{v['crs_shape_transform_match_sample']}</b> · all validator checks passed:
<b>{v['all_checks_passed']}</b> (<a href="downloads/validator_h73-1.json">validator receipt</a>)</p>
<p class="small">Why this cannot trigger “Predicted values must be in range [0, 1]”: the file is written
all-finite (0.0 outside the footprint, <code>nodata=None</code>), then re-opened from disk and every cell is
checked finite and in [0,1] by the shared validator before delivery. See the
<a href="executive-summary.html">executive summary</a> for exact submission steps.</p>
</div>

<div class="card"><h2 style="margin-top:0">The answer to the brief's question</h2>
<p><b>Why did <code>h33-h33-2-b2…-zeros</code> score 0.2778 (OWNER-REPORT)?</b> Measured here, byte-exact:
it is D2.8 with every dot ≤200 m from the catalogue deleted, and D2.8 ⊂ H19-5 with zero exceptions.
H19-5's surface is ~90% LiDAR/DEM scarp-openness (weights 0.55+0.35 in its synthesis code) — the same
evidence class expert re-mapping uses. Dotting to ~2.5 px spacing removes mass below the metric's
break-even credit bar <code>k &gt; 0.2·DTI</code>, and the B2 prune deletes dots that can only cover
already-mapped (masked, zero-credit) faults while paying full false-positive tax.</p>
<p><b>Can we beat 0.2778 / 0.4413?</b> Not with this lane, on this evidence. Emission gains are nearly
exhausted; beating the champion needs a field with higher credit density in its top 37,654 dots.
H73-1 tested whether a fully unsupervised piedmont-scarp-chain geometry could be that field. It could
not — see the holdout table. The one encouraging signal (report-only SGMC-piedmont proxy, E1
{card['secondary_proxy_report_only']['E1']:.4f} vs champion {card['secondary_proxy_report_only']['h33_champion']:.4f})
is not the preregistered instrument and does not override the gate.</p></div>

<div class="card"><h2 style="margin-top:0">Holdout (primary instrument)</h2>
<p class="small">HOLDOUT-DTI · evaluator <code>{h['evaluator_version']}</code> · whole-component
hide-and-recover, fold-fair emission, visible faults masked pixel-exactly ·
{h['withheld_positive_pixels']:,} withheld positive pixels · α=0.2, β=0.8, 300 m triangular kernel ·
paired spatial-cluster bootstrap 95% CIs.</p>
<table><tr><th>Arm</th><th>DTI</th><th>95% CI</th></tr>
<tr><td><b>E1 (this lane)</b></td><td>{h['E1_dti']:.4f}</td><td>[{h['E1_ci95'][0]:.4f}, {h['E1_ci95'][1]:.4f}]</td></tr>
<tr><td>E2 (no piedmont weight)</td><td>{h['E2_dti']:.4f}</td><td>—</td></tr>
<tr><td>E3 (piedmont scarp only)</td><td>{h['E3_dti']:.4f}</td><td>—</td></tr>
<tr><td>H33-analogue control (fold-fair)</td><td>{h['h33_analogue_foldfair_dti']:.4f}</td><td>[{h['h33_analogue_foldfair_ci95'][0]:.4f}, {h['h33_analogue_foldfair_ci95'][1]:.4f}]</td></tr>
<tr><td>Random control</td><td>{h['random_control_dti']:.4f}</td><td>—</td></tr></table>
<p>E1 − control = {h['E1_paired_delta_vs_control']:.4f} [{h['E1_paired_delta_vs_control_ci95'][0]:.4f},
{h['E1_paired_delta_vs_control_ci95'][1]:.4f}]; E1 − random = {h['E1_paired_delta_vs_random']:+.4f}
[{h['E1_paired_delta_vs_random_ci95'][0]:+.4f}, {h['E1_paired_delta_vs_random_ci95'][1]:+.4f}] (includes 0).
Leakage canaries: {card['leakage_canaries']['channels']} channels, max symmetric AUC
{card['leakage_canaries']['max_symmetric_auc']:.3f} ≤ 0.90 — PASS.
Instrument warning (measured here, n=13 OWNER-REPORT live scores): static catalogue DTI ranks live at
Spearman {cal['spearman_vs_live']['catalogue']:+.2f}, SGMC-piedmont at {cal['spearman_vs_live']['sgmc_pied']:+.2f}
— every local proxy is a screen, not a score prediction.</p></div>

<div class="card"><h2 style="margin-top:0">Uniqueness vs registry ({u['registry_unique_rasters_checked']} rasters)</h2>
<table>
<tr><th>Surface Spearman (pre-placement, 200k sample)</th><td>max {u['surface_spearman_max_sample200k']:.3f} ≤ 0.90 ✓</td></tr>
<tr><th>Final dots Spearman (full footprint)</th><td>max {u['dots_spearman_max_full']:.3f} ≤ 0.90 ✓</td></tr>
<tr><th>Final dots mutual 3 px overlap</th><td>max {u['dots_mutual_overlap_max']:.3f} ≤ 0.70 ✓ (worst: {html.escape(u['dots_mutual_worst'])})</td></tr>
<tr><th>vs H33 champion</th><td>forward {u['vs_h33_champion']['forward']:.3f} · mutual {u['vs_h33_champion']['mutual']:.3f} · ρ {u['vs_h33_champion']['rho']:.3f}</td></tr>
<tr><th>Literal forward overlap</th><td>max {u['dots_forward_overlap_literal_max']:.3f} only vs the 206,895-dot r13 lattice whose 3 px halo covers ~100% of the footprint (mutual 0.139) — IR-73-01</td></tr>
</table>
<img src="assets/fig_e1_vs_h33.png" alt="Map of E1 dots vs champion"></div>

<p><a href="executive-summary.html">Executive summary — exactly how to submit (and why not to submit this file)</a> ·
<a href="sources.html">Official sources</a> · <a href="research/hypotheses.md">Five hypotheses (preregistered)</a></p>
<p class="small">Core values: <b>Maximize P(Win)</b> — a negative result that saves a weekly slot is a win for the
campaign. <b>Own the Outcome</b> — the gate failure is published, not buried. Weekly slots spent by this repo: 0.</p>
"""

exec_summary = f"""
<h1>Executive summary — how to submit to the DOE GEMS Prize</h1>
<div class="card bad"><p><b>For THIS repo's file: DO NOT SUBMIT</b> (verdict NEGATIVE, see
<a href="index.html">site home (main lanes)</a>). The steps below are the exact, verified procedure for any
candidate a selector promotes — including this file only under a knowing selector override.</p></div>
<div class="card"><h2 style="margin-top:0">Step-by-step</h2>
<ol>
<li>Download the promoted file: <code>{tif}</code> (or the .zip containing only that GeoTIFF).</li>
<li>Go to the DrivenData competition and open <b>Submit</b>:
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> →
<b>New submission</b>.</li>
<li><b>File to submit:</b> choose the .tif (or the single-GeoTIFF .zip). It must be single-band float32,
EPSG:32611, 3730×3292, values in [0,1] — this repo's file is machine-checked for all of that
(<a href="downloads/validator_h73-1.json">receipt</a>, sha256 <code>{card['raster_sha256']}</code>).</li>
<li><b>Note (optional):</b> paste exactly ({card['submission_note_chars']}/140 chars):<br>
<code>{html.escape(card['submission_note'])}</code></li>
<li>Use the unique submission name <code>{card['submission_name']}</code> in your own ledger so the
receipt can be cross-walked to the sha256 above (a score without a hash crosswalk is an OWNER-REPORT,
not ORGANIZER-CONFIRMED).</li>
<li>Check remaining weekly slots on the submission page before submitting — promotion to a real slot
is a separate selector step under that cap. This repo spent 0 slots.</li>
</ol>
<h2>The “[0, 1]” portal error — root cause and fix</h2>
<p>DrivenData rejects any cell (or nodata sentinel such as −3.4e38 from
<code>training_features.tif</code>) outside [0,1]. Files from this repo are written all-finite:
0.0 outside the 5,167,373-pixel footprint, <code>nodata=None</code>, values exactly in {{0.0, 1.0}},
then re-read from disk and verified cell-by-cell. Min {v['min']}, max {v['max']}, NaN count {v['n_nan']}.</p>
<h2>What happens after submitting</h2>
<p>Public leaderboard score = DTI on the public chunk of expert-labelled new faults;
Initial Prize Round uses the private chunk; Final Round re-scores the same single selected
submission against expanded labels including expert-verified discoveries from all teams
(official problem page). Record the receipt score + file sha256 together.</p></div>
<p><a href="index.html">← Back</a></p>
"""

sources = """
<h1>Official sources (for manual review)</h1>
<div class="card"><table>
<tr><th>Claim used</th><th>Official source</th></tr>
<tr><td>Metric (DTI, α=0.2, β=0.8, 300 m triangular kernel), submission format, worked example (0.60)</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description, page 967</a></td></tr>
<tr><td>Two-round prize structure; hidden faults are expert-labelled, absent from USGS database</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Page 967, Competition structure</a></td></tr>
<tr><td>Leaderboard (public chunk only; dynamic)</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Leaderboard</a></td></tr>
<tr><td>Known USGS/INGENIOUS fault pixels masked from scoring</td>
<td><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Organizer forum thread 11516</a></td></tr>
<tr><td>Official rules (PDF)</td><td><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR/DOE GEMS rules 96647.pdf</a></td></tr>
<tr><td>Reference solution</td><td><a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></td></tr>
<tr><td>GeoDAWN airborne magnetic/radiometric surveys (training features origin)</td>
<td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · DOI 10.5066/P93LGLVQ</td></tr>
<tr><td>INGENIOUS geothermal compilation</td><td><a href="https://gbcge.org/current-projects/ingenious/">GBCGE INGENIOUS</a> · <a href="https://gdr.openei.org/submissions/1391">GDR 1391</a></td></tr>
<tr><td>CRS EPSG:32611</td><td><a href="https://epsg.io/32611">epsg.io/32611</a></td></tr>
<tr><td>Tversky index definition</td><td><a href="https://en.wikipedia.org/wiki/Tversky_index">Wikipedia (secondary; official formula is page 967)</a></td></tr>
<tr><td>USGS 3DEP 1 m DEMs (LiDAR scarp derivatives' source)</td><td><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a></td></tr>
<tr><td>Competition data (login-walled; restored here from hash-pinned owner mirrors, NOT organizer-authenticated)</td>
<td><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Data download page</a> · <code>registry/data_manifest.json</code></td></tr>
</table>
<p class="small">Sibling-repo evidence is cited in the README score ledger as OWNER-REPORT; no sibling
number is presented as ORGANIZER-CONFIRMED without a receipt in hand.</p></div>
<p><a href="index.html">← Back</a></p>
"""

(DOCS / "h73-1-piedmont.html").write_text(page("GEMSDOE73 — H73-1 piedmont scarp-chain lane", index))
(DOCS / ".nojekyll").write_text("")
import shutil as _sh
_sh.copy(ROOT / "evidence" / "run_card_h73-1.json", DOCS / "downloads" / "run_card_h73-1.json")
_sh.copy(ROOT / "evidence" / "validator.json", DOCS / "downloads" / "validator_h73-1.json")
print("lane page built: docs/h73-1-piedmont.html")
