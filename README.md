# Topology Benchmark

`topology_benchmark` is a reproducible visual-problem generator for evaluating geometric and
topological reasoning. The framework separates mathematical objects, exact ground-truth analysis,
question selection, and graphic representation so that a problem is solved from its prompt rather
than from generator metadata.

The built-in domains are **compact surfaces presented by polygon-edge gluings** and **polyhedral
nets of rigid regular faces**. They generate both single-object questions and relational questions
about maps or pairs of unfoldings.

```text
seed + difficulty + profile
            |
            v
     question intent
            |
            v
 mathematical object/map ---> exact analyzer ---> ground-truth answer
            |
            v
     display planning ---> deterministic SVG prompt
```

## Current capabilities

- Seeded, difficulty-controlled generation on a scale from 1 to 10.
- Intent-first sampling: the question family is selected before a compatible instance is built.
- Object problems with one diagram and morphism problems with source and target diagrams.
- Exact surface validation and invariant computation from combinatorial data.
- Integral cellular homology, including torsion and path coordinates in explicit bases.
- Deterministic, model-ready SVG output and a local browser viewer.
- YAML profiles for generation probabilities and rendering parameters.
- Sampling traces and complexity counts for reproducibility and cohort auditing.
- Protocol-based core types that can support additional mathematical domains and media types.

Both domains are wired into the command-line application and the domain-independent viewer.

## Quick start

