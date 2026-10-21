# GEMSDOE73 session H73-7 — candidate hypotheses ranked BEFORE the H73-7 holdout run

Evidence classes: **ORGANIZER-CONFIRMED** = organizer page/receipt read directly;
**OWNER-REPORT** = score in the project owner's ledger with no receipt in this repo;
**HOLDOUT-DTI** = local hide-and-recover number (evaluator, withheld px, 95% CI);
**MEASURED-HERE** = computed this session from hash-pinned bytes.

## Prior art already implemented in this repo (do not re-propose)

- **H73-A blind stepover** (`registry/run_card.json`): synthetic magnetic/gravity
  stepover generator; never holdout-run; verdict negative by its own card.
- **Hydrothermal permeability corridor** (`evidence/run_card.json`): synthetic
  dilatation×alteration×thermal product; its "HOLDOUT-DTI 0.1112" came from a
  hard-coded demo function — verdict voided (IR-73-11,
  `evidence/run_card_hydro_addendum_2026-10-21.json`).
- **H73-1 piedmont micro-scarp chain** (`evidence/run_card_h73-1.json`): the only
  previously *measured* lane. Fully unsupervised LiDAR scarp polarity × 1.3 km
  collinearity × subsurface-step witness. HOLDOUT-DTI (gems57-pooled-hide-v2,
  11,321 withheld px) E1 0.0548 [0.0417, 0.0688] vs fold-fair H33-analogue
  0.0939 [0.0813, 0.1076] → NEGATIVE.
- Ranked-but-unimplemented in `docs/research/hypotheses.md`: H73-2 leaderboard
  tomography (diagnostic), H73-3 magnetic contact-termination, H73-4 drainage
  deflection, H73-5 radiometric alteration lineaments.

## Why H33-2-B2 scored 0.2778 (the question, answered with this session's measurements)

Re-verified this session from the champion bytes themselves
(`GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`,
sha256 `c55bafc470…`, MEASURED-HERE; identical to `evidence/forensic.json`):

1. **Lineage is exact:** H33-2-B2 (37,654 dots) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131),
   zero exceptions. H33-2-B2 = D2.8 with **every dot ≤2.0 px from the catalogue
   deleted — 6,436 dots** (minimum retained distance 2.236 px; 0 dots on catalogue
   pixels in all three). The site previously said "1,152 dots from ~38,800" — wrong;
   corrected (IR-73-16).
2. **The metric rewards credit density, not mass.** DTI = T / (0.2·(T+F) + 0.8·|G|)
   (α=0.2, β=0.8, 300 m triangular kernel; official problem page). A non-redundant
   extra dot helps only if its kernel credit k > 0.2·DTI ≈ 0.056 at DTI 0.2778.
   Dotting H19-5's 121,131 px at ≈2.5–2.8 px spacing keeps trace coverage (k≥0.58
   anywhere on a covered trace) while paying the 0.2 false-positive tax once per
   ~6 px of trace instead of per pixel: OWNER-REPORT ladder 0.1922 (solid) →
   0.2477/0.2600 (dotted).
3. **The B=2 prune is free credit density.** Round-1 hidden truth excludes the
   published catalogue, so dots within 200 m of a known trace mostly cover known
   (masked, zero-credit) traces while paying full FP tax. Deleting 6,436 such dots
   cost no hidden recall and bought the final step to 0.2778 (OWNER-REPORT; no
   organizer receipt exists in any inspected repo — IR-73-02).
4. **The field matched the hidden set's construction.** H19-5 is ~90%
   scarp/openness weighted (weights 0.55+0.35 in `19GEMSDOE/src/gems/hypotheses.py`,
   per `docs/research/hypotheses.md`). Hidden faults were "manually identified by
   fault experts" — plausibly the same LiDAR-scarp population. Static check
   (MEASURED-HERE, reproduced): the champion scores DTI 0.0067 against the *full
   catalogue* — below random — because B2 deletes exactly the catalogue-covering
   dots. Any non-fold-fair catalogue holdout therefore ranks the champion last
   (IR-73-06); only fold-fair re-emission is a valid instrument.

**Can 0.2778 be beaten? Can 0.4413?** At fixed mass ≈37,654 the only lever left is
mean realised credit per dot; emission tricks show diminishing returns
(+0.0555, +0.0123, +0.0070 across the ladder). Beating 0.2778 needs a *field* whose
top dots localise expert-style scarps better in the terrain where the catalogue is
incomplete. 0.4413 (live #1 read 2026-10-21, ORGANIZER-CONFIRMED public page,
`registry/leaderboard_snapshot_2026-10-21.json`) needs ≈+60% credit density over
H33 at the same mass — no sibling field in 72+ repos has shown that; this session
does not claim it. It maximises P(a measurable, honestly-gated step past the
fold-fair champion analogue) and reports the result either way.

## The five candidates for this session, ranked by expected ΔDTI vs cost

