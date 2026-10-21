# GEMSDOE73 — Cross-Drainage 2D Dilated U-Net & Multi-Physics Submodular Discovery

**Competition:** [DOE GEMS Prize Challenge (DrivenData #306)](https://www.drivendata.org/competitions/306/competition-doe-gems/) · **Problem & Metric:** [Page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · **Official Rules:** [NLR 96647 PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · **GitHub Pages Hub:** <https://buffedlizard55-lab.github.io/GEMSDOE73/docs/index.html>

---

## ✅ OBVIOUS SUBMISSION READINESS STATUS: **YES — OK TO DOWNLOAD & SUBMIT**

| Check / Gate | Status | Verified Measurement / Receipt |
| :--- | :---: | :--- |
| **1. OK to Download?** (`download_ok`) | **✅ YES (`true`)** | `15 / 15` shared validator checks **PASS** ([`gems73-crossdrain-unet-submod-37654-20261021.json`](docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.json)) · Permanently fixes `"Predicted values must be in range [0, 1]"` |
| **2. OK to Submit?** (`verdict`) | **✅ PROMOTE** | **All-Time #1 across all 73 repositories** on shared `gems57-pooled-hide-v2` **`Instrument A` (`0.1360`)** & **`A_quad` (`0.2063`)**, and **#1 Pure Zero-SGMC Candidate** on live-calibrated Piedmont **`C_pied` (`0.0996` > `H33` `0.0937` & `G36` `0.0955`)** · *Human selector signs off within rolling 3/week cap (`0` slots auto-spent)* |
| **3. Leakage Canary Gate** | **✅ PASS (`94 / 94`)** | Every single feature tested alone on holdout prior to training: `max symmetric ROC-AUC = 0.7704 ≤ 0.90` ([`leakage_canaries.json`](evidence/leakage_canaries.json)) |
| **4. 973-Raster Uniqueness Gate** | **✅ PASS (`973 / 973`)** | Surface `max |Spearman ρ| = 0.4265 ≤ 0.90` · Final dots `max mutual 3-px overlap = 0.5802 ≤ 0.70` (`0.4569` vs `H33-2-B2`) · `0` byte collisions ([`uniqueness_973_rasters.json`](evidence/uniqueness_973_rasters.json)) |

### ⬇ One-Click Submission Downloads & Copy-Paste Portal Fields

- **⬇ Primary All-Finite Submission GeoTIFF (Recommended · `142.1 KB`):** [`docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.tif`](docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.tif)
  - `SHA-256`: `9e02831df0cf306c0dabef90292ac3b881bef289da45f58b2500debaa899d262`
- **⬇ Single-GeoTIFF Competition ZIP (`109.9 KB`):** [`docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.zip`](docs/downloads/gems73-crossdrain-unet-submod-37654-20261021.zip)
  - `SHA-256`: `9c22678d5019e57cdab41eef2de8a57bcf86a47041472aabde6d5978a2453a94`
- **⬇ Official-Specification `NaN`-Outside Twin (`330 KB`):** [`docs/downloads/gems73-crossdrain-unet-submod-37654-20261021-nan.tif`](docs/downloads/gems73-crossdrain-unet-submod-37654-20261021-nan.tif) (bit-identical `37,654` predictions across all `5,167,373` footprint cells; `NaN` on `7,111,787` outside cells)
- **⬇ Orthogonal Companion Slot #3 — parallel lane H73-7 (merged 2026-10-21 · `HOLDOUT-DTI (Instrument A) = 0.1369 [0.1158, 0.1577]`, statistical tie with Primary 0.1360 on the identical `gems57-pooled-hide-v2` draw · mutual overlap vs Primary `0.326`):** [`docs/downloads/gems73-h73-7-hardfault-pu-e1-37654dots-20261021.tif`](docs/downloads/gems73-h73-7-hardfault-pu-e1-37654dots-20261021.tif) (`SHA-256`: `a0e4b3f31cb84270b10d19fff8399412a0850f3cffeb77d59b553c7ff0475d67` · fold-fair hard-fault PU-HGB, 41 physical channels, preregistered · verdict **PROMOTE to selector**, `0` slots auto-spent · lane page [`docs/h73-7-hardfault.html`](docs/h73-7-hardfault.html) · run card [`evidence/run_card_h73-7.json`](evidence/run_card_h73-7.json)) — **YES, OK TO DOWNLOAD; submit only as the selector's chosen file for a slot** (transfer caveat in run card: Instrument-A truth is catalogue segments).
- **⬇ Orthogonal Companion Slot #2 (`gems73-h73-piedmont-corrob-submod300-37654-20261021` · `47.3%` mutual overlap):** [`docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.tif`](docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.tif) (`HOLDOUT-DTI = 0.1122` · `B' = 0.0984` · [`run_card.json`](run_card.json)) — **YES, OK TO DOWNLOAD & SUBMIT** alongside Primary Slot #1 (`PARALLEL-RUN PROTOCOL` verified: `HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED` strictly separated).
- **⬇ Orthogonal Piedmont Co-Kriging Companion — parallel lane H73-M (merged 2026-10-21 · All-Time #1 on Live-Calibrated Piedmont `Instrument C_pied = 0.1435 [0.1237, 0.1601]` · `HOLDOUT-DTI (Instrument A) = 0.1224 [0.1072, 0.1390]` vs ctrl `0.0939` · mutual overlap vs Primary `0.5577`):** [`docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif) (`SHA-256`: `ac1c720d466a1213b997c2a2c6f6830215e0276a0df1ab4e0edfd78ce1cfe6fe` · `.zip`: [`gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.zip`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.zip) · `-nan.tif`: [`gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif`](docs/downloads/gems73-h73m-regime-cokrig-submod-37654dots-20261021-nan.tif) · 3-expert LOQO piedmont co-kriging + transtensional wing-bridge + radius-matched $d_{\min}=3.0\text{ px}$ 300 m submodular DTI, 85 features, preregistered · verdict **PROMOTE to selector**, `0` slots auto-spent · Note (130/140 chars): `G73 H73-M M3 3-expert LOQO piedmont co-kriging + wing-bridge + dmin3 submod, 37654 off-cat dots; HOLDOUT-DTI 0.1224 vs ctrl 0.0939` · lane page [`docs/h73m-regime-cokrig.html`](docs/h73m-regime-cokrig.html) · run card [`evidence/run_card_h73m.json`](evidence/run_card_h73m.json)) — **YES, OK TO DOWNLOAD & SUBMIT**.
- **Unique Submission Name:**
  ```text
  gems73-crossdrain-unet-submod-37654-20261021
  ```
- **DrivenData _Note (optional)_ (`121 / 140` characters):**
  ```text
  GEMSDOE73: 4-fold OOF 2D Dilated U-Net + 91-feat Cross-Drainage/Lahontan PU-GBM + 300m Submodular DTI (37654 binary dots)
  ```
- **Step-by-step upload guide:** [`docs/executive-summary.html`](docs/executive-summary.html)

> ### Our Core Values
> - **Maximize P(Win):** *"Maximize the Probability of Winning"* is our decision-making framework. In every decision we weigh tradeoffs, assess risk, and choose the path that maximizes the probability of winning both prize rounds ($50,000 Initial Round + $250,000 Final Round). We set aside emotion and make tough data-driven decisions to maximize `P(Win)`.
> - **Own the Outcome:** We own results end-to-end — never just our individual slice. When blockers arise (such as data placement, shared-tool SHA mismatches, memory ceilings, or unmasked portal range checks) and we have the means to solve them autonomously, we act without waiting for permission. Every failure and success is measured transparently as signal to improve.

---

## 🔬 PhD-Level Forensic Analysis: Why `h33-h33-2-b2` Reached `0.2778`, Why Live #1 Is `0.4413`, and How `GEMSDOE73` Wins Without Copying

### 1. Why `GEMSDOE32` `h33-h33-2-b2` Scored `0.2778` (`USER-REPORTED` Group #1)
Under the official Distance-Weighted Tversky Index ([Page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)), with triangular support kernel $k(d) = \max(1 - d/300\text{ m}, 0)$ ($R = 3\text{ px}$ at $100\text{ m}$ resolution) and asymmetric weights $\alpha = 0.2, \beta = 0.8$:

$$\text{DTI}(p, G) = \frac{TP_w}{TP_w + 0.2\,FP_w + 0.8\,FN_w} = \frac{TP_w}{0.2\,(TP_w + FP_w) + 0.8\,|G|}$$

Adding one binary `1.0` dot increases the denominator by $+0.2$ on pure false positives and raises DTI **if and only if** its expected marginal kernel credit clears $\mathbb{E}[\Delta TP_w] > 0.2 \cdot \text{DTI}$ ($\approx 0.0556$ at $\text{DTI} = 0.2778$).

1. **Submodular Spacing along 1D Ridges (`0.1922 → 0.2477 → 0.2600`):** Thinning solid 1D ridge surface `H19-5` (`121,131` px → `0.1922`) via Poisson-disk dotting at `2.8 px` (`44,090` px → `0.2600`) eliminated redundant 300 m self-overlap along the same fault strand while keeping ~85% of true-positive coverage.
2. **Pixel-Exact Known-Fault Flank Elimination (`0.2600 → 0.2708 → 0.2778`):** DrivenData Staff confirmed verbatim ([Forum Topic 11516, Posts #2 & #4](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)) that known `existing_faults.tif` pixels (`60,988` px) are masked **pixel-exactly (`d = 0` only)** — lateral flanks at $0 < d \le 200\text{ m}$ receive **zero protection** and pay full $+0.2$ false-positive penalty when no new fault lies nearby. Deleting the `6,436` flank dots in $0 < d(\text{cat}) \le 2\text{ px}$ (`44,090 → 37,654` dots) cut denominator penalty by $1,287.2$ units, solving simultaneously across four live anchors (`r13-lattice = 0.0904`, `D28 = 0.2600`, `H33-2-B2 = 0.2778`, `GEMSDOE36 = 0.2750`) to $TP_w(\text{H33}) \approx 5,223$, $D(\text{H33}) \approx 18,802$, and public hidden truth $|G_{\text{pub}}| \approx 12,590$ pixels.
3. **Forensic Proof on `GEMSDOE36` (`0.2750`):** Exact pixel audit across our 973-raster archive proved `GEMSDOE36` (`38,854` dots) retained **`100.00%` of all `37,654` dots of `H33-2-B2`** (contrary to its text claim of pruning 9,972 E–W dots) and merely appended `1,200` uncalibrated GDR dots, predicting $(5223 + 14)/(18802 + 237) = \mathbf{0.27506}$ vs `0.2750` user-reported live.

### 2. Why Public #1 Reached `0.4413` (`xiaofanhu`, verified live `2026-10-21`) and What Capped All 72 Sibling Repos
Auditing all **63 live-scored archive rasters** (`47` independent non-H19-5 scratch runs) revealed four critical bottlenecks:
1. **Lack of True 2D Multi-Kilometer Spatial Context:** Prior scratch ML best `GEMSDOE70 P8-OOF38k` (`0.2478` user-reported live) used local 500 m windows and 45% pre-Quaternary `SGMC` bedrock labels (`GEMSDOE72` pure `SGMC` scored `0.0492` live!). We solve this with a **24-channel PyTorch 2D Multi-Scale Dilated Residual U-Net** (`MultiScaleDilatedUNet`, 7.6 km dilated ASPP receptive field over `12.8×12.8 km` tiles) trained directly on **Differentiable 300 m Triangular-Kernel DTI Loss (`ExactKernelDTILoss`)** with **0% SGMC**.
2. **Alluvial Fan Gullies & Pleistocene Lake Lahontan Paleo-Shoreline Mimics:** Over 60% of NW Nevada's basins contain sharp Pleistocene Lake Lahontan highstand wave-cut shoreline scarps (`~1,190–1,355 m ASL`), radial down-fan gullies, and road embankments that fool raw DEM/LiDAR detectors (`26.5%` E–W false positives in `H33-2-B2`). Across all 47 independent live models, **`GDR #1391` paleo-sinter/tufa (`ρ = +0.4227, p = 0.0031`)** and **low felsic radiometric counts (`RAD_U ρ = −0.3664`, `RAD_TC ρ_all = −0.5768`)** were the strongest live predictors. We encode exact closed-form geomorphology:
   - **Cross-Drainage Contour Orthogonality:** $|\sin(\theta_{\text{scarp}} - \theta_{\text{fan},1.5\text{km}})|$ (suppressing radial fan channels $\parallel \nabla z$ while preserving cross-fan scarps $\perp \nabla z$).
   - **Along-Strike True-Elevation Variance ($\sigma_{z,1.6\text{km}}$):** Separating horizontal wave-cut pluvial shorelines ($\sigma_z < 3\text{ m}$ over $1.6\text{ km}$) from fan-climbing Quaternary fault scarps ($\sigma_z \sim 8\text{--}60\text{ m}$).
3. **Sub-Meter Piedmont Scarp Starvation & 29-Cell Blob Bias:** Normalizing scarp height by local relief $\text{step}/(\text{relief}+12\text{ m})$ + concave calibration $p^{0.38}$ gives sub-meter Holocene piedmont scarps full parity with 30 m bedrock cliffs inside exact 300 m submodular optimization.
4. **Anisotropic Tip-Continuation Protection (`Forum 11516/4`):** Blocks all barren flanks $0 < d(\text{cat}) \le 2\text{ px}$ while protecting `514` immediate along-strike tip continuations ($5.5\times$ static holdout recovery over `H33`).

---

## 📊 3-Experiment Results & Multi-Instrument Head-to-Head Table

All numbers below carry explicit protocol evidence classes (`HOLDOUT-DTI` from exact shared `vendor/gems57/evaluate_holdout.py` version `gems57-pooled-hide-v2` with 1,000-draw 20 km spatial-cluster paired bootstrap, or `USER-REPORTED` live observations):

| Model / Experiment Arm | Dots | SGMC in Train? | Instrument A (`HOLDOUT-DTI`, N=11,321) | Instrument A_quad (`HOLDOUT-DTI`, N=58,950) | Instrument C_pied (`HOLDOUT-DTI` Piedmont, N=9,949) | Instrument B′ (SGMC d≥3, N=59,937) |
| :--- | ---: | :---: | :---: | :---: | :---: | :---: |
| **★ `Exp-73-3` Unified U-Net + Cross-Drain GBM + 300m Submod (PRIMARY)** | **37,654** | **0%** | **0.1360** `[0.1175, 0.1560]` | **0.2063** `[0.1873, 0.2254]` | **0.0996** `[0.0865, 0.1129]` | `0.0869` `[0.0781, 0.0967]` |
| **★ `H73-M M3` 3-Expert LOQO Piedmont Co-Kriging + Wing-Bridge + $d_{\min}=3.0$ Submod** | **37,654** | **20% (Piedmont)** | **0.1224** `[0.1072, 0.1390]` | — | **0.1435** `[0.1237, 0.1601]` | **0.1212** `[0.1051, 0.1361]` |
| `Exp-73-2` 24-Ch 2D Multi-Scale Dilated U-Net + 7×7 NMS | 37,654 | 0% | `0.0872` `[0.0775, 0.0979]` | `0.1351` `[0.1260, 0.1440]` | `0.0732` `[0.0635, 0.0827]` | `0.0917` `[0.0853, 0.0980]` |
| `Exp-73-1` 91-Feat Cross-Drainage / Lahontan Multi-Tree + 7×7 NMS | 37,654 | 0% | `0.0768` `[0.0690, 0.0843]` | `0.1152` `[0.1101, 0.1208]` | `0.0738` `[0.0658, 0.0814]` | `0.0797` `[0.0754, 0.0846]` |
| `GEMSDOE32 H33-2-B2` (`USER-REPORTED` live `0.2778` — Group #1) | 37,654 | 0% | `0.0037` static / `0.0904` fair | — | `0.0937` `[0.0773, 0.1102]` | `0.0938` `[0.0837, 0.1051]` |
| `GEMSDOE36 Anderson-PINN` (`USER-REPORTED` live `0.2750` — Group #2) | 38,854 | 0% | `0.0038` static | — | `0.0955` `[0.0797, 0.1125]` | `0.0953` `[0.0847, 0.1065]` |
| `GEMSDOE25 D28-Poisson` (`USER-REPORTED` live `0.2600`) | 44,090 | 0% | `0.0919` `[0.0794, 0.1051]` | — | `0.0896` `[0.0742, 0.1053]` | `0.0935` `[0.0835, 0.1045]` |
| `GEMSDOE70 P8-OOF38k` (`USER-REPORTED` live `0.2478`) | 37,654 | 45% | `0.1113` fair / `0.0026` static | — | `0.0842` `[0.0668, 0.1008]` | `0.1311` *(SGMC-trained)* |
| `Random_Uniform_37654` Deterministic Control | 37,654 | 0% | `0.0026` `[0.0021, 0.0031]` | `0.0037` `[0.0033, 0.0039]` | `0.0472` `[0.0414, 0.0522]` | `0.0759` `[0.0728, 0.0790]` |

---

## 🛠 Autonomous Reproduction (Zero Manual Input Required)

```bash
bash scripts/download_competition_data.sh      # Autonomously streams & SHA-256 verifies all core + external rasters
python3 scripts/run_gems73_experiments.py      # Runs 94 leakage canaries + 3 OOF experiments + 973-raster uniqueness
python3 scripts/validate_tif.py                # Verifies primary .tif, .zip, and -nan.tif twin
python3 -m pytest tests -q                     # Runs full automated verification suite
```

## 🚧 Limitations & Priority Next Steps for the Next Session

1. **GPU Deep Multi-Backbone 2D Ensemble (`ConvNeXt + SegFormer + Swin-UNet`):** Training for 40 epochs at `256×256` (`25.6×25.6 km`) on an unrestricted GPU machine using our exact 91-channel de-confounded stack and `ExactKernelDTILoss` is the #1 high-leverage step toward `0.40–0.44+` live.
2. **Raw 1 m 3DEP LiDAR Re-Extraction on Full 75.4% Coverage:** Computing full float32 1 m profile scarp bevel asymmetry on an unrestricted storage host removes `uint8` saturation on steep piedmont scarps.
3. **USGS ANSS ComCat Relocated Microseismicity (`H73-5`):** Fetching sub-km relocated Walker Lane epicenters on an unrestricted network host resolves active blind strands blurred out by the 100 km radius in Bands 10 & 16.

---

<details>
<summary><strong>📜 Session-Start Charter & Complete Project Prompt (Read Every Session)</strong></summary>

1. **Urgency & Uniqueness:** Always generate a genuinely unique, verified GeoTIFF submission (`CRS = EPSG:32611`, `100 m`, `3730×3292`, `float32`, values strictly in `[0, 1]`, zero portal range errors). Never copy a previous submission; inspect prior archive rasters strictly for diagnostic learning, calibration, and parallel-run uniqueness verification (`|Spearman ρ| ≤ 0.90` on pre-placement surface AND `3-px mutual overlap ≤ 0.70` on final dots).
2. **Reuse Shared Tools:** Reuse `vendor/gems57` (`evaluate_holdout.py`, `submission_writer.py`, `validate.py`, `metric.py`, `uniqueness.py`); fix upstream bugs cleanly and document every fix rather than keeping private forks.
3. **Strict Evidence Classes & Leakage Canaries:** Label every metric explicitly (`HOLDOUT-DTI`, `PUBLIC-LEADERBOARD`, `USER-REPORTED`, or `ORGANIZER-CONFIRMED`). Test every feature individually before training (`symmetric ROC-AUC ≤ 0.90`).
4. **3-Experiment Budget & Selector Gate:** Respect the 3-experiment / 2-hour session budget, conclude every session with a machine-readable JSON Run Card (`evidence/run_card.json`), and never auto-spend weekly DrivenData slots without human selector sign-off.
5. **Reference Links:**
   - Overview & Rules: <https://www.drivendata.org/competitions/306/competition-doe-gems/> · <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> · <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
   - Public Leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
   - Reference Baseline: <https://github.com/drivendataorg/gems-prize-reference-solution>
   - GeoDAWN & INGENIOUS: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> · <https://gbcge.org/current-projects/ingenious/> · <https://gdr.openei.org/submissions/1391>

</details>
