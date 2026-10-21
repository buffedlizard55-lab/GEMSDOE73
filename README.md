# GEMSDOE73 — H73-1 piedmont micro-scarp chain lane

**Core Values. Maximize P(Win)** — every weekly submission slot is an experiment, not a lottery
ticket; a preregistered negative that saves a slot is a deliverable. **Own the Outcome** — the
gate failure below is published with its evidence, not buried.

## ⬇ Submission file — status first

| Gate | Status | Detail |
|---|---|---|
| **1. OK to download** | ✅ **YES** | [⬇ `gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif`](docs/downloads/gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.tif) · [.zip](docs/downloads/gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021.zip) · [run card](evidence/run_card.json) · [validator receipt](evidence/validator.json). Single-band float32, EPSG:32611, 3730×3292, 37,654 dots, **0 NaN / all values in [0,1] in all 12,279,160 cells**, sha256 `d09dca2465f784e8a07571894cd12c689e4b34e8f7c14be321b5d6006b2d2ece` — cannot trigger *"Predicted values must be in range [0, 1]"*. |
| **2. Recommended to submit** | ⛔ **NO — DO NOT SUBMIT** | **Verdict `negative`.** Failed the preregistered gate: HOLDOUT-DTI (`gems57-pooled-hide-v2`, 11,321 withheld px) E1 **0.0548 [0.0417, 0.0688]** vs fold-fair H33-analogue control **0.0939 [0.0813, 0.1076]**, paired Δ −0.0391 [−0.0571, −0.0211]. Unique submission name `gems73-h73-1-piedmont-scarpchain-e1-37654dots-20261021`; paste-ready note (125/140 chars) is in the run card — use only under a knowing human-selector override. Weekly slots spent: **0**. |

Site: `docs/index.html` (GitHub Pages from `docs/` after merge) ·
[Executive summary — exactly how to submit](docs/executive-summary.html) ·
[Five preregistered hypotheses](docs/research/hypotheses.md) ·
[Irregularities](docs/irregularities.md) · [Score ledger](registry/score_ledger.csv)

## The brief's question, answered

**Why did `h33-h33-2-b2-…-zeros` score 0.2778 (OWNER-REPORT; no receipt in any inspected repo, IR-73-02)?**
Measured here from the bytes (`evidence/forensic.json`): it is *exactly* D2.8 minus every dot within
200 m of the catalogue (44,090 − 6,436 = 37,654), and `H33 ⊂ D2.8 ⊂ H19-5` with zero exceptions.
H19-5's surface is ~90% LiDAR/DEM scarp-openness (synthesis weights 0.55 + 0.35 in
`19GEMSDOE/src/gems/hypotheses.py`) — the same evidence expert re-mapping uses to build the hidden
set. Dotting at ~2.5 px spacing removes prediction mass whose marginal kernel credit is below the
metric's break-even `k > 0.2·DTI`, and the B2 prune deletes dots that can only cover already-mapped
(masked, zero-credit) traces while paying full false-positive tax against the hidden faults.

**Can we generate a unique submission scoring higher?** This lane tested the strongest untried
counterpart hypothesis — a fully *unsupervised* piedmont micro-scarp chain detector (no catalogue
imitation, which is selection-biased against exactly the faults experts had missed). It is genuinely
unique (vs champion: 17.7% dots within 300 m, Spearman 0.004; worst mutual overlap vs 77 registry
rasters 0.390) and it beats the champion on the report-only SGMC-piedmont proxy (0.1045 vs 0.0980),
the only local proxy that ranks OWNER-REPORT live scores positively here (ρ = +0.74, n = 13, vs −0.49
for the catalogue proxy). **But it failed the preregistered primary holdout gate and is not
significantly above random on that instrument**, so the honest verdict is `negative`. Nobody in this
campaign has shown a path to the verified public leader **0.4413** (read from the official leaderboard
2026-10-21, `evidence/leaderboard_snapshot.json`) with a reweighting of existing surfaces; that gap
needs higher credit density per dot, i.e. a better field, and this repo's contribution is to rule out
one cheap candidate field cleanly and to document why.

## Lane (single method)

