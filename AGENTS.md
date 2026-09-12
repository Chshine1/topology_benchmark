# Repository conventions

## Dependency injection and defaults

- Treat the application container as the composition root. Load and validate configuration
  there, register each configuration instance by its concrete type, and let the container
  construct services from their classes whenever constructor injection can express the graph.
- Service constructors must require every collaborator and configuration object they use.
  Do not make injected arguments nullable, give them defaults, load fallback configuration in a
  service, or resolve dependencies through a service locator.
- Put environment-specific selection and intentional defaults at an explicit boundary such as
  the CLI, a configuration loader, or the composition root. Pass the resulting non-null value
  inward.
- Audit nullable and defaulted parameters for ambiguity. Retain them only when omission is a real,
  documented domain state or a stable operation-level default; never use omission to hide a
  dependency or select between competing construction paths.
- Tests that construct a service directly must provide its dependencies explicitly. Prefer
  resolving integration subjects from the application container.

## Composition and registration

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

## Protocols

- Concrete classes that intentionally implement a repository protocol should inherit that
  protocol explicitly. This makes the architectural relationship searchable and lets static
  analysis validate the implementation at its declaration.
- Keep protocols only for active boundaries with consumers. Remove unused speculative protocols
  and their implementations instead of registering or maintaining them for possible future use.
- Prefer concrete unions or shared data models when code needs the complete variants and no
  consumer is polymorphic over an open-ended interface. Do not introduce a protocol only to give
  related data classes a nominal parent.

## Properties and data

- Represent immutable domain state as public frozen-dataclass fields. Do not add private backing
  fields plus forwarding properties when no validation, translation, or compatibility boundary
  exists.
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

- Do not preserve obsolete import modules, renamed-symbol aliases, forwarding properties, or
  test-only helpers in production solely for backward compatibility. Update repository callers
  to the canonical API and remove the legacy surface; keep specialized fixtures in tests.
- During every change, identify durable architectural decisions and recurring review lessons.
  Record them in `AGENTS.md` when they will guide future work across tasks; do this proactively
  before finishing rather than waiting for an explicit request.
- Keep these instructions focused on reusable constraints and reasoning. Do not record temporary
  implementation details, one-off bug descriptions, or facts that are already obvious from code.
