# Torus-slice domain

## Object and observation

Each component starts with a round planar core circle in `R^3`. An ellipse in the normal-radial
profile plane is swept around that circle to produce an `EllipticTorus`; its two semiaxes and profile
angle are sampled independently. `RoundTorus` remains available as the equal-semiaxis special case.
A family is accepted only after a conservative lower bound on every pair of core-circle distances
exceeds the maximum radial reach of the corresponding profiles.

The observed value is a `TorusSliceObservation`: the hidden family, a unit height direction, and a
strictly increasing finite list of heights. The renderer intersects the union with each plane
`<x, height_direction> = h` and shows the resulting curves as aligned panels. It deliberately omits
the core circles, all parameters, equations, component colors, and any 3D overview.

## Construction families

- A one- through four-component unlink made from separated coplanar ellipses.
- One Hopf-linked pair, optionally accompanied by separated unlinked components.
- Two mutually separated Hopf-linked pairs in a four-component family.
- A connected three- or four-component Hopf chain in which every consecutive pair is linked.
- Complete three- and four-component Hopf links in which every pair is linked.

A common rigid motion prevents the panels from reducing to canned axis-aligned pictures. Independent
profile eccentricities and angles break the overly regular section shapes of circular-profile tori.
Complete links are generated as stereographic images of distinct Hopf fibers, then randomized and
certified; this supplies linking graphs `K3` and `K4` in addition to matchings and paths. Top and
bottom empty sections still make births and deaths of section components visible.

## Exact answers

For two core circles, linking is computed as the oriented intersection number of the second core
with the planar disk bounded by the first. Plane/circle intersections reduce to a trigonometric
linear equation, after which only crossings inside the disk contribute. The benchmark can therefore
answer linking questions without solving from its own rendered image.

Difficulty controls family size, section count, construction, and question family:

| Difficulty | Typical questions |
| --- | --- |
| 1–2 | Number of hidden tori |
| 3–5 | Torus count or linking of two cores |
| 6–7 | Complete unlink or number of linked pairs |
| 8 | Linked-pair count in families of up to four tori |
| 9–10 | Path, matching, and complete-link graphs with up to four components |

The `torus-slices-v2` profile intentionally treats the diagrams as visual evidence. It does not
provide exact plane-curve equations, perform symbolic reconstruction, or enumerate all algebraic
families compatible with insufficient slices. Ambient-isotopy comparison remains a natural future
question family, but should be added with an explicit morphism model and an ambiguity certificate
rather than as an always-true deformation question.

Shuffled-panel ordering and omitted-level reconstruction are not scored question families. Height
reflection and alternative interpolations make ordering ambiguous, while labelled equal spacing
reduces missingness to arithmetic. A future version should add either certified candidate
possibility or a partial order with a uniquely checked completion, and should expose metric data only
after its contribution to identifiability is made explicit.
