"""Graph validation survives a matrix deeper than Python's recursion limit.

Every stored matrix is validated on load and on save, and nothing caps the unit
count. While the cycle search recursed, a long enough chain of relations turned
a matrix that should merely be reported on into a RecursionError, which the app
surfaces as a 500 rather than a finding.
"""

import sys

from pipeline.harris_matrix import _find_cycle


def _chain(length):
    nodes = {f"n{index}" for index in range(length)}
    edges = {(f"n{index}", f"n{index + 1}") for index in range(length - 1)}
    return nodes, edges


def test_a_long_acyclic_chain_reports_no_cycle():
    depth = sys.getrecursionlimit() * 3
    nodes, edges = _chain(depth)
    assert _find_cycle(nodes, edges) is None


def test_a_cycle_closing_a_long_chain_is_still_found():
    depth = sys.getrecursionlimit() * 3
    nodes, edges = _chain(depth)
    edges.add((f"n{depth - 1}", "n0"))

    cycle = _find_cycle(nodes, edges)

    assert cycle is not None
    assert cycle[0] == cycle[-1] == "n0"
    assert len(cycle) == depth + 1


def test_traversal_order_is_unchanged_on_a_small_graph():
    """The iterative search visits starts in sorted order and neighbours in
    the order _adjacency imposes, so the reported cycle is the same one the
    recursive search reported."""
    nodes = {"a", "b", "c", "d"}
    edges = {("a", "b"), ("b", "c"), ("c", "a"), ("a", "d")}

    assert _find_cycle(nodes, edges) == ["a", "b", "c", "a"]


def test_a_self_contained_cycle_reached_from_elsewhere_is_reported():
    nodes = {"a", "b", "c"}
    edges = {("a", "b"), ("b", "c"), ("c", "b")}

    assert _find_cycle(nodes, edges) == ["b", "c", "b"]
