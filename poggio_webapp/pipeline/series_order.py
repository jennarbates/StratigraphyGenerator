"""Where a model's stratigraphic order comes from, and how sure it is.

GemPy needs one total order of surfaces, young to old. This module decides
which evidence supplies it and says so, because the three available sources are
not equally trustworthy and one of them is wrong at this site in a way the
others are not.

In descending order of authority:

1. **A Harris matrix.** The excavation's own record of stratigraphic
   relationships, built by the people who dug it, and already part of every
   trenchbook. ``pipeline/harris_matrix.py`` models it and can sort it.
2. **Recorded layer sequence.** Each wall's layers are drawn top to bottom, so
   adjacent pairs are ordering constraints. ``merge_walls.merged_series_order``
   derives an order from them. Real evidence, but only about what one wall saw.
3. **Mean elevation.** Not evidence at all -- an assumption that higher means
   younger, applied to whatever the points happen to say.

*Excavation and Documentation Procedures* rules the third out as a general
rule at Poggio Civitate, in as many words:

    we excavate in reverse chronological order of deposition (from most recent
    to oldest) ... sometimes, however, stratigraphically newer deposits may
    exist at lower elevations than stratigraphically older deposits

T104 is exactly that case: the 2025 report describes the Intermediate Phase
surface diving over 2 m below the contemporary floor of OC2/Workshop. An
elevation sort will confidently invert it.

So elevation ordering stays -- a model with no other information still has to
be buildable -- but it is labelled as the assumption it is, in the build log and
in the viewer manifest, rather than passing for a result.

**Contemporaneity.** The procedures also describe deposits with no order
relative to each other: "soil deposits on either side of the wall ... should be
made separate loci", excavated simultaneously because they are
"stratigraphically at the same level". A Harris matrix represents that
faithfully by having no edge between them. GemPy cannot: its stack is a total
order. So the order this module returns will separate them anyway, and it
records which adjacent pairs were placed arbitrarily so the model does not
present an invented sequence as a recorded one.
"""

from __future__ import annotations

from . import convert_coords

HARRIS = "harris-matrix"
RECORDED = "recorded-sequence"
ELEVATION = "elevation"
SUPPLIED = "supplied"

# What each source is, in one line, for the build log and the manifest.
SOURCE_DESCRIPTIONS = {
    HARRIS: "the trench's Harris matrix",
    RECORDED: "the layer sequence recorded on each wall",
    ELEVATION: (
        "mean elevation, an assumption that higher means younger. This site's "
        "procedures record cases where it does not: stratigraphically newer "
        "deposits can sit at lower elevations than older ones. Supply a Harris "
        "matrix or a series order to replace this"
    ),
    SUPPLIED: "an order supplied with the build request",
}


class SeriesOrderError(ValueError):
    """The stratigraphy cannot be ordered. The message is user-facing."""


def describe(source):
    """A sentence naming where an order came from."""
    return (
        f"stratigraphic order came from {SOURCE_DESCRIPTIONS[source]}"
        if source in SOURCE_DESCRIPTIONS
        else f"stratigraphic order came from {source}"
    )


def _unit_surface(unit):
    """The model surface a Harris unit refers to, or None.

    A field-sheet unit is labelled with the bare locus number, so it becomes
    ``Locus 6`` through the same function the converter uses -- the names have
    to match as strings for GemPy to fuse anything. An illustrator unit's label
    is already the layer name the converter emits.
    """
    label = (unit.label or "").strip()
    if not label:
        return None
    schema_types = {ref.schema_type for ref in unit.source_refs}
    if "FieldWallProfile" in schema_types:
        return convert_coords.surface_id(label)
    return label


def _component_surfaces(matrix):
    """{correlation representative: {surface names of its units}}."""
    from .harris_matrix import correlation_components

    components = correlation_components(matrix)
    grouped = {}
    for unit in matrix.units:
        surface = _unit_surface(unit)
        if surface is None:
            continue
        grouped.setdefault(components[unit.id], set()).add(surface)
    return grouped


def _related_pairs(matrix):
    """Correlation-collapsed (younger, older) pairs that a relation asserts."""
    from .harris_matrix import _collapsed_graph, correlation_components

    components = correlation_components(matrix)
    _nodes, relation_ids_by_edge = _collapsed_graph(matrix, components)
    return set(relation_ids_by_edge)


def _reachable(pairs):
    """Transitive closure, so an ordering implied through a chain counts."""
    successors = {}
    for younger, older in pairs:
        successors.setdefault(younger, set()).add(older)

    closure = {}
    for start in successors:
        seen = set()
        stack = list(successors[start])
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(successors.get(node, ()))
        closure[start] = seen
    return closure


def from_harris(matrix, available_surfaces=None):
    """A young-to-old surface order from a Harris matrix.

    ``available_surfaces``, when given, is the set of surface names the model
    actually has points for. Anything else is dropped: ``run_build`` refuses a
    series order naming a surface absent from the points CSV, and a matrix
    legitimately holds units this model does not cover.

    Returns ``(order, arbitrary_pairs, notes)``. ``arbitrary_pairs`` lists
    adjacent pairs the matrix does not order -- GemPy's stack forced a choice
    between deposits the excavation recorded as unordered.
    """
    from .harris_matrix import topological_order

    try:
        component_order = topological_order(matrix)
    except ValueError as error:
        raise SeriesOrderError(
            f"the Harris matrix cannot be ordered: {error}. Resolve the cycle "
            "in the matrix before building"
        ) from error

    grouped = _component_surfaces(matrix)
    notes = []
    order = []
    placed_component = {}

    for component in component_order:
        surfaces = sorted(grouped.get(component, ()))
        if available_surfaces is not None:
            surfaces = [s for s in surfaces if s in available_surfaces]
        for surface in surfaces:
            if surface in placed_component:
                continue
            placed_component[surface] = component
            order.append(surface)

    if available_surfaces is not None:
        missing = sorted(set(available_surfaces) - set(order))
        if missing:
            raise SeriesOrderError(
                "the Harris matrix has no unit for these modelled surfaces: "
                + ", ".join(repr(name) for name in missing)
                + ". Add them to the matrix, or build without it -- a partial "
                "order would silently drop them from the model"
            )

    # Pairs the matrix genuinely orders, including through a chain.
    closure = _reachable(_related_pairs(matrix))
    arbitrary = []
    for earlier, later in zip(order, order[1:]):
        first, second = placed_component[earlier], placed_component[later]
        if first == second:
            continue
        if second not in closure.get(first, ()):
            arbitrary.append((earlier, later))

    if arbitrary:
        notes.append(
            "the Harris matrix records no relationship between "
            + "; ".join(f"{a!r} and {b!r}" for a, b in arbitrary)
            + ". Deposits can be contemporary -- either side of a wall, for "
            "instance -- but GemPy's stack needs a total order, so one was "
            "imposed. Those boundaries in the model are not evidence"
        )
    return order, arbitrary, notes


def matrices_for_trench(trench_label, summaries):
    """Matrix summaries whose trench matches, canonical labels compared."""
    from naming import canonical_trench

    wanted = canonical_trench(trench_label)
    if not wanted:
        return []
    return [
        summary for summary in summaries
        if canonical_trench(summary.get("trench")) == wanted
    ]
