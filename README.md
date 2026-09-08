# Topology Benchmark

`topology_benchmark` generates reproducible visual problems about compact surfaces presented by
polygon gluings. The domain model contains only combinatorial mathematical data:

```text
SurfacePresentation
├── polygons     names and side counts for topological discs
├── gluings     disjoint pairs of complete polygon sides
└── paths        directed side sequences, continuous in the quotient
```

There are no coordinates, colors, curves, stored genera, or preselected classification recipes
in a surface. The analyzer derives quotient vertices, connected components, Euler characteristic,
boundary circles, orientability, genus, and integral cellular homology from the gluing data.

## Quick start

The project uses Python 3.14 and Pixi.

```powershell
pixi install -e dev
pixi run -e dev python -m topology_benchmark --seed 42 --difficulty 8
pixi run -e dev test
pixi run -e dev check
```

Every prompt is a vector `image/svg+xml` document. A fixed seed and difficulty reproduce the complete
problem byte for byte. Object problems contain one prompt; morphism problems contain source and
target prompts. The local viewer understands the same representation:

```powershell
pixi run -e dev python -m topology_benchmark --serve --difficulty 5
```

## Probabilistic generation

Generation is intent-first: the seeded sampler chooses an object or morphism question family,
then the surface, paths, and arrow family are sampled conditionally. This makes diagrams usually
serve the question without turning alignment into a hard rule. By default, incidental paths and
target-only questions about a displayed morphism remain as 7.5% noise.

Named random streams isolate decisions, so adding an unrelated sampling step does not perturb
existing choices. Reproducibility is stable within a `profile_version`; intentionally changing a
profile's semantics should also change that version. Problems expose a compact sampling trace and
complexity counts in their metadata for cohort audits.

Defaults live in `domains/surfaces/generation.yaml`. Difficulty values at anchors 1, 4, 7, and 10
are linearly interpolated. The profile controls subject and question weights, polygon count, side
and path-length continuation probabilities, gluing density, visual budget, morphism families, and
question-to-family affinities. The latter are preferences, not exclusions. Path lengths use a
truncated geometric distribution and full two-disc sphere quotients become rare as difficulty
increases. Display-safety caps remain four polygons, eight sides per polygon, and seven path
segments.

As with rendering, an override YAML is recursively layered over the defaults:

```python
from topology_benchmark import build_container

container = build_container(generation_config="my-generation-overrides.yaml")
```

The CLI equivalent is `--generation-config my-generation-overrides.yaml`. A small override can
change just one policy layer:

```yaml
generation:
  profile_version: "surface-v2"
  noise_probability: 0.05
  difficulty:
    morphism_probability: {1: 0.02, 4: 0.15, 7: 0.35, 10: 0.55}
```

## Polygon quotients

`Polygon(name, sides)` represents a topological disc with cyclically ordered sides.
`EdgeGluing(first, second, label, same_direction)` identifies two whole sides. Validation ensures
that every side occurs in at most one gluing and every label is unique. Unglued sides form the
surface boundary. A presentation may contain any finite number of polygons and may be disconnected.

Pairing complete sides at most once gives the expected two-dimensional neighborhoods away from
vertices, but arbitrary pairings can still create a singular quotient vertex. The analyzer checks
each vertex link and accepts it only when the link is a circle or interval. This is what makes the
subsequent surface classification valid.

For a valid quotient it computes

```text
χ = (# quotient vertices) - (# quotient edges) + (# polygons).
```

Boundary components are connected cycles of unglued quotient edges. Polygon-orientation
constraints across glued edges determine orientability. Euler characteristic, boundary count, and
orientability then determine the genus of each connected component.

## Paths and homology

A `SurfacePath` is a nonempty sequence of `OrientedEdge` values. Consecutive edges must meet at the
same quotient vertex, although their original polygon vertices need not agree. A path is a cycle
exactly when its final quotient vertex equals its initial quotient vertex.

The cellular analyzer constructs `C2 -> C1 -> C0` directly. A spanning forest of the quotient
1-skeleton gives an explicit fundamental-cycle basis for `ker(d1)`. Polygon boundaries become
integer relation vectors in that basis. Integer row and column operations compute a Smith normal
form (cross-checked by determinantal divisors),
so `CellularHomology` exposes:

- the quotient-edge and cycle bases;
- the polygon-boundary relation vectors;
- the Smith diagonal;
- a Smith basis and the integer coordinate transformation into it;
- ranks and torsion for `H0`, `H1`, and `H2`.

A cyclic path is converted to coordinates in the same cycle basis, modulo those displayed
relations. Consequently the answer retains enough information to identify the class even when the
Smith basis is not unique.

## Vector rendering

`MatplotlibGluingDiagramRenderer` lays out regular polygons at render time and emits deterministic
SVG. Its visual randomness is seeded from the generation request and never enters the domain
object. It provides the requested conventions:

- matching words and arrows mark glued sides;
- every regular polygon uses the same side length, independent of its number of sides;
- glued sides belonging to different polygons are dotted;
- unglued boundary sides remain solid, so dotted cross-polygon identifications stay distinctive;
- a path edge may be displayed on either member of its glued pair;
- dynamic programming selects a lift maximizing consecutive sides on the same polygon, with
  seeded tie-breaking when the lift is non-unique;
- each maximal lifted run is replaced by a chord, while a one-side run curves outward;
- overlapping interior segments use symmetric curvature lanes, while overlapping edge segments
  use distinct outward curvature lanes;
- polygon-local closed runs are expanded into their directed boundary-edge arcs instead of being
  replaced by misleading interior circles;
- paths are thinner than polygon edges and receive typed, seeded display styles: numbered tags or
  one, two, three, ... arrowheads record segment order.

Rendering defaults are organized in `domains/surfaces/rendering.yaml` under `canvas`, `geometry`,
`stroke`, `arrows`, `labels`, and `palettes`. A custom YAML file may override only the values it
needs; omitted values inherit the defaults. The composition root validates the merged settings and
injects the same immutable configuration into the planner and renderer:

```python
from topology_benchmark import build_container

container = build_container("my-rendering-overrides.yaml")
```

The same override can be passed to the CLI or local viewer with
`--rendering-config my-rendering-overrides.yaml`.

For example, a small override can enlarge polygons and further lighten paths:

```yaml
rendering:
  geometry:
    side_length: 140
  stroke:
    path_width: 1.2
  labels:
    tag_offset: 28
```

## Morphisms

`BoundaryGluingMorphism` is a quotient obtained by adding pairings between previously unglued
sides. `PolygonAttachmentMorphism` includes a surface after attaching a new polygon along one side.
Both retain source, target, and construction data, and validate that the declared target is exact.

Questions cover surface classification, integral homology, path cycle/class calculations, changes
under morphisms, and elementary properties of the generated maps.
