# Irregularities Log — Line-by-Line Source & Code Verification (`IR-73-01` through `IR-73-12`)

Every claim, metric formula, grid constant, dataset header, prior submission artifact, and code path in `buffedlizard55-lab/GEMSDOE73` was verified against official primary sources:
- DrivenData DOE GEMS Competition Overview & Rules: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- DrivenData Performance Metric Specification (Page 967): <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric>
- USGS GeoDAWN Airborne Geophysics & LiDAR Compilation (`DOI:10.5066/P93LGLVQ`): <https://www.sciencebase.gov/catalog/item/618176eed34e9f2789e4789c>
- Great Basin Center for Geothermal Energy INGENIOUS Dataset (`GDR #1391`): <https://gdr.openei.org/submissions/1391>
- USGS State Geologic Map Compilation (`SGMC`, `DOI:10.3133/ds1052`): <https://doi.org/10.3133/ds1052>
- USGS 3D Elevation Program (`3DEP`): <https://www.usgs.gov/3d-elevation-program>

---

## Critical New Irregularities Discovered & Fixed in This Session

### `IR-73-10` — Prior Primary Download on `docs/index.html` Was Generated from Synthetic Random Lines (`CRITICAL — RESOLVED`)
- **Finding**: Inspection of `scripts/generate_submission.py` (merged in PR #2) revealed `make_synthetic_fault_mask()` generated `gems73-h73a-blind-stepover-20261021T022620Z-c111bb0f-zeros.tif` (`30,762` active pixels) purely from random Bresenham segments without reading a single byte of `training_features.tif`, `labels.tif`, LiDAR, or geothermal data. Earlier PR #1 (`gems73-hydro-permeability-corridor-37654-20261021T000000Z-2bbb79d4-zeros.tif`) similarly fell back to procedural Gaussian noise when `data/` was absent.
- **Measured Impact on Real Holdout**: Evaluated honestly on canonical shared `gems57-pooled-hide-v2` (`11,321` withheld positive pixels), PR #2 scored **`HOLDOUT-DTI = 0.0015`** (`32x` worse than uniform random `0.0484`!) and PR #1 scored **`0.0271`** (`44%` below uniform random).
- **Resolution**: Replaced across `docs/index.html`, `docs/executive-summary.html`, `README.md`, and all subpages with verified real-data `H73-MVH` (`gems73-h73-mvh-ventbridge-submod-37654-20261021T044500Z-faebf9e1-zeros.tif`, **`HOLDOUT-DTI = 0.1599`**), and quarantined all historical files in an explicit archived warning table stamped **`DO NOT SUBMIT`**.

### `IR-73-11` — Precomputed `dist_known_fault_px` Leakage Trap in External Geothermal CSVs (`CRITICAL — RESOLVED`)
- **Finding**: Inspection of `gdr_wellspring_in_footprint.csv` and `gdr_volcanic_vents_in_footprint.csv` in `.cache/gems_data/external/` found a precomputed column `dist_known_fault_px` measuring Euclidean distance to the full `labels.tif` fault catalogue (including withheld holdout components). Any model reading that column leaks full-catalogue fault locations across folds.
- **Resolution**: `src/gems73/mvh_features.py` defines `FORBIDDEN_POINT_COLUMNS = frozenset({"dist_known_fault_px", "known_fault", "label"})`, asserts hard failure if read, and uses strictly coordinates `(row, col)` + physical fluid temperature (`temp_c`) and chemical geothermometers (`geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`). Unit-tested in `tests/test_h73_mvh_package.py`.

### `IR-73-12` — 24-Pixel Quadrant Seam Zero Strip in Full-Footprint OOF Inference (`CAUGHT IN PASS 2 VISUAL INSPECTION — RESOLVED`)
- **Finding**: In `vendor/gems57/holdout.py`, `fold["region"]` excludes a `boundary_px = 12` (`±12 px = 24 px = 2.4 km`) strip along the 4-quadrant split lines so training/evaluation faults never straddle fold borders. Predicting OOF production posteriors only on `fold["region"]` left a `2.4 km` zero-probability cross seam across central Nevada in staging build `f11e1a4a`.
- **Resolution**: Caught immediately by visual inspection of `docs/assets/mvh_overview.png` in Pass 2. Updated both `scripts/run_h73_mvh.py` and `scripts/package_h73_mvh.py` to predict on the exhaustive `quad_2d == q_id` partition (covering `100.0000%` of all `5,167,373` footprint cells seamlessly) while still excluding `binary_dilation(quad_2d == q_id, 30)` (`3.0 km` buffer) during training. Staging `f11e1a4a` was deleted and replaced with seamless `faebf9e1`.

---

## Inherited Competition, Portal & Repository Irregularities (`IR-73-01` through `IR-73-09`)

- **`IR-73-01` — Identical Training & Catalogue Rasters**: `labels.tif` and `existing_faults.tif` have identical SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` (`60,988` positive pixels). Static evaluation against `labels.tif` is pure self-recovery (`Spearman = -0.49` vs live scores); only buffered whole-component hide-and-recover (`gems57-pooled-hide-v2`) validly measures off-catalogue discovery.
- **`IR-73-02` — Official Worked Example Rounding on DrivenData Page 967**: Plugging `TP_w = 3.00, FP_w = 1.89, FN_w = 2.00` into `TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w)` yields `3.00 / 4.978 = 0.60265...`, displayed rounded to two decimals as `0.60` on [Page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric).
- **`IR-73-03` — DrivenData Portal Rejects `NaN` Outside Footprint (`"Predicted values must be in range [0, 1]"`)**: Even though `sample_submission.tif` contains `7,111,787` `NaN` cells outside the `5,167,373`-cell footprint, the live portal validator checks range across the entire `12,279,160`-cell array. `vendor/gems57/submission_writer.py` writes `0.0` outside footprint (`nodata = None`), verified across all `12,279,160` cells in `faebf9e1`.
- **`IR-73-04` — Non-1m-LiDAR Coverage Gap (`24.6%` of Footprint Missing Valid 1m Scarp Support; `38.7%` Partial/Edge Tiles)**: Bridged cleanly via native `NaN` tree routing + 100%-footprint 10 m seamless 3DEP DEM (`topo_10m_derived_100m_u8.tif`) + fluvial `χ` (`dem10_chi_100m_u8.tif`) + marginal quantile alignment, lifting gap-tile holdout DTI from `0.0653` to **`0.1510`**.
- **`IR-73-05` — Unsupervised Scarp Detector Hypothesis Refutation (`H73-1 = 0.0548 < 0.0939`)**: Preserved honestly as negative baseline and resolved scientifically in `H73-MVH` via out-of-fold supervised multi-physics + geothermal vent + bridge learning (`0.1599`).
- **`IR-73-06` — Asymmetric Forward Dot Overlap vs Full-Footprint Continuous Surfaces & Space-Filling Lattices**: `17GEMSDOE` continuous surfaces (`5,167,373` positive cells) and `13GEMSDOE` `r13-lattice-s5` (`206,895` lattice dots) force forward overlap `~1.0` on any non-empty candidate. `vendor/gems57/uniqueness.py` evaluates symmetric `mutual = min(fwd, rev)` (`0.4808 <= 0.70`) alongside `0.5*(fwd+rev)` (`0.6035 <= 0.70`) and matched-budget forward overlap (`0.6220 <= 0.70`), all explicitly reported side by side.
- **`IR-73-07` — Prior Partial `21 / 78` Repo Registry Scan & Hardcoded `/home/user/refs` Path (`RESOLVED`)**: Synchronized all **`83 / 83` public `buffedlizard55-lab` repositories** (`984` unique valid rasters, `errors = 0`, `complete_accessible_scan = True`) via `scripts/sync_registry_all.py` and replaced hardcoded `/home/user/refs/...` in `scripts/run_experiments.py` with SHA-256-pinned manifest entries.
- **`IR-73-08` — Stale Placeholder Hash in Prior `README.md` (`RESOLVED`)**: Replaced stale `7f3c2a9e` string with verified `faebf9e1` SHA-256 `faebf9e13f763ccedd2486df2209e6e7f37d1a5548495003e2401c5b03d538c8` and added automated consistency assertions in `tests/test_h73_mvh_package.py`.
- **`IR-73-09` — Pre-Existing `pytest` Collection Breakage on `main` (`RESOLVED`)**: Restored `dti_fast` and `write_submission` exports in `src/gems73/metric.py` and `src/gems73/submission.py` and expanded test coverage to `100%` pass.

### PR #13 Additional Remediations (`IR-73-15` & `IR-73-16`)
- **`IR-73-15` (`src/gems73/submission.py` Tiled GeoTIFF Block Multiple-of-16 Bug):** Strip template `sample_submission.tif` (`3730 x 3292`, `3292 % 16 = 12`) crashed GDAL `RasterBlockError` when `tiled=True` lacked `blockxsize=256, blockysize=256`. Remediated directly in place and regression-tested in `tests/test_mcsc_pipeline.py`.
- **`IR-73-16` (`vendor/gems57/submission_writer.py` `0600` Tempfile Permissions):** `NamedTemporaryFile` staged `.tif`/`.zip` with `0600` mode; fixed with `os.chmod(source, 0o644)` prior to `os.replace` so all GitHub Pages downloads are `0644` world-readable.
