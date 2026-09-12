from typing import ClassVar

from attrs import field, frozen

from topology_benchmark.core.validation import nonempty

from .object import EdgeGluing, SurfacePresentation


@frozen
class BoundaryGluingMorphism:
    source: SurfacePresentation
    target: SurfacePresentation
    identifications: tuple[EdgeGluing, ...] = field(
        validator=nonempty("a boundary gluing needs at least one identification")
    )
    family: str = "boundary-quotient"

    name: ClassVar[str] = "boundary-gluing-quotient"

    def __attrs_post_init__(self) -> None:
        available = set(self.source.unglued_edges)
        additions = {
            edge for gluing in self.identifications for edge in (gluing.first, gluing.second)
        }
        if len(additions) != 2 * len(self.identifications) or not additions <= available:
            raise ValueError("a boundary gluing must pair distinct unglued source edges")
        if (
            self.target.polygons != self.source.polygons
            or self.target.paths != self.source.paths
            or set(self.target.gluings) != {*self.source.gluings, *self.identifications}
        ):
            raise ValueError("target is not the quotient specified by the identifications")


@frozen
class PolygonAttachmentMorphism:
    """``attachment`` pairs a source side first and a side of ``new_polygon`` second."""

    source: SurfacePresentation
    target: SurfacePresentation
    attachment: EdgeGluing
    new_polygon: int
    family: str = "attachment"

    name: ClassVar[str] = "polygon-attachment-inclusion"

    def __attrs_post_init__(self) -> None:
        if self.new_polygon != len(self.source.polygons):
            raise ValueError("the attached polygon must be new")
        if self.attachment.first not in self.source.unglued_edges:
            raise ValueError("an attachment must use an unglued source edge")
        if self.attachment.second.polygon != self.new_polygon:
            raise ValueError("attachment must use a side of the new polygon")
        if (
            self.target.polygons[:-1] != self.source.polygons
            or self.target.paths != self.source.paths
            or set(self.target.gluings) != {*self.source.gluings, self.attachment}
        ):
            raise ValueError("target is not the declared polygon attachment")


type SurfaceMorphism = BoundaryGluingMorphism | PolygonAttachmentMorphism
