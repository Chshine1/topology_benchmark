from dataclasses import dataclass

from .object import EdgeGluing, SurfacePresentation


@dataclass(frozen=True, slots=True)
class BoundaryGluingMorphism:
    source: SurfacePresentation
    target: SurfacePresentation
    identifications: tuple[EdgeGluing, ...]
    family: str = "boundary-quotient"

    @property
    def name(self) -> str:
        return "boundary-gluing-quotient"

    def __post_init__(self) -> None:
        if not self.identifications:
            raise ValueError("a boundary gluing needs at least one identification")
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


@dataclass(frozen=True, slots=True)
class PolygonAttachmentMorphism:
    source: SurfacePresentation
    target: SurfacePresentation
    attachment: EdgeGluing
    new_polygon: int
    family: str = "attachment"

    @property
    def name(self) -> str:
        return "polygon-attachment-inclusion"

    @property
    def identifications(self) -> tuple[EdgeGluing, ...]:
        return (self.attachment,)

    def __post_init__(self) -> None:
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
