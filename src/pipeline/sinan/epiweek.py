"""Re-export the shared Sunday-anchored epi-week helper.

Kept so existing imports (`src.pipeline.sinan.epiweek`) and the SINAN README
keep working; the canonical definition lives in `src.pipeline.epiweek`.
"""

from __future__ import annotations

from ..epiweek import floor_to_sunday

__all__ = ["floor_to_sunday"]
