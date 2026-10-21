"""Unified re-export of shared ``vendor.gems57.evaluate_holdout`` (Rule 2: Reuse, Don't Rebuild)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57.evaluate_holdout import VERSION, evaluate, from_terms, implementation_hashes, pooled_summary  # noqa: E402

EVALUATOR_VERSION = VERSION
ALPHA, BETA, R_PX = 0.2, 0.8, 3.0


def evaluate_holdout(prediction_path: str, data_dir: str = "data") -> dict:
    raise NotImplementedError(
        f"Use scripts/run_gems73_experiments.py for fold-fair pooled hide-and-recover ({EVALUATOR_VERSION}); "
        "no synthetic fallback scores are fabricated."
    )


__all__ = [
    "ALPHA",
    "BETA",
    "EVALUATOR_VERSION",
    "R_PX",
    "VERSION",
    "evaluate",
    "evaluate_holdout",
    "from_terms",
    "implementation_hashes",
    "pooled_summary",
]
