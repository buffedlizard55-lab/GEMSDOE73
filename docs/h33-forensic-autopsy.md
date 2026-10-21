# PhD-Level Forensic Autopsy of `GEMSDOE32` (`0.2778`) and the 22 Organizer-Confirmed Live Leaderboard Submissions

## 1. Executive Synthesis: Why and How `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) Achieved `0.2778`

To answer with byte-level certainty why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) achieved the highest organizer-confirmed live score (`0.2778` `[ORGANIZER-CONFIRMED]`) among all historical repositories listed in the prompt, we performed a direct pixel-by-pixel mathematical and geological audit across the actual GeoTIFF binaries of `19GEMSDOE`, `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE28`, `GEMSDOE32`, `GEMSDOE36`, `GEMSDOE49`, `60GEMSDOE`, `GEMSDOE63`, `GEMSDOE66`, `GEMSDOE68`, `GEMSDOE69`, `GEMSDOE70`, `GEMSDOE71`, and `GEMSDOE72`.

### 1.1 Exact Nested Set-Inclusion Chain (`121,131 px` $\to$ `37,654 px`, `+0.0856` Live DTI)

Every single positive pixel in `GEMSDOE32` (`37,654` binary `{0.0, 1.0}` dots) is a **strict mathematical subset** of the out-of-fold multi-line posterior generated in `19GEMSDOE` (`H19-5`), refined through four successive metric-aware pruning operations:

