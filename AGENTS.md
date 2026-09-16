# Repository conventions

## Dependency injection and defaults

- Treat the application container as the composition root. Load and validate configuration
  there, register each configuration instance by its concrete type, and let the container
  construct services from their classes whenever constructor injection can express the graph.
- Service constructors must require every collaborator and configuration object they use.
  Do not make injected arguments nullable, give them defaults, load fallback configuration in a
  service, or resolve dependencies through a service locator.
- Give each domain one complete deployable YAML document containing its full generation,
  presentation, recipe-selection, and profile-version policy. Do not layer partial override files;
  require every schema field so omitted values fail validation at startup. Retain nullable fields
  only when an explicit null is a meaningful configured state.
- Put environment-specific selection and intentional defaults at an explicit boundary such as
  the CLI, a configuration loader, or the composition root. Pass the resulting non-null value
  inward.
- Audit nullable and defaulted parameters for ambiguity. Retain them only when omission is a real,
  documented domain state or a stable operation-level default; never use omission to hide a
  dependency or select between competing construction paths.
- Tests that construct a service directly must provide its dependencies explicitly. Prefer
  resolving integration subjects from the application container.

## Composition and registration

- Keep deployable YAML files in the project-level `config/` directory rather than beside Python
  modules. Typed schemas and loaders belong with their domain code, while the composition root
  explicitly selects the configuration files passed to those loaders.
- Keep `build_container` as a small orchestration boundary: load and validate external
  configuration there, create the container, and delegate registrations to cohesive
  `add_<domain>_domain` functions located with their domains.
- A domain registration function owns that domain's concrete services, protocol bindings, and
  lifetimes. It may accept already validated configuration instances, but it must not read CLI
  arguments, environment variables, or configuration files.
- Register stateless analyzers as container singletons, while still injecting them into every
  consumer. Do not construct analyzers or other collaborators inside service methods. Introduce
  an injected factory only when creating distinct instances is part of the required lifecycle.

## Method ownership

- Use an instance method whenever behavior reads injected collaborators or instance state.
- Use a class method when behavior participates in subclass-aware class behavior and calls other
  overridable class helpers through `cls`.
- Keep a static method only for a leaf operation that needs neither instance state nor
  subclass-aware dispatch. Do not qualify protected helper calls with a concrete class name from
  within that class.
- Mark intentional method overrides with `typing.override`, including explicit protocol
  implementations. Model required template-method hooks as protected abstract methods so missing
  implementations are caught before the orchestration path invokes them.
- Prefer an underscore-prefixed name for an intentionally unused positional-only parameter. When
  an inherited public signature must preserve a keyword parameter name, `del parameter` is an
  acceptable explicit unused-parameter marker.

## Errors and method extraction

- Use `ValueError` for invalid values and violated construction invariants. Preserve `KeyError` for
  ordinary `Mapping.__getitem__` misses, but translate user-controlled application lookups into
  structured application exceptions carrying the rejected value and available choices.
- Translate exceptions only at boundaries that can add meaning or recover: CLI adapters format
  correctable request/configuration errors, HTTP adapters map known errors to status codes, and
  pipeline provider failures may become per-item results. Do not broadly classify internal
  `ValueError` failures as user input errors.
- HTTP boundaries that catch operational or unexpected failures must log the exception with its
  traceback before returning a server-error response. Keep console error logging visible even
  when request logging is customized.
- Publish each new multi-file run through a staging directory and move the completed directory
  into place atomically. Clean up staging data on failure, and keep collision behavior explicit so
  a reproducible run cannot be mistaken for a successful overwrite.
- Identify a dataset from its fully resolved generation law, root seed, schema, and domain
  configuration fingerprints. Keep model, provider, prompt, retry, and scoring settings in a
  separate evaluation identity so persisted datasets can be reused across evaluations.
- Persist each model prediction as an atomic per-item checkpoint. Resume an evaluation by loading
  validated checkpoints, and derive aggregate JSONL and summary artifacts from the complete set.
- Bump a domain's generation profile version whenever code changes can alter its generated
  mathematical objects, prompts, answers, or rendered media; dataset identity relies on that
  version alongside resolved configuration.
- Represent exhausted bounded generation with a specific operational exception rather than a
  generic `RuntimeError`. Reserve `AssertionError` for unreachable internal states.
