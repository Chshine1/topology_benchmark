# Torus-slice domain

## Object and observation

Each component starts with a round embedded circle in `R^3`, specified internally by a center,
unit plane normal, and major radius. A positive tube radius smaller than the major radius turns the
circle into a rigid round torus. A family is accepted only after a conservative lower bound on every
pair of core-circle distances exceeds the sum of the corresponding tube radii.

The observed value is a `TorusSliceObservation`: the hidden family, a unit height direction, and a
strictly increasing finite list of heights. The renderer intersects the union with each plane
`<x, height_direction> = h` and shows the resulting curves as aligned panels. It deliberately omits
the core circles, all parameters, equations, component colors, and any 3D overview.

## Construction families

- A one- through four-component unlink made from separated coplanar circles.
- One Hopf-linked pair, optionally accompanied by separated unlinked components.
- Two mutually separated Hopf-linked pairs in a four-component family.

A common rigid motion prevents the panels from reducing to a fixed collection of canned axis-
aligned pictures. Top and bottom empty sections make births and deaths of section components
visible.

## Exact answers

For two round circles, linking is computed as the oriented intersection number of the second circle
with the planar disk bounded by the first. Plane/circle intersections reduce to a trigonometric
linear equation, after which only crossings inside the disk contribute. The benchmark can therefore
answer whether a pair is linked and count linked pairs without solving from its own rendered image.

Difficulty currently controls family size, section count, and question family:

| Difficulty | Typical questions |
| --- | --- |
| 1–2 | Number of hidden tori |
| 3–5 | Torus count or linking of two cores |
| 6–7 | Complete unlink or number of linked pairs |
| 8–10 | Linked-pair count in families of up to four tori |

The `torus-slices-v1` profile intentionally treats the diagrams as visual evidence. It does not
provide exact plane-curve equations, perform symbolic reconstruction, or enumerate all algebraic
families compatible with insufficient slices. Those are natural future question families once an
ambiguity certificate is added.
