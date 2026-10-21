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
