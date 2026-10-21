# GEMSDOE73 — Regime-Stratified Multi-Physics Co-Kriging & Radius-Matched Submodular Fault Detector for the DOE GEMS Prize

## ✅ VERDICT: `PROMOTE` — OK TO DOWNLOAD AND SUBMIT TO DRIVENDATA

- **Primary Recommended Submission GeoTIFF (DrivenData Portal-Safe `-zeros.tif`):**
  - **File:** [`docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif) (`142,737` bytes)
  - **SHA-256:** `ac1c720d466a1213b997c2a2c6f6830215e0276a0df1ab4e0edfd78ce1cfe6fe`
  - **Single-Member ZIP Archive:** [`docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.zip`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.zip) (`124,992` bytes, SHA-256 `f5eb5816d90242c11e71542790dac2eddba9f9ace16acda40a4a9b882ea17a50`)
  - **Companion NaN-Outside Spec Twin (`-nan.tif`):** [`docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif) (`205,671` bytes, SHA-256 `923e2aecd972af1854a52fe83971d43707e578bb765eef224ea159c3ee899678`)
  - **Authoritative Run Card JSON:** [`evidence/run_card.json`](evidence/run_card.json) / [`registry/run_card.json`](registry/run_card.json) / [`docs/downloads/run_card.json`](docs/downloads/run_card.json)
  - **GitHub Pages Executive Summary Subpage:** [`docs/executive-summary.html`](docs/executive-summary.html) (and [`docs/index.html`](docs/index.html))
  - **DrivenData Submission Name (`57 / 140` chars):**
    ```text
    gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros
    ```
  - **DrivenData Submission Note (`130 / 140` chars):**
    ```text
    G73 H73-M M3 3-expert LOQO piedmont co-kriging + wing-bridge + dmin3 submod, 37654 off-cat dots; HOLDOUT-DTI 0.1224 vs ctrl 0.0939
    ```
  - **Format & Portal Safety Verification (`15 / 15` checks passed in [`evidence/validator_h73m.json`](evidence/validator_h73m.json)):** Single-band `float32`, `3292 × 3730`, `EPSG:32611`, `100 m` pixels, `nodata=None`, 100% finite values in `[0.0, 1.0]` (`0` NaNs, `0` Infs — immune to DrivenData's `"Predicted values must be in range [0, 1]"` error), exact `37,654` binary `1.0` off-catalogue dots (`> 200 m` from visible catalogue, `0` dots on visible catalogue, `0` dots outside survey footprint, minimum Euclidean inter-dot spacing $d_{\min} = 3.0\text{ px} = 300\text{ m}$).

---

## Core Values

**Maximize P(Win)** — every weekly submission slot is an experiment, not a lottery ticket. We weigh tradeoffs, assess risk, and choose the path that maximizes probability of winning.

**Own the Outcome** — we own results end-to-end, not just our slice. We treat failure and success as signals and act without waiting for permission.

---

## Summary of All Gates & Multi-Instrument Results (`PARALLEL-RUN PROTOCOL`)

Every number in this repository is explicitly labeled with its evidence class (`HOLDOUT-DTI`, `PROXY-DTI (report-only, non-gating)`, or `ORGANIZER-CONFIRMED`). No projection is ever written as a score.

| Gate / Evaluation Instrument | Evidence Class & Evaluator | Promoted `H73-M M3` (`37,654` dots) | Primary Control (`h33_analogue_foldfair` / `H33`) | Paired Bootstrap $\Delta$ & 95% CI | Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Gating Holdout (`Instrument A`)** | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, 11,321 withheld pos px, 4 folds, 1,000-draw paired 20 km cluster bootstrap) | **`0.1224`** (`[0.1072, 0.1390]`) | `0.0939` (`[0.0813, 0.1076]`) | **`+0.0285` (`+30.4%`)**, 95% CI **`[+0.0154, +0.0419]`** | **✅ PASS (`CI > 0`)** |
| **Gain vs Prior Repo Baseline (`H73-1 E1`)** | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, 11,321 withheld pos px) | **`0.1224`** (`[0.1072, 0.1390]`) | `0.0548` (`[0.0417, 0.0688]`) | **`+0.0676` (`+123.5%`)**, 95% CI **`[+0.0512, +0.0848]`** | **✅ PASS (`CI > 0`)** |
| **Piedmont Off-Catalogue Proxy (`Instrument C_pied`)** | `PROXY-DTI (report-only)` (`9,949` piedmont SGMC px, $d_{\text{cat}}>2.5\text{ px}$, relief $\le P_{75}$, slope $\le P_{80}$, depth $\ge 250\text{ m}$) | **`0.1435`** (`[0.1237, 0.1601]`) | `0.0937` (`G70 P9`: `0.1112`, `G70 P8`: `0.0842`, `H73-1`: `0.0789`) | **`+0.0499` (`+53.2%`)**, 95% CI **`[+0.0319, +0.0656]`** | **✅ #1 Across All Repos** |
| **Full Off-Catalogue SGMC Proxy (`Instrument B'`)** | `PROXY-DTI (report-only)` (`59,937` SGMC px, $d_{\text{cat}} \ge 3.0\text{ px}$) | **`0.1212`** (`[0.1051, 0.1361]`) | `0.0938` (`[0.0799, 0.1071]`) | **`+0.0274` (`+29.2%`)**, 95% CI **`[+0.0135, +0.0408]`** | **✅ PASS** |
| **Single-Feature Leakage Canary (`85` channels)** | `HOLDOUT-DTI CANARY` (`evidence/canaries_h73m.json`, gate $\le 0.90$) | Max symmetric AUC = **`0.7950`** | Gate threshold $\le 0.9000$ | `85 / 85` features pass on both catalogue & withheld truth | **✅ PASS (`85/85`)** |
| **Registry Uniqueness Audit (`161` unique rasters)** | `REGISTRY-MEASUREMENT` (`evidence/uniqueness_h73m.json`, 217 `.tif` files scanned) | Surface $|\rho| = 0.3587 \le 0.90$ · Dots $|\rho| = 0.1329 \le 0.90$ | Worst mutual & sparse ($\le 150\text{k}$ dots) 3 px overlap = **`0.6677 <= 0.70`** (vs `G70 P9`) | Vs `GEMSDOE32 H33`: `0.4186` · Vs `G70 P8-OOF38k`: `0.3882` · Vs `H73-1`: `0.2679` | **✅ PASS ($\le 0.70$)** |
| **Experiment Budget Cap** | `PARALLEL-RUN PROTOCOL` ($\le 3$ experiments, $\le 2$ hours) | `3` experiments (`M1`, `M2`, `M3`) | Runtime `120.9s` (with cached LOQO experts) | Within budget | **✅ PASS** |

