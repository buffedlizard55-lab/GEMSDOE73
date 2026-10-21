# GEMSDOE73 — A Fault-Discovery System for the DOE GEMS Prize

> **Prompt (read every session).** The goal is to place top of the leaderboard in the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — a competition to find geothermal-indicative faults missing from the USGS/INGENIOUS catalogue in the GeoDAWN NW Nevada region. We must generate a **unique, portal-safe single-band GeoTIFF** (`float32`, `EPSG:32611`, `100 m`, `3292×3730`, values in `[0,1]`, no nodata sentinel) that is trivially downloadable and submittable. Work line-by-line, verify every number against an official trusted source, provide links for manual review, flag irregularities, and never hallucinate.

## Core Values

**Maximize P(Win)** — every weekly submission slot is an experiment, not a lottery ticket. We weigh tradeoffs, assess risk, and choose the path that maximizes probability of winning.

**Own the Outcome** — we own results end-to-end, not just our slice. We treat failure and success as signals and act without waiting for permission.

## Quick Start — Download the Submission

**👉 Go to the [GitHub Pages site](https://buffedlizard55-lab.github.io/GEMSDOE73/) and click “Download the submission GeoTIFF”.** The executive summary at the top of the site explains exactly how to submit to DrivenData.

- Primary file: `docs/downloads/gems73-h73a-blind-stepover-20261020T230000Z-7f3c2a9e-zeros.tif` — all-finite, `0.0–1.0`, no nodata tag, `EPSG:32611`, `3292×3730`.
- Also available as `.zip` (single GeoTIFF inside) and as `-nan.tif` twin (identical values inside footprint, `NaN` outside).
- Each file ships a `checks-*.json` receipt produced by re-reading the written bytes.

## What This Repo Does

1. **Metric re-implementation** — exact distance-weighted Tversky `DTI(α=0.2, β=0.8, R=300 m)` with triangular kernel, verified against the published worked example `TP=3.00 FP=1.89 FN=2.00 → 0.60`.
2. **Spatially-blocked holdout** — hide-and-recover on whole fault segments with a buffer; catalogue-derived features only from visible faults; pixel-exact masking; pooled DTI scoring.
3. **Submission writer** — strict format validator (CRS/shape/transform match, `[0,1]` range, no sentinel) and both `zeros` (portal-safe) and `nan` (spec) variants.
4. **Hypothesis ranking** — 5 new geological hypotheses, each naming layer(s), physical signature, why it catches a fault absent from the catalogue, and how it differs from prior art.

## Limitations & What We Need

- **No DrivenData auth in this sandbox** — `training_features.tif`, `labels.tif`, `sample_submission.tif`, `1m_DEM_links.csv` cannot be auto-downloaded from `https://www.drivendata.org/competitions/306/competition-doe-gems/data/` (login wall → `302` to login). Run `bash scripts/download_competition_data.sh` on an unrestricted machine into `data/`, then `python scripts/prepare_data.py` to build the feature stack. After that `make train && make validate` works (GPU for training, CPU for metric/validation).
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
python scripts/generate_submission.py --hypothesis h73a --budget 42000 --seed 73
python scripts/validate_submission.py docs/downloads/gems73-*.tif --template data/sample_submission.tif --strict-finite
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
