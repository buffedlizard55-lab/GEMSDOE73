# GEMSDOE73 session-2 — five NEW candidate hypotheses (H73-6 … H73-10), ranked BEFORE any session-2 holdout run

Written 2026-10-21, after the diagnostic screen in `evidence/diagnostics_x.json`
(MEASURED-HERE per-pixel AUCs, 38 channels) and **before** any `HOLDOUT-DTI` was computed
for these candidates. Evidence classes: **ORGANIZER-CONFIRMED** = DrivenData leaderboard /
submission-page receipt read this session; **OWNER-REPORT** = score in the project brief's
ledger with no receipt in this repo; **HOLDOUT-DTI** = local hide-and-recover (evaluator
version, withheld positives, 95% CI); **MEASURED-HERE** = computed this session from
SHA-256-pinned bytes (`registry/data_manifest.json`, restore receipt `data/restore_receipt.json`).

## What session-1 established (do not re-litigate)

1. Champion lineage byte-exact: `H33-2-B2 (37,654) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131)`;
   H33-2-B2 = D2.8 minus every dot ≤2 px from the catalogue (`evidence/forensic.json`).
2. H73-1 piedmont scarp-chain FAILED its preregistered gate:
   HOLDOUT-DTI (`gems57-pooled-hide-v2`, 11,321 withheld px) E1 0.0548 [0.0417, 0.0688]
   vs fold-fair H33-analogue 0.0939 [0.0813, 0.1076]; ablations: no-piedmont E2 0.0339,
   scarp×piedmont-only E3 0.0564 → **piedmont weight helps (+0.021), 1.3 km straight-chain
   occupancy and the soft subsurface witness (0.55+0.45·w) add nothing** on the instrument.
3. Diagnostic screen (session-2, `evidence/diagnostics_x.json`): every single channel is
   weak per-pixel (best catalogue AUCs: lidar upface 0.587, downface 0.582, geodetic
   2nd-invariant 0.577, earthquake-intensity 0.576); none approaches the 0.90 leakage gate.
   Within H19-5 support, near-catalogue vs far pixels are best separated by radiometric
   **U/K (AUC 0.590)** and **isostatic-gravity slope (0.568)**; magnetic horizontal gradient
   is *inverse* (0.431) — a magnetic witness would favour proxy-false-positives.
4. Leaderboard read 2026-10-21 (ORGANIZER-CONFIRMED page read, no file crosswalk):
   #1 xiaofanhu 0.4413, #2 cfld__ 0.3904, #3 Batik Shirt Brothers 0.3894. Group best
   0.2778 (H33-2-B2) remains OWNER-REPORT (IR-73-02: no receipt in any repo inspected).

## Why 0.2778 won, in one paragraph (PhD answer, updated)

DTI(α=0.2, β=0.8, R=300 m) pays for *credit density*: a non-redundant dot helps iff its
realised kernel credit `k > α·DTI` (≈0.055 at DTI 0.2778). H33-2-B2 stacked three
credit-density gains on the best expert-like field then available: (i) H19-5's surface is
~90% LiDAR/DEM scarp-openness — the same evidence human mappers use, and the hidden set
was "manually identified by fault experts" (official problem page, verified this session);
(ii) dotting 121,131 → 44,090 px at ≈2.5 px spacing kept trace coverage (`k ≥ ~0.6`) while
deleting redundant mass below the credit bar; (iii) the B2 prune deleted 6,436 dots that
could only cover already-mapped, masked (zero-credit) traces. Successive emission gains
shrank (+0.055, +0.012, +0.007 OWNER-REPORT ladder), so beating 0.2778 now requires a
*field* with higher credit density in its top 37,654 dots — better trace localisation and
better false-line rejection — not more thinning. 0.4413 needs ≈+60% credit density over
H33 at equal mass; no sibling reweighting has approached that, and this session does not
claim it reachable in one lane. Target: beat the fold-fair holdout control, then let a
selector decide on a slot. **A projection is never written as a score.**

## The five new hypotheses

### H73-6 (RANK 1 — this session's lane) Trace-localised, independently-corroborated scarps

- **Layers:** `lidar_scarp_features_u8.tif` `step_max`(3), `downface_max`(6), `upface_max`(7),
  `cross_max`(8), `ex_max`(1), `valid`(12) [USGS 3DEP 1 m derivatives, hash-pinned];
  `training_features.tif` `det_elev`(12), `det_elev_slope`(19), `depth_to_base_surf`(15),
  `iso_grav_anom_slope`(5); `geodawn_extensions_u8.tif` `UK`(2) [USGS GeoDAWN radiometrics].
- **Physical signature (single method paragraph — the lane):** a one-sided LiDAR step
  (polarity-weighted, as H73-1) is first **ridge-thinned by orientation non-maximum
  suppression on its own structure tensor**, so credit is spent on the scarp *centreline*
  (kernel credit `k≈1`) instead of its 100–300 m flank (`k≈0.3–0.7`); the thinned trace
  must then be **corroborated within 200 m by a non-topographic edge** — the stronger of a
  U/K radiometric gradient ridge (hydrothermal K-metasomatism / lithologic break) and the
  isostatic-gravity slope ridge (basement density step) — with a soft piedmont weight
  (deep basement × gentle slope × low relief) retained from the session-1 ablation.
