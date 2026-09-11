# Polyhedral Nets and Folding: Core Principles

## Motivation

A polyhedral net is not just a collection of polygons with edge identifications; it carries metric data: exact edge
lengths, face angles, and rigid shapes. This allows reasoning about rigid folding, convexity, and isometry, making the
domain distinct from purely topological polygon gluing.

## Generation from Real Geometry

Start with a validated convex 3D polyhedron, including vertex coordinates and oriented polygonal face cycles. Choose a
face-dual spanning tree, unfold across those hinges without stretching, and reject developments whose face interiors
overlap. Faces may be irregular and need not share a common edge length.

## What Makes Good Problems

Reveal as little as the question needs. Provide a to-scale net and label only queried faces, edges, or corners. When the
visible information is insufficient, show a minimal number of matching seam hints. Ask questions such as:

- How are several marked corners partitioned into folded vertices?
- What is the edge-count distance, or number of shortest paths, between two marked cells?
- Which reconstructed vertex has greater angular defect?

## Core Principle: Certified Observability

Unlabelled boundary edges can admit several abstract gluings. Enumerate all pairings compatible with visible metric data,
its finite rendering precision, partial hints, spherical topology, and the convexity promise. Emit an ordinary question
only when its answer is identical for every remaining completion. Extrinsic coordinate questions require a unique
completion. Exact source-length differences below the visual tolerance cannot be used to certify an answer.

Marks communicate premises rather than conclusions: letters identify queried objects, colored edge dots disclose only
selected seam pairs, and curvature questions display all corner angles to a stated precision. Difficulty is measured by
the remaining folding inference, with more scaffolding at easier levels. Comparisons must share a drawing scale and show
face correspondences; trivial negative comparisons with visibly incompatible face inventories are not sampled.

At a quotient vertex, the incident face-angle sum determines intrinsic discrete curvature:

- Sum < 360° → positive angular defect
- Sum = 360° → zero angular defect
- Sum > 360° → negative angular defect

These terms deliberately avoid claiming that intrinsic curvature alone selects an outward, inward, coplanar, or
collision-free spatial realization.

## Analysis Challenge

The benchmark separates source truth from observable truth. Source seams may select truthful hints, but they cannot be
used as the answer unless the rendered observation and stated promises determine that answer. Candidate enumeration tests
edge coverage, vertex links, Euler characteristic, and angular defect; generation keeps objects small enough for complete
certification.

## Difference from Topological Polygon Gluing

Topological invariants such as Euler characteristic or boundary count are insufficient to capture the domain. The
essential challenge is metric folding: inferring rigid spatial structure from planar geometry.
