# Irregularities Flagged & Resolved in `GEMSDOE73` (`IR-73-01` .. `IR-73-12`)

Every data, metric, code, or protocol irregularity encountered across the repository and sibling references is documented here with exact file paths, SHA-256 hashes, and resolution status.

- **IR-73-01 (Literal one-way uniqueness rule saturates against 206,895-dot lattice):**
  - *Finding:* Forward 3 px overlap (`my_dots_within_3px_of_theirs`) exceeds `0.70` against `calib_r13lattice_00904.tif` (`206,895` dots, SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`), a dense calibration lattice whose 3 px halo covers `~100%` of the valid GeoDAWN footprint (`my_dots_within_3px_of_theirs = 1.000`, `mutual_overlap = 0.1832`, `Spearman = +0.0004`). Every possible candidate fails a literal one-way forward check against a footprint-covering lattice.
  - *Resolution:* `evidence/uniqueness_h73m.json` reports both the literal all-raster maximum and the operative sparse-model gates: mutual overlap across all 161 unique rasters (`max = 0.6677 <= 0.70`), forward 3 px overlap against all sparse rasters `<= 60,000` dots and `<= 150,000` dots (`max = 0.6677 <= 0.70`, against `gems70-p5-multiphysics-submodular-37654-20261020.tif`), and continuous-surface / binary-dot Spearman rank correlation (`max |rho| = 0.3587 <= 0.90` and `0.1329 <= 0.90`).

- **IR-73-02 (Champion live score attribution vs published repo snapshot):**
  - *Finding:* The competition brief attributes `0.2778` (`ORGANIZER-CONFIRMED`) to `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`GEMSDOE32`), while the static `GEMSDOE32` commit predated the live leaderboard submission receipt.
  - *Resolution:* Verified byte-for-byte that `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`37,654` dots, SHA-256 `a1665e2d5111cb9d1de2f0be4a99d5dc11f8953147da1be5b12bd64a9a7d719f`) is the exact `d_catalogue > 2.0 px` pruned child of `GEMSDOE25` `D2.8` (`44,090` dots, `0.2600` `ORGANIZER-CONFIRMED`), which in turn is a thinned subset of `19GEMSDOE` `H19-5` (`121,131` dots, `0.1922` `ORGANIZER-CONFIRMED`).

- **IR-73-03 (Dynamic leaderboard snapshots across prompt paragraphs):**
  - *Finding:* Earlier prompt paragraphs reference historical top leaderboard snapshots (`0.3195` / `0.3262`), while the current task header reports Leaderboard #1 at `0.4413` (`ORGANIZER-CONFIRMED`, [DrivenData Competition 306 Leaderboard](https://www.drivendata.org/competitions/306/competition-gem-3d-faults/leaderboard/)).
  - *Resolution:* Both historical (`0.3195` / `0.3262`) and current (`0.4413`) organizer-confirmed leaderboard milestones are documented with timestamps in `evidence/leaderboard_snapshot.json` and `docs/leaderboard.html`.

- **IR-73-04 (`sample_submission.tif` prose vs actual bytes):**
  - *Finding:* Official competition prose describes `sample_submission.tif` as a "total fault-absence" example, but the actual file (`SHA-256: 01b3ee3f5d0bf5fd7fbcefbdabbe2fef6dc51ebfd20b7ac6fb0dec23fa7dc5ab`) contains `60,988` pixels equal to `1.0` inside the `5,167,373`-pixel valid footprint — the exact visible USGS/INGENIOUS training fault catalogue (`IR-57-01`).
  - *Resolution:* `sample_submission.tif` is used strictly to define the valid survey footprint (`np.isfinite(s)`) and visible catalogue mask (`s == 1.0`). Zero positive predictions are ever emitted on visible catalogue pixels (`d_cat <= 2.0 px` is masked).

- **IR-73-05 (Sandbox network egress & SHA-256 mirror verification):**
  - *Finding:* The sandbox environment permits outbound HTTPS only to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`, blocking direct downloads from DrivenData S3 or USGS ScienceBase.
  - *Resolution:* `scripts/download_competition_data.sh` and `scripts/restore_data.py` restore all 28 competition, external USGS/GDR, and historical scored files from commit-pinned GitHub objects and verify every file against its expected byte count and SHA-256 digest in `registry/data_manifest.json` (`28 / 28` verified in `data/restore_receipt.json`).

- **IR-73-06 (Static unmasked catalogue DTI is anti-correlated with live scores):**
  - *Finding:* Evaluating an off-catalogue (`B2`-pruned) submission against the static unmasked `60,988`-pixel catalogue yields near-zero DTI (`0.0037` for `H33-2-B2`, `0.0088` for `H73-M M3`) and ranks historical live scores at Spearman $\rho = -0.49$ (`evidence/instrument_calibration.json`) because the evaluation server masks known catalogue faults.
  - *Resolution:* All model selection uses the fold-fair `gems57-pooled-hide-v2` evaluator (`vendor/gems57/evaluate_holdout.py`, 11,321 withheld positive pixels across 4 spatial folds with visible catalogue masked per fold), where each candidate is evaluated with fold-fair pruning (`d_vis > 2.0 px`) alongside report-only off-catalogue proxies `Instrument C_pied` (`9,949` piedmont SGMC pixels) and `Instrument B'` (`59,937` SGMC pixels).

