# Topology Benchmark

`topology_benchmark` generates reproducible visual problems about compact surfaces and maps
between them. A surface is given only as polygons with directed, worded edge identifications.
Euler characteristic, connected components, boundary components, orientability, genus, and
integral homology are computed from that quotient presentation; none of them is stored beside it.

The benchmark can make questions whose subject is either:

- a **surface object**, or
- a **boundary-gluing morphism**, represented by its source, target, and the boundary edges that
  the quotient map identifies.

This makes morphisms first-class mathematical data rather than transient mutations. Invariants
and questions can consequently be defined on arrows just as they are on objects.

## Quick start

The project uses Python 3.14 and Pixi.

```powershell
pixi install -e dev
pixi run -e dev python -m topology_benchmark --seed 42 --difficulty 8
pixi run -e dev test
pixi run -e dev check
```

The CLI writes a JSON `Problem`. Every prompt has media type `image/svg+xml`; its `content` is a
complete SVG document. Object problems contain one prompt. Morphism problems contain source and
target prompts in that order.

### Visual demo

Run the zero-dependency local viewer and open the printed address:

```powershell
pixi run -e dev python -m topology_benchmark --serve --difficulty 5
```

By default it listens only on `http://127.0.0.1:8000`. The page displays every prompt, lets you
replay a chosen seed, generates a fresh random seed with one button, adjusts difficulty, and keeps
the answer hidden until requested. The server also exposes:

```text
GET /api/problem?seed=42&difficulty=7
GET /health
```

The viewer is domain-independent. It depends only on a `ProblemProvider` with a `generate()`
method and renders prompts according to their `media_type` (`image/*`, `audio/*`, or text-like
fallback). `SurfaceBenchmark` is simply the provider selected by the current composition root.
Use `--host` and `--port` to change the bind address when needed.

```python
from pathlib import Path

from topology_benchmark import SurfaceBenchmark, build_container

benchmark = build_container().resolve(SurfaceBenchmark)
problem = benchmark.generate(seed=42, difficulty=8)

for index, prompt in enumerate(problem.prompts):
    Path(f"prompt-{index}.svg").write_text(prompt.content, encoding="utf-8")

print(problem.metadata["subject"])  # "object" or "morphism"
print(problem.question)
print(problem.answer)               # keep hidden in an evaluation harness
```

A fixed seed and difficulty reproduce the complete problem byte for byte. Difficulty ranges from
1 through 10 and controls the available combinatorial complexity and question subjects.

## Surface objects

`SurfacePresentation` is the mathematical object and the only source of truth:

```text
SurfacePresentation
├── polygons      finite closed 2-cells with placed vertices
├── marks         (polygon edge, word, arrow direction)
├── paths         Bezier drawing plus a signed marked-edge word
└── palette       generated display parameter
```

Each gluing word must occur on exactly two edges. The two arrows say how those complete edges are
identified. Unmarked edges remain in the boundary. Multiple polygons may remain disconnected or
be joined by marks, so the same model represents connected and disconnected compact surfaces.

There is intentionally no stored `genus`, `orientable`, `boundary_components`, or parallel
“topology” member. Keeping both a presentation and precomputed classification data would permit
inconsistent objects. Classification data belongs to analysis results and invariant answers.

### Quotient-complex analysis

`SurfaceAnalyzer` derives the topology directly from the presentation:

1. A disjoint-set quotient identifies polygon vertices according to matching directed edges.
2. Polygon connectivity determines the connected components.
3. The quotient cell counts give `χ = V - E + F`.
4. The graph of unmarked quotient edges gives the boundary circles.
5. Orientation constraints across every glued edge determine orientability.
6. Every quotient-vertex link is checked to be one circle or one interval.
7. The classification theorem then derives genus and integral homology.

For each derived connected component with boundary count `b`:

