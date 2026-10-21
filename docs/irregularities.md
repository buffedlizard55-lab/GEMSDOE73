# Irregularities flagged for review (GEMSDOE73)

- **IR-73-01 (literal uniqueness rule saturates):** forward 3 px overlap exceeds 0.70 only
  against the 206,895-dot r13 lattice (0.994; mutual 0.139), whose halo covers ~100% of the
  footprint — every possible candidate fails the literal one-way rule against it. Operative
  gates reported: mutual overlap (max 0.390), forward vs sparse (<=150k dots) rasters (max 0.480).
- **IR-73-02 (champion score attribution):** the brief assigns 0.2778 to
  `h33-h33-2-b2-...-zeros`, but the GEMSDOE32 site itself states no organiser score exists for
  its artifacts (at publish time). No receipt/hash crosswalk is in any repo inspected.
  Treated as OWNER-REPORT throughout.
- **IR-73-03 (leaderboard snapshots conflict in brief):** 0.4413 vs 0.3195/0.3262 are dated
  snapshots of the same dynamic page. This session read #1 = 0.4413 officially
  (`evidence/leaderboard_snapshot.json`, 2026-10-21).
- **IR-73-04 (sample submission wording vs bytes):** the official page calls the sample a
  total-fault-absence raster; the hash-pinned bytes contain 60,988 pixels equal to 1, exactly
  the catalogue pixels (MEASURED-HERE). Used only as the grid/footprint template.
- **IR-73-05 (data provenance):** competition files are login-walled on DrivenData and this
  sandbox cannot reach Dropbox/USGS directly. Files were restored from owner GitHub mirrors
  pinned by SHA-256 (`registry/data_manifest.json`, receipt `data/restore_receipt.json`).
  Hashes prove mirror consistency, NOT organiser authentication.
- **IR-73-06 (instrument anti-correlation):** static DTI vs the full catalogue ranks
  OWNER-REPORT live scores at Spearman -0.49 (n=13, MEASURED-HERE); the live champion scores
  0.0067 on it, below random (0.0504). Any non-fold-fair catalogue holdout is anti-evidence
  for B2-style candidates.
- **IR-73-07 (registry scan incomplete):** uniqueness was checked against 77 unique rasters
  accessible in this session (5 sibling clones + scored mirrors), not all ~72 sibling repos
  or any private registry. Vendor summary `complete_accessible_scan=false` is recorded.
- **IR-73-08 (identical proxy values):** in `evidence/instrument_calibration.json`, the
  Hedge-v2 and Ens12 rasters give byte-identical SGMC proxy DTIs despite different total dot
  counts, suggesting a shared off-catalogue mask; cause not investigated (diagnostic only).
- **IR-73-09 (pre-existing main test breakage, found at merge):** on `origin/main` (195015e)
  `pytest tests` already fails collection: `tests/test_metric.py` imports `dti_fast` and
  `tests/test_writer.py` imports `write_submission/WIDTH/HEIGHT` from `src.gems73`, which the
  PR#1+#2 merged library no longer exports. Verified identical failure in a clean worktree of
  origin/main before this lane's merge; not caused by H73-1 (its tests pass: 5 passed with
  `tests/test_metric_and_submission.py tests/test_holdout.py`). Fix belongs to the main-lane
  library consolidation, flagged here rather than rewritten inside this lane.
- **IR-73-09 RESOLVED (session-2, 2026-10-21):** `tests/test_metric.py` rewritten against the
  real src API (duplicate definitions + phantom `dti_fast` removed), `tests/test_writer.py`
  rewritten against `write_submission_geotiff`, which exposed a real writer fragility
  (`tiled=True` without block sizes) fixed in `src/gems73/submission.py` + `grid.py`
  (`blockxsize/blockysize=256`). Full suite: 13 passed.
- **IR-73-10 (site promoted a synthetic file as PRIMARY — corrected):** until 2026-10-21 the
  home/executive pages labelled the H73-A blind-stepover file "PRIMARY / Tier 1" and invited
  submission, while `registry/run_card.json` already recorded verdict *negative* and "holdout
  not yet run". The file is a random-geometry synthetic generator
  (`scripts/generate_submission.py`, now header-deprecated). Site rebuilt with separate
  download/submit gates for every file; no file is currently submit-recommended.