`S = sqrt(scarp_n · clip(1.4·chain)) · (0.55+0.45·substep) · (0.45+0.55·pied_soft)` — one-sided 1 m-LiDAR
step polarity × 16-azimuth 1.3 km straight-chain occupancy × subsurface-step witness (basement-depth
gradient / gravity slope / magnetic gradient) × soft piedmont weight (deep basement, gentle slope, low
relief); greedy dotted emission, 37,654 dots, 2.5 px spacing, >200 m from catalogue. No catalogue/SGMC
training, no distance-to-catalogue feature, no scored raster input. Named mimic: Lake Lahontan
shoreline benches / terrace risers. Experiments E1/E2/E3 (budget: 3) are frozen in
[`registry/preregistration.json`](registry/preregistration.json), written before any holdout run.

## Reproduce (line by line)

```bash
pip install -r requirements.txt
python scripts/restore_data.py --group core     --target-dir .cache/gems_data
python scripts/restore_data.py --group external --target-dir .cache/gems_data
python scripts/restore_data.py --group scored   --target-dir .cache/gems_data
python scripts/run_experiments.py      # forensic, components, canaries, holdout, proxy
python scripts/build_submission.py     # shared fail-closed writer -> docs/downloads/
python scripts/check_submission.py     # independent re-read validator ([0,1] proof)
python scripts/audit_registry.py       # uniqueness, surface + dots (needs sibling clones in ../refs layout recorded in evidence/uniqueness.json)
python scripts/calibrate_instruments.py
python scripts/build_run_card.py && python scripts/make_figures.py && python scripts/build_site.py
python -m pytest tests -q
```

Data restore uses hash-pinned owner GitHub mirrors (`registry/data_manifest.json`); the organiser
download is login-walled and sandbox egress cannot reach Dropbox/USGS — hashes prove mirror
consistency, **not** organiser authentication (IR-73-05). Shared evaluator/writer are vendored
byte-identical (`vendor/VENDOR.md`); no private fork.

## Limitations & next steps (selector / next session)

1. **Instrument problem is now the binding constraint.** Catalogue hide-and-recover anti-ranks live
   scores (ρ −0.49 here; −0.64 in GEMSDOE70 S3). Next session should preregister a *combined*
   promotion rule (fold-fair holdout + off-catalogue piedmont proxy + live-anchor ladder) **before**
   running it, rather than letting any single proxy veto or promote.
2. **The 100 m-aggregated LiDAR u8 bands are weak alone** (best single-channel AUC 0.61 withheld).
   The champion's advantage likely comes from native-scale 1 m/10 m openness features + ML mimic
   suppression. A next lane needs those cached native-scale features (present in sibling caches, not
   yet in this repo's manifest) — name and hash-pin them before use.
3. **No new external data was obtained.** The named free official sources for the queued hypotheses
   (USGS ComCat/FDSN seismicity; NGL MIDAS GNSS strain) are unreachable from this sandbox
   (egress allow-list) — verified blocked in sibling repos; fetch on an unrestricted machine.
4. **Registry scan is partial** (77 unique rasters; IR-73-07). A complete 72-repo inventory refresh
   should precede any future `promote` verdict.
5. **GitHub Pages** must be enabled (Settings → Pages → branch `main`, folder `/docs`) after merge if
   not already on; all site links are relative and were audited locally.

## Standing brief (read every session)

> Generate a **unique** TIF submission for the DOE GEMS Prize — never a copy of a previous
> submission. Stay in one preregistered lane; if rank-correlation vs any registry raster exceeds
> 0.90 or >70% of dots fall within 3 px of one registry raster's dots, log a duplicate and stop.
> Reuse the shared template (`evaluate_holdout.py`, `submission_writer.py`, cached feature stack);
> hide-and-recover holdout with whole segments withheld, catalogue features from visible faults
> only, visible faults masked pixel-exactly, pooled DTI (α 0.2, β 0.8, 300 m triangular kernel).
> Label every number HOLDOUT-DTI (evaluator, withheld n, 95% CI) or ORGANIZER-CONFIRMED (receipt).
> Single-feature AUC > 0.90 = leakage until proven otherwise. End with one JSON run card
> (hypothesis, mechanism, named mimic, holdout + CI, registry correlation/overlap, sha256,
> validator, name + ≤140-char note, verdict promote/negative). Budget: 3 experiments / 2 hours.
> Never spend a weekly slot here — promotion is a separate selector step. Competition:
> https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ·
> leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ ·
> reference: https://github.com/drivendataorg/gems-prize-reference-solution ·
> rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