---

## Submission Eligibility of All GeoTIFF Files in `docs/downloads/`

| File in `docs/downloads/` | Role / Lane | In-Footprint Dots | Primary `HOLDOUT-DTI` (`Instrument A`) | Piedmont `PROXY-DTI` (`Instrument C_pied`) | Submission Verdict |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif`** (`SHA-256: ac1c720d...`) | **`H73-M M3` Primary Promoted** | `37,654` (`0` outside, `0` on cat) | **`0.1224`** `[0.1072, 0.1390]` | **`0.1435`** `[0.1237, 0.1601]` | **✅ PROMOTE — OK TO DOWNLOAD & SUBMIT** |
| `gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif` (`SHA-256: 923e2aec...`) | `H73-M M3` NaN-Outside Twin | `37,654` (`NaN` outside footprint) | **`0.1224`** `[0.1072, 0.1390]` | **`0.1435`** `[0.1237, 0.1601]` | ⚠️ Spec twin (submit `-zeros.tif` above to DrivenData portal) |
| `gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif` (`SHA-256: d09dca24...`) | `H73-1 E1` Unsupervised Baseline | `37,654` | `0.0548` `[0.0417, 0.0688]` | `0.0789` `[0.0650, 0.0934]` | ❌ **NEGATIVE BASELINE — DO NOT SUBMIT** |
| `gems73-hydro-permeability-corridor-37654-20261021T000000Z-2bbb79d4-zeros.tif` (`SHA-256: 2bbb79d4...`) | Retired PR #1 Synthetic (`IR-73-10/11`) | `16,180` (`21,474` outside footprint!) | `0.0271` | `0.0294` | ❌ **RETIRED SYNTHETIC — DO NOT SUBMIT** |
| `gems73-h73a-blind-stepover-20261021T022620Z-c111bb0f-zeros.tif` (`SHA-256: 46859dc6...`) | Retired PR #2 Synthetic (`IR-73-01/11`) | `30,762` (random Bresenham lines) | `0.0015` | `0.0175` | ❌ **RETIRED SYNTHETIC — DO NOT SUBMIT** |

---

## Part 1 — PhD-Level Forensic Study of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778` `ORGANIZER-CONFIRMED`)