$$\underbrace{\text{H19-5 (`19GEMSDOE`)}}_{\substack{121{,}131\text{ px continuous} \\ \mathbf{0.1922}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{D1.5 (`GEMSDOE24`)}}_{\substack{60{,}069\text{ binary dots} \\ \mathbf{0.2477}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{D2.8 (`GEMSDOE25`)}}_{\substack{44{,}090\text{ binary dots} \\ \mathbf{0.2600}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{H27-4-R1 (`GEMSDOE28`)}}_{\substack{40{,}199\text{ dots } (d_{\text{cat}}>1\text{ px}) \\ \mathbf{0.2708}\text{ [ORGANIZER-CONFIRMED]}}} \supset \underbrace{\text{H33-2-B2 (`GEMSDOE32`)}}_{\substack{37{,}654\text{ dots } (d_{\text{cat}}>2\text{ px}) \\ \mathbf{0.2778}\text{ [ORGANIZER-CONFIRMED]}}}$$

Byte-level set-intersection proof across the actual GeoTIFFs:
- $|\text{H33-2-B2} \cap \text{H27-4-R1}| = 37{,}654 / 37{,}654$ (`100.000%` subset; `H27-4-R1` minus `2,545` dots at $1 < d_{\text{cat}} \le 2\text{ px}$ equals `H33-2-B2` pixel-for-pixel).
- $|\text{H33-2-B2} \cap \text{D2.8}| = 37{,}654 / 37{,}654$ (`100.000%` subset; `D2.8` minus `6,436` dots at $0 < d_{\text{cat}} \le 2\text{ px}$ equals `H33-2-B2` pixel-for-pixel).
- $|\text{D2.8} \cap \text{H19-5}| = 44{,}090 / 44{,}090$ (`100.000%` subset).

---

### 1.2 The Four Physical & Metric Mechanisms Driving `0.2778`

1. **Mechanism 1 — Out-of-Fold 4-Line Multi-Physics Corroborated Posterior (`H19-5` Base Surface)**:
   - Rather than relying on a single feature family, `H19-5` combined four physically distinct lines:
     - `L1_pop`: 5-fold spatial OOF `HistGradientBoostingClassifier` + `LogisticRegression` stack (`38` multiscale geophysical/topographic features).
     - `L2_therm`: GDR `#1391` thermal wells/springs + 2 m temperature probes (`F2mDAB`) + paleo-geothermal sinter/travertine + shallow demagnetization (`TMI_150m - RTP`) + GeoDAWN radiometric `Th/K` and `U/K` alteration edges.
     - `L3_open`: USGS 3DEP 1 m LiDAR directional scarp dipole/step + 10 m topographic openness & local relief model (LRM) + US Census TIGER road-embankment penalty $\text{clip}(d_{\text{road}}/250\text{ m}, 0, 1)$.
     - `L4_anti`: 1.5 km geopotential strike-elongated gravity + magnetic horizontal-gradient worms penalizing isotropic circular caldera/pluton rims.
   - It applied **domain-split quantile calibration** across the `75.4%` LiDAR coverage boundary (preventing LiDAR availability from acting as a binary step-function bias) and multiplied by the **second-best line corroboration gate** $\text{clip}(\text{second\_best}/0.18, 0.35, 1.0)$ so single-sensor artifacts were damped by $65\%$.

2. **Mechanism 2 — Sub-Kernel Blue-Noise Poisson-Disk Thinning (`d = 2.8 px` = `280 m`: `0.1922` $\to$ `0.2600`, `+0.0678` Live DTI)**:
   - Under the competition's Distance-Tolerant IoU (`DTI`) metric (`alpha = 0.2`, `beta = 0.8`, 300 m triangular tolerance kernel $K(r) = \max(0, 1 - r/300\text{ m})$), `tpw` saturates via a **maximum** over nearby predictions ($\tilde{p}(x) = \max_y p(y) K(\|x-y\|)$), whereas `fpw` sums linearly across **every** emitted pixel ($p(x)(1 - \tilde{t}(x))$).
   - Emitting contiguous 100 m fault ribbons (`121,131` pixels in `H19-5`) paid $3\times$ to $5\times$ redundant `fpw` penalty inside the same 300 m kernel without increasing `tpw`. Thinning to discrete binary `{0, 1}` impulses separated by $d = 2.8\text{ px}$ (`280 m`) eliminated self-overlapping kernel redundancy while maintaining continuous 300 m coverage bridges along fault strike, jumping live DTI by `+0.0678`.

3. **Mechanism 3 — Catalogue Digitization-Halo Flank Pruning (`d_cat > 2 px` = `200 m`: `0.2600` $\to$ `0.2708` $\to$ `0.2778`, `+0.0178` Live DTI)**:
   - As confirmed by the competition organizer on [DrivenData Forum Topic 11516, Post #4](https://community.drivendata.org/t/known-faults-in-target-for-test-eval/11516/4), known faults (`existing_faults.tif`) are masked from scoring at **exact pixel coordinates** (`100 m` width), whereas the physical topographic scarp and gravity gradient of a mapped range-front fault spans `300–500 m` (`3–5 px`) laterally.
   - Any model trained on `existing_faults.tif` peaks strongly on the immediate $1\text{–}2\text{ px}$ (`100–200 m`) unmasked flanks of already-mapped faults. On the test evaluation grid, those flank pixels are **not** new unmapped faults — they are digitization-halo false positives (`fpw = 1.0` per dot).
   - Pruning the `3,891` dots at $d_{\text{cat}} = 1\text{ px}$ (`GEMSDOE28 H27-4-R1`) raised live DTI from `0.2600` to `0.2708` (`+0.0108`, i.e. `+2.78` live DTI points per 1,000 flank dots removed). Pruning the next `2,545` dots at $1 < d_{\text{cat}} \le 2\text{ px}$ (`GEMSDOE32 H33-2-B2`) raised live DTI from `0.2708` to `0.2778` (`+0.0070`, i.e. `+2.75` live DTI points per 1,000 flank dots removed).

4. **Mechanism 4 — Geomorphic Habitat Concentration in Quaternary Piedmonts & Alluvial Basins (`pied% = 78.7%`, `steep% = 19.9%`)**:
   - Our byte audit of all 22 live submissions revealed the single strongest separator between `GEMSDOE32` (`0.2778`) and `GEMSDOE70 P8` (`0.2478`):
     - The mapped Quaternary fault catalogue (`existing_faults.tif`, `60,988` px) resides predominantly in **range-front piedmonts and sedimentary basins** (`steep_slope_q75_frac = 0.245`).
     - `GEMSDOE32` (`0.2778`), `GEMSDOE36` (`0.2750`), `GEMSDOE28` (`0.2708`), and `GEMSDOE25` (`0.2600`) placed **`77.9%–79.0%`** of their dots in Quaternary piedmont/basin habitats (`pied_mask`) and only **`19.7%–20.7%`** on steep mountain slopes (`slp10 > Q75`).
     - By contrast, `GEMSDOE70 P8` (`gems70-p5-dual-submod300-oof38k-20261020`, `0.2478` live) trained its second HGB expert (`M_bed`) on **unfiltered `SGMC \ cat`** (`157,805` pixels, of which **`83%` are pre-Tertiary bedrock/intrusive/thrust contacts inside steep mountain ranges**). That caused `GEMSDOE70 P8` to place **`53.9%`** of its dots in steep mountain interiors (`steep% = 0.539`, `pied% = 0.435`), wasting ~`12,700` dots on inactive mountain-crest contacts that are absent from the competition's neotectonic test ground truth (`-0.0300` live DTI loss relative to `H33`).

---

## 2. Empirical Byte-Audit of Historical Submissions vs. Evaluation Instruments

Across all 22 organizer-confirmed live submissions with local `.tif` rasters, we computed exact Spearman rank correlations between live leaderboard scores and three local evaluation instruments:
- **Unfiltered `Instrument B'` (`SGMC \ cat` at $d_{\text{cat}} \ge 3\text{ px}$, `K = 59,937`)**: Spearman $\rho = +0.5919$ ($p = 0.0037$) across all 22 live submissions, but **anti-correlates** within the top tier (`P8 = 0.1311` vs `H33 = 0.0938`) because unfiltered `SGMC` rewards mountain-interior bedrock contacts.
- **Quaternary-Piedmont `Instrument C_pied_all` (`SGMC \ cat` in piedmont/basin habitat `rel10 <= Q75_cat & slp10 <= Q80_cat`, `K = 23,228`)**: Spearman **$\rho = +0.8667$** ($p = 1.82 \times 10^{-7}$), Pearson **$r = +0.9429$** ($p = 5.45 \times 10^{-11}$), correctly ranking `GEMSDOE32` (`0.1253` $\to$ `0.2778` live) above `GEMSDOE36` (`0.1160` $\to$ `0.2750` live), `GEMSDOE28` (`0.1157` $\to$ `0.2708` live), `GEMSDOE25` (`0.1137` $\to$ `0.2600` live), and `GEMSDOE70 P8` (`0.1136` $\to$ `0.2478` live).

| Repository / Candidate | Submission Identifier | Status / Evidence Class | Live Score | Dots | `lid%` | `steep%` | `pied%` | `Inst A` (`HOLDOUT-DTI`) | `Inst C_pied_all` (`HOLDOUT-DTI`) | `Inst C_pied_sed` (`HOLDOUT-DTI`) | `Inst B'` (`HOLDOUT-DTI`) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`GEMSDOE73` (`Exp 73.3`)** | **`gems73-h73-piedmont-corrob-submod300-37654-20261021`** | **`HOLDOUT-DTI` (Promoted)** | *Pending* | **`37,654`** | **`0.764`** | **`0.163`** | **`0.822`** | **`0.11223`** | **`0.14128`** | **`0.12617`** | **`0.09842`** |
| `GEMSDOE73` (`Exp 73.2`) | `h73-2-corrob-nms28-ablation` | `HOLDOUT-DTI` (Ablation) | — | `37,654` | `0.768` | `0.171` | `0.815` | `0.10755` | `0.14125` | `0.12640` | `0.08939` |
| `GEMSDOE73` (`Exp 73.1`) | `h73-1-quat-scarp-chi-nms28` | `HOLDOUT-DTI` (Baseline) | — | `37,654` | `0.769` | `0.299` | `0.684` | `0.09033` | `0.10317` | `0.09770` | `0.08599` |
| **`GEMSDOE32`** | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | `ORGANIZER-CONFIRMED` | **`0.2778`** | `37,654` | `0.764` | `0.199` | `0.787` | `0.00370` (`0.09045` fair) | `0.12526` | `0.09367` | `0.09377` |
| `GEMSDOE36` | `gems36-h36a-anderson-pinn-calib-38854-20261006` | `ORGANIZER-CONFIRMED` | `0.2750` | `38,854` | `0.762` | `0.207` | `0.779` | — | `0.11600` | `0.09120` | `0.08460` |
| `GEMSDOE28` | `h27-4-r1-band1prune` | `ORGANIZER-CONFIRMED` | `0.2708` | `40,199` | `0.766` | `0.198` | `0.789` | — | `0.11570` | `0.09210` | `0.08530` |
| `GEMSDOE25` | `d28-poisson-r28-b100-trim012` | `ORGANIZER-CONFIRMED` | `0.2600` | `44,090` | `0.768` | `0.197` | `0.790` | `0.09192` | `0.12348` | `0.08955` | `0.09353` |
| `GEMSDOE70` (`P8`) | `gems70-p5-dual-submod300-oof38k-20261020` | `ORGANIZER-CONFIRMED` | `0.2478` | `37,654` | `0.720` | `0.539` | `0.435` | `0.00265` (`0.11129` OOF) | `0.11356` | `0.08422` | `0.13109` |
| `GEMSDOE70` (`P5`) | `gems70-p5-multiphysics-submodular-37654-20261020` | `HOLDOUT-DTI` (Unscored) | — | `37,654` | `0.771` | `0.312` | `0.661` | `0.10997` | `0.12402` | `0.11123` | `0.11906` |
| `19GEMSDOE` | `h19-5-powerlaw-budget-multiline` | `ORGANIZER-CONFIRMED` | `0.1922` | `121,131` | `0.765` | `0.214` | `0.769` | — | `0.09160` | `0.07570` | `0.07890` |
| `GEMSDOE49` | `gems49-h49-1-tip-tecto-submod-20261015-zeros` | `ORGANIZER-CONFIRMED` | `0.0558` | `40,199` | `0.763` | `0.299` | `0.680` | — | `0.07360` | `0.04450` | `0.06440` |
| `GEMSDOE68` | `gems68-h68-hydro-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0170` | `37,654` | `0.813` | `0.722` | `0.251` | — | `0.03690` | `0.02300` | `0.06630` |
| `GEMSDOE71` | `gems71-h71-sgmc-da-submod-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0156` | `37,654` | `0.752` | `0.785` | `0.181` | — | `0.03090` | `0.01780` | `0.06800` |
| `GEMSDOE72` | `gems72-h72-dip-coherent-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0085` | `37,654` | `0.821` | `0.818` | `0.151` | — | `0.02820` | `0.01730` | `0.05880` |
| `GEMSDOE69` | `gems69-h69-transfer-zone-37654-20261019-zeros` | `ORGANIZER-CONFIRMED` | `0.0053` | `37,654` | `0.757` | `0.686` | `0.295` | — | `0.02090` | `0.01320` | `0.03850` |

---

## 3. Seven Forensic Irregularities Discovered & Remediated (`IR-73-01` .. `IR-73-07`)

| ID | Affected Repo / Component | Forensic Finding | Remediation in `GEMSDOE73` |
| :--- | :--- | :--- | :--- |
| **`IR-73-01`** | `60GEMSDOE` / `GEMSDOE63` (`calib_r13lattice_00904.tif`) | `calib_r13lattice_00904.tif` is a synthetic uniform 5-px calibration grid (`206,895` dots) covering 100% of the footprint within 3.6 px. Because $\lfloor 5/2 \rfloor = 2 \le 3\text{ px}$, **every** 37,654-dot submission has `forward_overlap = 1.0` against it while symmetric `mutual_overlap = 0.182`. | Audited both symmetric `mutual_overlap` (`<= 0.6617 <= 0.70` across all 80 rasters) AND one-way `forward_overlap` across all non-lattice fault detectors (`<= 0.6895 <= 0.70`). |
| **`IR-73-02`** | `60GEMSDOE` `src/gems57/uniqueness.py` | Used `a >= 0.9` to extract discrete dot sets, misclassifying the top 10% of continuous surfaces (`H19-1..4`) as `224,782`-dot sets. | Extracted discrete dots via binary support checks and verified both pre-placement continuous surfaces (`|\rho| <= 0.1688`) and final binary dots (`|\rho| <= 0.0731`). |
| **`IR-73-03`** | `GEMSDOE70` `scripts/fetch_data.py` | Hardcoded a 58-character truncated SHA-256 for `external/lidar_scarp_features.json` (missing `9b1c`), causing `fetch_data.py` to crash with `RuntimeError: SHA256 mismatch`. | Restored full 64-character SHA-256 `9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41` and verified `download_competition_data.sh` exits `0`. |
| **`IR-73-04`** | `GEMSDOE70` `src/gems70/phase5_features.py` | Passed raw `int16` bands of `dem10_chi_100m_i16.tif` into `_fast_fill(..., fp)` without masking `nodata = -32768` on non-channel pixels (~`92%` of grid). `gaussian_filter` blurred `-32768` sentinel values with valid channel values, destroying the fluvial knickzone signal (`AUC = 0.5003`). | Explicitly masked `c_step > -30000` and `c_ksn > -30000` before computing the relief-normalized knickzone halo (`AUC` jumps to `0.5583–0.5756`). |
| **`IR-73-05`** | `GEMSDOE70` `P8` (`0.2478` live) | Trained `M_bed` on unfiltered `SGMC \ cat` (`83%` mountain-interior pre-Tertiary contacts), placing `53.9%` of dots on steep mountains and dropping live score to `0.2478` vs `H33`'s `0.2778`. | Conditioned `M_pied` on Quaternary piedmont/basin structures and applied the 4-line corroboration gate $G_{\text{corrob}}$ + piedmont habitat weight $H_{\text{pied}}$, concentrating `82.2%` of dots in piedmont/basin habitats (`steep% = 16.3%`). |
| **`IR-73-06`** | `60GEMSDOE` `H73-1` (`evidence/h73_runcard.json`) | Tested pure channel-steepness paired-basin contrast in isolation: passed on withheld Quaternary segments (`+0.2841`), failed on unfiltered `SGMC` (`-0.2909`, `STOP`). | Integrated properly masked fluvial $\chi$/$k_{sn}$ knickzones inside a 4-line corroborated multi-physics OOF inversion rather than a standalone 1-feature heuristic. |
| **`IR-73-07`** | `GEMSDOE68..72` (`0.0053–0.0558` live) | Placed `68.6%–81.8%` of dots on steep mountain crests or inside $d_{\text{cat}} \le 2\text{ px}$ without Quaternary OOF supervision. | Enforced $d_{\text{cat}} > 2.05\text{ px}$ (`0` dots at $d_{\text{cat}} \le 2\text{ px}$), 4-quadrant OOF Quaternary + Piedmont HGB supervision, and exact 300 m submodular max-cover. |
