"""Competition grid constants (verified 2026-10-21 from GEMSDOE32 shipped file)."""
from affine import Affine

WIDTH, HEIGHT = 3292, 3730
CRS = "EPSG:32611"
TRANSFORM_TUPLE = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
TRANSFORM = Affine(*TRANSFORM_TUPLE)