### RANK 1 — IMPLEMENTED (lane H73-7): Hard-fault Positive-Unlabelled ranker

- **Layers:** all 19 official `training_features.tif` bands (magnetics, gravity,
  strain, seismicity, detrended topography, basement depth, conductivity);
  10 bands of `lidar_scarp_features_u8.tif` (USGS 3DEP 1 m derivatives);
  8 GeoDAWN radiometric/extension bands (K/Th/U/TC, Th/K, U/K, U/Th, TMI↑150 m);
  the 4 unsupervised H73-1 components (scarp_n, chain, substep, pied_soft) as
  *features*, not as the surface. All hash-pinned in `registry/data_manifest.json`;
  no new external data required (verified obtainable: already restored).
- **Physical signature:** a learned ranking over physical transforms *re-weighted
  toward hard examples*: catalogue positives with weak LiDAR step, deep basement
  and gentle slope (weight 1+2h, h∈[0,1]) count up to 3× — the catalogue
  subpopulation closest to covered, expert-added faults.
- **Why catalogue-missing faults:** plain catalogue imitation spends its budget on
  easy bedrock/range-front traces (the population the hidden set was selected
  *against*; SGMC off-catalogue faults have median basement depth 91 m vs catalogue
  322 m, `docs/research/hypotheses.md`). Hard-weighting shifts probability mass to
  low-visibility piedmont structures while keeping physical corroboration.
- **How it differs from prior art:** sibling supervised lanes (6GEMSDOE hgb88
  0.0286, GEMSDOE43 sup01-hgb21 0.0424, GEMSDOE70 P5 0.2478 OWNER-REPORT) trained
  unweighted catalogue imitation, some with distance-to-catalogue features. H73-7
  uses no catalogue-derived feature, no scored-raster input, PU-style negatives
  (>5 px from *visible* faults only), and hard-example weights; E2 ablates the
  weights, E3 ablates the entire scarp family.
- **Named mimic:** lithologic contacts / fan surfaces; catalogue mapping bias itself.
- **Cost:** low–medium (minutes on 2 CPU cores; all data on disk). **Validatable
  locally: yes** — fold-fair on gems57-pooled-hide-v2. Frozen in
  `registry/preregistration_h73-7.json`.

### RANK 2 — H73-3 magnetic contact-termination (not implemented this session)

Structure-tensor eigenframe jumps in RTP/TMI (`rtp` 2, `tmi` 14, `tc` 6, `tmi_vg` 9):
faults that *offset* magnetic units rather than gradient ridges. Persists under
cover, but sibling worm/Euler/tilt lanes scored 0.03–0.10 live (OWNER-REPORT) and
most terminations are lithologic contacts (the mimic). Medium cost (new tensor
code); validatable locally with existing data. Deferred: lower expected ΔDTI than
Rank 1 and it would be a second lane in one session (protocol: one lane).

### RANK 3 — H73-5 linear hydrothermal-alteration zones (not implemented)

Straight Th/K-high, K-low lineaments coincident with a `cond_surf` clay-cap breach
(GeoDAWN radiometrics + band 17). Maps fluid pathways, not traces; standalone
conjunction lane scored 0.0782 live (OWNER-REPORT, 15GEMSDOE); playa evaporites
mimic it. Low–medium cost; data on disk. Kept as corroboration features inside
Rank 1 (radiometric channels), not as its own lane.

### RANK 4 — H73-4 drainage-deflection chains (not implemented)

Valley-skeleton collinearity in `det_elev`/`det_elev_slope`. The fluvial-χ sibling
scored 0.0351 live (OWNER-REPORT, 60GEMSDOE); 100 m detrended elevation is coarse
and lithologic knickpoints mimic it. Medium cost (flow routing on 5.2 M px);
validatable locally. Lowest expected ΔDTI of the validatable set.

### RANK 5 — H73-2 leaderboard tomography (diagnostic only, never a submission)

Regress ~90 OWNER-REPORT live DTIs onto per-raster terrain-stratum coverages to
infer where the hidden set lives. Uses the real objective but cannot be validated
on hide-and-recover without circularity and risks public/private split overfitting.
Cost low; **not validatable** → not viable as a submission lane by this session's
gate. No external data would fix that; it is a design limitation, not a data gap.

## Preregistered outcome rule

Frozen in `registry/preregistration_h73-7.json`: at most 3 experiments (E1/E2/E3);
promotion only if the best beats the fold-fair H33-analogue control on pooled
HOLDOUT-DTI with paired 95% CI excluding 0, all 41 leakage canaries ≤0.90
symmetric AUC, and both uniqueness stages pass (surface Spearman ≤0.90; mutual
3 px dot overlap ≤0.70). Otherwise NEGATIVE, site banner DO NOT SUBMIT, 0 weekly
slots spent by this repo. Results: `evidence/selection_h73-7.json`,
`evidence/run_card_h73-7.json`.
