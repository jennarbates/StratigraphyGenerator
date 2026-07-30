"""Deterministic, dependency-free SVG rendering for Harris matrices."""

from collections import defaultdict
from dataclasses import dataclass
from xml.etree import ElementTree

from .harris_matrix import (
    HarrisMatrix,
    correlation_components,
    validate_matrix_graph,
)

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_MAX_UNITS = 250
_MINIMUM_WIDTH = 720
_PAGE_MARGIN = 40
_HEADER_HEIGHT = 164
_NODE_HEIGHT = 52
_NODE_MINIMUM_WIDTH = 150
_NODE_HORIZONTAL_PADDING = 36
_NODE_GAP = 36
_RANK_GAP = 92
_BOTTOM_MARGIN = 52

ElementTree.register_namespace("", _SVG_NAMESPACE)


class HarrisRenderError(ValueError):
    """Raised when a matrix cannot be rendered safely."""


@dataclass(frozen=True)
class _DisplayNode:
    representative_id: str
    unit_ids: tuple[str, ...]
    label: str
    rank: int
    width: int


def _svg_element(name, attributes=None, *, text=None):
    element = ElementTree.Element(
        f"{{{_SVG_NAMESPACE}}}{name}",
        attributes or {},
    )
    if text is not None:
        element.text = _xml_text(text)
    return element


def _xml_text(value) -> str:
    """Return text containing only characters allowed in XML 1.0."""
    return "".join(
        character
        if (
            character in "\t\n\r"
            or 0x20 <= ord(character) <= 0xD7FF
            or 0xE000 <= ord(character) <= 0xFFFD
            or 0x10000 <= ord(character) <= 0x10FFFF
        )
        else "\uFFFD"
        for character in str(value)
    )


def _normalized_label(label: str) -> str:
    return " ".join(label.split()).casefold()


def _estimated_text_width(text: str, *, size=14) -> int:
    return max(1, round(len(text) * size * 0.62))


def _node_width(label: str) -> int:
    return max(
        _NODE_MINIMUM_WIDTH,
        _estimated_text_width(label) + _NODE_HORIZONTAL_PADDING,
    )


def _display_nodes(matrix, components, ranks):
    units_by_component = defaultdict(list)
    for unit in matrix.units:
        units_by_component[components[unit.id]].append(unit)

    nodes = []
    for representative_id, units in units_by_component.items():
        ordered_units = sorted(
            units,
            key=lambda unit: (_normalized_label(unit.label), unit.id),
        )
        label = " = ".join(unit.label for unit in ordered_units)
        nodes.append(_DisplayNode(
            representative_id=representative_id,
            unit_ids=tuple(unit.id for unit in ordered_units),
            label=label,
            rank=ranks[representative_id],
            width=_node_width(label),
        ))
    return nodes


def _longest_path_ranks(order, edges):
    adjacent = defaultdict(list)
    for younger_id, older_id in edges:
        adjacent[younger_id].append(older_id)
    for children in adjacent.values():
        children.sort()

    ranks = {node_id: 0 for node_id in order}
    for younger_id in order:
        for older_id in adjacent[younger_id]:
            ranks[older_id] = max(
                ranks[older_id],
                ranks[younger_id] + 1,
            )
    return ranks


def _ranked_nodes(nodes):
    ranks = defaultdict(list)
    for node in nodes:
        ranks[node.rank].append(node)
    return {
        rank: sorted(
            rank_nodes,
            key=lambda node: (
                _normalized_label(node.label),
                node.representative_id,
            ),
        )
        for rank, rank_nodes in sorted(ranks.items())
    }


def _rank_width(nodes):
    if not nodes:
        return 0
    return (
        sum(node.width for node in nodes)
        + _NODE_GAP * (len(nodes) - 1)
    )