The project targets Python 3.14 and uses [Pixi](https://pixi.sh/) for its environment and tasks.

```powershell
pixi install -e dev
pixi run -e dev python -m topology_benchmark --seed 42 --difficulty 8
pixi run -e dev python -m topology_benchmark --domain polyhedral-nets --seed 42 --difficulty 8
pixi run -e dev test
pixi run -e dev check
```

The CLI writes one JSON-serialized `Problem` to standard output. Start the interactive local viewer
instead with:

```powershell
pixi run -e dev python -m topology_benchmark --serve --difficulty 5
```

Then open `http://127.0.0.1:8000`. The viewer can generate a new seed, replay a seed at a selected
difficulty, switch between the surface and polyhedral-net domains, show all prompts, and reveal the
exact answer. `--domain polyhedral-nets` selects the initially displayed domain but does not disable
the switch. The server also exposes:

- `GET /health`
- `GET /api/problem?domain=polyhedral-nets&seed=42&difficulty=8`

Useful CLI options are:

```text
--seed INTEGER
--difficulty {1,...,10}
--domain {surfaces,polyhedral-nets}
--serve
--host HOST
--port PORT
--generation-config PATH
--rendering-config PATH
```

## Problem contract

The cross-domain API consists of immutable dataclasses:

```python
from topology_benchmark import SurfaceBenchmark, build_container

benchmark = build_container().resolve(SurfaceBenchmark)
problem = benchmark.generate(seed=42, difficulty=8)

print(problem.question)
print(problem.answer)
print(problem.prompts[0].media_type)  # image/svg+xml in the surface domain
```

A `Problem` contains:

| Field | Meaning |
| --- | --- |
| `question` | Natural-language task shown to the answerer |
| `prompts` | One or more `PromptData` values containing media and display metadata |
| `answer` | Exact computed ground truth (`int`, `bool`, or `str` in the surface domain) |
| `seed` | Seed needed to reproduce the instance |
| `metadata` | Difficulty, intent, profile, complexity counts, and sampling trace |

`PromptData` contains a MIME `media_type`, its serialized `content`, and representation metadata.
The generic viewer knows how to display image, audio, and text prompts; the current surface renderer
always emits an inline `image/svg+xml` document.

For a fixed seed, difficulty, configuration, and `profile_version`, generation is reproducible.
Named random streams isolate decisions, so introducing an unrelated sampling step does not shift
existing choices. A deliberate semantic change to a generation profile should therefore also bump
its `profile_version`.

## Polyhedral-net domain

The v2 domain starts from a real convex `Polyhedron3D` with rational coordinates and possibly
irregular polygonal faces. It validates the closed oriented boundary and exact convex support
planes, chooses a random face-dual spanning tree, develops the faces into the plane, and rejects
overlapping layouts. `PolyhedralFolding` keeps the source and closing seams away from the renderer.

Before emitting a question, the analyzer enumerates every equal-length boundary pairing compatible
with the visible hints. It retains pairings that form a spherical manifold with positive angular
defect. An ordinary question is emitted only when every retained completion gives the same answer;
hard extrinsic questions require a unique completion. If necessary, the generator reveals a small
number of true seam pairs as matching colored dots until this condition holds.

Questions use sparse labels and ask for spatial relations: which edges or corners coincide, whether
two non-adjacent planar faces meet after folding, how many faces meet at a vertex, which marked
vertex has greater discrete curvature, and—after anchoring a base face—which marked vertex is
highest. At the highest difficulties, two independently developed nets may also be compared for
intrinsic isometry after each completion is certified unique. Faces are drawn to scale, but
source-family names, hidden seams, completion counts, and answer-derived geometry are not exposed
in metadata. Legacy regular-face models remain available for direct API callers and regression
tests.

## Surface domain

### Combinatorial model

The mathematical object deliberately contains no rendering coordinates, colors, curves, cached
genus, or preselected solution recipe:

```text
SurfacePresentation
|-- polygons     names and side counts for topological discs
|-- gluings      disjoint pairs of complete polygon sides
`-- paths        directed side sequences, continuous in the quotient
```

`Polygon(name, sides)` is a topological disc with cyclically ordered sides. An `EdgeGluing` pairs
two complete sides and records whether their native directions agree. Each side may participate in
at most one gluing, and gluing labels are unique. Unglued sides form the boundary. Presentations may
contain several polygons and may be disconnected.

Arbitrary edge pairings can create a singular quotient vertex. `SurfaceAnalyzer` constructs each
vertex link and requires it to be a circle or interval before applying surface classification. The
random generators retry invalid candidates and use a simple valid fallback if their retry budget is
exhausted.

For a valid quotient the analyzer derives quotient vertices and edges, connected components,
boundary circles, orientability, and genus. In particular,

```text
chi = (# quotient vertices) - (# quotient edges) + (# polygons).
```

### Questions

The current question catalog is:

| Subject | Family | Question kinds |
| --- | --- | --- |
| Surface | Global | Euler characteristic; boundary-component count; connected-component count |
| Surface | Classification | orientability; integral `H_0`, `H_1`, and `H_2` |
| Surface | Path | whether a displayed path is a cycle; its cellular/Smith representative |
| Morphism | Relational | changes in Euler characteristic, boundary count, or component count; injectivity; surjectivity; homology isomorphism |
| Morphism | Target-only noise | target homology; target orientability |

Morphism problems currently use two first-class arrow types:

- `BoundaryGluingMorphism`: a quotient formed by pairing previously unglued source sides.
- `PolygonAttachmentMorphism`: an inclusion formed by attaching one new polygon along a source side.

The generator realizes these through five instance families: full disk-boundary gluing, polygon
attachment, partial inter-component gluing, self-boundary gluing, and annulus closure. Each morphism
retains its exact source, target, and construction data and validates that the declared target is the
one specified by that construction.

### Paths and integral homology

A `SurfacePath` is a nonempty sequence of oriented polygon sides. Consecutive sides must meet at the
same quotient vertex even when their original polygon vertices differ. It is a cycle precisely when
its final quotient vertex equals its initial one.

The analyzer constructs the cellular chain complex `C2 -> C1 -> C0`. A spanning forest of the
quotient 1-skeleton gives an explicit fundamental-cycle basis for `ker(d1)`, and polygon boundaries
become integer relation vectors in that basis. Integer row and column operations compute a Smith
normal form, cross-checked using determinantal divisors. The result exposes:

- quotient-edge and cycle bases;
- polygon-boundary relation vectors;
- the Smith diagonal and a corresponding Smith basis;
- the integer coordinate transformation into that basis;
- ranks and torsion for `H0`, `H1`, and `H2`.

A cyclic displayed path is converted to coordinates in the same basis and reduced by the same
relations. The answer includes the bases and coordinates because a Smith basis need not be unique.

## Generation profiles

Defaults live in
`src/topology_benchmark/domains/surfaces/generation.yaml`. Values specified at difficulty anchors
1, 4, 7, and 10 are linearly interpolated. The profile controls:

- object-versus-morphism probability and question-family weights;
- polygon counts, side-count continuation, and gluing density;
- path-length continuation and visual complexity budgets;
- morphism-family weights and question-to-family affinities;
- rare intentional noise and retry limits.

Affinities are preferences rather than exclusions. By default, incidental paths and target-only
questions about a displayed morphism each occur at a low 7.5% noise rate. Path lengths follow a
truncated geometric distribution, and simple two-disc sphere quotients become rare at high
difficulty. Current display-safety caps are four polygons, eight sides per polygon, and seven total
path segments.

An override YAML is recursively layered over the defaults, so it only needs to contain changed
values:

```yaml
generation:
  profile_version: "surface-v2"
  noise_probability: 0.05
  difficulty:
    morphism_probability: {1: 0.02, 4: 0.15, 7: 0.35, 10: 0.55}
```

Use it from Python or the CLI:

```python
container = build_container(generation_config="my-generation-overrides.yaml")
```

```powershell
pixi run -e dev python -m topology_benchmark `
  --generation-config my-generation-overrides.yaml --seed 42 --difficulty 8
```

## SVG representation

`SurfaceDiagramPlanner` converts combinatorial objects into a graphics-library-neutral diagram
plan. `MatplotlibGluingDiagramRenderer` then lays out regular polygons and serializes that plan as
SVG. Visual choices use a renderer-specific stream derived from the problem seed and never enter
the mathematical object.

The notation is designed to preserve the information needed to solve a problem:

- Matching labels and arrows identify glued sides and their relative directions.
- All regular polygons use the same side length, independent of side count.
- Cross-polygon glued sides are dotted; unglued boundary sides remain solid.
- A path side may be displayed on either representative of a glued pair.
- Dynamic programming chooses a lift favoring consecutive runs on one polygon, with seeded
  tie-breaking.
- A maximal multi-edge run is drawn as a chord, while a one-edge run curves outward.
- Coincident interior and edge runs are separated into curvature lanes.
- Polygon-local closed runs are expanded into their actual directed boundary arcs rather than a
  misleading interior circle.
- Thin, colored paths use numbered tags or repeated arrowheads to encode segment order.

Rendering defaults live in `src/topology_benchmark/domains/surfaces/rendering.yaml`, grouped under
`canvas`, `geometry`, `stroke`, `arrows`, `labels`, and `palettes`. Overrides are recursively merged
and validated:

```yaml
rendering:
  geometry:
    side_length: 140
  stroke:
    path_width: 1.2
  labels:
    tag_offset: 28
```

```python
container = build_container(rendering_config="my-rendering-overrides.yaml")
```

## Architecture and extension points

```text
src/topology_benchmark/
|-- core/                         shared Problem types, protocols, probability, recipes
|-- application/                  dependency wiring, benchmark service, local HTTP demo
|-- domains/surfaces/
|   |-- models/                   pure combinatorial objects and morphisms
|   |-- analysis.py               validation, classification, cellular homology
|   |-- generation.py             intent/context value types
|   |-- generation.yaml           default probabilistic profile
|   |-- rendering.yaml            default visual profile
|   `-- components/               generators, intent, questions, answers, display, renderer
`-- utils/                        shared implementation utilities
```

The core protocols separate object generation, conditional generation, transformations, invariants,
questions, representations, and composition. A new problem domain should preserve the same central
boundary: the renderer receives a mathematical object but the object must not contain the answer or
display-specific geometry. Exact answers should be computed independently of how the prompt is
drawn.

## Development

```powershell
pixi run -e dev test          # pytest suite
pixi run -e dev typecheck     # Pyrefly
pixi run -e dev lint          # Ruff checks
pixi run -e dev format-check  # verify formatting
pixi run -e dev check         # typecheck + lint + format-check
```

Tests cover topological validity, known quotient constructions, homology, deterministic rendering,
path layout, configuration layering, probability cohorts, reproducibility, and the generic demo
contract.
