"""Library-level acceptance tests for ``article_graph.analyze`` (AC-1..AC-12)."""

from __future__ import annotations

import copy
import socket
import unittest
from unittest import mock

from article_graph import analyze

GRAPH_AB = {"nodes": ["A", "B"], "edges": [["A", "B"]]}
EXPECTED_AB = {
    "path": ["A", "B"],
    "reachable": ["A", "B"],
    "degrees": [
        {"id": "A", "in": 0, "out": 1},
        {"id": "B", "in": 1, "out": 0},
    ],
}


class AnalyzeExampleTests(unittest.TestCase):
    def test_ac1_example(self) -> None:
        self.assertEqual(analyze(GRAPH_AB, "A", "B"), EXPECTED_AB)

    def test_ac2_no_path(self) -> None:
        result = analyze(GRAPH_AB, "B", "A")
        self.assertEqual(
            result,
            {
                "path": None,
                "reachable": ["B"],
                "degrees": EXPECTED_AB["degrees"],
            },
        )

    def test_ac3_source_equals_target(self) -> None:
        self.assertEqual(analyze(GRAPH_AB, "A", "A")["path"], ["A"])
        looping = {"nodes": ["A"], "edges": [["A", "A"]]}
        self.assertEqual(analyze(looping, "A", "A")["path"], ["A"])

    def test_ac4_tie_break_is_independent_of_input_order(self) -> None:
        edges = [["A", "C"], ["C", "D"], ["A", "B"], ["B", "D"]]
        for ordered in (edges, list(reversed(edges))):
            graph = {"nodes": ["D", "C", "B", "A"], "edges": ordered}
            self.assertEqual(analyze(graph, "A", "D")["path"], ["A", "B", "D"])

    def test_ac5_duplicates_and_loops_count_once(self) -> None:
        graph = {
            "nodes": ["A", "B"],
            "edges": [["A", "B"], ["A", "B"], ["A", "A"], ["A", "A"]],
        }
        result = analyze(graph, "A", "B")
        self.assertEqual(
            result["degrees"],
            [
                {"id": "A", "in": 1, "out": 2},
                {"id": "B", "in": 1, "out": 0},
            ],
        )

    def test_ac6_cycle_terminates(self) -> None:
        graph = {"nodes": ["A", "B"], "edges": [["A", "B"], ["B", "A"]]}
        self.assertEqual(analyze(graph, "A", "A")["reachable"], ["A", "B"])
        self.assertEqual(analyze(graph, "A", "B")["path"], ["A", "B"])

    def test_ac7_isolated_node_has_zero_degrees(self) -> None:
        graph = {"nodes": ["A", "B"], "edges": [["A", "A"]]}
        self.assertEqual(
            analyze(graph, "A", "A")["degrees"],
            [
                {"id": "A", "in": 1, "out": 1},
                {"id": "B", "in": 0, "out": 0},
            ],
        )

    def test_ac11_input_is_not_mutated_and_calls_are_independent(self) -> None:
        graph = copy.deepcopy(GRAPH_AB)
        snapshot = copy.deepcopy(graph)
        first = analyze(graph, "A", "B")
        self.assertEqual(graph, snapshot)
        first["path"].append("MUTATED")
        second = analyze(graph, "A", "B")
        self.assertEqual(second, EXPECTED_AB)
        self.assertEqual(graph, snapshot)


class AnalyzeLexicographicTests(unittest.TestCase):
    def test_ids_are_compared_element_by_element_not_concatenated(self) -> None:
        graph = {
            "nodes": ["A", "B", "BA", "Z"],
            "edges": [["A", "B"], ["B", "Z"], ["A", "BA"], ["BA", "Z"]],
        }
        # Element-wise: ["A", "B", "Z"] < ["A", "BA", "Z"].
        # Concatenation would wrongly prefer "A" + "BAZ" over "A" + "BZ".
        self.assertEqual(analyze(graph, "A", "Z")["path"], ["A", "B", "Z"])

    def test_multi_candidate_tie_break_uses_complete_path(self) -> None:
        graph = {
            "nodes": ["S", "A", "B", "Z", "T"],
            "edges": [
                ["S", "A"],
                ["A", "Z"],
                ["Z", "T"],
                ["A", "B"],
                ["B", "T"],
            ],
        }
        # Equal length 4: ["S", "A", "B", "T"] vs ["S", "A", "Z", "T"].
        self.assertEqual(analyze(graph, "S", "T")["path"], ["S", "A", "B", "T"])

    def test_ascii_order(self) -> None:
        graph = {
            "nodes": ["a", "B", "1", "Z"],
            "edges": [["Z", "a"], ["1", "B"]],
        }
        result = analyze(graph, "Z", "a")
        self.assertEqual(result["reachable"], ["Z", "a"])
        self.assertEqual([item["id"] for item in result["degrees"]], ["1", "B", "Z", "a"])


