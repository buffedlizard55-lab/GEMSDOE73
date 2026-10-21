"""Holdout access — thin delegate to the shared vendor evaluator.

Session-2 fix (IR-73-11): the previous revision returned hard-coded
"synthetic-demo" numbers (mean DTI 0.1112) whenever ``data/`` was absent.
Hard-coded scores are indistinguishable from measurements downstream and
were cited as HOLDOUT-DTI in ``evidence/run_card.json``. They are removed.
There is exactly one evaluator in this repo — the shared
``vendor/gems57/evaluate_holdout.py`` (``gems57-pooled-hide-v2``) — per
parallel-run protocol rule 2 ("never keep a private fork"). The runnable
entry points are ``scripts/run_experiments.py`` (session-1 H73-1) and
``scripts/run_experiments_x.py`` (session-2 H73-6), which restore hash-pinned
data into ``.cache/gems_data`` and call the vendor code directly.
"""
from __future__ import annotations

EVALUATOR_VERSION = "gems57-pooled-hide-v2"
ALPHA, BETA, R_PX = 0.2, 0.8, 3.0


def evaluate_holdout(prediction_path: str, data_dir: str = ".cache/gems_data") -> dict:
    """Delegate to the vendor evaluator; fail loudly if unavailable.

    Returns the vendor pooled summary for a single candidate against the
    fold-fair controls only when the full experiment scripts are used; this
    helper intentionally does not fabricate a number for a lone file,
    because the preregistered instrument requires fold-fair re-emission
    (a static B2-pruned file scores ~0 against catalogue truth by design).
    """
    raise NotImplementedError(
        "Use scripts/run_experiments_x.py (H73-6) or scripts/run_experiments.py "
        "(H73-1): the preregistered instrument is fold-fair hide-and-recover "
        f"({EVALUATOR_VERSION}) and cannot score a lone static file. "
        "No synthetic fallback numbers are provided (IR-73-11)."
    )