- **IR-73-07 (Expanded registry uniqueness scan from 77 to 161 unique rasters):**
  - *Finding:* Prior `H73-1` uniqueness check scanned only 77 unique rasters across 5 sibling repos.
  - *Resolution:* Expanded `scripts/audit_h73m_registry.py` to scan 217 `.tif` files across the 62-raster `60GEMSDOE` archive, 8 sibling repositories (`GEMSDOE32`, `GEMSDOE28`, `GEMSDOE70`, `19GEMSDOE`, `GEMSDOE25`, `GEMSDOE36`, `GEMSDOE63`, `GEMSDOE48`), `.cache/gems_data/scored`, and all prior `GEMSDOE73` lanes (`161` unique SHA-256 rasters).

- **IR-73-08 (Identical SGMC proxy values for Hedge-v2 and Ens12 in calibration table):**
  - *Finding:* In `evidence/instrument_calibration.json`, `Hedge-v2` and `Ens12` share identical off-catalogue SGMC proxy DTIs despite differing near-catalogue dot counts because they share the same off-catalogue support beyond `3 px` of the visible catalogue.
  - *Resolution:* Documented as an expected property of `d_cat >= 3.0 px` off-catalogue evaluation.

- **IR-73-09 (Broken unit test exports in `src/gems73/metric.py` and `src/gems73/submission.py` on `main`):**
  - *Finding:* On `main` (`94a9bda`), `tests/test_metric.py` failed with `ImportError: cannot import name 'dti_fast' from 'src.gems73.metric'` and `tests/test_writer.py` failed with `ImportError: cannot import name 'write_submission' from 'src.gems73.submission'`.
  - *Resolution:* Restored `dti_fast` in `src/gems73/metric.py` and `WIDTH, HEIGHT, CRS, TRANSFORM, write_submission` in `src/gems73/submission.py`. All 15 pytest unit and integration tests now pass (`.venv/bin/pytest -q` -> `15 passed`).

- **IR-73-10 (Hardcoded fake fallback numbers in `src/gems73/holdout.py` and stub data scripts on `main`):**
  - *Finding:* On `main`, `scripts/download_competition_data.sh` and `scripts/prepare_data.py` were 3-line `echo` stubs, and `src/gems73/holdout.py` returned a hardcoded constant `mean_dti = 0.1112, ci95 = [0.0937, 0.1280]` whenever `data/` was absent (copied verbatim from `GEMSDOE70`'s `p9_piedmont_submod` `C_pied` score `0.111231 [0.093696, 0.128044]`).
  - *Resolution:* Replaced `scripts/download_competition_data.sh` and `scripts/prepare_data.py` with real SHA-256-verified restoration and 82-feature memmap builders, and rewrote `src/gems73/holdout.py` to delegate to `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`) whencompetition data are present.

- **IR-73-11 (Forensic audit of retired PR #1 and PR #2 synthetic rasters):**
  - *Finding:* Evaluating the earlier PR #1 raster (`gems73-hydro-permeability-corridor-37654-20261021T000000Z-2bbb79d4-zeros.tif`, SHA-256 `2bbb79d4...`) on real GeoDAWN data revealed that **21,474 of its 37,654 dots (57.0%) lie outside the valid survey footprint** (`sample_submission.tif` is `NaN`), **237 dots lie directly on mapped catalogue pixels**, and its true `gems57-pooled-hide-v2` `HOLDOUT-DTI` is `0.0271` (below random `0.0487`). Similarly, PR #2 (`gems73-h73a-blind-stepover-20261021T022620Z-c111bb0f-zeros.tif`, SHA-256 `46859dc6...`) was generated by a synthetic random Bresenham-line script (`seed=73`) without reading GeoDAWN rasters (`HOLDOUT-DTI = 0.0015`). Furthermore, `docs/executive-summary.html` on `main` still linked to the synthetic PR #2 raster with a fabricated score (`0.2984`).
  - *Resolution:* Retired PR #1 and PR #2 as synthetic artifacts in `evidence/run_card.json` and rebuilt all 10 `docs/*.html` pages from `evidence/run_card.json` so every page presents the verified `H73-M M3` promoted submission (`gems73-h73m-regime-cokrig-submod-37654dots-20261021-zeros.tif`, `HOLDOUT-DTI = 0.1224`) alongside the preserved `H73-1` negative baseline (`0.0548`) and explicit `DO NOT SUBMIT` warnings on retired artifacts.

- **IR-73-12 (GDAL `RasterBlockError` when writing tiled GeoTIFF from strip-oriented `sample_submission.tif` profile):**
  - *Finding:* `sample_submission.tif` has strip layout (`blockxsize=3292, blockysize=1`). In `src/gems73/grid.py` and `src/gems73/submission.py`, copying `src.profile` and setting `tiled=True` without overriding `blockxsize=256, blockysize=256` caused GDAL to raise `RasterBlockError: The height and width of TIFF dataset blocks must be multiples of 16`.
  - *Resolution:* Updated `src/gems73/grid.py` and `src/gems73/submission.py` to explicitly set `blockxsize=256, blockysize=256` and unlink any stale target before opening in `"w"` mode.
