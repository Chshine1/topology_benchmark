"""Morphism models live in ``models``; generators live in ``generator``.

This module re-exports the first-class boundary quotient for a convenient domain API.
"""

from topology_benchmark.domains.surfaces.models import (
    BoundaryGluingMorphism,
    EdgeIdentification,
    PolygonAttachmentMorphism,
)

__all__ = ["BoundaryGluingMorphism", "EdgeIdentification", "PolygonAttachmentMorphism"]
