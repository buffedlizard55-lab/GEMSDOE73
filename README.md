# GEMSDOE73 — A Fault-Discovery System for the DOE GEMS Prize

> **Prompt (read every session).** The goal is to place top of the leaderboard in the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — a competition to find geothermal-indicative faults missing from the USGS/INGENIOUS catalogue in the GeoDAWN NW Nevada region. We must generate a **unique, portal-safe single-band GeoTIFF** (`float32`, `EPSG:32611`, `100 m`, `3292×3730`, values in `[0,1]`, no nodata sentinel) that is trivially downloadable and submittable. Work line-by-line, verify every number against an official trusted source, provide links for manual review, flag irregularities, and never hallucinate.

## Core Values

**Maximize P(Win)** — every weekly submission slot is an experiment, not a lottery ticket. We weigh tradeoffs, assess risk, and choose the path that maximizes probability of winning.

**Own the Outcome** — we own results end-to-end, not just our slice. We treat failure and success as signals and act without waiting for permission.

## Quick Start — Download the Submission

**👉 Go to the [GitHub Pages site](https://buffedlizard55-lab.github.io/GEMSDOE73/) — the banner at the top names the current candidate and both gates (download / submit).**

- Current candidate (lane **H73-7**, verdict **PROMOTE to selector** — passed its preregistered holdout gate):
  `docs/downloads/gems73-h73-7-hardfault-pu-e1-37654dots-20261021.tif`
  (sha256 `a0e4b3f31cb84270b10d19fff8399412a0850f3cffeb77d59b553c7ff0475d67`, 37,654 dots, all-finite `[0,1]`, `nodata=None`, `EPSG:32611`, `3730×3292`; also as `.zip`, with a validator receipt `.json` from re-reading the bytes).
  **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 11,321 withheld px): **0.1369 [0.1158, 0.1577]** vs fold-fair
  H33-analogue control 0.0939 [0.0813, 0.1076], paired Δ +0.0430 [0.0230, 0.0627]. This is a *local holdout*
  number, **not** a leaderboard score — no organizer score exists for this file. Promotion to a real weekly
  slot is a separate selector step (check the cap on the DrivenData submission page); this repo spends 0 slots.
  Exact submission steps + the paste-in note: `docs/executive-summary.html`.
- **DO NOT SUBMIT** the older `gems73-h73a-blind-stepover-…` or `gems73-hydro-permeability-corridor-…` files in
  `docs/downloads/`: synthetic-generator artifacts never scored on the real instrument. The hydro lane's
  "HOLDOUT-DTI 0.1112 / promote" came from a hard-coded demo function in `src/gems73/holdout.py` — voided
  (IR-73-10, `evidence/run_card_hydro_addendum_2026-10-21.json`); the tool now refuses to invent numbers.
- **DO NOT SUBMIT** the H73-1 piedmont file either (measured, verdict NEGATIVE; see bottom of this README).

## What This Repo Does

1. **Metric re-implementation** — exact distance-weighted Tversky `DTI(α=0.2, β=0.8, R=300 m)` with triangular kernel, verified against the published worked example `TP=3.00 FP=1.89 FN=2.00 → 0.60`.
2. **Spatially-blocked holdout** — hide-and-recover on whole fault segments with a buffer; catalogue-derived features only from visible faults; pixel-exact masking; pooled DTI scoring.
3. **Submission writer** — strict format validator (CRS/shape/transform match, `[0,1]` range, no sentinel) and both `zeros` (portal-safe) and `nan` (spec) variants.
4. **Hypothesis ranking** — 5 new geological hypotheses, each naming layer(s), physical signature, why it catches a fault absent from the catalogue, and how it differs from prior art.

## Limitations & What We Need

- **No DrivenData auth in this sandbox** — the competition files cannot be fetched from DrivenData directly (login wall). Working path used by lanes H73-1/H73-7: `.venv/bin/python scripts/restore_data.py --group all` restores all 23 files (incl. the 400 MB 19-band feature stack) from owner GitHub mirrors, SHA-256-verified against `registry/data_manifest.json` (mirror consistency, **not** organizer authentication — IR-73-05). `1m_DEM_links.csv` itself is not mirrored; its derived 100 m LiDAR stack is.
- **No hallucinated scores** — every number is labelled `HOLDOUT-DTI` (evaluator version, withheld positives, 95 % CI) or `ORGANIZER-CONFIRMED` (submission-page receipt). Projections are never written as scores.
- **External data must be free & licensed for sharing** — only USGS 3DEP, USGS GeoDAWN (DOI 10.5066/P93LGLVQ), USGS SGMC, GDR 1391 (CC BY 4.0), NBMG INGENIOUS REST, ComCat are permitted; each is listed in `docs/sources.html` with fetch status.

## Repository Layout

```
docs/               # GitHub Pages site (index, executive-summary, hypotheses, research, leaderboard, sources, irregularities)
docs/downloads/     # Submission GeoTIFFs + audit JSONs
src/gems73/         # Reusable library: grid, metric, emission, submission, holdout
scripts/            # Builders, validators, fetchers
data/               # (git-ignored) competition rasters after manual download
tests/              # Metric & validator unit tests
registry/           # Machine-readable run card, scores, manifests
evidence/           # Holdout logs, leakage canaries
```