- Extract a helper when it owns a named policy, invariant, or reusable domain operation. Do not
  extract a method merely to hide a short expression; names such as `require_<concept>` should make
  validation and exception translation explicit.

## Protocols

- Name protocol interfaces `I<Capability>` and name the primary concrete implementation
  `<Capability>`. Apply modifiers such as `LlmBased` only when they distinguish current,
  materially different behavior; do not reserve names such as `Default`, `Exact`, or `Base` for
  hypothetical alternatives.
- Concrete classes that intentionally implement a repository protocol should inherit that
  protocol explicitly. This makes the architectural relationship searchable and lets static
  analysis validate the implementation at its declaration.
- Keep protocols only for active boundaries with consumers. Remove unused speculative protocols
  and their implementations instead of registering or maintaining them for possible future use.
- Prefer concrete unions or shared data models when code needs the complete variants and no
  consumer is polymorphic over an open-ended interface. Do not introduce a protocol only to give
  related data classes a nominal parent.
- Keep immutable mathematical objects and closed morphism variants as data. Put behavioral
  variability behind registered problem recipes, generators, analyzers, and renderers.
- Configuration may weight stable registered capability IDs, but must not name import paths or
  construct dependency graphs. A recipe owns compatibility between generation, certification,
  question formulation, answer computation, and presentation.
- Use stable string IDs for capabilities that cross configuration, persistence, or request
  boundaries. Use concrete classes or protocols for in-process dependency registration; do not
  add string identities to services merely to recover their implementation type at runtime.
- Keep test doubles in tests and inject them through production protocols. Do not expose fake or
  fixed implementations as deployable configuration choices merely to support offline tests.
- Model adapters must handle each supported question-section media type explicitly and reject
  unsupported types before making an external request. Do not silently encode every section as the
  provider's dominant media type.
- Carry binary question media such as PNG as validated base64 at in-memory and JSON boundaries, but
  decode it to real binary files in dataset artifacts. Hash artifact bytes rather than decoded text,
  and remove nondeterministic renderer metadata before deriving persisted content identity.
- Keep concrete representation method signatures aligned with their shared representation
  protocol. Put domain-specific display annotations on the immutable observed value passed to the
  renderer instead of widening `render` with optional keyword parameters.
- Keep response extraction and answer-equivalence policy behind an injected scoring boundary.
  Pipeline orchestration must not grow a central type switch whenever a domain adds an answer form.
- Keep semantic presentation planning, visual-style selection, and backend serialization separate.
  Model style prevalence as a finite distribution over complete typed profiles, and implement
  reusable visual effects as backend primitives rather than branching on style IDs. Treat a 3D
  realization as an explicit representation policy; do not infer one from combinatorial data merely
  to decorate it with a Blender backend.
- Run automatic Matplotlib label adjustment only after every artist is present. Represent curved or
  nonrectangular collision geometry with sampled points rather than whole-artist bounding boxes,
  which forbid large areas that contain no visible stroke.
- Make scoring exhaustive over the supported answer-value union. Parse structured answers into
  canonical values, compare semantic forms rather than presentation syntax, and reject unsupported
  answer types instead of silently converting them to strings.
- Represent problem-recipe selection as a distribution over registered recipe objects. Recipe-specific
  generation parameters belong in typed configuration carried by the recipe; generators must not
  inspect recipe IDs to choose behavior.
- Resolve external recipe IDs and difficulty-aware defaults at the application boundary into one
  non-null distribution before sampling a recipe. Do not encode ID, override-distribution, and
  default-distribution selection as parallel nullable recipe or selector arguments.
- Make each registered problem recipe own its complete generation lifecycle and return a concrete
  problem from `generate`. Selection boundaries should resolve and distribute recipe objects, then
  invoke the selected recipe directly; adding a recipe must not extend a central dispatch branch.
- Express a recipe's stochastic generation intent as a typed distribution over semantic outcomes,
  constraints, or annotated domain objects. Do not encode it as coarse question-category enums or
  boolean hints that generators translate through hidden probability branches.
- Keep semantic laws separate from their realization algorithms. Finite laws should retain exact
  operations such as conditioning, pushforward, probability, and expectation; generators may use
  bounded sampling to realize a selected outcome when the full object space is not enumerable.
