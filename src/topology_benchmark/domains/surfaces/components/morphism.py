"""Morphism models live in ``models``; generators live in ``generator``.

This module re-exports the first-class boundary quotient for a convenient domain API.
"""

from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    EdgeGluing,
    PolygonAttachmentMorphism,
)

__all__ = [
    "BoundaryGluingMorphism",
    "EdgeGluing",
    "PolygonAttachmentMorphism",
]
