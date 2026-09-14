# Topology Benchmark

`topology_benchmark` is a reproducible visual-problem generator for evaluating geometric and
topological reasoning. The framework separates mathematical objects, exact ground-truth analysis,
question selection, and graphic representation so that a problem is solved from its supplied
question material rather than from hidden generator state.

The built-in domains are **compact surfaces presented by polygon-edge gluings**, **polyhedral
nets**, and **round tori observed through parallel level sections**. They generate single-object
questions as well as relational questions about links or pairs of unfoldings.

```text
seed + difficulty + profile
            |
            v
  question distribution
            |
            v
 registered question ---> object/morphism generator ---> exact analyzer
            |
            v
 certified answer + display planning ---> deterministic question sections
```

## Current capabilities

- Seeded, difficulty-controlled generation on a scale from 1 to 10.
- Typed question distributions: select configured question objects before compatible instances are built.
- Object problems with one or more visual observations.
- Exact surface validation and invariant computation from combinatorial data.
- Integral cellular homology, including torsion and path coordinates in explicit bases.
- Deterministic, model-ready SVG output and a local browser viewer.
- Equation-free, aligned level-section diagrams for spatial reconstruction of torus links.
- YAML profiles for generation probabilities and rendering parameters.
- Protocol-based core types that can support additional mathematical domains and media types.

All three domains are wired into the command-line application and the domain-independent viewer.

## Quick start

