# GEMSDOE73 — A Fault-Discovery System for the DOE GEMS Prize

> **Prompt (read every session).** The goal is to place top of the leaderboard in the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — a competition to find geothermal-indicative faults missing from the USGS/INGENIOUS catalogue in the GeoDAWN NW Nevada region. We must generate a **unique, portal-safe single-band GeoTIFF** (`float32`, `EPSG:32611`, `100 m`, `3292×3730`, values in `[0,1]`, no nodata sentinel) that is trivially downloadable and submittable, with its download/submit status obvious. Follow the PARALLEL-RUN PROTOCOL: one lane per session; reuse the shared vendor evaluator/writer (never fork); holdout = fold-fair hide-and-recover (α=0.2, β=0.8, 300 m triangular kernel); label every number HOLDOUT-DTI (evaluator, withheld N, 95% CI) or ORGANIZER-CONFIRMED (receipt) — projections are never scores; leakage canary AUC ≤ 0.90 per feature; end with a JSON run card; stop after 3 experiments; never spend a weekly slot from inside a lane (promotion is a selector step). Work line-by-line, verify every number against an official trusted source, provide links for manual review, flag irregularities, and never hallucinate.

## Core Values

**Maximize P(Win)** — every weekly submission slot is an experiment, not a lottery ticket. We weigh tradeoffs, assess risk, and choose the path that maximizes probability of winning.

**Own the Outcome** — we own results end-to-end, not just our slice. We treat failure and success as signals and act without waiting for permission.

## ⭐ Session-2 status (2026-10-21) — read this first

**New unique TIF generated:** `docs/downloads/gems73-h73-6-traceloc-x1-37654dots-20261021.tif`
(sha256 `2e6098900c9f7be25a8c2074bb24297c89947ed4dc0d79cf5931a1ab84946554`, 37,654 dots).
**OK to download: YES. Recommended to submit: NO — verdict NEGATIVE.**
Lane H73-6 (trace-localised, independently-corroborated scarps; 3 preregistered experiments
X1/X2/X3) scored HOLDOUT-DTI (`gems57-pooled-hide-v2`, 11,321 withheld px) X1 **0.0592**
[0.0490, 0.0700] vs fold-fair H33-analogue control **0.0939** [0.0813, 0.1076] — better than
session-1 (0.0548) and random (0.0484), but it fails the promotion gate, so **no file in this
repo is currently submit-recommended** and 0 weekly slots were spent. Full detail:
`docs/h73-6-traceloc.html` · run card `evidence/run_card_x.json` · hypotheses
`docs/research/hypotheses_x.md` · preregistration `registry/preregistration_x.json`.

Two session-2 corrections every future session must know (see `docs/irregularities.md`):
**IR-73-10** — the old site promoted the synthetic H73-A file as "PRIMARY"; retracted.
**IR-73-11** — `src/gems73/holdout.py` previously returned hard-coded synthetic holdout
numbers; removed. The hydrothermal-corridor file has **no trustworthy score; do not submit it.**

## Quick Start — Download (one click)