def _header_width(matrix, warning_text):
    text_widths = [
        _estimated_text_width(matrix.title, size=24),
        _estimated_text_width(
            f"Site: {matrix.site or '—'}  •  Trench: {matrix.trench or '—'}",
            size=13,
        ),
        _estimated_text_width(
            "Chronology flows downward: younger units are above older units.",
            size=12,
        ),
        _estimated_text_width(
            f"Relationships: above • cuts • fills • precedes • other  |  "
            f"{warning_text}",
            size=12,
        ),
    ]
    return max(text_widths) + 2 * _PAGE_MARGIN


def _append_text(
    parent,
    text,
    *,
    x,
    y,
    size,
    weight="400",
    css_class=None,
    anchor="start",
):
    attributes = {
        "x": str(x),
        "y": str(y),
        "fill": "#252c27",
        "font-family": (
            "Inter, system-ui, -apple-system, BlinkMacSystemFont, "
            "Segoe UI, sans-serif"
        ),
        "font-size": str(size),
        "font-weight": weight,
        "text-anchor": anchor,
    }
    if css_class is not None:
        attributes["class"] = css_class
    parent.append(_svg_element("text", attributes, text=text))


def _warning_text(warning_count):
    suffix = "" if warning_count == 1 else "s"
    return f"{warning_count} graph warning{suffix}"


def _serialize(root) -> str:
    return ElementTree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=True,
    ).decode("utf-8")