| Type | Euler characteristic | `H_1(-; Z)` | `H_2(-; Z)` |
|---|---:|---|---|
| orientable genus `g` | `2 - 2g - b` | `Z^(2g)` if closed, else `Z^(2g+b-1)` | `Z` if closed, else `0` |
| non-orientable genus `g` | `2 - g - b` | `Z^(g-1) ⊕ Z/2` if closed, else `Z^(g+b-1)` | `0` |

For disconnected surfaces, homology is the direct sum over derived components and `H_0` has one
copy of `Z` per component.

Paths are part of the presentation but do not store a purported homology class. A signed marked-
edge word denotes based edge loops using a deterministic spanning forest of the quotient
1-skeleton. The analyzer converts it to coordinates in the resulting fundamental-cycle basis,
modulo cellular face boundaries. Open paths are rendered with visible endpoints and are not
cycles.

## Surface morphisms

`BoundaryGluingMorphism` represents an actual quotient map. It retains:

- its `source` surface;
- its `target` quotient surface;
- every `EdgeIdentification(first, second, word, same_direction)` imposed by the map.

Construction validates that each newly glued member is an unmarked source boundary edge and that
no source edge is reused. Both source and target are independently analyzed from their own
presentations.

`PolygonAttachmentMorphism` is the complementary inclusion map. It retains the source, target,
new polygon, and attaching edge pair. Its target is validated to be exactly that attachment. The
source embeds in the result, and the added disc retracts across its attaching interval.

The generator currently produces three meaningful families:

- attaching a new polygon along a boundary interval, represented as an injective inclusion;
- gluing the entire boundaries of two polygonal discs, producing a sphere and merging components;
- gluing the two boundary circles of an annulus, producing a torus or Klein bottle according to
  the chosen direction.

These maps support arrow invariants and questions such as:

- `χ(target) - χ(source)`;
- changes in boundary or connected-component count;
- the target's integral homology and orientability;
- whether the map is injective or surjective;
- whether it induces isomorphisms on homology.

Other categorical constructions can follow the same model: a collapse can be a quotient arrow,
and induced maps on homology can carry explicit matrix data. They should retain their construction
data rather than merely returning a modified surface.

## Questions and visual variation

Object questions cover Euler characteristic, boundary count, component count, orientability,
integral homology, cycle recognition, and cellular path representatives. Morphism questions cover
both target invariants and properties or effects of the quotient map.

All randomness belongs to generators. They sample polygon count, fundamental word, placement,
shape, palette, path controls, path curvature, and morphism members. `SvgGluingDiagramRenderer`
only realizes stored parameters and is byte-for-byte deterministic for a fixed presentation.
Thus generation produces parameters for an object representation; rendering is not probabilistic.

## Architecture

```text
src/topology_benchmark/
├── core/
│   ├── models.py                 Problem and prompt values
│   ├── protocols.py              object, arrow, transformation, invariant contracts
│   └── recipe.py, composer.py     generic object-problem composition
├── domains/surfaces/
│   ├── models.py                 polygon quotients, paths, quotient morphisms
│   ├── analysis.py               topology derived from the quotient cell complex
│   ├── ports.py                  typed domain extension points
│   └── components/
│       ├── generator.py          object and morphism generators
│       ├── representation.py     deterministic SVG renderer
│       ├── invariant.py          object and morphism ground truth
│       └── question.py           object and morphism question banks
├── application/
│   ├── services.py               seeded subject selection and composition
│   └── bootstrap.py              Lagom dependency bindings
└── __main__.py                    JSON CLI
```

The core now distinguishes a `Morphism`, which has a source and target and may itself be examined,
from a `Transformation`, which is a recipe-stage operation. This avoids conflating categorical
arrows with implementation functions that happen to modify an object.

## Extending the framework

For a new object domain, provide an immutable presentation, seeded generator, exact analyzer or
invariants, deterministic renderer, and question bank. For a new morphism family, provide an
immutable arrow with source, target, and sufficient construction data to compute induced
invariants. A morphism generator can then be treated like any other subject generator.

Validate changes with:

```powershell
pixi run -e dev test
pixi run -e dev check
```