1. **Exact Subset Hierarchy (`H33-2-B2 ⊂ D2.8 ⊂ D1.5 ⊂ H19-5`):**
   Byte-level verification across `.cache/gems_data/scored/` and `GEMSDOE32` proves:
   - `19GEMSDOE` `H19-5` (`121,131` binary dots) scored `0.1922` `ORGANIZER-CONFIRMED`.
   - `GEMSDOE24` `D1.5` (`60,069` dots, $1.5\text{ px}$ thinning of `H19-5`) scored `0.2339` `ORGANIZER-CONFIRMED`.
   - `GEMSDOE25` `D2.8` (`44,090` dots, $2.8\text{ px}$ thinning of `H19-5`) scored `0.2600` `ORGANIZER-CONFIRMED`.
   - `GEMSDOE32` `H33-2-B2` (`37,654` dots) is the exact set difference $\texttt{D2.8} \cap \{x : d_{\text{catalogue}}(x) > 2.0\text{ px}\ (200\text{ m})\}$, deleting `6,436` near-catalogue dots and jumping to **`0.2778` `ORGANIZER-CONFIRMED`** (`+0.0178` live DTI).
2. **Mathematical Proof of the B2 Catalogue-Clearance Theorem:**
   Under $\mathrm{DTI} = \mathrm{TP}_w / (0.8\,K + 0.2\,\mathrm{TP}_w + 0.2\,\mathrm{FP}_w)$ with $R = 300\text{ m} = 3\text{ px}$, known catalogue pixels (`sample_submission.tif == 1.0`, `60,988` pixels) are masked on the evaluation server. Any dot within $200\text{ m}$ of the visible catalogue wastes its $300\text{ m}$ kernel on masked pixels ($\Delta\mathrm{TP}_w \approx 0$) while paying $+0.2$ in the denominator ($6{,}436 \times 0.2 = 1{,}287.2$ wasted denominator units).
3. **Why `GEMSDOE70`'s `P8-OOF38k` Scored `0.2478` Live Despite `0.1113` on `Instrument A`:**
   `P8-OOF38k` weighted its structural head 50% on unfiltered off-catalogue SGMC faults (`SGMC \ cat`). Because **84.9% of `SGMC \ cat` pixels lie in steep pre-Quaternary mountain-interior bedrock** rather than geothermal basin/piedmont corridors, `P8-OOF38k`'s score on the live-calibrated piedmont proxy **`Instrument C_pied`** (`9,949` low-relief deep-basin SGMC pixels, Spearman $\rho = +0.74$ to $+0.87$ with live leaderboard scores) dropped to **`0.0842`** (`-10.1%` below `H33 = 0.0937`).
4. **How `H73-M M3` Beats Both `H33` and `GEMSDOE70` `P8`/`P9`:**
   - Trains **3 regime-specialized 4-quadrant LOQO experts** (`M_Q` active Quaternary scarp expert, `M_P` piedmont/hydrothermal expert, `M_S` piedmont-gated structural expert that upweights piedmont traces by `4.2x` and downweights mountain-interior bedrock contacts by `0.35x`),
   - Co-kriges them with a spatially varying piedmont weight $\pi_{\text{pied}}(x) \in [0, 1]$ and a **Cross-Contour Pluvial Shoreline Gate** (`M1`),
   - Applies strictly fold-safe **Anisotropic Transtensional Fracture Mechanics** (strike-projected tip lobe + $\pm 28^\circ$ Andersonian wing-crack bridge + relay annulus + top-decile `H73-1` piedmont scarp-chain witness) (`M2`), and
   - Allocates `37,654` off-catalogue dots ($d_{\text{cat}} > 200\text{ m}$) via lazy-greedy 300 m submodular DTI maximization with **radius-matched minimum inter-dot spacing $d_{\min} = 3.0\text{ px}$ ($300\text{ m}$)** (`M3`), achieving **`0.1224` on `Instrument A` (`+30.4%` vs `H33`)** and **`0.1435` on `Instrument C_pied` (`+53.2%` vs `H33`)**.

