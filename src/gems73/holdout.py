"""Spatially-blocked holdout — pointer to the shared instrument.

REPAIR 2026-10-21 (H73-7 session): the previous revision returned hard-coded
"synthetic demo" numbers (mean DTI 0.1112, CI [0.0937, 0.1280]) whenever
``data/`` was absent. Those constants were quoted as HOLDOUT-DTI evidence in
``evidence/run_card.json`` (hydro-permeability lane, verdict "promote").
A function that fabricates a plausible holdout result is a leakage of trust,
not a demo: it is removed here, in the shared tool, per parallel-run
protocol rule 2 ("if a shared tool is wrong, fix it once in the template").
See IR-73-10 in ``docs/irregularities.md`` and
``evidence/run_card_hydro_addendum_2026-10-21.json``.

The real instrument (used by every measured lane in this repo) is the shared
``gems57-pooled-hide-v2`` evaluator vendored unchanged at
``vendor/gems57/evaluate_holdout.py`` with folds from
``vendor/gems57/holdout.buffered_component_draw``: whole fault components
withheld with a buffer, catalogue-based features from visible faults only,
visible faults masked pixel-exactly, pooled DTI (alpha 0.2, beta 0.8,
300 m triangular kernel). Run it via ``scripts/run_experiments.py``
(H73-1) or ``scripts/run_experiments_h73_7.py`` (H73-7) after restoring the
hash-pinned data with ``scripts/restore_data.py``.
"""
from __future__ import annotations

# Kept for import compatibility with historical code/tests. This version
# string never corresponded to a runnable evaluator in this module; measured
# results in this repo all carry evaluator_version "gems57-pooled-hide-v2".
EVALUATOR_VERSION = "gems73-holdout-DEPRECATED-use-gems57-pooled-hide-v2"
ALPHA, BETA, R_PX = 0.2, 0.8, 3.0


def evaluate_holdout(prediction_path: str, data_dir: str = "data") -> dict:
    """Refuse to invent a holdout score.

    Raises RuntimeError always: scoring requires the restored competition
    rasters and the shared vendor instrument (see module docstring). There
    is deliberately no synthetic fallback — a number without data behind it
    must never be labelable HOLDOUT-DTI.
    """
    raise RuntimeError(
        "gems73.holdout.evaluate_holdout no longer returns synthetic/demo "
        "numbers (removed 2026-10-21, IR-73-10). Restore the hash-pinned "
        "data with scripts/restore_data.py and score candidates with the "
        "shared vendor instrument gems57-pooled-hide-v2 "
        "(vendor/gems57/evaluate_holdout.py), e.g. via "
        "scripts/run_experiments_h73_7.py."
    )
