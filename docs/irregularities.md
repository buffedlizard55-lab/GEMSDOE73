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
- **IR-73-10 (fabricated holdout in a shared tool — FIXED 2026-10-21, H73-7 session):**
  `src/gems73/holdout.evaluate_holdout()` returned hard-coded "synthetic demo" numbers
  (mean DTI 0.1112, CI [0.0937, 0.1280], 12,226 withheld) whenever `data/` was absent.
  Those constants were quoted as HOLDOUT-DTI evidence in `evidence/run_card.json`
  (hydro-permeability lane) under a "promote" verdict. No pixel was ever withheld or
  scored. Fix: the function now raises `RuntimeError` (shared tool repaired once, per
  protocol rule 2); `tests/test_holdout.py` asserts the refusal; the hydro verdict is
  voided in `evidence/run_card_hydro_addendum_2026-10-21.json`; the site demotes both
  synthetic lanes (hydro corridor, blind stepover — the latter's own card already said
  verdict negative while the site promoted it as "Tier 1 / one-click", a contradiction
  now corrected on every page).
- **IR-73-11 (site forensic numbers wrong — FIXED):** the home/executive pages said the
  H33 champion deleted "1,152 dots (from ~38,800 → 37,654)" from an "H27-4 dotted
  ridge, 0.2708 base". Measured from the bytes (twice, independently): H33 = D2.8
  (44,090) minus 6,436 dots at distance ≤2.0 px from the catalogue; D2.8 ⊂ H19-5
  (121,131). Also `README.md`'s quick-start named a non-existent file
  (`...20261020T230000Z-7f3c2a9e...`). Both corrected.
- **IR-73-12 (literal forward-overlap gate vs H73-7):** the H73-7 candidate exceeds the
  brief's literal one-way 0.70 forward-overlap rule against four dense/union registry
  rasters (r13 lattice 206,895 dots: 0.994; gems10 h25-ctx-ridge 174,232 dots: 0.808;
  gems10 h28-dotted 69,281 dots: 0.756; gems28 h37-1 union-pool 38,545 dots: 0.723;
  gems27 h28-1 59,075 dots: 0.710) while passing the shared tool's operative gates
  (mutual ≤0.504 worst; Spearman ≤0.0573 dots / ≤0.2089 surface; vs champion mutual
  0.217). Same saturation family as IR-73-01, extended: union/ridge rasters are
  *designed* to cover the ridge network, so any geologically-placed field is largely
  within 3 px of their dots. Reported in full in `evidence/run_card_h73-7.json` for
  the selector rather than resolved silently in the lane's favour. One registry file
  errored in the audit: `GEMS36_FORMAT_TEST_NOT_SUBMISSION.tif` (grid mismatch — by
  its own name not a submission; cannot share this grid's dot geography).
- **IR-73-13 (writer tile bug — FIXED):** `src/gems73/grid.write_submission` and
  `src/gems73/submission.write_submission_geotiff` set `tiled=True` while inheriting
  the template's strip block size (sample_submission.tif: blockxsize 3292), which
  GDAL rejects ("TileWidth … multiples of 16"). Both now set 256×256 blocks.
  The shipped H73-7 file was written by the fail-closed vendor writer and is
  unaffected. IR-73-09 is READY: `pytest tests/` now collects and passes (17 passed).
