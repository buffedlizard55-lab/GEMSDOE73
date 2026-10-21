# GEMSDOE73 — Lane H73: 4-Line Corroborated Piedmont/Fluvial-Knickzone/Hydrothermal/Dip-Projected Out-of-Fold Multi-Physics Inversion with Exact 300 m Submodular Max-Cover

> ### ✅ SUBMISSION READINESS VERDICT: `PROMOTE` — **YES, OK TO DOWNLOAD & SUBMIT TO DRIVENDATA (`download_and_submit_ok = true`)**
>
> - **Unique Submission Name**: `gems73-h73-piedmont-corrob-submod300-37654-20261021`
> - **Submission Note (`131 / 140` chars)**:
>   ```text
>   GEMS73 H73: 4-line corroborated piedmont/chi/hydro/dip OOF HGB + 300m submodular max-cover, 37654 binary [0,1] off-cat dots, 0 NaN.
>   ```
> - **Direct Download Links (GitHub Pages & Repository Paths)**:
>   - **Primary Submission GeoTIFF (`-zeros.tif`, `142,140` bytes)**: [`docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.tif`](docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.tif) | [GitHub Pages Direct Download](https://buffedlizard55-lab.github.io/GEMSDOE73/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.tif)
>   - **Named Submission GeoTIFF (`.tif`, `142,140` bytes)**: [`docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021.tif`](docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021.tif) | [GitHub Pages Direct Download](https://buffedlizard55-lab.github.io/GEMSDOE73/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021.tif)
>   - **Compressed ZIP Archive (`.zip`, `107,256` bytes)**: [`docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.zip`](docs/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.zip) | [GitHub Pages Direct Download](https://buffedlizard55-lab.github.io/GEMSDOE73/downloads/gems73-h73-piedmont-corrob-submod300-37654-20261021-zeros.zip)
>   - **Canonical JSON Run Card (`run_card.json`)**: [`run_card.json`](run_card.json) | [`evidence/h73/run_card.json`](evidence/h73/run_card.json)
>   - **GitHub Pages Site**: [`docs/index.html`](docs/index.html) &middot; [`docs/executive-summary.html`](docs/executive-summary.html) &middot; [`docs/h33-autopsy.html`](docs/h33-autopsy.html) &middot; [`docs/hypotheses-and-ablation.html`](docs/hypotheses-and-ablation.html) &middot; [`docs/audit-and-sources.html`](docs/audit-and-sources.html)
> - **Cryptographic & Format Verification (`15 / 15` Checks `True`)**:
>   - **GeoTIFF SHA-256**: `846d5fe0fe53c618ebfa467c2545b7b78a459747be4aa1598d54e4979311c932` (`142,140` bytes)
>   - **ZIP SHA-256**: `a0b7f8a0f6909a5407a141d0bf01cf4e86248357e2330edb10ad690317738587` (`107,256` bytes)
>   - **Grid & Values**: Single-band `float32`, `EPSG:32611`, `3730 x 3292` @ `100 m` (`[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`), `12,279,160 / 12,279,160` finite pixels, **`0` NaNs anywhere**, **`0` Infs**, `min = 0.0`, `max = 1.0`, `37,654` binary `{0.0, 1.0}` positive dots, `0` dots on mapped catalogue `existing_faults.tif` (`min d_cat = 2.2361 px > 2.0 px`). Guaranteed immune to DrivenData's `"Predicted values must be in range [0, 1]"` validation error.

---

## 1. PhD-Level Forensic Autopsy: Why and How `GEMSDOE32` (`0.2778`) Achieved the Highest Historical Score

To answer with byte-level rigor why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) achieved **`0.2778` `[ORGANIZER-CONFIRMED]`** — the highest confirmed live score among all repositories listed in the prompt — we audited the exact GeoTIFF binaries across `6GEMSDOE` through `GEMSDOE72` (`88` `.tif` files, `80` unique SHA-256 digests).

### 1.1 Exact Nested Set-Inclusion Chain (`121,131 px` $\to$ `37,654 px`, `+0.0856` Live DTI)

Every single positive pixel in `GEMSDOE32` (`37,654` binary `{0.0, 1.0}` dots) is a **strict pixel-wise subset** of the out-of-fold multi-line posterior generated in `19GEMSDOE` (`H19-5`):

$$\underbrace{\text{H19-5 (`19GEMSDOE`)}}_{\substack{121{,}131\text{ px continuous} \\ \mathbf{0.1922}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{D1.5 (`GEMSDOE24`)}}_{\substack{60{,}069\text{ binary dots} \\ \mathbf{0.2477}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{D2.8 (`GEMSDOE25`)}}_{\substack{44{,}090\text{ binary dots} \\ \mathbf{0.2600}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{H27-4-R1 (`GEMSDOE28`)}}_{\substack{40{,}199\text{ dots } (d_{\text{cat}}>1\text{ px}) \\ \mathbf{0.2708}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{H33-2-B2 (`GEMSDOE32`)}}_{\substack{37{,}654\text{ dots } (d_{\text{cat}}>2\text{ px}) \\ \mathbf{0.2778}\text{ [ORGANIZER-CONFIRMED]}}}$$

1. **Out-of-Fold 4-Line Multi-Physics Corroborated Posterior (`H19-5`, `0.1922` `[ORGANIZER-CONFIRMED]`)**:
   - Fused four distinct physical evidence streams: `L1_pop` (5-fold spatial OOF `HistGradientBoostingClassifier` + `LogisticRegression` on 38 multiscale features), `L2_therm` (GDR `#1391` thermal wells/springs + 2 m temperature probes + paleo-geothermal sinter + `TMI_150m - RTP` demagnetization + GeoDAWN `Th/K`, `U/K` alteration edges), `L3_open` (1 m LiDAR scarp dipole/step + 10 m topographic openness/LRM + US Census TIGER road penalty), and `L4_anti` (1.5 km geopotential strike worms).
   - Applied **domain-split quantile calibration** across the `75.4%` LiDAR coverage seam and gated single-sensor spikes by $\text{clip}(\text{second\_best}/0.18, 0.35, 1.0)$.
2. **Sub-Kernel Blue-Noise Impulse Packing (`d = 2.8 px` = `280 m`: `0.1922` $\to$ `0.2600` `[ORGANIZER-CONFIRMED]`, `+0.0678` Live DTI)**:
   - Under the competition's Distance-Tolerant IoU (`DTI`) metric ($\alpha=0.2, \beta=0.8$, 300 m triangular tolerance kernel $K(r) = \max(0, 1 - r/300\text{ m})$), true-positive coverage `tpw` uses a **spatial maximum** $\tilde{p}(x) = \max_y p(y) K(\|x-y\|)$, whereas false-positive penalty `fpw` sums **linearly** across every emitted pixel $p(x)(1 - \tilde{t}(x))$.
   - Thinning contiguous ribbons (`121,131` px) into binary `{0, 1}` dots separated by $d = 2.8\text{ px}$ (`44,090` dots) eliminated $3\times$ to $5\times$ self-overlapping kernel redundancy while maintaining continuous 300 m bridges along strike.
3. **Catalogue Digitization-Halo Flank Pruning ($d_{\text{cat}} > 2\text{ px}$ = `200 m`: `0.2600` $\to$ `0.2708` $\to$ `0.2778` `[ORGANIZER-CONFIRMED]`, `+0.0178` Live DTI)**:
   - Per [DrivenData Forum Topic 11516, Post #4](https://community.drivendata.org/t/known-faults-in-target-for-test-eval/11516/4), known faults (`existing_faults.tif`) are masked from test evaluation at **exact pixel coordinates** (`100 m` width), whereas the physical topographic scarp and gravity gradient of a mapped fault spans `300–500 m` (`3–5 px`) laterally.
   - Pruning the `3,891` immediate-flank dots at $d_{\text{cat}} = 1\text{ px}$ (`GEMSDOE28`) added `+0.0108` live DTI (`+2.78` DTI points per 1,000 flank dots removed). Pruning the next `2,545` flank dots at $1 < d_{\text{cat}} \le 2\text{ px}$ (`GEMSDOE32`) added another `+0.0070` live DTI (`+2.75` DTI points per 1,000 flank dots removed).
4. **Geomorphic Habitat Concentration in Quaternary Piedmonts & Alluvial Basins (`pied% = 78.7%`, `steep% = 19.9%`)**:
   - The mapped Quaternary fault catalogue (`existing_faults.tif`, `60,988` px) is concentrated in **range-front piedmonts and sedimentary basins** (`steep% = 24.5%`).
   - `GEMSDOE32` (`0.2778`), `GEMSDOE36` (`0.2750`), `GEMSDOE28` (`0.2708`), and `GEMSDOE25` (`0.2600`) placed **`77.9%–79.0%`** of their dots in Quaternary piedmont/basin habitats (`pied_mask`) and only **`19.7%–20.7%`** on steep mountain slopes (`slp10 > Q75`).
   - By contrast, `GEMSDOE70 P8` (`gems70-p5-dual-submod300-oof38k-20261020`, `0.2478` `[ORGANIZER-CONFIRMED]`) trained its second HGB expert (`M_bed`) on **unfiltered `SGMC \ cat`** (`157,805` pixels, of which **`83%` are pre-Tertiary bedrock/intrusive/thrust contacts inside steep mountain ranges**). That caused `GEMSDOE70 P8` to place **`53.9%`** of its dots in steep mountain interiors (`steep% = 0.539`, `pied% = 0.435`), losing `-0.0300` live DTI relative to `GEMSDOE32` (`IR-73-05`).

---

## 2. How `GEMSDOE73` (`Exp 73.3`) Surpasses `GEMSDOE32` (`0.2778`) and `GEMSDOE70` (`0.2478`)

1. **Fixes `IR-73-04` (`dem10_chi_100m_i16.tif` Nodata `-32768` Corruption)**:
   - `GEMSDOE70` passed raw `int16` bands of `dem10_chi_100m_i16.tif` into `_fast_fill(..., fp)` without masking `nodata = -32768` on non-channel pixels (~`92%` of the grid), blurring `-32768` with valid channel values (`raw AUC = 0.5003`). Masking `> -30000` before diffusing `step_max * log1p(ksn_max) / sqrt(rel10 + 9)` restores the range-front fluvial knickzone signal (`single-feature AUC = 0.5583–0.5756`).
2. **Fixes `IR-73-05` (Mountain-Interior Bedrock Contamination) via Piedmont-Conditioned Structural Supervision (`M_pied`) & 4-Line Corroboration (`G_corrob`)**:
   - Trains a dedicated 4-quadrant OOF `HistGradientBoostingClassifier` expert (`M_pied`) on off-catalogue structural traces strictly conditioned on Quaternary piedmont/basin geomorphic habitat, fused with our 4-quadrant Quaternary OOF expert (`M_neo`), structural expert (`M_bed`), 4 physical lines (`L1` relief-normalized scarp + fluvial $\chi$ knickzones, `L2` geopotential + $60^\circ$ dip-projected basement step, `L3` GDR `#1391` hydrothermal conduits + radiometric/demagnetization alteration, `L4` fold-visible crack-tip/relay/length mechanics), and gated by median-line corroboration $G_{\text{corrob}} = \text{clip}(0.55 + 0.45\,\text{median}(L_1,L_2,L_3), 0.55, 1.0)$ and piedmont habitat $H_{\text{pied}}$.
   - Concentrates **`82.2%`** of emitted dots in Quaternary piedmont/basin habitats (`steep% = 16.3%`).
3. **Replaces Isotropic `d = 2.8 px` NMS with Exact Unblurred 300 m Triangular-Kernel Submodular Max-Cover**:
   - Directly maximizes the competition's 21-pixel 300 m kernel coverage objective via accelerated lazy-greedy submodular optimization (Minoux 1978), increasing `Instrument A` `HOLDOUT-DTI` from `0.10755` (`Exp 73.2` with `2.8 px` NMS) to **`0.11223`** (`Exp 73.3` with exact 300 m submodular max-cover) on the identical posterior surface (`+0.00468` gain solely from exact 300 m submodular placement).

---

## 3. Five Candidate Geological Hypotheses & Preregistered 3-Experiment Ablation

### 3.1 Five Candidate Geological Hypotheses (`H73-A` .. `H73-E`)

| Rank | ID | Candidate Hypothesis | Specific Layers Involved | Physical Signature & Mathematical Transform | Named Non-Fault Mimic & De-Confounder | Why It Catches Unmapped (Off-Catalogue) Faults | Expected DTI Gain | Cost |
| :---: | :---: | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **#1** | **`H73-A`** *(Executed as `Exp 73.3`)* | **4-Line Corroborated Piedmont/Intrabasin Multi-Physics & Fluvial-Knickzone OOF Inversion + Exact 300 m Submodular Max-Cover** | `lidar_scarp_features_u8.tif`, `dem10_onesided3.f32.npy`, `dem10_steep_ratio_max.f32.npy`, `topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_{i16,u8}.tif`, `tiger_road_distance_m.tif`, `training_features.tif` (19 bands), `geodawn_extensions_u8.tif`, GDR `#1391` thermal wells/2m-probes/sinter, OOF `sgmc_faults_100m.tif` targets | $S_{73.2} = \text{rank}_Q(M_{\text{neo}}^{0.42} S_{\text{struct}}^{0.32} S_{\text{phys}}^{0.26} G_{\text{corrob}}^{0.28} H_{\text{pied}}^{0.06})$ packed via exact unblurred 300 m triangular-kernel lazy-greedy submodular max-cover (`37,654` binary `{0,1}` dots at $d_{\text{cat}} > 2.05\text{ px}$). | (1) Pleistocene Lake Lahontan (`1330m`/`1235m`) & Bonneville (`1463m`/`1552m`) wave-cut paleoshorelines ($\sigma_z < 3\text{ m}$); (2) US Census TIGER highway/rail embankments ($d_{\text{road}} < 250\text{ m}$); (3) Steep pre-Tertiary mountain-interior contacts. | Master range-front faults ($L \ge 1.8\text{ km}$) are already in `existing_faults.tif`. Hidden test faults are degraded `0.4–1.5 m` piedmont scarps, blind intrabasin faults expressed by fluvial knickzones + gravity/magnetic steps + hydrothermal upflow, and tip splays at $d_{\text{cat}} > 200\text{ m}$. | **High** (`+0.02178` vs `H33` fair on `Inst A`; `+0.01602` vs `H33` on `Inst C_pied_all`) | Medium (~150 s) |
| **#2** | **`H73-B`** *(Executed as `Exp 73.1`)* | **Relief-Normalized Multi-Scale Scarp, Fluvial $\chi$-$k_{sn}$ Knickzone & Geopotential Strike-Worm OOF Detector (`d=2.8 px` NMS)** | `lidar_scarp_features_u8.tif`, `dem10_onesided3.f32.npy`, `dem10_chi_100m_{i16,u8}.tif` (fixing `IR-73-04` `-32768` nodata), `tiger_road_distance_m.tif`, `training_features.tif` | Relief-normalized 1 m LiDAR scarp asymmetry + 10 m one-sided breakline + masked fluvial knickzone halo $G_{3.5}\!\left(\frac{\Delta\ln k_{sn}\ln(1+k_{sn}) + 0.35\,n_{\text{knick}}}{\sqrt{\text{rel}_{10}+9}}\right)$, thinned at $d=2.8\text{ px}$. | Pluvial paleoshoreline benches & highway embankment cuts. | Normalizing topographic steps and channel knickzones by $\sqrt{\text{rel}_{10} + 9}$ prevents steep canyon walls from drowning out subtle $<1.5\text{ m}$ alluvial-fan fault scarps. | Moderate (`0.09033` `Inst A`; `0.10317` `Inst C_pied_all`) | Low (~45 s) |
| **#3** | **`H73-C`** *(Executed as `Exp 73.2`)* | **4-Line Corroborated Piedmont-Conditioned Dual OOF Posterior + Greedy `d=2.8 px` NMS Thinning** | All 46 static physical features + 3 fold-visible mechanical channels | Identical 4-line corroborated posterior $S_{73.2}$ as `H73-A`, emitted via greedy $d=2.8\text{ px}$ Poisson-disk NMS (`place_dots_nms`). | Same triple mimic decontamination as `H73-A`. | Directly measures the incremental value of piedmont-conditioned structural supervision ($M_{\text{pied}}$) + hydrothermal line $L_3$ + 4-line corroboration gate $G_{\text{corrob}}$ over `H73-B` while holding `2.8 px` NMS fixed. | High (`+0.01722` over `Exp 73.1` on `Inst A`; `+0.03808` on `Inst C_pied_all`) | Medium (~120 s) |
| **#4** | **`H73-D`** *(Col 45 in `H73-A..C`)* | **Andersonian $60^\circ$ Updip-Projected Basement-to-Surface Gradient Coincidence Operator** | `depth_to_base_surf` (Band 15), `iso_grav_anom_hg` (Band 18), `topo_10m_derived_100m_u8.tif` | Projects horizontal basement gradient $\|\nabla Z_b\|$ updip along $-\nabla Z_b / \|\nabla Z_b\|$ by $\Delta x_\perp = \text{clip}(Z_b \cot 60^\circ, 0, 1.2\text{ km})$. | Differential compaction across buried paleovalleys without brittle surface rupture. | Normal faults dipping $55^\circ\text{–}65^\circ$ basinward produce a basement density/gravity step displaced `300–1,200 m` hanging-wall-ward of the surface trace. | Moderate standalone (`AUC = 0.5356`); integrated as Col 45 | Low (~5 s) |
| **#5** | **`H73-E`** *(External Lane)* | **Sentinel-1 / ARIA InSAR Phase-Gradient & Terra ASTER TIR/SWIR Silicification/Argillic Lineaments** | ASF DAAC Sentinel-1 ARIA unwrapped interferograms + LP DAAC Terra ASTER `AST_05` / `AST_07XT` | Stacked LOS phase-velocity gradient $\|\nabla v_{\text{LOS}}\|$ + quartz/argillic alteration lineament ratio. | Agricultural pumping subsidence bowls & evaporite playas. | Detects aseismically creeping intrabasin faults and silicified fault-core breccia ribs lacking topographic scarps. | Blocked in sandbox egress allowlist; documented for external runs | External |

---

### 3.2 3-Experiment Ablation & Benchmark Comparison (`HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED`)

| Arm / Submission | Evidence Class | Live Score | Dots | `pied%` | `steep%` | `Inst A` (`HOLDOUT-DTI`, `K=11,321`) | `Inst C_pied_all` (`HOLDOUT-DTI`, `K=23,228`) | `Inst C_pied_sed` (`HOLDOUT-DTI`, `K=9,949`) | `Inst B'` (`HOLDOUT-DTI`, `K=59,937`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- |
| **`Exp 73.3` (`H73-A` Hero Submod300)** | **`HOLDOUT-DTI` (Promoted)** | *Pending* | **`37,654`** | **`82.2%`** | **`16.3%`** | **`0.11223`** `[0.09602, 0.12746]` | **`0.14128`** `[0.12527, 0.15871]` | **`0.12617`** `[0.10542, 0.14866]` | **`0.09842`** `[0.08572, 0.11234]` |
| `Exp 73.2` (`H73-C` Corrob + 2.8px NMS) | `HOLDOUT-DTI` | — | `37,654` | `81.5%` | `17.1%` | `0.10755` `[0.09225, 0.12209]` | `0.14125` `[0.12533, 0.15806]` | `0.12640` `[0.10574, 0.14893]` | `0.08939` `[0.07778, 0.10212]` |
| `Exp 73.1` (`H73-B` Quat+Scarp+$\chi$ + 2.8px NMS) | `HOLDOUT-DTI` | — | `37,654` | `68.4%` | `29.9%` | `0.09033` `[0.07507, 0.10572]` | `0.10317` `[0.09136, 0.11596]` | `0.09770` `[0.08161, 0.11524]` | `0.08599` `[0.07585, 0.09665]` |
| **`GEMSDOE32` (`h33-h33-2-b2`)** | `ORGANIZER-CONFIRMED` | **`0.2778`** | `37,654` | `78.7%` | `19.9%` | `0.00370` static / `0.09045` fold-fair | `0.12526` `[0.11260, 0.13897]` | `0.09367` `[0.07891, 0.10885]` | `0.09377` `[0.08253, 0.10591]` |
| `GEMSDOE36` (`anderson-pinn-38854`) | `ORGANIZER-CONFIRMED` | `0.2750` | `38,854` | `77.9%` | `20.7%` | — | `0.11600` | `0.09120` | `0.08460` |
| `GEMSDOE28` (`h27-4-r1-band1prune`) | `ORGANIZER-CONFIRMED` | `0.2708` | `40,199` | `78.9%` | `19.8%` | — | `0.11570` | `0.09210` | `0.08530` |
| `GEMSDOE25` (`d28-poisson-r28`) | `ORGANIZER-CONFIRMED` | `0.2600` | `44,090` | `79.0%` | `19.7%` | `0.09192` `[0.07919, 0.10524]` | `0.12348` `[0.11118, 0.13672]` | `0.08955` `[0.07577, 0.10388]` | `0.09353` `[0.08261, 0.10542]` |
| `GEMSDOE70 P8` (`dual-submod300-oof38k`) | `ORGANIZER-CONFIRMED` | `0.2478` | `37,654` | `43.5%` | `53.9%` | `0.00265` static / `0.11129` OOF | `0.11356` `[0.10006, 0.12749]` | `0.08422` `[0.07067, 0.09876]` | `0.13109` `[0.11805, 0.14492]` |
| `GEMSDOE70 P5` (`multiphysics-submod`) | `HOLDOUT-DTI` (Unscored) | — | `37,654` | `66.1%` | `31.2%` | `0.10997` | `0.12402` `[0.10930, 0.13937]` | `0.11123` `[0.09370, 0.12979]` | `0.11906` `[0.10574, 0.13322]` |
| `random_control` (Uniform off-catalogue) | `HOLDOUT-DTI` | — | `37,654` | `67.8%` | `25.0%` | `0.04550` `[0.04014, 0.05068]` | `0.06076` `[0.05571, 0.06542]` | `0.04552` `[0.04015, 0.05104]` | `0.07127` `[0.06667, 0.07582]` |

---

## 4. Complete Auditable Leaderboard Table (`ORGANIZER-CONFIRMED` Live Receipts)

| Rank | Repository | Submission Identifier | Evidence Class | Live DTI Score | Emitted Dots | `pied%` | `steep%` | `Inst C_pied_all` (`HOLDOUT-DTI`) |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Ext #1 | External Leader #1 | [DrivenData Leaderboard #1](https://www.drivendata.org/competitions/311/doe-gems/leaderboard/) | `ORGANIZER-CONFIRMED` | **`0.4413`** | — | — | — | — |
| Ext #2 | External Leader #2 | [DrivenData Leaderboard #2](https://www.drivendata.org/competitions/311/doe-gems/leaderboard/) | `ORGANIZER-CONFIRMED` | **`0.3195`** | — | — | — | — |
| **Int #1** | [`GEMSDOE32`](https://github.com/buffedlizard55-lab/GEMSDOE32) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | `ORGANIZER-CONFIRMED` | **`0.2778`** | `37,654` | `78.7%` | `19.9%` | `0.12526` |
| Int #2 | [`GEMSDOE36`](https://github.com/buffedlizard55-lab/GEMSDOE36) | `gems36-h36a-anderson-pinn-calib-38854-20261006` | `ORGANIZER-CONFIRMED` | `0.2750` | `38,854` | `77.9%` | `20.7%` | `0.11600` |
| Int #3 | [`GEMSDOE28`](https://github.com/buffedlizard55-lab/GEMSDOE28) | `h27-4-r1-band1prune` | `ORGANIZER-CONFIRMED` | `0.2708` | `40,199` | `78.9%` | `19.8%` | `0.11570` |
| Int #4 | `GEMSDOE25` | `d28-poisson-r28-b100-trim012` | `ORGANIZER-CONFIRMED` | `0.2600` | `44,090` | `79.0%` | `19.7%` | `0.12348` |
| Int #5 | [`GEMSDOE70`](https://github.com/buffedlizard55-lab/GEMSDOE70) | `gems70-p5-dual-submod300-oof38k-20261020` | `ORGANIZER-CONFIRMED` | `0.2478` | `37,654` | `43.5%` | `53.9%` | `0.11356` |
| Int #6 | `GEMSDOE24` | `d1.5-poisson-r18` | `ORGANIZER-CONFIRMED` | `0.2477` | `60,069` | `78.1%` | `20.4%` | `0.10460` |
| Int #7 | [`19GEMSDOE`](https://github.com/buffedlizard55-lab/19GEMSDOE) | `h19-5-powerlaw-budget-multiline` | `ORGANIZER-CONFIRMED` | `0.1922` | `121,131` | `76.9%` | `21.4%` | `0.09160` |
| Int #8 | [`16GEMSDOE`](https://github.com/buffedlizard55-lab/16GEMSDOE) | `H16-1` | `ORGANIZER-CONFIRMED` | `0.1855` | `115,201` | `78.5%` | `19.6%` | `0.09650` |
| Int #9 | [`17GEMSDOE`](https://github.com/buffedlizard55-lab/17GEMSDOE) | `H17-4` | `ORGANIZER-CONFIRMED` | `0.1723` | `98,945` | `75.2%` | `22.8%` | `0.09670` |
| Int #10 | [`15GEMSDOE`](https://github.com/buffedlizard55-lab/15GEMSDOE) | `H15-1` | `ORGANIZER-CONFIRMED` | `0.1681` | `100,765` | `75.6%` | `22.5%` | `0.09330` |
| Int #11 | [`18GEMSDOE`](https://github.com/buffedlizard55-lab/18GEMSDOE) | `h18-1-scarp-worm-oof-calibrated` | `ORGANIZER-CONFIRMED` | `0.1558` | `97,978` | `72.8%` | `25.3%` | `0.08230` |
| Int #12 | [`11GEMSDOE`](https://github.com/buffedlizard55-lab/11GEMSDOE) | `r9-calib` | `ORGANIZER-CONFIRMED` | `0.1462` | `87,113` | `78.7%` | `19.4%` | `0.08820` |
| Int #13 | [`9GEMSDOE`](https://github.com/buffedlizard55-lab/9GEMSDOE) | `r7-hybrid` | `ORGANIZER-CONFIRMED` | `0.1072` | `74,797` | `77.9%` | `20.0%` | `0.08880` |
| Int #14 | [`13GEMSDOE`](https://github.com/buffedlizard55-lab/13GEMSDOE) | `r13-lattice` | `ORGANIZER-CONFIRMED` | `0.0904` | `206,895` | `67.8%` | `25.0%` | `0.06230` |
| Int #15 | [`6GEMSDOE`](https://github.com/buffedlizard55-lab/6GEMSDOE) | `r4-full-footprint` | `ORGANIZER-CONFIRMED` | `0.0785` | `99,457` | `76.1%` | `21.7%` | `0.07820` |
| Int #16 | [`GEMSDOE49`](https://github.com/buffedlizard55-lab/GEMSDOE49) | `gems49-h49-1-tip-tecto-submod-20261015-zeros` | `ORGANIZER-CONFIRMED` | `0.0558` | `40,199` | `68.0%` | `29.9%` | `0.07360` |
| Int #17 | [`GEMSDOE68`](https://github.com/buffedlizard55-lab/GEMSDOE68) | `gems68-h68-hydro-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0170` | `37,654` | `25.1%` | `72.2%` | `0.03690` |
| Int #18 | [`GEMSDOE71`](https://github.com/buffedlizard55-lab/GEMSDOE71) | `gems71-h71-sgmc-da-submod-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0156` | `37,654` | `18.1%` | `78.5%` | `0.03090` |
| Int #19 | [`10GEMSDOE`](https://github.com/buffedlizard55-lab/10GEMSDOE) | `r8-centerlines` | `ORGANIZER-CONFIRMED` | `0.0108` | `26,735` | `72.0%` | `25.5%` | `0.01910` |
| Int #20 | [`GEMSDOE72`](https://github.com/buffedlizard55-lab/GEMSDOE72) | `gems72-h72-dip-coherent-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0085` | `37,654` | `15.1%` | `81.8%` | `0.02820` |
| Int #21 | [`7GEMSDOE`](https://github.com/buffedlizard55-lab/7GEMSDOE) | `r5-skeleton` | `ORGANIZER-CONFIRMED` | `0.0067` | `28,759` | `69.2%` | `28.1%` | `0.01520` |
| Int #22 | [`GEMSDOE69`](https://github.com/buffedlizard55-lab/GEMSDOE69) | `gems69-h69-transfer-zone-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0053` | `37,654` | `29.5%` | `68.6%` | `0.02090` |

---

## 5. Official Verified Primary Sources & Literature Table

| Category | Official Dataset / Publication | Verified URL / DOI | Role in `GEMSDOE73` |
| :--- | :--- | :--- | :--- |
| Competition Portal | DrivenData Competition #311: DOE GEMS — Reveal Hidden Faults | <https://www.drivendata.org/competitions/311/doe-gems/> | Official grid (`EPSG:32611`, `3730 x 3292` @ `100 m`), 300 m DTI metric ($\alpha=0.2, \beta=0.8$) |
| Organizer Forum | DrivenData Forum Topic 11516, Post #4 (Known Faults in Target for Test Eval) | <https://community.drivendata.org/t/known-faults-in-target-for-test-eval/11516/4> | Confirms known faults are masked at exact pixel coordinates (`d_cat > 2.05 px` flank collar) |
| Primary Data (INGENIOUS) | OpenEI GDR Submission #1734: Great Basin INGENIOUS Dataset | <https://gdr.openei.org/submissions/1734> | 19-band `training_features.tif`, `existing_faults.tif`, 2 m temperature probes (`F2mDAB`), paleo-sinter |
| Primary Data (Geothermal) | OpenEI GDR Submission #1391: Great Basin Thermal Springs, Wells & Geothermometry | <https://gdr.openei.org/submissions/1391> | Thermal spring/well coordinates and quartz/chalcedony/Na-K-Ca geothermometers (`L3`) |
| Geologic Compilation | Horton et al. (2017), USGS Data Series 1052: State Geologic Map Compilation (SGMC) | <https://doi.org/10.3133/ds1052> | `sgmc_faults_100m.tif` (strictly held-in quadrant targets for `M_pied` & `M_bed` and OOF evaluation) |
| High-Res Elevation | U.S. Geological Survey 3D Elevation Program (3DEP) 1 m LiDAR & 10 m Seamless DEM | <https://www.usgs.gov/3d-elevation-program> | `lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_{i16,u8}.tif` |
| Airborne Geophysics | U.S. Geological Survey GeoDAWN Radiometric & Aeromagnetic Surveys | <https://www.usgs.gov/centers/gggsc/science/geodawn> | `geodawn_extensions_u8.tif` (`Th/K`, `U/K` alteration edges, `TMI_150m` shallow demagnetization) |
| Cultural De-Confounder | U.S. Census Bureau TIGER/Line Primary & Secondary Roads | <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html> | `tiger_road_distance_m.tif` highway/railroad embankment de-confounder (Col 44) |
| Fluvial Geomorphology | Perron & Royden (2013), *Earth Surface Processes and Landforms* 38(6), 570–576 | <https://doi.org/10.1002/esp.3302> | Integral $\chi$-transformed channel steepness $k_{sn}$ and range-front knickzone steps (Col 41) |
| Joint Geophysics | Gallardo & Meju (2004), *Journal of Geophysical Research: Solid Earth* 109(B3) | <https://doi.org/10.1029/2003JB002771> | Cross-gradient structural coupling $\|\nabla g \cdot \nabla\text{RTP}\|$ vs $\|\nabla g \times \nabla\text{RTP}\|$ (Cols 22–23) |
| Fault Mechanics | Anderson (1905), *Transactions of the Edinburgh Geological Society* 8(3), 387–402 | <https://doi.org/10.1144/transed.8.3.387> | $60^\circ$ normal-fault dip-projected basement step (Col 45) & strike favorability (Col 24) |
| Submodular Optimization | Minoux (1978), *Optimization Techniques*, Lecture Notes in Control and Information Sciences 7, 234–243 | <https://doi.org/10.1007/BFb0006528> | Accelerated lazy-greedy maximization of the 300 m triangular kernel coverage objective |

---

## 6. Data Restoration & End-to-End Reproduction

```bash
# 1. Restore & SHA-256 verify all 3 core competition GeoTIFFs, 17 external layers, & 13 10m DEM channels
bash scripts/download_competition_data.sh

# 2. Prepare & verify the 46-feature physical memmap (h73_static46.mmap) and grid manifest
.venv/bin/python scripts/prepare_data.py

# 3. Execute the preregistered 3-experiment suite (Exp 73.1, Exp 73.2, Exp 73.3), 49 leakage canaries,
#    80-raster uniqueness audit, GeoTIFF emission, and canonical run_card.json generation
.venv/bin/python scripts/run_experiment_h73.py

# 4. Run the automated verification test suite
.venv/bin/pytest -q
```

---

## 7. Canonical JSON Run Card (`run_card.json`)

```json
{
  "schema": "gems73.run-card.v1",
  "lane": "H73: 4-Line Corroborated Piedmont/Fluvial-Knickzone/Hydrothermal/Dip-Projected OOF Multi-Physics + 300 m Submodular Max-Cover",
  "hypothesis": "H73-A: Relief-normalized 1m/10m scarp & openness breaklines + range-front fluvial chi/ksn knickzones (fixing IR-73-04 -32768 nodata) + 60-deg dip-projected basement steps + GDR #1391 hydrothermal/2m-probe/sinter conduits + fold-proper crack-tip/relay mechanics, combined with 4-quadrant OOF Quaternary (M_neo) and piedmont-conditioned structural (M_pied, M_bed) HGB experts, gated by 4-line median corroboration and Quaternary piedmont/basin habitat, and emitted via exact unblurred 300 m triangular-kernel submodular max-cover.",
  "mechanism": "Active normal faults at range-front piedmonts and intrabasin step-overs produce coincident relief-normalized topographic steps, upstream channel-steepness knickzones (step_max * log1p(ksn_max) / sqrt(rel10+9)), updip-projected basement density/magnetic gradients, and hydrothermal/alteration upflow plumes. Requiring multi-line corroboration and piedmont-habitat conditioning eliminates steep pre-Tertiary mountain-crest false positives while exact 300 m submodular max-cover eliminates self-overlapping kernel waste.",
  "named_non_fault_mimic": "(1) Pleistocene Lake Lahontan (1330 m Sehoo / 1235 m Dendritic) and Lake Bonneville (1463 m Provo / 1552 m Bonneville) wave-cut paleoshoreline benches following flat elevation contours (sigma_z < 3 m); (2) US Census TIGER highway/railroad embankment cuts within 250 m of mapped roads; (3) Steep pre-Tertiary mountain-interior bedrock contacts and intrusive pluton rims (high orthogonal |grad(g) x grad(RTP)| in high-relief terrain).",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels": 11321,
    "dti": 0.11223012667702426,
    "ci95": [0.09602190053267526, 0.12745740608140163],
    "paired_vs_h33_reference": {"delta": 0.10853034499139468, "ci95": [0.0927771297385803, 0.12339477917176582]},
    "paired_vs_h33_fold_fair": {"delta": 0.021784411581348306, "ci95": [0.010658330937971036, 0.03193263731817417]},
    "paired_vs_d28_reference": {"delta": 0.02030813958271821, "ci95": [0.008780506688624373, 0.03054713937777261]}
  },
  "correlation_overlap_vs_registry": {
    "rasters_checked": 80,
    "surface_pre_placement_unique": true,
    "surface_worst_spearman_full_footprint": 0.16881646273915074,
    "dots_final_unique": true,
    "dots_worst_spearman_full_footprint": 0.07307778986888586,
    "dots_worst_mutual_overlap_3px": 0.6617092473575185,
    "dots_worst_non_lattice_forward_overlap_3px": 0.6894885005577097,
    "duplicate": false
  },
  "raster_sha256": "846d5fe0fe53c618ebfa467c2545b7b78a459747be4aa1598d54e4979311c932",
  "validator_output": {
    "all_checks_passed": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "n_finite": 12279160,
    "n_nan": 0,
    "min": 0.0,
    "max": 1.0,
    "emitted_positive_pixels": 37654,
    "on_catalogue_positive_pixels": 0
  },
  "submission_name": "gems73-h73-piedmont-corrob-submod300-37654-20261021",
  "submission_note": "GEMS73 H73: 4-line corroborated piedmont/chi/hydro/dip OOF HGB + 300m submodular max-cover, 37654 binary [0,1] off-cat dots, 0 NaN.",
  "verdict": "promote",
  "download_and_submit_ok": true
}
```

---

## 8. Full Verbatim Task Prompt

```text
Carefully review the repo and first analyze the results of these submissions and their scores:

https://buffedlizard55-lab.github.io/GEMSDOE68/
gems68-h68-hydro-37654-20261019-zeros: 0.0170

https://buffedlizard55-lab.github.io/GEMSDOE69/
gems69-h69-transfer-zone-37654-20261019-zeros: 0.0053

https://buffedlizard55-lab.github.io/GEMSDOE71/
gems71-h71-sgmc-da-submod-37654-20261019-zeros: 0.0156

https://buffedlizard55-lab.github.io/GEMSDOE72/
gems72-h72-dip-coherent-37654-20261019-zeros: 0.0085

https://buffedlizard55-lab.github.io/6GEMSDOE/
r4-full-footprint: 0.0785

https://buffedlizard55-lab.github.io/7GEMSDOE/
r5-skeleton: 0.0067

https://buffedlizard55-lab.github.io/9GEMSDOE/
r7-hybrid: 0.1072

https://buffedlizard55-lab.github.io/10GEMSDOE/
r8-centerlines: 0.0108

https://buffedlizard55-lab.github.io/11GEMSDOE/
r9-calib: 0.1462

https://buffedlizard55-lab.github.io/13GEMSDOE/
r13-lattice: 0.0904

https://buffedlizard55-lab.github.io/15GEMSDOE/
H15-1: 0.1681

https://buffedlizard55-lab.github.io/16GEMSDOE/
H16-1: 0.1855

https://buffedlizard55-lab.github.io/17GEMSDOE/
H17-4: 0.1723

https://buffedlizard55-lab.github.io/18GEMSDOE/
h18-1-scarp-worm-oof-calibrated: 0.1558

https://buffedlizard55-lab.github.io/19GEMSDOE/
h19-5-powerlaw-budget-multiline: 0.1922

https://buffedlizard55-lab.github.io/GEMSDOE28/
h27-4-r1-band1prune: 0.2708

https://buffedlizard55-lab.github.io/GEMSDOE32/
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

https://buffedlizard55-lab.github.io/GEMSDOE36/
gems36-h36a-anderson-pinn-calib-38854-20261006: 0.2750

https://buffedlizard55-lab.github.io/GEMSDOE49/
gems49-h49-1-tip-tecto-submod-20261015-zeros: 0.0558

https://buffedlizard55-lab.github.io/60GEMSDOE/
https://github.com/buffedlizard55-lab/60GEMSDOE

https://buffedlizard55-lab.github.io/GEMSDOE63/
https://github.com/buffedlizard55-lab/GEMSDOE63

https://buffedlizard55-lab.github.io/GEMSDOE66/
https://github.com/buffedlizard55-lab/GEMSDOE66

https://buffedlizard55-lab.github.io/GEMSDOE70/
https://github.com/buffedlizard55-lab/GEMSDOE70
gems70-p5-dual-submod300-oof38k-20261020: 0.2478

Specifically answer why and how did https://buffedlizard55-lab.github.io/GEMSDOE32/ (h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778) get the highest score of these sites? Can we generate a submission that is higher than 0.2778? How?

PARALLEL-RUN PROTOCOL (read first, obey strictly):
1. STAY IN YOUR LANE. Your assigned methodological lane is at the bottom of this prompt. Do not drift into another lane. Before promoting any raster, verify against registry/ that raster rank-correlation is <= 0.90 and 3 px dot overlap is <= 70% with every prior raster. If higher, it is a duplicate — do not promote.
2. REUSE TEMPLATE INFRASTRUCTURE. Do not rebuild data loaders, the evaluator, the validator, or the feature cache. Call the shared evaluate_holdout.py, submission_writer.py, and cached feature stack. Holdout is hide-and-recover: withhold whole fault segments (with buffer), derive any catalogue-based features ONLY from visible faults, mask visible faults pixel-exactly as the host does, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel).
3. NO PROJECTIONS AS SCORES. Every number must be labeled HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission receipt). Never write a "projected leaderboard score."
4. LEAKAGE CANARY. Test each feature alone on holdout; if any single feature gets AUC > 0.90, treat it as catalogue leakage until proven otherwise.
5. OUTPUT ONE RUN CARD. End with a single JSON run card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, correlation/overlap vs registry, raster SHA-256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), unique submission name + <=140-char note, and verdict: promote (uses one of the 3 weekly slots) or negative (logged, not uploaded).
6. RESPECT THE BUDGET: at most 3 experiments and 2 hours compute. Prefer a clean negative result over a leaked or duplicate positive.

Based on what has already been tried, what are 3–5 candidate geological hypotheses we haven't tried yet? For each, name the specific layer(s) involved, the physical signature you'd look for, why it would catch a fault that's missing from the USGS/INGENIOUS catalogue rather than one that's already in it, and how it differs from what we've already implemented. Rank them by expected DTI improvement and implementation cost, then validate the top one on a spatially-blocked holdout set before touching the full pipeline.

For all checks on uniqueness, test on BOTH the continuous surface before placement AND the final dots!

Note that: You MUST generate a unique .tif submission file for the competition — do not copy a previous submission! Also, make it obvious at the very beginning of the site / executive summary whether it is OK to download and submit the generated .tif submission for the competition (and have a direct download link for the .tif right there, along with a unique submission name and short note to include with the submission)! Make sure that predicted values are in the range [0, 1] for the .tif file so that we don't get the "Error: Predicted values must be in range [0, 1]" error when submitting!

Before beginning, first review the entire repository, including the git commit history, branches, any existing pulls or issues, and deployment infrastructure, to understand what has already been done, what remains, and any irregularities that need to be addressed. Put the prompt in the repo README.md. Do not expect any manual input—work autonomously, methodically, and thoroughly line by line with PhD-level rigor, zero hallucinations, and verified official sources. Organize all sources and leaderboard results into clean, auditable tables with links. Complete the data restoration/preparation step (e.g., running scripts/download_competition_data.sh or scripts/prepare_data.py) and then execute the experiment script to generate the verified submission files and evidence metrics. Run through the prompt at least 3 times: first to implement and verify everything, second to review and fix any bugs or edge cases, and third to re-check the result against the original request. When finished, create a pull request and merge it.
```
