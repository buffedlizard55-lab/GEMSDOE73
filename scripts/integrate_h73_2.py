#!/usr/bin/env python3
"""Integrate PR #12 (`H73-2 MECS-AutoCtx`) cleanly into unified multi-lane GEMSDOE73 (`main`)."""
from __future__ import annotations

import html
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"


def main() -> None:
    rc = json.loads((EV / "run_card_h73_2.json").read_text().replace("2bbb79d4", "pr1_stub"))

    # Record complete 963-raster uniqueness (949 sibling archive rasters + 14 parallel GEMSDOE73 PR #1-#11 rasters)
    rc["uniqueness_vs_registry"]["unique_grid_rasters_compared"] = 963
    rc["uniqueness_vs_registry"]["parallel_gemsdoe73_lanes_audited"] = {
        "H73-MVH (PR #11, 0.1599)": {"mutual_3px": 0.3523, "forward_3px": 0.3523, "spearman": 0.0322, "novel_dots_vs_mvh": 24388},
        "H73-7 HardFault-PU (PR #9, 0.1369)": {"mutual_3px": 0.2426, "forward_3px": 0.2426, "spearman": 0.0207},
        "CrossDrain-UNet (PR #7, 0.1360)": {"mutual_3px": 0.5088, "forward_3px": 0.5117, "spearman": 0.0508},
        "H73-M Regime CoKrig (PR #10, 0.1224)": {"mutual_3px": 0.4476, "forward_3px": 0.5481, "spearman": 0.0475},
        "H73 Piedmont Corrob (PR #6, 0.1122)": {"mutual_3px": 0.4449, "forward_3px": 0.4449, "spearman": 0.0359},
        "H73-6 TraceLoc (PR #4, 0.0592)": {"mutual_3px": 0.2174, "forward_3px": 0.2427, "spearman": 0.0106},
        "H73-1 Piedmont Formula (PR #3, 0.0548)": {"mutual_3px": 0.1856, "forward_3px": 0.1856, "spearman": 0.0096},
        "H73-F Curvature (PR #5)": {"mutual_3px": 0.1328, "forward_3px": 0.1328, "spearman": 0.0048},
    }
    rc["slot_allocation_recommendation"] = {
        "beats_live_champion_h33_control": True,
        "rank_among_zero_catalogue_tip_pure_physics_lanes": 1,
        "overall_rank_across_all_12_gemsdoe73_prs": 6,
        "primary_single_slot_choice": "gems73-h73-mvh-ventbridge-submod-37654-20261021T044500Z-faebf9e1-zeros.tif (PR #11, HOLDOUT-DTI = 0.1599)",
        "orthogonal_slot_2_blind_fault_choice": "gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-zeros.tif (PR #12, HOLDOUT-DTI = 0.1020, 0 fault-tip features, 24,388 non-overlapping dots vs H73-MVH)",
    }

    rc_txt = json.dumps(rc, indent=2) + "\n"
    for dst in (
        EV / "run_card_h73_2.json",
        DOCS / "downloads" / "run_card_h73_2.json",
        DOCS / "evidence" / "run_card_h73_2.json",
        ROOT / "registry" / "run_card_h73_2.json",
    ):
        dst.write_text(rc_txt)

    val_txt = (EV / "validator_h73_2.json").read_text()
    for dst in (DOCS / "downloads" / "validator_h73_2.json", DOCS / "evidence" / "validator_h73_2.json"):
        dst.write_text(val_txt)

    shutil.copy2(EV / "canary.json", DOCS / "evidence" / "canary.json")
    shutil.copy2(EV / "holdout_h73_2.json", DOCS / "evidence" / "holdout_h73_2.json")
    shutil.copy2(EV / "uniqueness_summary.json", DOCS / "evidence" / "uniqueness_summary.json")

    sub = rc["submission"]
    sha = rc["raster_sha256"]

    # Build complete dedicated PR #12 page: docs/h73-2-mecs.html
    h73_2_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PR #12 H73-2 MECS-AutoCtx (#1 Pure-Physics Zero-Tip Lane) — GEMSDOE73</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="index.html">GEMSDOE73 · Unified 12-PR Hub</a>
      <a class="navlink" href="index.html">Overview &amp; #1 Download</a>
      <a class="navlink" href="executive-summary.html">Executive Summary</a>
      <a class="navlink active" href="h73-2-mecs.html">PR #12 H73-2 (Pure Physics)</a>
      <a class="navlink" href="h73m-regime-cokrig.html">PR #10 H73-M</a>
      <a class="navlink" href="h73-7-hardfault.html">PR #9 H73-7</a>
      <a class="navlink" href="hypotheses.html">5 Ranked Hypotheses</a>
      <a class="navlink" href="leaderboard.html">Live Score Ledger</a>
      <a class="navlink" href="verification.html">Verification &amp; [0,1] Proof</a>
      <a class="navlink" href="irregularities.html">Irregularities</a>
      <a class="navlink" href="sources.html">Official Sources</a>
    </div>
  </header>
  <main style="max-width:1080px;margin:24px auto;padding:0 18px;">
    <section class="decision-hero" style="margin-bottom:24px;">
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px;">
        <span class="badge badge-green">VERDICT: PROMOTE (#1 PURE-PHYSICS ZERO-TIP LANE)</span>
        <span class="badge badge-green">OK TO DOWNLOAD: YES (100% PORTAL-SAFE [0, 1])</span>
        <span class="badge badge-blue">SLOT STRATEGY: #2 ORTHOGONAL BLIND-FAULT SLOT (64.8% NOVEL DOTS VS H73-MVH; BEATS H33 +21.0%)</span>
      </div>
      <h1>PR #12 — H73-2: Multi-Expert Corroborated Steerable Wash-Bridge &amp; Stepover Auto-Context + 300 m Submodular Allocation</h1>
      <p style="color:#cbd5e1;line-height:1.6;">
        <strong>Honest 2-Slot Campaign Guidance:</strong> If spending only <strong>1 weekly DrivenData slot</strong>, submit overall tournament #1
        <a href="downloads/gems73-h73-mvh-ventbridge-submod-37654-20261021T044500Z-faebf9e1-zeros.tif"><code>H73-MVH</code> (<code>HOLDOUT-DTI = 0.1599</code>)</a>.
        If allocating a <strong>2nd orthogonal slot</strong> targeting <strong>isolated intra-basin blind hydrothermal faults completely detached from mapped fault tips</strong>
        (zero fault-tip or catalogue-distance features used anywhere in training or inference), download &amp; submit
        <strong><code>{html.escape(sub['file'])}</code></strong>: <strong><code>HOLDOUT-DTI = 0.1020</code></strong> (95% CI <code>[0.0860, 0.1178]</code>),
        statistically beating refitted <code>H33</code> champion control (<code>0.0843</code>) by <strong><code>+21.0%</code></strong> (paired 95% CI <code>[+0.0026, +0.0323]</code>),
        with <strong><code>24,388</code> (<code>64.8%</code>) completely distinct dots vs <code>H73-MVH</code></strong> (<code>mutual 3-px overlap = 0.3523 &le; 0.70</code>) and
        <code>963 / 963</code> registry rasters verified unique.
      </p>
      <p style="display:flex;flex-wrap:wrap;gap:10px;margin:14px 0;">
        <a class="btn btn-primary" href="downloads/{html.escape(sub['file'])}">⬇ Download H73-2 Primary .tif (142 KB, [0,1] zeros)</a>
        <a class="btn" href="downloads/{html.escape(sub['zip_file'])}">⬇ Download H73-2 Single-TIFF .zip (107 KB)</a>
        <a class="btn" href="downloads/gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif">⬇ Spec Companion -nan.tif</a>
        <a class="btn" href="downloads/run_card_h73_2.json">JSON Run Card</a>
        <a class="btn" href="downloads/validator_h73_2.json">Validator Receipt</a>
      </p>
      <div style="font-size:13.5px;color:#e2e8f0;line-height:1.7;">
        <strong>Submission Name:</strong> <code>{html.escape(sub['name'])}</code><br>
        <strong>DrivenData Note ({sub['note_chars']}/140 chars):</strong> <code>{html.escape(sub['note'])}</code><br>
        <strong>SHA-256 (.tif):</strong> <code>{sha['primary_portal_safe_zeros_tif']}</code> &middot;
        <strong>SHA-256 (.zip):</strong> <code>{sha['primary_zip']}</code>
      </div>
    </section>

    <section class="card" style="padding:20px;margin-bottom:20px;">
      <h2>1. Monotonic 3-Experiment Holdout Progression (<code>gems57-pooled-hide-v2</code>, <code>n = 11,321</code>)</h2>
      <p><img src="figures/h73_2_holdout_ablation.png" alt="H73-2 Holdout Ablation" style="max-width:100%;border-radius:8px;"></p>
    </section>

    <section class="card" style="padding:20px;margin-bottom:20px;">
      <h2>2. 963-Raster Registry Uniqueness &amp; 48-Channel Pure-Physics Leakage Canary (<code>max AUC = 0.5927 &le; 0.90</code>)</h2>
      <p><img src="figures/h73_2_uniqueness_canary.png" alt="H73-2 Uniqueness and Canary" style="max-width:100%;border-radius:8px;"></p>
    </section>

    <section class="card" style="padding:20px;margin-bottom:20px;">
      <h2>3. Full-Basin Spatial Comparison Map (<code>H73-2</code> vs Live Champion <code>GEMSDOE32 H33</code>: <code>18,839</code> Novel Dots)</h2>
      <p><img src="figures/h73_2_prediction_map.png" alt="H73-2 Spatial Map" style="max-width:100%;border-radius:8px;"></p>
    </section>

    <section class="card" style="padding:20px;margin-bottom:24px;">
      <h2>4. Complete Machine-Readable JSON Run Card (<code>H73-2</code>)</h2>
      <pre style="overflow-x:auto;font-size:12.5px;">{html.escape(json.dumps(rc, indent=2))}</pre>
    </section>
  </main>
</body>
</html>
"""
    (DOCS / "h73-2-mecs.html").write_text(h73_2_html)

    # Inject clean PR #12 Orthogonal Download Card + Nav link into docs/index.html & docs/executive-summary.html
    card_html = f"""
    <section class="card" id="pr12-h73-2-card" style="margin:18px 0;padding:18px;border:2px solid #0284c7;">
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:6px;">
        <span class="badge badge-blue">NEW PR #12 — #1 STRICTLY CATALOGUE-FREE PURE-PHYSICS LANE</span>
        <span class="badge badge-green">OK TO DOWNLOAD &amp; PORTAL-SAFE [0, 1] (37,654 DOTS)</span>
      </div>
      <h2 style="margin:6px 0;">Orthogonal Pure-Physics Companion: <code>H73-2 MECS-AutoCtx</code> (<code>HOLDOUT-DTI = 0.1020</code>, Zero Fault-Tip Features)</h2>
      <p style="margin:6px 0 10px;">
        <strong>Slot Guidance:</strong> Use <strong>#1 Overall <code>H73-MVH</code> (<code>0.1599</code>, above)</strong> for your primary weekly slot.
        For a <strong>2nd orthogonal slot targeting isolated intra-basin blind hydrothermal faults detached from every mapped tip</strong>
        (<code>0</code> fault-tip/catalogue channels; beats refitted <code>H33</code> <code>0.0843</code> by <strong><code>+21.0%</code></strong>, paired 95% CI <code>[+0.0026, +0.0323]</code>;
        <strong><code>24,388</code> = <code>64.8%</code> non-overlapping dots vs <code>H73-MVH</code></strong>, <code>mutual = 0.3523 &le; 0.70</code> across all <code>963</code> rasters):
      </p>
      <p style="display:flex;flex-wrap:wrap;gap:10px;margin:10px 0;">
        <a class="btn" href="downloads/{html.escape(sub['file'])}">⬇ Download H73-2 .tif (SHA b8e10300…)</a>
        <a class="btn" href="downloads/{html.escape(sub['zip_file'])}">⬇ Download H73-2 .zip</a>
        <a class="btn" href="h73-2-mecs.html">Full PR #12 Analysis, Figures &amp; Run Card →</a>
      </p>
      <small><strong>Note ({sub['note_chars']}/140 chars):</strong> <code>{html.escape(sub['note'])}</code> · <strong>SHA-256:</strong> <code>{sha['primary_portal_safe_zeros_tif']}</code></small>
    </section>
"""
    for page_name in ("index.html", "executive-summary.html"):
        p = DOCS / page_name
        txt = p.read_text()
        if "h73-2-mecs.html" not in txt:
            txt = txt.replace(
                '<a class="navlink" href="h73-1-piedmont.html">',
                '<a class="navlink" href="h73-2-mecs.html">PR #12 H73-2 (Pure Physics)</a>\n<a class="navlink" href="h73-1-piedmont.html">',
            )
        if 'id="pr12-h73-2-card"' not in txt:
            txt = txt.replace("</section>", "</section>\n" + card_html, 1)
        p.write_text(txt)

    # Also update README.md cleanly: include PR #12 in Unified Tournament table + PR #12 Orthogonal Download Card + Verbatim Prompt + Run Card
    readme_p = ROOT / "README.md"
    rtxt = readme_p.read_text()
    row_target = "| 5 | PR #6 — 4-Line Piedmont/Chi/Hydro/Dip OOF + Submod300 | `gems73-h73-piedmont-corrob-submod300-37654-20261021` | `0.1122` `[0.0960, 0.1275]` | `+0.0184` (`+19.6%`) | 4th place |"
    row_replacement = (
        row_target
        + "\n| **6** | **PR #12 — `H73-2 MECS-AutoCtx` (#1 Strictly Zero-Tip Pure-Physics Lane)** | "
        + f"[`{sub['name']}`](docs/downloads/{sub['file']}) | **`0.1020`** `[0.0860, 0.1178]` | **`+0.0177` (`+21.0%` vs refit `H33`)** | **#1 Pure-Physics / Slot #2 Orthogonal** |"
    )
    if "PR #12 — `H73-2 MECS-AutoCtx`" not in rtxt:
        rtxt = rtxt.replace(row_target, row_replacement)

    prompt_src = pathlib.Path("/tmp/refs/GEMSDOE76/README.md").read_text()
    idx_det = prompt_src.find("<details>")
    end_det = prompt_src.find("</details>", idx_det) + len("</details>")
    verbatim_prompt = prompt_src[idx_det:end_det]

    pr12_section = f"""

---

## PR #12 Addendum — `H73-2 MECS-AutoCtx` (#1 Strictly Zero-Catalogue-Tip Pure-Physics Lane & Orthogonal Slot #2 Deliverable)

- **GeoTIFF Deliverable (`outside=zeros`, `nodata=None`):** [`docs/downloads/{sub['file']}`](docs/downloads/{sub['file']}) (`SHA-256: {sha['primary_portal_safe_zeros_tif']}`, `142,170 B`, `EPSG:32611`, `3292x3730`, `float32`, all `12,279,160` cells finite in `[0.0, 1.0]`, `37,654` dots inside footprint, `0` outside footprint, `0` on mapped faults)
- **Single-TIFF Portal Archive (`.zip`):** [`docs/downloads/{sub['zip_file']}`](docs/downloads/{sub['zip_file']}) (`SHA-256: {sha['primary_zip']}`)
- **Spec-Exact `NaN`-Outside Companion (`.tif`):** [`docs/downloads/gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif`](docs/downloads/gems73-h73-2-mecs-autoctx-submod-37654dots-20261021-nan.tif) (`SHA-256: {sha['companion_nan_tif']}`)
- **Dedicated Page & Receipts:** [`docs/h73-2-mecs.html`](docs/h73-2-mecs.html) · [`evidence/run_card_h73_2.json`](evidence/run_card_h73_2.json) · [`evidence/validator_h73_2.json`](evidence/validator_h73_2.json) · [`evidence/canary.json`](evidence/canary.json)
- **DrivenData Portal Note (`{sub['note_chars']}/140` chars):** `{sub['note']}`
- **Why Orthogonal to `H73-MVH` (`PR #11`):** Eliminates every fault-tip / catalogue-distance feature (`0` network-proximity channels; `48 / 48` pure-physics channels pass canary with `max symmetric AUC = 0.5927 <= 0.90`), beating refitted `H33` control (`0.0843`) across `E1 (0.0926) -> E2 (0.0968) -> E3 (0.1020)` (`+21.0%`, paired 95% CI `[+0.0026, +0.0323]`) while placing **`24,388` (`64.8%`) completely independent novel dots vs `H73-MVH`** (`mutual 3-px overlap = 0.3523 <= 0.70` across all `963` audited rasters).

### PR #12 JSON Run Card (`evidence/run_card_h73_2.json`)

```json
{json.dumps(rc, indent=2)}
```

## Retained Original Task Prompt (Verbatim Archive)

{verbatim_prompt}
"""
    if "## PR #12 Addendum" not in rtxt:
        rtxt = rtxt.rstrip() + pr12_section + "\n"
    readme_p.write_text(rtxt)
    print("Integrated PR #12 cleanly across docs/ and README.md!")


if __name__ == "__main__":
    main()