def render_harris_svg(matrix: HarrisMatrix) -> str:
    """Render a validated matrix as deterministic youngest-to-oldest SVG."""
    if not isinstance(matrix, HarrisMatrix):
        raise HarrisRenderError("A validated HarrisMatrix is required.")
    if len(matrix.units) > _MAX_UNITS:
        raise HarrisRenderError(
            "Harris Matrix SVG rendering supports at most "
            f"{_MAX_UNITS} units; this matrix contains {len(matrix.units)}."
        )

    report = validate_matrix_graph(matrix)
    if not report["ok"]:
        error_codes = sorted({
            issue["code"]
            for issue in report["errors"]
        })
        raise HarrisRenderError(
            "Cannot render a matrix with graph errors: "
            f"{', '.join(error_codes)}."
        )

    edges = [tuple(edge) for edge in report["display_edges"]]
    ranks = _longest_path_ranks(report["topological_order"], edges)
    components = correlation_components(matrix)
    nodes = _display_nodes(matrix, components, ranks)
    nodes_by_rank = _ranked_nodes(nodes)
    warning_text = _warning_text(len(report["warnings"]))

    widest_rank = max(
        (_rank_width(rank_nodes) for rank_nodes in nodes_by_rank.values()),
        default=0,
    )
    width = max(
        _MINIMUM_WIDTH,
        widest_rank + 2 * _PAGE_MARGIN,
        _header_width(matrix, warning_text),
    )
    if nodes_by_rank:
        last_rank = max(nodes_by_rank)
        height = (
            _HEADER_HEIGHT
            + last_rank * (_NODE_HEIGHT + _RANK_GAP)
            + _NODE_HEIGHT
            + _BOTTOM_MARGIN
        )
    else:
        height = _HEADER_HEIGHT + 116

    root = _svg_element(
        "svg",
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "role": "img",
            "aria-labelledby": "harris-svg-title harris-svg-description",
        },
    )
    root.append(_svg_element(
        "title",
        {"id": "harris-svg-title"},
        text=matrix.title or "Untitled Harris Matrix",
    ))
    root.append(_svg_element(
        "desc",
        {"id": "harris-svg-description"},
        text=(
            "Harris Matrix with younger units at the top and older units "
            "at the bottom."
        ),
    ))
    root.append(_svg_element(
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "fill": "#fffdf8",
        },
    ))

    header = _svg_element("g", {"class": "harris-header"})
    _append_text(
        header,
        matrix.title or "Untitled Harris Matrix",
        x=_PAGE_MARGIN,
        y=38,
        size=24,
        weight="700",
        css_class="harris-title",
    )
    _append_text(
        header,
        f"Site: {matrix.site or '—'}  •  Trench: {matrix.trench or '—'}",
        x=_PAGE_MARGIN,
        y=64,
        size=13,
        css_class="harris-context",
    )
    _append_text(
        header,
        "Chronology flows downward: younger units are above older units.",
        x=_PAGE_MARGIN,
        y=92,
        size=12,
        weight="600",
        css_class="harris-direction-legend",
    )
    _append_text(
        header,
        (
            "Relationships: above • cuts • fills • precedes • other  |  "
            f"{warning_text}"
        ),
        x=_PAGE_MARGIN,
        y=114,
        size=12,
        css_class="harris-relationship-legend",
    )
    _append_text(
        header,
        f"Generated from saved revision {matrix.revision} at "
        f"{matrix.updated_at.isoformat()}",
        x=_PAGE_MARGIN,
        y=136,
        size=11,
        css_class="harris-generation-time",
    )
    header.append(_svg_element(
        "line",
        {
            "x1": str(_PAGE_MARGIN),
            "x2": str(width - _PAGE_MARGIN),
            "y1": "150",
            "y2": "150",
            "stroke": "#d6cebd",
            "stroke-width": "1",
        },
    ))
    root.append(header)

    if not nodes:
        _append_text(
            root,
            "No units have been added to this matrix.",
            x=width / 2,
            y=_HEADER_HEIGHT + 48,
            size=15,
            weight="600",
            css_class="harris-empty",
            anchor="middle",
        )
        _append_text(
            root,
            "Add or import units, then save to generate the diagram.",
            x=width / 2,
            y=_HEADER_HEIGHT + 76,
            size=12,
            css_class="harris-empty-help",
            anchor="middle",
        )
        return _serialize(root)

    positions = {}
    for rank, rank_nodes in nodes_by_rank.items():
        rank_width = _rank_width(rank_nodes)
        x = (width - rank_width) / 2
        y = _HEADER_HEIGHT + rank * (_NODE_HEIGHT + _RANK_GAP)
        for node in rank_nodes:
            positions[node.representative_id] = (x, y, node.width)
            x += node.width + _NODE_GAP

    edge_group = _svg_element("g", {"class": "harris-edges"})
    for younger_id, older_id in edges:
        younger_x, younger_y, younger_width = positions[younger_id]
        older_x, older_y, older_width = positions[older_id]
        line = _svg_element(
            "line",
            {
                "class": "harris-edge",
                "x1": str(younger_x + younger_width / 2),
                "y1": str(younger_y + _NODE_HEIGHT),
                "x2": str(older_x + older_width / 2),
                "y2": str(older_y),
                "stroke": "#657067",
                "stroke-width": "2",
                "stroke-linecap": "round",
            },
        )
        line.append(_svg_element(
            "title",
            text=f"Younger {younger_id} to older {older_id}",
        ))
        edge_group.append(line)
    root.append(edge_group)

    node_group = _svg_element("g", {"class": "harris-nodes"})
    for rank, rank_nodes in nodes_by_rank.items():
        for node in rank_nodes:
            x, y, node_width = positions[node.representative_id]
            group = _svg_element(
                "g",
                {
                    "class": "harris-node",
                    "data-representative-id": node.representative_id,
                    "data-unit-ids": ",".join(node.unit_ids),
                    "data-rank": str(rank),
                },
            )
            group.append(_svg_element(
                "rect",
                {
                    "x": str(x),
                    "y": str(y),
                    "width": str(node_width),
                    "height": str(_NODE_HEIGHT),
                    "rx": "7",
                    "fill": "#fffdf8",
                    "stroke": "#7a3428",
                    "stroke-width": "2",
                },
            ))
            _append_text(
                group,
                node.label,
                x=x + node_width / 2,
                y=y + _NODE_HEIGHT / 2 + 5,
                size=14,
                weight="650",
                css_class="harris-node-label",
                anchor="middle",
            )
            node_group.append(group)
    root.append(node_group)
    return _serialize(root)