- **Why it catches catalogue-missing faults:** magnitude ranking (H73-1) floods the budget
  with broad range-front step responses that are already mapped; unmapped piedmont scarps
  are narrow, low steps whose *centreline* is mappable but whose peak magnitude is buried.
  NMS surfaces centrelines regardless of absolute step height, and the non-topographic
  witness keeps traces that offset basement/radiometric units — i.e. through-going
  structures — over purely surficial breaks.
- **Named non-fault mimic:** linear infrastructure and land-use edges (roads, canals,
  field boundaries) — also narrow, straight, centreline-like. Discriminators: they rarely
  coincide with a gravity-slope basement step; residual risk is published, not hidden.
  Secondary mimic: Lahontan shoreline benches (no basement step; witness suppresses).
- **How it differs from everything shipped:** H73-1 used straight-chain occupancy + a soft
  top-2 subsurface factor and *no* orientation thinning, *no* radiometric witness;
  H19-5 corroborates topographic lines with each other (~90% topo weight), never requires
  a non-topographic edge; no sibling in the brief's ledger combines structure-tensor NMS
  of a polarity scarp with a U/K-or-gravity corroboration gate. No scored raster is an
  input; no catalogue/SGMC training; no distance-to-catalogue feature (emission exclusion
  only, fold-fair).
- **Cost:** low (all layers on disk, hash-pinned; minutes CPU). **Validatable locally: yes.**
  Expected Δ vs holdout control: unknown until measured — that is the point of the gate.

### H73-7 (RANK 2) Witness-only corroboration (no thinning) — folded into H73-6 as ablation X3

Scarp magnitude × U/K-or-gravity witness × piedmont. Ranked below H73-6 because session-1
showed soft witnesses alone add ≈0; kept as the X3 ablation so the design isolates whether
thinning or corroboration (or neither) carries any gain. Cost: low. Validatable: yes.

### H73-8 (RANK 3) Absolute-elevation bench rejection — NOT viable in this sandbox

- **Layers needed:** absolute (non-detrended) elevation. `det_elev` has the regional trend
  removed, destroying the paleo-shoreline elevation bands (~constant absolute elevation)
  that identify Lahontan benches.
- **Specific free official source:** USGS 3DEP 1 m DEM tiles via the competition's own
  `1m_DEM_links.csv` (data page; USGS, public domain). **Obtainability check this session:**
  sandbox egress is limited to github/pypi hosts, so the tiles cannot be fetched or
  validated here. The hypothesis is therefore recorded as *viable off-sandbox only* and is
  **not** this session's lane (per brief: do not propose as viable what cannot be validated).
- Mimic targeted: Lahontan benches / terrace risers. Cost off-sandbox: medium (tile mosaic).

### H73-9 (RANK 4) Magnetic contact-termination lines (offset markers, not gradient ridges)

- **Layers:** `rtp`(2), `tmi`(14), `tmi_vg`(9), `tc`(6). **Signature:** structure-tensor
  eigenframe *discontinuity* across a straight line — a fault that truncates/offsets a
  magnetic unit — rather than a gradient maximum ("worm").
- **Why rank 4:** every magnetic-ridge/Euler/tilt sibling lane scored 0.03–0.10
  (OWNER-REPORT), and this session's screen shows `tmi_hg` *inverse* (0.431) on the
  near-vs-far diagnostic. Terminations are mostly lithologic contacts (named mimic).
  Cost: medium. Validatable: yes, but low prior.

### H73-10 (RANK 5) Seismicity-aligned scarps

- **Layers:** `ieq_n100a15`(16), `deq_n100a15`(10) × lidar scarp. **Signature:** scarp
  traces coincident with earthquake-density gradient ridges (active blind structures).
- **Why rank 5:** `ieq` has a respectable catalogue AUC (0.576, MEASURED-HERE) but its
  100 km kernel cannot localise a trace to the 300 m credit radius; epicentre scatter is
  the named mimic. Useful at most as a regional prior. Cost: low. Validatable: yes.

## Preregistered experiments (budget: 3) — frozen in `registry/preregistration_x.json`

X1 = H73-6 full (soft-NMS ridge × witness factor × piedmont factor);
X2 = X1 without witness (thinning only); X3 = X1 without NMS (witness only).
Emission frozen for all arms including controls: score-ordered greedy dots, 2.5 px minimum
spacing, 37,654 dots, allowed only >2.0 px from *visible* catalogue (fold-fair) /
full catalogue (production). Instrument: shared `gems57-pooled-hide-v2`
(`vendor/gems57/evaluate_holdout.py` + `holdout.buffered_component_draw(seed=20,
buffer_px=3, boundary_px=12)`), controls = fold-fair H19-5-support dotting
("H33-analogue", session-1 HOLDOUT-DTI 0.0939) and random dots. Promotion rule: selected
arm must beat the H33-analogue on pooled HOLDOUT-DTI with paired 95% CI excluding 0,
pass every leakage canary (single-feature symmetric AUC ≤ 0.90), and pass uniqueness
(Spearman ≤ 0.90 and mutual 3 px overlap ≤ 0.70 vs every accessible registry raster,
surface and dots). Else verdict **negative**, file labelled DO-NOT-SUBMIT, 0 slots spent.