---

## Part 2 — Five Ranked Geological Hypotheses (`docs/research/hypotheses.md`)

1. **`H73-M` (Rank 1 — Executed & Promoted):** *Regime-Stratified Multi-Physics Co-Kriging + Anisotropic Transtensional Wing-Bridge + Radius-Matched ($d_{\min}=3.0\text{ px}$) Submodular 300 m DTI Allocator* (`HOLDOUT-DTI = 0.1224` vs `0.0939` control, paired $\Delta = +0.0285$, 95% CI `[+0.0154, +0.0419]`; `PROXY-DTI C_pied = 0.1435` vs `0.0937`, paired $\Delta = +0.0499$).
2. **`H73-B` (Rank 2):** *Fluvial $\chi$-Disequilibrium & $k_{sn}$ Knickpoint Alignment Across Unmapped Range-Front Transfer Zones* (`dem10_chi_100m_i16.tif`, `topo_10m_derived_100m_u8.tif`; integrated as 6 channels inside `H73-M`).
3. **`H73-C` (Rank 3):** *Hydrothermal Demagnetization Trough & Potassic/Argillic (`K/Th`) Alteration Halo Detector* (`radiometrics_grid.tif`, `external_context_100m.tif`, `GDR_1391`; integrated as 9 channels inside `H73-M`).
4. **`H73-D` (Rank 4):** *Multi-Azimuth Radon-Transform Sub-Basin Transfer Fault Tracker* (`iso_grav_anom_hg`, `cond_surf`, `geod_shearrate`; deferred to respect the 3-experiment budget cap).
5. **`H73-1` (Rank 5 — Preserved Unsupervised Baseline):** *Unsupervised Piedmont Scarp-Chain + Subsurface Co-Step Detector* (`HOLDOUT-DTI = 0.0548` vs `0.0939`, verdict `negative`; retained as top-decile witness `s_h73_1_tail` inside `H73-M`).

---

## Reproducible Commands

```bash
# 1. Restore and SHA-256 verify all 28 competition, external USGS/GDR, and scored files
bash scripts/download_competition_data.sh

# 2. Build or verify the 82-feature disk-backed memmap (.cache/work/h73m_features_fp.f32)
.venv/bin/python scripts/prepare_data.py

# 3. Run the preregistered 3-experiment H73-M suite (M1, M2, M3) + 85-feature leakage canary
.venv/bin/python scripts/run_h73m_experiments.py

# 4. Package the promoted GeoTIFF (-zeros.tif, .zip, and -nan.tif) via vendor/gems57/submission_writer.py
.venv/bin/python scripts/build_h73m_submission.py

# 5. Run the 161-raster registry uniqueness audit & assemble the authoritative Run Card and GitHub Pages site
.venv/bin/python scripts/audit_h73m_registry.py
.venv/bin/python scripts/build_run_card_h73m.py
.venv/bin/python scripts/generate_figures.py
.venv/bin/python scripts/build_site.py

# 6. Run the full 15-test pytest suite
.venv/bin/pytest -q
```

---

## Official Trusted Sources (Verified Line-by-Line)

