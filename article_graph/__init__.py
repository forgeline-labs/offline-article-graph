"""Offline directed article graph analysis.

Public API: :func:`analyze`.
"""

from __future__ import annotations

import re
from collections import deque

__all__ = ["analyze"]

__version__ = "0.1.0"

_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,32}")
_MAX_NODES = 1000
_MAX_EDGES = 10000


def _require_id(value: object, what: str) -> str:
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{what} must match [A-Za-z0-9_-]{{1,32}}")
    return value


def _parse_graph(graph: object) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Validate ``graph`` and return the adjacency map and unique edges."""
    if not isinstance(graph, dict):
        raise ValueError("graph must be a JSON object")
    if set(graph.keys()) != {"nodes", "edges"}:
        raise ValueError("graph must contain exactly 'nodes' and 'edges'")

    nodes = graph["nodes"]
    edges = graph["edges"]
    if not isinstance(nodes, list):
        raise ValueError("'nodes' must be a list")
    if not isinstance(edges, list):
        raise ValueError("'edges' must be a list")
    if len(nodes) > _MAX_NODES:
        raise ValueError(f"'nodes' must contain at most {_MAX_NODES} items")
    if len(edges) > _MAX_EDGES:
        raise ValueError(f"'edges' must contain at most {_MAX_EDGES} items")

    adjacency: dict[str, list[str]] = {}
    for node in nodes:
        node_id = _require_id(node, "node id")
        if node_id in adjacency:
            raise ValueError(f"duplicate node id: {node_id}")
        adjacency[node_id] = []

    unique_edges: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, list):
            raise ValueError("each edge must be a list of two node ids")
        if len(edge) != 2:
            raise ValueError("each edge must contain exactly two node ids")
        source = _require_id(edge[0], "edge id")
        target = _require_id(edge[1], "edge id")
        if source not in adjacency:
            raise ValueError(f"edge source is not a known node: {source}")
        if target not in adjacency:
            raise ValueError(f"edge target is not a known node: {target}")
        pair = (source, target)
        if pair not in seen:
            seen.add(pair)
            unique_edges.append(pair)
            adjacency[source].append(target)

    return adjacency, unique_edges


def _breadth_first_distances(adjacency: dict[str, list[str]], source: str) -> dict[str, int]:
    """Return the BFS distance from ``source`` to every reachable node."""
    distance = {source: 0}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current]:
            if neighbour not in distance:
                distance[neighbour] = distance[current] + 1
                queue.append(neighbour)
    return distance


def _shortest_path(
    adjacency: dict[str, list[str]],
    distance: dict[str, int],
    source: str,
    target: str,
) -> list[str] | None:
    """Shortest directed path, ties broken by the smallest full ID sequence."""
    if target not in distance:
        return None
    if source == target:
        return [source]

    predecessors: dict[str, list[str]] = {node: [] for node in distance}
    for node, neighbours in adjacency.items():
        if node not in distance:
            continue
        for neighbour in neighbours:
            if neighbour in distance:
                predecessors[neighbour].append(node)

    layers: dict[int, list[str]] = {}
    for node, level in distance.items():
        layers.setdefault(level, []).append(node)

    best: dict[str, tuple[str, ...]] = {source: (source,)}
    for level in range(1, distance[target] + 1):
        for node in layers.get(level, []):
            candidates = [
                best[parent] + (node,)
                for parent in predecessors[node]
                if distance[parent] == level - 1
            ]
            # Every reachable node at ``level`` has at least one such parent.
            best[node] = min(candidates)
    return list(best[target])


def analyze(graph: object, source: object, target: object) -> dict[str, object]:
    """Analyze a directed article graph.

    ``graph`` is an exact dict ``{"nodes": [...], "edges": [[...], ...]}``.
    Returns ``{"path": list[str] | None, "reachable": list[str],
    "degrees": [{"id": str, "in": int, "out": int}, ...]}``.
    Invalid input raises :class:`ValueError`. The input is never mutated and
    no I/O (including network access) is performed.
    """
    adjacency, unique_edges = _parse_graph(graph)

    source_id = _require_id(source, "source id")
    target_id = _require_id(target, "target id")
    if source_id not in adjacency:
        raise ValueError(f"unknown source id: {source_id}")
    if target_id not in adjacency:
        raise ValueError(f"unknown target id: {target_id}")

    distance = _breadth_first_distances(adjacency, source_id)
    path = _shortest_path(adjacency, distance, source_id, target_id)
    reachable = sorted(distance)

    in_degree = dict.fromkeys(adjacency, 0)
    out_degree = dict.fromkeys(adjacency, 0)
    for edge_source, edge_target in unique_edges:
        out_degree[edge_source] += 1
        in_degree[edge_target] += 1

    degrees = [
        {"id": node, "in": in_degree[node], "out": out_degree[node]} for node in sorted(adjacency)
    ]

    return {"path": path, "reachable": reachable, "degrees": degrees}
