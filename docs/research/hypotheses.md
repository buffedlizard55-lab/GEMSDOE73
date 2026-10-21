# GEMSDOE73 — five candidate geological hypotheses, ranked (written BEFORE any GEMSDOE73 holdout run)

Evidence classes used everywhere in this repo: **ORGANIZER-CONFIRMED** = copied from a
DrivenData submission-page/leaderboard receipt as reported by the project owner in the brief;
**HOLDOUT-DTI** = local hide-and-recover number (evaluator version, withheld positives, 95% CI);
**OWNER-REPORT** = a score in the brief's ledger with no receipt in this repo; **MEASURED-HERE** =
computed in this session from hash-pinned bytes (command in `scripts/` / `evidence/`).

## What the forensic pass established (MEASURED-HERE, `evidence/forensic.json`)

1. **Champion lineage is exact:** `H33-2-B2 (37,654 dots) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131)`,
   zero exceptions; H33-2-B2 = D2.8 with every dot at Euclidean distance ≤ 2 px from the
   catalogue deleted (44,090 − 6,436 = 37,654; minimum retained distance 2.236 px).
2. **H19-5's surface is ~90% scarp/openness:** in `19GEMSDOE/src/gems/hypotheses.py`
   `synthesize_h19_5_openness_thermal_corroborated`, the two scarp/openness lines carry
   weights 0.55 + 0.35 = 0.90 (LiDAR regime); tip/relay and thermal lines carry 0.05 each,
   then a second-best-line corroboration gate and a ridge/NMS top-≈2.4% emission.
3. **Static H33 scores 0.0067 against the full catalogue — worse than random (0.0504)** —
   because the B2 prune deletes exactly the dots that would cover catalogue traces.
   Any instrument that scores a *static* candidate against catalogue truth therefore ranks
   the live champion last. Only **fold-fair** re-emission (prune against *visible* faults
   only) is a valid holdout for B2-style candidates.
4. **SGMC off-catalogue faults are mostly not piedmont faults:** median slope 13.4 (catalogue
   5.6), median depth-to-basement 91 m (catalogue 322 m); only 15.1% lie in the piedmont
   domain defined below. A detector trained to imitate SGMC/catalogue pixels is trained on
   the population the hidden expert set was *selected against* (already-mappable bedrock
   and range-front traces).

## Why H33-2-B2 scored highest (0.2778, OWNER-REPORT in brief; no receipt in this repo)

The metric is `DTI = T / (0.2·(T+F) + 0.8·|G|)` (α=0.2, β=0.8, 300 m triangular kernel;
official page 967). Three multiplicative effects, in order of size:

- **The field:** a scarp/openness-dominated expert ensemble finds the same class of
  Quaternary scarps that expert LiDAR re-mapping finds — the likeliest construction of the
  hidden set ("manually identified by fault experts", official problem page).
- **Dotting:** thinning 121,131 → 44,090 px removes mass whose marginal kernel credit is
  below the break-even bar `k > 0.2·DTI ≈ 0.052` at DTI 0.26; retained dots at ≈2.4–2.8 px
  spacing still cover a trace at `k ≥ 0.6`.
- **The B2 prune:** dots ≤200 m from a *known* fault can almost only cover known (masked,
  zero-credit) traces while paying full false-positive tax against the hidden set; deleting
  6,436 such dots (+0.0070 live, OWNER-REPORT ladder 0.2708 → 0.2778) is the cheapest
  credit-density gain in the family's history.

**Can 0.2778 be beaten, and 0.4413 (current public leader, OWNER-REPORT)?** At fixed mass
37,654 and the implied hidden-set size, DTI scales with mean realised credit per dot.
Emission tricks are nearly exhausted (each successive thinning bought less: +0.0555, then
+0.0123, then +0.0070). Beating 0.2778 needs a *field* whose top-37,654 dots carry higher
credit density — i.e. better scarp-trace localisation in the terrain class where the
catalogue is incomplete. 0.4413 would require roughly +60% credit density over H33 at the
same mass; no reweighting of existing surfaces in 72 sibling repos has produced that, so we
do not claim it is reachable in one lane. We maximise P(beat 0.2778) and report honestly.

## The five hypotheses

### H73-1 (RANK 1 — this repo's lane) Piedmont micro-scarp chains with step polarity and a subsurface-step witness — fully unsupervised

- **Layers:** `lidar_scarp_features_u8.tif` bands `step_max`(3), `downface_max`(6),
  `upface_max`(7), `cross_max`(8), `ex_max`(1), `valid`(12) [USGS 3DEP 1 m DEM derivatives];
  official `training_features.tif` bands `det_elev`(12), `det_elev_slope`(19),
  `depth_to_base_surf`(15), `iso_grav_anom_slope`(5), `tmi_hg`(3).
- **Physical signature:** (i) a one-sided topographic step (polarity
  `|down−up|/(down+up+1)`), normalised *against piedmont background* via a soft piedmont
  weight (deep basement × gentle slope × low 500 m relief), so a 0.5–2 m scarp in alluvium
  outranks a 20 m bedrock break; (ii) **collinearity**: the best 16-azimuth, 1.3 km line
  occupancy of the scarp skeleton through the pixel (en-échelon scarplet chains);
  (iii) a **subsurface-step witness**: top-2 mean of normalised basement-depth gradient,
  isostatic-gravity slope and magnetic horizontal gradient.