**👉 [GitHub Pages site](https://buffedlizard55-lab.github.io/GEMSDOE73/) — the download button and
per-file ⬇/🚫 gate table are at the very top.** The [executive summary](docs/executive-summary.html)
gives exact DrivenData steps, the unique name + ≤140-char Note to paste, and the
"Predicted values must be in range [0, 1]" fix (all files: all-finite, `nodata=None`, re-read-verified).

| File | Download? | Submit? |
|---|---|---|
| `gems73-h73-6-traceloc-x1-37654dots-20261021.tif` (session-2) | ✅ YES | 🚫 NO (NEGATIVE 0.0592 vs 0.0939) |
| `gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif` (session-1) | ✅ YES | 🚫 NO (NEGATIVE 0.0548 vs 0.0939) |
| `gems73-h73a-blind-stepover-…-zeros.tif` (synthetic) | ⚠️ review only | 🚫 NO (no real holdout) |
| `gems73-hydro-permeability-corridor-…-zeros.tif` (synthetic-demo) | ⚠️ review only | 🚫 NO (score void, IR-73-11) |

Submission name / Note for the session-2 file (only if a selector overrides):
`gems73-h73-6-traceloc-x1-37654dots-20261021` /
`G73 H73-6 X1 traceloc NMS+UK/grav witness 37654 dots; HOLDOUT 0.0592 vs ctrl 0.0939 NEGATIVE` (92/140).

## Why did 0.2778 win, and can we beat it? (one paragraph)

DTI pays for credit density (`k > 0.2·DTI ≈ 0.056` per non-redundant dot). The champion
`h33-h33-2-b2` (0.2778, **OWNER-REPORT** — no receipt in any repo, IR-73-02) is byte-verified
`D2.8 ⊂ H19-5` minus every dot ≤200 m from the catalogue: an expert-like scarp/openness field,
dotted to ≈2.5 px spacing, with zero-credit catalogue mass deleted. Emission gains are
exhausted; beating it needs a *field* with higher credit density. Neither H73-1 nor H73-6 is
that field on the fold-fair instrument. Current leader 0.4413 (ORGANIZER-CONFIRMED read
2026-10-21) needs ≈+60% credit density over H33 — not claimed reachable here. Next best bet:
H73-8 absolute-elevation bench rejection (USGS 3DEP 1 m DEMs, needs unrestricted machine).

## What This Repo Does

1. **Metric** — exact DTI(α=0.2, β=0.8, R=300 m), worked example `3.00/1.89/2.00 → 0.60` in tests.
2. **Holdout** — shared vendor `gems57-pooled-hide-v2`: whole-component hide-and-recover,
   fold-fair emission, pixel-exact visible masking, pooled DTI + paired bootstrap CIs.
3. **Writer/validator** — vendor fail-closed writer; every TIF re-read from disk
   (all 12,279,160 cells finite in [0,1], CRS/shape/transform = sample).
4. **Hypotheses** — session-1 H73-1…5 (`docs/research/hypotheses.md`) + session-2 H73-6…10
   (`docs/research/hypotheses_x.md`), each with layers, signature, off-catalogue rationale,
   named mimic, ranking by expected gain vs cost.

## Limitations & What We Need

- **Data placement — SOLVED, no login used:** `python scripts/restore_data.py --group all`
  restores 23 files from owner GitHub mirrors into `.cache/gems_data/`, SHA-256-verified
  (receipt `data/restore_receipt.json`). Hashes prove mirror consistency, **not** organiser
  authentication. Originals: https://www.drivendata.org/competitions/306/competition-doe-gems/data/ (login).
- **Sandbox egress = github/pypi only** → USGS 3DEP/GeoDAWN originals and Dropbox mirrors
  cannot be fetched here; H73-8 must run on an unrestricted machine. No GPU needed (CPU only).
- **Holdout ≠ leaderboard:** catalogue hide-and-recover is a slot-saving screen; static
  catalogue DTI anti-ranks live scores (Spearman −0.49). Only organiser receipts are scores.
- **External data:** free + share-licensed only (USGS 3DEP/GeoDAWN/SGMC, GDR, INGENIOUS, ComCat) — see `docs/sources.html`.

## How to Regenerate / Verify (no manual input)

```bash
pip install -r requirements.txt
python scripts/restore_data.py --group all          # 23 files, hash-verified
python scripts/run_experiments_x.py                 # H73-6 X1/X2/X3 + controls (~2 min)
python scripts/build_submission_x.py                # vendor writer (fail-closed)
python scripts/check_submission_x.py                # independent re-read validator
python scripts/validate_tif.py docs/downloads/gems73-h73-6-traceloc-x1-37654dots-20261021.tif
python -m pytest tests/ -q                          # 13 passed
python scripts/build_site_x.py                      # rebuild index/executive/lane pages
```

## Verify No Hallucinations (line-by-line, official sources)

- Problem + metric + format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (re-fetched 2026-10-21)
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ (#1 0.4413, #2 0.3904, #3 0.3894 on 2026-10-21; `evidence/leaderboard_snapshot.json`)
- About/resources: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7
- INGENIOUS: https://gbcge.org/current-projects/ingenious/ · GDR 1391: https://gdr.openei.org/submissions/1391
- EPSG:32611: https://epsg.io/32611 · Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Full table with fetch status + SHA-256 pins: `docs/sources.html`; all defects: `docs/irregularities.md` (IR-73-01…14).

## Repository Layout

```
docs/               # GitHub Pages site (index, executive-summary, lane pages, research, sources, irregularities)
docs/downloads/     # Submission GeoTIFFs + ZIPs + receipts/run cards
src/gems73/         # Library: grid, metric, emit, surface (H73-1), surface_x (H73-6), submission, holdout delegate
vendor/gems57/      # Shared template code, used verbatim (evaluator, folds, writer, validator)
scripts/            # restore_data, run_experiments(_x), build/check submission(_x), build_site(_x), validators
registry/           # data_manifest (sha pins), preregistrations, run cards, leaderboard snapshots
evidence/           # holdout/canary/uniqueness/validator JSON per lane (suffix _x = session-2)
tests/              # 13 tests: metric identities, writer [0,1] bytes, emission, holdout honesty
```

## Lane history

- **H73-6 session-2 (this lane)** — verdict NEGATIVE, see ⭐ section above.
- **H73-1 session-1 (PR #3)** — piedmont micro-scarp chain, verdict NEGATIVE
  (0.0548 vs 0.0939; file sha256 `d09dca24…`; `docs/h73-1-piedmont.html`).
- **H73-A / hydrothermal (pre-PR#3 mains)** — synthetic generators, no real holdout,
  promotion retracted (IR-73-10/11). Retained for provenance; **do not submit.**

## License & Disclosure

Code MIT. External data retains its original license. No organiser authentication is
misrepresented; no score is claimed without a receipt; negative results are deliverables.
