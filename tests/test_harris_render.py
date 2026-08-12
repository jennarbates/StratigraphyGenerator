import re
from xml.etree import ElementTree

import pytest

from poggio_webapp.pipeline.harris_matrix import HarrisMatrix
from poggio_webapp.pipeline.harris_render import (
    HarrisRenderError,
    render_harris_svg,
)

A = "unit-00000000000a"
B = "unit-00000000000b"
C = "unit-00000000000c"
D = "unit-00000000000d"


def unit(unit_id, label=None):
    return {
        "id": unit_id,
        "label": label or unit_id[-1].upper(),
        "unit_type": "deposit",
        "description": None,
        "source_refs": [],
    }


def relation(number, younger_id, older_id):
    return {
        "id": f"rel-{number:012x}",
        "younger_id": younger_id,
        "older_id": older_id,
        "kind": "above",
        "evidence": "",
        "source": "manual",
        "notes": None,
    }


def correlation(number, unit_ids):
    return {
        "id": f"corr-{number:012x}",
        "unit_ids": unit_ids,
        "notes": None,
    }


def matrix(
    *,
    units=(),
    relations=(),
    correlations=(),
    title="T123 Harris Matrix",
    site="Poggio Civitate",
    trench="T123",
):
    return HarrisMatrix.model_validate(
        {
            "schema_version": 1,
            "matrix_id": "0123456789ab",
            "revision": 4,
            "title": title,
            "site": site,
            "trench": trench,
            "notes": "",
            "source_job_ids": [],
            "units": list(units),
            "relations": list(relations),
            "correlations": list(correlations),
            "suggestions": [],
            "created_at": "2026-07-28T08:00:00+00:00",
            "updated_at": "2026-07-28T09:30:00+00:00",
        }
    )


def parse(svg):
    return ElementTree.fromstring(svg)


def elements(root, name):
    return root.findall(f".//{{http://www.w3.org/2000/svg}}{name}")


def display_nodes(root):
    return {
        group.attrib["data-representative-id"]: group
        for group in elements(root, "g")
        if group.attrib.get("class") == "harris-node"
    }


def node_y(group):
    rect = next(
        child for child in group if child.tag == "{http://www.w3.org/2000/svg}rect"
    )
    return float(rect.attrib["y"])


def test_single_node_svg_contains_metadata_and_one_display_node():
    root = parse(render_harris_svg(matrix(units=[unit(A, "Locus 7")])))

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert list(display_nodes(root)) == [A]
    text = " ".join(root.itertext())
    assert "T123 Harris Matrix" in text
    assert "Poggio Civitate" in text
    assert "T123" in text
    assert "2026-07-28T09:30:00+00:00" in text
    assert "1 graph warning" in text


def test_linear_three_node_graph_ranks_top_to_bottom():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[relation(1, A, B), relation(2, B, C)],
    )

    nodes = display_nodes(parse(render_harris_svg(graph)))

    assert node_y(nodes[A]) < node_y(nodes[B]) < node_y(nodes[C])


def test_branch_and_merge_uses_longest_path_ranks():
    graph = matrix(
        units=[unit(A), unit(B), unit(C), unit(D)],
        relations=[
            relation(1, A, B),
            relation(2, A, C),
            relation(3, B, D),
            relation(4, C, D),
        ],
    )

    nodes = display_nodes(parse(render_harris_svg(graph)))

    assert node_y(nodes[A]) < node_y(nodes[B])
    assert node_y(nodes[A]) < node_y(nodes[C])
    assert node_y(nodes[B]) == node_y(nodes[C])
    assert node_y(nodes[B]) < node_y(nodes[D])


def test_disconnected_components_render_in_stable_label_order():
    graph = matrix(
        units=[
            unit(D, "Delta"),
            unit(B, "Bravo"),
            unit(C, "Charlie"),
            unit(A, "Alpha"),
        ],
        relations=[relation(1, A, B), relation(2, C, D)],
    )

    first = render_harris_svg(graph)
    second = render_harris_svg(
        graph.model_copy(update={"units": list(reversed(graph.units))})
    )

    assert first == second
    root = parse(first)
    rank_zero = sorted(
        (
            float(
                next(child for child in group if child.tag.endswith("rect")).attrib["x"]
            ),
            representative,
        )
        for representative, group in display_nodes(root).items()
        if node_y(group)
        == min(node_y(candidate) for candidate in display_nodes(root).values())
    )
    assert [representative for _x, representative in rank_zero] == [A, C]


