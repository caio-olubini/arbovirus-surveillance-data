"""ERA5 climate pipeline: Zenodo + ARCO → UF × epidemiological-week features."""

from __future__ import annotations

from .transform import ClimateTransformResult, transform

__all__ = ["ClimateTransformResult", "transform"]