The project targets Python 3.14 and uses [Pixi](https://pixi.sh/) for its environment and tasks.

```powershell
pixi install -e dev
pixi run -e dev python -m topology_benchmark --seed 42 --difficulty 8
pixi run -e dev python -m topology_benchmark --domain polyhedral-nets --seed 42 --difficulty 8
pixi run -e dev python -m topology_benchmark --domain torus-slices --seed 42 --difficulty 8
pixi run -e dev test
pixi run -e dev check
```

The CLI writes one JSON-serialized `Problem` to standard output. Start the interactive local viewer
instead with:

```powershell
pixi run -e dev python -m topology_benchmark --serve --difficulty 5
```

Then open `http://127.0.0.1:8000`. The viewer can generate a new seed, replay a seed at a selected
difficulty, switch among the domains, show every question section, and reveal the exact answer. A `--domain`
selection changes the initially displayed domain but does not disable the switch. The server also
exposes:

- `GET /health`
- `GET /api/problem?domain=polyhedral-nets&seed=42&difficulty=8`
- `GET /api/problem?domain=torus-slices&seed=42&difficulty=8`

Useful CLI options are:

```text
--seed INTEGER
--difficulty {1,...,10}
--domain {surfaces,polyhedral-nets,torus-slices}
--serve
--host HOST
--port PORT
--generation-config PATH
--rendering-config PATH
```

## Problem contract

The cross-domain API consists of immutable dataclasses:

```python
from topology_benchmark import BenchmarkCatalog, GenerationRequest, build_container

catalog = build_container().resolve(BenchmarkCatalog)
request = GenerationRequest(seed=42, difficulty=8)
problem = catalog.generate(domain="surfaces", request=request)
# Or select one registered recipe directly, without rejection sampling.
problem = catalog.generate_recipe(
    domain="surfaces",
    request=request,
    recipe_id="boundary-change",
)

print(problem.question)
print(problem.answer)
print(problem.sections[0].media_type)  # image/svg+xml in the surface domain
```

A `Problem` contains:

| Field | Meaning |
| --- | --- |
| `question` | Natural-language task shown to the answerer |
| `sections` | One or more `QuestionSection` values containing supplied question material |
| `answer` | Exact computed ground truth (`int`, `bool`, `str`, or an integer tuple) |
| `seed` | Seed needed to reproduce the instance |
| `question_id` | Stable registered question ID used for dataset selection and result grouping |

`QuestionSection` contains a MIME `media_type` and its serialized `content`. The generic viewer
knows how to display image, audio, and text sections; the current surface renderer
always emits an inline `image/svg+xml` document.

For a fixed seed, difficulty, configuration, and `profile_version`, generation is reproducible.
Named random streams isolate decisions, so introducing an unrelated sampling step does not shift
existing choices. A deliberate semantic change to a generation profile should therefore also bump
its `profile_version`.

### Registered recipe selection

Pipeline YAML uses stable recipe IDs to control the generated dataset mixture. `BenchmarkCatalog`
resolves each ID to its registered question object and a distribution concentrated on that object.
Calling `generate` uses the domain's configured difficulty-aware default distribution, while
`generate_recipe` explicitly requests one recipe.

Adding a question means implementing the domain question protocol/base class, declaring its typed
configuration and collaborators, and registering the instance. It does not require editing a
central question-building branch. Default difficulty-aware distributions are assembled in each
domain registration boundary and resolved by `BenchmarkCatalog` before it calls a provider.

## Polyhedral-net domain

The v8 domain starts from a real convex `Polyhedron3D` with rational coordinates and possibly
irregular polygonal faces. It validates the closed oriented boundary and exact convex support
planes, chooses a random face-dual spanning tree, develops the faces into the plane, and rejects
overlapping layouts. `PolyhedralFolding` keeps the source and closing seams away from the renderer.

Before emitting a question, the analyzer enumerates every boundary pairing compatible with the
visible hints and a finite visual tolerance on drawn edge lengths. Thus a small difference known
only to the source geometry cannot silently disambiguate a picture. It retains pairings that form a
spherical manifold with positive angular defect. An ordinary question is emitted only when every
retained completion gives the same answer; hard extrinsic questions require a unique completion.
If necessary, the generator reveals a small number of true seam pairs as matching colored dots.
Scaffolding decreases with difficulty rather than treating missing information as difficulty.

Questions use sparse labels and ask for complete partitions of marked corners into folded vertices,
distances and shortest-path counts between marked vertices, edges, or faces in the folded
1-skeleton, seam matches, vertex degree, and discrete-curvature comparisons. Curvature diagrams show
every planar corner angle, rounded to the stated precision, and reject
near-tied defect comparisons. Extrinsic height questions are withheld because a flat net does not
make the required dihedral reconstruction sufficiently readable.
Two-net isometry generation is withheld until hard negative examples can be built from the same
rigid panel kit; comparison rendering uses face correspondences and one shared scale. Source-family
names, hidden seams, completion counts, and answer-derived geometry are not exposed.

## Torus-slice domain

An `EllipticTorus` sweeps a rotated elliptical profile around a regular planar `RoundCircle` in
`R^3`; `RoundTorus` is the circular-profile special case. Generated families independently vary the
profile eccentricities and angles. They contain one to four tori and use separated unknots,
Hopf-linked pairs, connected chains, or complete Hopf links in which every pair is linked. Before a
scene is accepted, a conservative distance bound certifies that every pair of tubes is disjoint.

The answerer does not see the core circles, their centers, radii, plane normals, implicit quartic
equations, link template, or a perspective rendering. The question material contains only several parallel
plane intersections, arranged at a common scale in a common coordinate frame. Empty sections above
and below the family are retained. More sections and more components appear as difficulty rises, so
one must mentally track how the planar curves are born, merge, split, and move through space.

Questions ask for the number of hidden tori, whether two core curves are linked, whether a family is
completely unlinked, or the number of linked pairs. Ground-truth linking numbers are computed as
oriented intersections of one circular core with the disk bounded by the other; they are not
estimated from the picture. The profile supplies rich finite samples for spatial inference but does
not expose symbolic section equations or claim to enumerate every algebraic family compatible with
a sparse observation. Shuffled ordering and missingness are intentionally not scored without an
identifiability certificate.

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
| Surface | Path | whether a displayed path is a cycle; its coefficients in a displayed homology basis |
| Morphism | Relational | changes in Euler characteristic, boundary count, or component count; injectivity; surjectivity; homology isomorphism |
| Morphism | Target-only | target homology; target orientability |

Morphism questions are registered alongside object questions and render separate source and target
sections. The generation model contains two first-class arrow types:

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

For a path-coordinate question, tagged arrows `e1`, `e2`, ... identify chosen oriented quotient
edges. The question directly defines ordered generators for the invariant-factor decomposition of
`H1` as integer edge chains, such as `h1 = e1 - e3 + e4`, and states the order of each torsion
generator. Only the queried path is drawn as a path. The exact answer is its coefficient tuple in
those generators, with torsion coordinates canonically reduced.

## Generation profiles

Defaults live in `config/surfaces/generation.yaml`. Values specified at difficulty anchors are
linearly interpolated. The profile controls:

- object-versus-morphism subject weights and conditional recipe weights;
- polygon counts, side-count continuation, and gluing density;
- path-length continuation and visual complexity budgets;
- morphism-family weights and per-question affinities, converted at configuration load time into a
  typed generation policy so the generator never dispatches on question IDs;
- rare intentional noise and retry limits.

Incidental paths occur at a low 7.5% noise rate. Path lengths follow a truncated geometric
distribution. Current display-safety caps are four polygons, eight sides per polygon, and seven
query-path segments; path-coordinate diagrams tag at most eight quotient edges.

An override YAML is recursively layered over the defaults, so it only needs to contain changed
values:

```yaml
generation:
  profile_version: "surface-v3"
  noise_probability: 0.05
  difficulty:
    question_family_weights:
      path: {1: 0.10, 4: 0.20, 7: 0.35, 10: 0.50}
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

Rendering defaults live in `config/surfaces/rendering.yaml`, grouped under
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
config/
|-- pipeline.example.yaml         example dynamic-evaluation run
`-- surfaces/
    |-- generation.yaml           default probabilistic profile
    `-- rendering.yaml            default visual profile
src/topology_benchmark/
|-- core/
|   |-- errors.py, validation.py  repository-wide errors and attrs validators
|   |-- generation/               shared object-generation contracts
|   |-- presentation/             shared representation contracts
|   |-- probability/              finite laws, sampling, and profile interpolation
|   |-- problem/                  problem values, recipes, providers, and question distributions
|   `-- structures/               shared structural primitives such as disjoint sets
|-- application/                  composition root, benchmark catalog, local HTTP demo
|-- domains/surfaces/
|   |-- benchmark.py              thin provider/orchestration shell
|   |-- question_distribution.py  domain question distribution
|   |-- generation/
|   |   |-- config.py             typed generation configuration and loader
|   |   |-- context/              semantic conditions and contexts by subject
|   |   |   |-- object.py
|   |   |   `-- morphism.py
|   |   `-- generator/            realization services by subject
|   |       |-- object.py
|   |       `-- morphism.py
|   |-- models/                    immutable surface objects, morphisms, and facts
|   |-- questions/                independently registered question implementations
|   |-- rendering/                rendering config, diagram planning, and renderer
|   |-- services/                 explicitly named services such as surface_analyzer.py
|   |-- ports.py                  active generator and representation boundaries
|   `-- registration.py           domain-owned container bindings
|-- domains/polyhedral_nets/
|   |-- benchmark.py, config.py, ports.py, question_distribution.py, registration.py
|   |-- generation/               net realization and compatible-completion enumeration
|   |-- models/                   immutable net and folding values
|   |-- questions/                registered polyhedral question capabilities
|   |-- rendering/                SVG net presentation
|   `-- services/                 net, cell-graph, and observation analysis
|-- domains/torus_slices/
|   |-- benchmark.py, config.py, ports.py, question_distribution.py, registration.py
|   |-- generation/               semantic generation context and realization
|   |-- models/                   torus geometry and observations
|   |-- questions/                registered slice question capabilities
|   |-- rendering/                SVG slice presentation
|   `-- services/                 torus-family analysis
`-- pipeline/
    |-- config.py, registration.py
    |-- dataset_generator.py      dataset-generation entrypoint
    |-- evaluator.py              model-evaluation entrypoint
    |-- dataset/                  generated values and persistence
    |-- evaluation/               provider, scorer, results, and persistence
    `-- serialization/            shared JSON serialization primitives
```

The core provides generic `QuestionCatalog`, `QuestionChoice`, and `QuestionDistribution` types and
collects domain providers in an injected `BenchmarkCatalog`. Each domain defines the question
protocol or base class appropriate to its lifecycle: surface and torus questions generate complete
problems, while polyhedral questions build certified drafts from enumerated compatible foldings.
Mathematical objects and the closed surface-morphism union remain immutable data rather than
behavioral interfaces. Questions coordinate compatible generation, certification, wording, exact
answers, and rendering. Configuration selects only stable registered IDs and probabilities, never
Python import paths or dependency graphs. A new domain registers its provider, questions, default
distribution, and collaborators at the composition root; renderers never receive hidden answers or
answer-derived geometry.

Surface object recipes carry configured finite laws over semantic outcomes such as component count,
path count, path closure, and nontrivial homology. The surface generator realizes the selected outcome
without inspecting a question ID or interpreting question-category flags. Because these laws are
finite distributions, callers can compute their exact pushforwards, conditional probabilities, and
expectations in addition to sampling presentations from them.
Morphism recipes follow the same lifecycle: configuration resolves a difficulty-aware finite law
over morphism conditions, and the generator realizes the selected family without applying
question-specific affinities or changing families on retry exhaustion.

## Dynamic evaluation pipeline

The pipeline creates a new dataset at run time, optionally sends its public question sections to a model,
and scores the returned answers. Copy `config/pipeline.example.yaml` and configure the run size, weighted
domain mixture, internal generation levels, and optional `recipes` mixture. Generation levels
retain the existing generator controls but are deliberately absent from public examples and result
tables: they are not presented as validated measurements of difficulty.

Omit `run.seed` for an unpredictable 128-bit seed. The resolved seed is written to the private run
manifest, so the run can later be reproduced by putting that value into the configuration. Item
seeds are derived independently from the root seed and item position. Target recipes are validated
against the injected benchmark catalog before generation and dispatched directly. Unknown domains
or recipe IDs therefore fail at startup rather than consuming a retry budget or silently changing
the requested distribution.

Generate a dataset without making API calls:

```powershell
pixi run -e dev python -m topology_benchmark.pipeline config/pipeline.example.yaml --generate-only
```

After configuring a model provider, run it and score its responses:

```powershell
pixi run -e dev python -m topology_benchmark.pipeline config/pipeline.example.yaml
```

Each run has a content-derived identifier and writes a separate directory containing:

| Artifact | Contents |
| --- | --- |
| `dataset.public.jsonl` | IDs, domains, questions, and relative media paths |
| `media/` | The SVG question sections sent to or published for answerers |
| `ground_truth.private.jsonl` | Answers, question IDs, and generator seeds |
| `manifest.private.json` | Resolved root seed, configuration, and realized mix |
| `predictions.jsonl` | Raw responses, extracted answers, correctness, and API errors |
| `summary.json` | Overall and per-question accuracy plus failed-request count |

For an API with the OpenAI Chat Completions request shape, add:

```yaml
model_provider:
  base_url: https://provider.example/v1
  model: provider-model-id
  api_key_env: BENCHMARK_API_KEY
  timeout_seconds: 60

evaluation:
  max_retries: 2
```

Set the key only in the process environment; it is never read from YAML or written to run
artifacts. The adapter sends multimodal `messages` to `POST {base_url}/chat/completions` and asks
the model to finish with `FINAL_ANSWER: ...`. It currently sends the native SVG as a base64 data
URL. If an available API accepts only PNG or uses a different schema, implement an `IModelProvider`
adapter in `pipeline/evaluation/model_provider.py`; PNG rasterization should happen at that
boundary so the
generated mathematical instance stays unchanged. Test doubles belong in tests and are injected
through the same `IModelProvider` protocol; they are not deployable provider choices.

Before connecting a tutor-provided API, obtain its base URL, model identifier, authentication
method, multimodal request/response example, accepted image MIME types and size limits, rate limits,
and available request budget. An OpenAI-compatible endpoint with native SVG support needs only the
configuration above. Other APIs need a small provider adapter; SVG-incompatible APIs also need an
SVG-to-PNG dependency or service.

To test the pipeline itself:

```powershell
pixi run -e dev python -m pytest tests/test_pipeline.py
pixi run -e dev test
pixi run -e dev check
```

Keep `ground_truth.private.jsonl` and `manifest.private.json` away from the evaluated model. Fresh
generation reduces exposure to memorized instances, but it does not prevent reconstruction by a
party that has the generator and the private root seed.

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