def test_correlated_labels_collapse_in_stable_label_order():
    graph = matrix(
        units=[unit(A, "Zeta"), unit(B, "alpha"), unit(C, "Older")],
        relations=[relation(1, A, C)],
        correlations=[correlation(1, [B, A])],
    )

    root = parse(render_harris_svg(graph))
    nodes = display_nodes(root)
    label_texts = [
        "".join(text.itertext())
        for text in elements(root, "text")
        if text.attrib.get("class") == "harris-node-label"
    ]

    assert set(nodes) == {A, C}
    assert "alpha = Zeta" in label_texts


def test_correlation_collapse_relation_error_rejects_rendering():
    graph = matrix(
        units=[unit(A), unit(B)],
        relations=[relation(1, A, B)],
        correlations=[correlation(1, [A, B])],
    )

    with pytest.raises(HarrisRenderError, match="relation-within-correlation"):
        render_harris_svg(graph)


def test_transitive_redundant_edge_is_not_drawn():
    graph = matrix(
        units=[unit(A), unit(B), unit(C)],
        relations=[
            relation(1, A, B),
            relation(2, B, C),
            relation(3, A, C),
        ],
    )

    root = parse(render_harris_svg(graph))

    assert (
        len(
            [
                line
                for line in elements(root, "line")
                if line.attrib.get("class") == "harris-edge"
            ]
        )
        == 2
    )
    assert len(graph.relations) == 3


def test_every_saved_unit_label_appears_once_in_display_labels():
    labels = ["Locus 7", "Cut 12", "Wall 3"]
    graph = matrix(
        units=[
            unit(A, labels[0]),
            unit(B, labels[1]),
            unit(C, labels[2]),
        ],
    )

    root = parse(render_harris_svg(graph))
    displayed = " | ".join(
        "".join(text.itertext())
        for text in elements(root, "text")
        if text.attrib.get("class") == "harris-node-label"
    )

    for label in labels:
        assert displayed.count(label) == 1


def test_xml_sensitive_and_script_looking_text_is_escaped_and_inert():
    hostile = '<script src="https://evil.example/x">& "locus"</script>'
    svg = render_harris_svg(
        matrix(
            units=[unit(A, hostile)],
            title='Title <& "quoted">',
            site="Site & trench",
        )
    )

    root = parse(svg)

    assert hostile in " ".join(root.itertext())
    assert "<script" not in svg.casefold()
    assert "&lt;script" in svg.casefold()
    assert "https://evil.example/x" in " ".join(root.itertext())
    assert not elements(root, "script")


def test_repeated_renders_are_byte_identical():
    graph = matrix(
        units=[unit(B), unit(A)],
        relations=[relation(1, A, B)],
    )

    assert render_harris_svg(graph) == render_harris_svg(graph)


@pytest.mark.parametrize(
    "graph",
    [
        matrix(),
        matrix(units=[unit(A)]),
    ],
)
def test_width_height_and_viewbox_are_positive(graph):
    root = parse(render_harris_svg(graph))
    viewbox = [float(value) for value in root.attrib["viewBox"].split()]

    assert float(root.attrib["width"]) > 0
    assert float(root.attrib["height"]) > 0
    assert viewbox[0:2] == [0, 0]
    assert viewbox[2] > 0
    assert viewbox[3] > 0


def test_more_than_250_units_gives_focused_error():
    graph = matrix(
        units=[unit(f"unit-{number:012x}", f"Unit {number}") for number in range(251)]
    )

    with pytest.raises(
        HarrisRenderError,
        match=r"250.*251|251.*250",
    ):
        render_harris_svg(graph)


def test_svg_has_no_active_or_external_content_or_server_path():
    svg = render_harris_svg(matrix(units=[unit(A, "Safe")]))
    lowered = svg.casefold()

    assert "/users/" not in lowered
    assert "file://" not in lowered
    assert "<script" not in lowered
    assert "<foreignobject" not in lowered
    assert "<image" not in lowered
    assert "<link" not in lowered
    assert not re.search(r"(?:href|src)=[\"']https?://", lowered)


def test_youngest_node_y_coordinate_is_less_than_oldest():
    graph = matrix(
        units=[unit(A, "Youngest"), unit(B, "Oldest")],
        relations=[relation(1, A, B)],
    )

    nodes = display_nodes(parse(render_harris_svg(graph)))

    assert node_y(nodes[A]) < node_y(nodes[B])