class AnalyzeValidationTests(unittest.TestCase):
    def assert_invalid(self, graph: object, source: object = "A", target: object = "A") -> None:
        with self.assertRaises(ValueError):
            analyze(graph, source, target)

    def test_ac8_edge_to_missing_node(self) -> None:
        self.assert_invalid({"nodes": ["A"], "edges": [["A", "B"]]})

    def test_ac8_duplicate_nodes(self) -> None:
        self.assert_invalid({"nodes": ["A", "A"], "edges": []})

    def test_ac8_unknown_source_and_target(self) -> None:
        self.assert_invalid({"nodes": ["A"], "edges": []}, "B", "A")
        self.assert_invalid({"nodes": ["A"], "edges": []}, "A", "B")

    def test_empty_graph_queries_fail(self) -> None:
        self.assert_invalid({"nodes": [], "edges": []}, "A", "A")

    def test_invalid_graph_shapes(self) -> None:
        invalid_graphs = [
            None,
            [],
            "graph",
            {},
            {"nodes": ["A"]},
            {"nodes": ["A"], "edges": [], "extra": 1},
            {"nodes": ("A",), "edges": []},
            {"nodes": ["A"], "edges": ()},
            {"nodes": ["A"], "edges": [("A", "A")]},
            {"nodes": ["A"], "edges": [["A"]]},
            {"nodes": ["A"], "edges": [["A", "A", "A"]]},
            {"nodes": ["A"], "edges": ["AA"]},
            {"nodes": ["A"], "edges": [[1, "A"]]},
        ]
        for graph in invalid_graphs:
            with self.subTest(graph=graph):
                self.assert_invalid(graph)

    def test_invalid_ids(self) -> None:
        bad_ids = ["", "A" * 33, "A B", "A.B", "Ä", "A/B", 1, None, True]
        for bad in bad_ids:
            with self.subTest(bad=bad):
                self.assert_invalid({"nodes": [bad], "edges": []}, bad, bad)
                self.assert_invalid({"nodes": ["A"], "edges": []}, bad, "A")
                self.assert_invalid({"nodes": ["A"], "edges": []}, "A", bad)

    def test_id_length_boundaries(self) -> None:
        valid32 = "a" * 32
        graph = {"nodes": [valid32], "edges": []}
        self.assertEqual(analyze(graph, valid32, valid32)["path"], [valid32])
        self.assert_invalid({"nodes": ["a" * 33], "edges": []})

    def test_extra_fields_in_degree_objects_do_not_exist(self) -> None:
        degree = analyze(GRAPH_AB, "A", "B")["degrees"][0]
        self.assertEqual(set(degree), {"id", "in", "out"})
        self.assertIs(type(degree["in"]), int)
        self.assertIs(type(degree["out"]), int)


class AnalyzeLimitTests(unittest.TestCase):
    @staticmethod
    def graph_with_limits(node_count: int, edge_count: int) -> dict[str, list]:
        nodes = [f"N{index}" for index in range(node_count)]
        base = [[nodes[index], nodes[(index + 1) % node_count]] for index in range(node_count)]
        edges = [base[index % len(base)] for index in range(edge_count)]
        return {"nodes": nodes, "edges": edges}

    def test_ac10_maximum_limits_are_inclusive_and_accepted(self) -> None:
        graph = self.graph_with_limits(1000, 10000)
        result = analyze(graph, "N0", "N999")
        self.assertEqual(len(result["degrees"]), 1000)
        self.assertEqual(len(result["path"]), 1000)

    def test_ac10_above_limits_rejected(self) -> None:
        with self.assertRaises(ValueError):
            analyze(self.graph_with_limits(1001, 0), "N0", "N0")
        with self.assertRaises(ValueError):
            analyze(self.graph_with_limits(2, 10001), "N0", "N1")


class AnalyzeIsolationTests(unittest.TestCase):
    def test_ac12_no_network_access(self) -> None:
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network used")):
            self.assertEqual(analyze(GRAPH_AB, "A", "B"), EXPECTED_AB)


if __name__ == "__main__":
    unittest.main()
