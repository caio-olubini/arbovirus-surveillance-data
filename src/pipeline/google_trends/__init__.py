"""Google Trends transforms: weekly search + monthly related topics/queries."""

from __future__ import annotations

from .related_transform import GTrendsRelatedTransformResult, transform_related
from .transform import GTrendsTransformResult, transform

__all__ = [
    "GTrendsTransformResult",
    "GTrendsRelatedTransformResult",
    "transform",
    "transform_related",
]