- Use the shared finite-distribution abstraction for weighted selection across domains, difficulty
  levels, problem recipes, and semantic outcomes. Compose dependent selections with distribution
  operations so the joint law remains available for exact inspection; do not implement local
  weighted-choice sampling loops.

## Properties and data

- Use a type alias only when it gives a repeated type expression a stable domain meaning or names a
  closed set of variants. Do not alias an already-readable generic specialization merely to give it
  a different noun; spell out the specialization at its use sites.
- Use frozen attrs classes for small immutable values that require validation, regardless of which
  package contains them. Express independent field invariants declaratively with attrs validators;
  do not implement them imperatively in `__post_init__`. Represent mutually exclusive shapes as
  concrete unions rather than nullable fields with cross-field checks.
- Use frozen dataclasses for plain immutable records that do not require validation. Represent
  immutable state as public fields; do not add private backing fields plus forwarding properties
  when no validation, translation, or compatibility boundary exists.
- Use a property for a cheap derived value, a read-only view that protects mutable internal state,
  or a genuinely uniform interface whose implementations derive the value differently.
- Do not retain forwarding properties as aliases for renamed fields. Update callers to the
  canonical field. Prefer a method when work is expensive, parameterized, state-changing, or can
  fail in ways ordinary attribute access would not suggest.
- Do not add Java-style `get_` or `set_` methods. Plain fields are the default, and explicit
  operation names should describe mutations when mutation is necessary.
- Do not add generic metadata dictionaries as extension points or mix operational data with
  diagnostics. Model required domain and pipeline concepts as explicit typed fields; introduce
  logging, audit, or monitoring through dedicated boundaries only when those capabilities exist.

## Maintenance and architectural memory

- Treat a package root as a human navigation boundary. Keep roughly four or five ordinary modules
  there, limited to recurring architectural entrypoints such as `abstractions.py`, `config.py`,
  `registration.py`, and primary orchestration services. Group implementation details into
  role-oriented subpackages before the root becomes a flat inventory.
- Consolidate a domain's public boundary protocols, answer type, recipe catalog, and recipe
  distribution in its root `abstractions.py`. Do not fragment these closely related declarations
  into one-abstraction root modules such as `ports.py`, `recipe_catalog.py`, or
  `recipe_distribution.py`.
- Organize pipeline support by the lifecycle it serves, such as `dataset/` or `evaluation/`. Do not
  create broad technical buckets such as `artifacts/` when their contents belong to distinct
  workflows.
- Organize cross-domain core code by the concept it supports: problem lifecycle, probability,
  generation, presentation, or structural primitives. Keep only truly repository-wide conventional
  modules such as errors and validation at the core package root.
- Name a module after the concrete capability it owns, such as `answer_scorer.py`. Do not use a
  broad process noun such as `scoring.py` or a technical category such as `protocols.py` to collect
  unrelated responsibilities; split multiple capabilities into focused modules or a cohesive
  capability package.
- Keep a context or aggregate beside the value types that define its shape. When a capability has
  several roles and subject families, give it a package with role-oriented subpackages and
  subject-named modules, such as `generation/context/object.py` and
  `generation/generator/object.py`. Do not use generic catch-all packages such as `components`.
- Name modules after the concrete capability or role they own. Avoid catch-all names such as
  `runner`, `manager`, `helpers`, or `utils` when the contents span generation, evaluation,
  persistence, or other distinct lifecycles; split those roles and keep shared leaf operations
  inside the narrowest owning package.
- Keep domain problem-recipe implementations in a `recipes/` package. Put their shared lifecycle
  in `base.py` and group concrete recipes into subject- or feature-named modules; do not collect a
  recipe family in a generic `question.py` module or retain the obsolete `questions/` package name.
- Do not preserve obsolete import modules, renamed-symbol aliases, forwarding properties, or
  test-only helpers in production solely for backward compatibility. Update repository callers
  to the canonical API and remove the legacy surface; keep specialized fixtures in tests.
- During every change, identify durable architectural decisions and recurring review lessons.
  Record them in `AGENTS.md` when they will guide future work across tasks; do this proactively
  before finishing rather than waiting for an explicit request.
- Keep these instructions focused on reusable constraints and reasoning. Do not record temporary
  implementation details, one-off bug descriptions, or facts that are already obvious from code.