## Verify No Hallucinations (line-by-line)

Every factual claim on the site links to an official verified source:

- Competition overview & problem description: https://www.drivendata.org/competitions/306/competition-doe-gems/ and /page/967/
- About page & additional resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf → mirrored as https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0
- GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and and https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index

Check `docs/sources.html` for the full table with fetch status and SHA256 pins.

## Leaderboard Context (2026-10-21 live read)

| Rank | Participant | Best DTI |
|------|-------------|----------|
| 1 | xiaofanhu | 0.4413 |
| 2 | cfld__ | 0.3904 |
| 3 | Batik Shirt Brothers | 0.3811 |

The group's previous best across 78 sibling repos peaked at `0.2778` (GEMSDOE32 `h33-h33-2-b2`, 37,654 dots, pruned flank `B=2`) and `0.2710` (GEMSDOE28 `h36-1`). See `docs/research.html` for the PhD-level post-mortem of why that file scored highest and how we aim to beat it.

## How to Regenerate

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_data.py --group all          # 23 hash-pinned files -> .cache/gems_data
.venv/bin/python scripts/run_experiments_h73_7.py              # canaries + 3 preregistered experiments + holdout
.venv/bin/python scripts/build_submission_h73_7.py             # fail-closed vendor writer -> docs/downloads/*.tif/.zip/.json
.venv/bin/python scripts/audit_registry_h73_7.py               # uniqueness stages A+B vs accessible registry
.venv/bin/python scripts/build_run_card_h73_7.py               # protocol JSON card
.venv/bin/python scripts/build_site_h73_7.py                   # site front pages from the run card
.venv/bin/python -m pytest tests/ -q                           # 17 passed
```

## License & Disclosure

All code is MIT. External data retains its original license (see sources). No organizer authentication is misrepresented; no score is claimed without a receipt.

## Parallel lane H73-1 — piedmont micro-scarp chain (PR #3) — verdict NEGATIVE, do not submit

A third, independent lane merged alongside the hydrothermal corridor and blind stepover lanes above.
**Download-for-review: yes. Submit: NO.** It failed its preregistered holdout gate
(HOLDOUT-DTI `gems57-pooled-hide-v2`, 11,321 withheld px: E1 0.0548 [0.0417, 0.0688] vs fold-fair
H33-analogue control 0.0939 [0.0813, 0.1076]). It is format-valid and unique — vs the two main-lane
rasters in this repo: mutual 3 px overlap 0.067 (hydro corridor) and 0.043 (blind stepover);
vs the H33 champion: forward 0.177. File:
`docs/downloads/gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif`
(sha256 `d09dca2465f784e8a07571894cd12c689e4b34e8f7c14be321b5d6006b2d2ece`).
Full lane page: `docs/h73-1-piedmont.html` · run card: `evidence/run_card_h73-1.json` ·
preregistration: `registry/preregistration.json` · hypotheses: `docs/research/hypotheses.md` ·
irregularities: `docs/irregularities.md`. Negative results are deliverables; weekly slots spent by
this lane: 0.

## Parallel lane H73-7 — hard-fault PU ranker (this session) — verdict PROMOTE to selector

Fold-fair HistGradientBoosting PU ranker on 41 physical channels (19 official bands + 10 LiDAR +
8 radiometric/extension + 4 unsupervised H73-1 components), positives weighted toward low-visibility
catalogue pixels; no distance-to-catalogue feature, no scored-raster input. **HOLDOUT-DTI**
(`gems57-pooled-hide-v2`, 11,321 withheld px): E1 **0.1369 [0.1158, 0.1577]** vs the exactly-reproduced
fold-fair H33-analogue control 0.0939 [0.0813, 0.1076] (paired Δ +0.0430 [0.0230, 0.0627]); ablations
E2 (unweighted) 0.1364, E3 (no scarp family) 0.1211 — so the gain is the supervised physical stack,
not the weighting, on this instrument. Canaries 41/41 ≤ 0.6105. Uniqueness (85-raster accessible scan):
surface ρ ≤ 0.2089, dots ρ ≤ 0.0573, worst mutual overlap 0.504 (vs champion 0.217); literal one-way
forward overlap exceeds 0.70 only vs dense/union rasters (IR-73-12, printed in the run card).
File: `docs/downloads/gems73-h73-7-hardfault-pu-e1-37654dots-20261021.tif`
(sha256 `a0e4b3f31cb84270b10d19fff8399412a0850f3cffeb77d59b553c7ff0475d67`).
**Download: yes. Submit: selector decision** — the holdout's truth is catalogue segments, so transfer
to the expert hidden set is unproven (sibling supervised lanes live-scored 0.0286–0.2478 OWNER-REPORT);
no live score is claimed. Lane page: `docs/h73-7-hardfault.html` · run card:
`evidence/run_card_h73-7.json` · preregistration: `registry/preregistration_h73-7.json` ·
hypotheses: `docs/research/hypotheses_h73-7.md`. Weekly slots spent by this repo: 0.