- **Competition Specification & Metric:** [DrivenData Competition 306 — Gaze into the Void: 3D Subsurface Fault Detection](https://www.drivendata.org/competitions/306/competition-gem-3d-faults/) · [Leaderboard](https://www.drivendata.org/competitions/306/competition-gem-3d-faults/leaderboard/) · [U.S. DOE GEMS Prize on HeroX](https://www.herox.com/GEMSPrize)
- **INGENIOUS & Great Basin Play Fairway Data:** [DOE Geothermal Data Repository (GDR) Submission 1391](https://gdr.openei.org/submissions/1391) · Faulds, J.E. et al. (2015/2021), *Structural Controls of Geothermal Systems in the Great Basin Region*, Geothermics ([doi:10.1016/j.geothermics.2015.09.003](https://doi.org/10.1016/j.geothermics.2015.09.003))
- **GeoDAWN & 3DEP Elevation:** [USGS GeoDAWN Survey](https://www.usgs.gov/centers/gggsc/science/geodawn) · [USGS 3D Elevation Program (3DEP)](https://www.usgs.gov/3d-elevation-program)
- **USGS Fault Compilations:** [USGS Quaternary Fault and Fold Database](https://www.usgs.gov/natural-hazards/earthquake-hazards/faults) · Horton, J.D. et al. (2017), [USGS Data Series 1052 — State Geologic Map Compilation (SGMC)](https://doi.org/10.3133/ds1052)
- **Potential-Field & Submodular Theory:** Miller, H.G. & Singh, V. (1994), *Potential field tilt*, J. Appl. Geophys. ([doi:10.1016/0926-9851(94)90022-1](https://doi.org/10.1016/0926-9851(94)90022-1)) · Blakely, R.J. & Simpson, R.W. (1986), Geophysics ([doi:10.1190/1.1442197](https://doi.org/10.1190/1.1442197)) · Reheis, M.C. (1999), [USGS MF-2323](https://doi.org/10.3133/mf2323) · Minoux, M. (1978), [doi:10.1007/BFb0006528](https://doi.org/10.1007/BFb0006528)

---

<details>
<summary><strong>Original Competition Task &amp; PARALLEL-RUN PROTOCOL Prompt (Verbatim)</strong></summary>

```text
Please review the entire repo for the competition and execute the task at hand. We MUST generate a unique tif submission for the competition. It must be easy to download and submit the submission, and it must be immediately obvious on the site whether it is OK to download and submit the generated tif submission for the competition.

Review the h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros submission which scored 0.2778 and is the highest score across the group of GEMSDOE websites we have created (#1 on the leaderboard is currently 0.4413). Study this at the PhD level to understand why this submission scored the highest and whether we can beat it. Before writing any code, generate 3–5 candidate geological hypotheses that haven't been tried yet. Each must name the specific layer(s) it uses, the physical signature it looks for, why that signature catches a fault that the USGS/INGENIOUS mapper missed, and how it differs from existing implementations in the repo. Rank them by expected DTI improvement and implementation cost.

PARALLEL-RUN PROTOCOL (this session is one of several running at once):
1. Stay in your lane. Before running experiments, check that your hypothesis is not already the main line of this repo or a duplicate of a scored submission in the registry. Before declaring a candidate ready, compute its surface rank-correlation (must be <= 0.90) and 3px dot overlap (must be <= 70%) against registry rasters.
2. Reuse, don't rebuild. Use the shared template tools (evaluate_holdout.py, submission_writer.py, cached feature stack) verbatim. Do not write a new holdout, metric, or validator. If a tool is broken, fix it in the template and note the fix.
3. Separate evidence classes. Every number you report must be labeled either HOLDOUT-DTI (with evaluator version, withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (with the submission-page receipt). Never write a projection as a score.
4. Leakage & mimic checks. Run the single-feature holdout AUC canary (any feature > 0.90 means catalogue leakage) and name the non-fault geological feature most likely to fool your detector and why your gate rejects it.
5. Stop on budget. Cap at 3 experiments or 2 hours. If none beats the current holdout best with a paired bootstrap CI excluding 0, report a clean negative result and do not recommend spending a weekly submission slot.
6. End with one Run Card (JSON + 10-line summary): hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, correlation/overlap vs registry, raster sha256, validator output, submission name + <=140-char note, and verdict: promote / negative.

Goal: Place top of the leaderboard in the DOE GEMS Prize Challenge (https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
Core Values:
- Maximize P(Win): Every weekly submission slot is an experiment, not a lottery ticket.
- Own the Outcome: We own results end-to-end, not just our slice.
- Work autonomously with no manual input; verify line-by-line from official trusted sources with links; flag any irregularities; no hallucinations.
- Run the task through Pass 1 (implement & verify), Pass 2 (review for bugs/edge cases/missing requirements & fix), and Pass 3 (re-check against original prompt & finalize), then create and merge a PR to main.
```

</details>