- **Why it catches catalogue-missing faults:** the USGS/INGENIOUS catalogue was compiled
  largely from surface geology and pre-/early-LiDAR mapping; low piedmont scarps on
  alluvial aprons are invisible in a 100 m DEM and under-mapped in bedrock-focused work,
  yet they are exactly what expert 1 m-LiDAR re-mapping adds, and range-front/piedmont
  faults are the Great Basin's geothermal upflow structures.
- **Named non-fault mimic:** Pleistocene Lake Lahontan shoreline benches and fluvial
  terrace risers — also one-sided piedmont steps. Discriminators built into the signature:
  shorelines are contour-parallel and curve with the basin, so they score lower on
  1.3 km *straight-line* occupancy, and they have no basement/gravity/magnetic step.
- **How it differs from everything in the sibling repos:** no supervised training on the
  catalogue or SGMC anywhere (H19-5, GEMSDOE70 P5/P9 are OOF/LOQO gradient-boosting
  ensembles); no distance-to-catalogue feature; no scored raster is an input. The detector
  is the geometry (polarity × straight chain × subsurface witness) inside a soft piedmont
  domain — the anti-selection-bias counterpart of catalogue imitation.
- **Cost:** low (all layers hash-pinned on disk; ~minutes CPU). **Validatable locally: yes.**

### H73-2 (RANK 2) Leaderboard tomography over geological basis surfaces — diagnostic only

- **Layers:** the ~12 restored scored rasters + the H73-1 component surfaces.
- **Signature:** non-negative regression of OWNER-REPORT live DTIs onto per-raster
  stratum coverages (piedmont/bedrock × near/far catalogue), to estimate which terrain
  class the hidden set actually occupies.
- **Why rank 2, not 1:** it uses the real objective but only ~90 noisy scalar
  observations, the public/private chunk split makes geographic overfitting likely, and it
  cannot be validated on the hide-and-recover holdout without circularity. Used here only
  as a sanity check on H73-1's terrain bet, never as the submission surface.

### H73-3 (RANK 3) Offset/truncated magnetic markers (contact-termination lines)

- **Layers:** `rtp`(2), `tmi`(14), `tc`(6), `tmi_vg`(9).
- **Signature:** orientation/texture discontinuity of the RTP field across a straight
  line (structure-tensor eigenframe jump), i.e. a fault that *offsets* a magnetic unit,
  rather than a gradient ridge ("worm") itself.
- **Why off-catalogue:** subsurface offsets persist under alluvial cover.
- **Why rank 3:** sibling worm/Euler/tilt lanes scored 0.03–0.10 live (OWNER-REPORT);
  most magnetic terminations are lithologic contacts, the named mimic.

### H73-4 (RANK 4) Drainage-deflection and aligned-valley chains

- **Layers:** `det_elev`(12), `det_elev_slope`(19).
- **Signature:** valley-skeleton × multi-azimuth collinearity across drainage divides.
- **Why off-catalogue:** scarp-less faults still deflect drainage.
- **Why rank 4:** the fluvial-χ lane scored 0.0351 live (OWNER-REPORT, 60GEMSDOE);
  lithologic knickpoints are the mimic and 100 m detrended elevation is coarse for this.

### H73-5 (RANK 5) Linear hydrothermal-alteration zones

- **Layers:** `geodawn_rad_u8.tif` (K, Th, U, TC), `geodawn_extensions_u8.tif`
  (Th/K, U/K, U/Th), `cond_surf`(17), `depth_to_base_surf`(15).
- **Signature:** straight Th/K-high / K-low alteration lineaments coincident with a
  conductivity (clay-cap) breach, piedmont-gated.
- **Why off-catalogue:** alteration maps fluid pathways, not mapped traces.
- **Why rank 5 as a standalone:** the conjunction alteration lane scored 0.0782 live
  (OWNER-REPORT, 15GEMSDOE); playa evaporites and lithologic radiometric contacts mimic it.
  Retained as future corroboration, not as this lane (one method per lane).

## Preregistered experiments (budget: 3)

Frozen in `registry/preregistration.json`. E1 = H73-1 full formula; E2 = E1 without the
piedmont weight; E3 = E1 without chain and subsurface factors. Emission frozen for all:
score-ordered greedy dots, 2.5 px minimum spacing, 37,654 dots, allowed only where
distance to *visible* catalogue > 2.0 px. Primary instrument: shared
`gems57-pooled-hide-v2` (`vendor/gems57/evaluate_holdout.py`, folds from
`holdout.buffered_component_draw(seed=20, buffer_px=3, boundary_px=12)`), fold-fair
emission, controls = fold-fair H19-5-support dotting ("H33-analogue") and random dots.
Promotion rule: the selected experiment must beat the H33-analogue control on pooled
HOLDOUT-DTI with a paired 95% CI excluding 0, pass every leakage canary (single-feature
AUC ≤ 0.90), and pass uniqueness (Spearman ≤ 0.90 and ≤ 70% dots within 3 px vs every
registry raster, surface and dots). Otherwise the verdict is **negative** and the file is
labelled DO-NOT-SUBMIT. No weekly slot is spent by this repo; promotion is a selector step.