- **IR-73-11 (hard-coded holdout numbers — removed):** `src/gems73/holdout.py` returned
  fabricated "synthetic-demo" HOLDOUT-DTI values (mean 0.1112) whenever `data/` was absent,
  and `evidence/run_card.json` cited them with verdict *promote* for the hydrothermal-corridor
  file. The stub is replaced by a fail-loud delegate to the shared vendor evaluator; both
  stale run cards carry additive `_superseded_2026-10-21` markers (original fields preserved).
  No trustworthy score exists for the hydrothermal file; do not submit it.
- **IR-73-12 (session-2 lane relatedness):** H73-6 X1 shares the session-1 `scarp_n` +
  `pied_soft` base by design; vs H73-1 E1 dots: forward 0.596, reverse 0.693, mutual 0.596
  (all < 0.70 gate, reverse within 0.007 of it), surface ρ 0.120. Unique per protocol, but
  the two lanes are cousins, not strangers — disclosed wherever uniqueness is reported.
  Registry scope this session: 16 accessible rasters (vs 77 in session-1); IR-73-07 stands.
- **IR-73-13 (leaderboard moved between same-day reads):** #3 read 0.3811 (43 submissions)
  earlier on 2026-10-21 and 0.3894 (45 submissions) later the same day. Latest read is in
  `evidence/leaderboard_snapshot.json`; treat all leaderboard figures as dated snapshots.
- **IR-73-14 (src metric docstring identity):** `src/gems73/metric.py` claimed
  `DTI = T/(0.2(T+FP)+0.8|G|)`, collapsing the distinct sums T (over truth) and M (over
  dots). Code computed TP/FP/FN directly and was unaffected; docstring corrected to the
  vendor form `T/(0.2(T+S-M)+0.8|G|)`. Shared-tool fix reported here per protocol rule 2.
- **IR-73-15 (literal forward-overlap gate vs H73-7, extension of IR-73-01):** the H73-7
  candidate exceeds the brief's literal one-way 0.70 forward-overlap rule against four
  dense/union registry rasters (r13 lattice 206,895 dots: 0.994; gems10 h25-ctx-ridge
  174,232 dots: 0.808; gems10 h28-dotted 69,281 dots: 0.756; gems28 h37-1 union-pool
  38,545 dots: 0.723; gems27 h28-1 59,075 dots: 0.710) while passing the shared tool's
  operative gates (mutual ≤0.504 worst; dots ρ ≤0.0573; surface ρ ≤0.2089; vs champion
  mutual 0.217; vs every comparable-mass lane merged to main in parallel, forward ≤0.408
  and mutual ≤0.326 — `evidence/uniqueness_h73-7_vs_main_lanes.json`). Union/ridge rasters
  are designed to cover the ridge network, so any geologically-placed field is largely
  within 3 px of their dots. Printed in `evidence/run_card_h73-7.json` for the selector
  rather than resolved silently. (This lane's branch numbered this IR-73-12 before the
  parallel merge; renumbered at merge to avoid colliding with session-2's IR-73-12.)
  One registry file errored in the H73-7 audit: `GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif`
  (grid mismatch — by its own name not a submission).
- **IR-73-16 (branch-time site forensic error, already corrected on main):** the pre-merge
  site said the H33 champion deleted "1,152 dots (from ~38,800 → 37,654)" from an
  "H27-4 0.2708 base", and the README quick-start named a non-existent file. Measured
  (twice): 6,436 dots deleted from D2.8's 44,090 (D2.8 ⊂ H19-5, 121,131). Main's
  forensic section already carries the correct 6,436; recorded here so the H73-7 lane's
  earlier branch-time correction (its IR-73-11) has a main-numbered home.
- **IR-73-17 (two PROMOTE candidates tie on Instrument A):** main's crossdrain lane
  (PR #7) reports HOLDOUT-DTI Instrument A 0.136023 [0.117451, 0.155962] and H73-7
  reports 0.136888 [0.115779, 0.157736] on the identical evaluator/draw (11,321 withheld
  px). The point estimates differ by 0.0009 — indistinguishable. Site/README present
  H73-7 as Orthogonal Slot #3, not as a replacement primary; any "#1" language on the
  site pre-dates this merge and should be read as of its lane's merge date. Both lanes
  share the catalogue-supervised transfer caveat; distinguishing them needs a live slot
  each or a less catalogue-biased instrument, neither of which this repo can simulate.
