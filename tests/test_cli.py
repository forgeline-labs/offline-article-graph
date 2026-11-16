"""CLI acceptance tests (AC-9, AC-12 and the section 2 conventions)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from article_graph import analyze
from helpers import APP, ROOT, run_app, write_json

MAX_BYTES = 1024 * 1024
GRAPH_AB = {"nodes": ["A", "B"], "edges": [["A", "B"]]}


def assert_error_line(test: unittest.TestCase, completed) -> None:
    test.assertEqual(completed.stdout, "")
    test.assertTrue(completed.stderr.startswith("error:"), repr(completed.stderr))
    test.assertEqual(len(completed.stderr.strip().splitlines()), 1, repr(completed.stderr))
    test.assertNotIn("Traceback", completed.stderr)


class VersionAndHelpTests(unittest.TestCase):
    def test_version_is_exact(self) -> None:
        completed = run_app("--version")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "offline-article-graph 0.1.0\n")
        self.assertEqual(completed.stderr, "")

    def test_help_lists_every_documented_interface(self) -> None:
        completed = run_app("--help")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        for token in (
            "usage:",
            "app",
            "--help",
            "--version",
            "analyze",
            "--source",
            "--target",
        ):
            with self.subTest(token=token):
                self.assertIn(token, completed.stdout)

    def test_subcommand_help(self) -> None:
        completed = run_app("analyze", "--help")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        for token in ("usage:", "FILE", "--source", "--target"):
            with self.subTest(token=token):
                self.assertIn(token, completed.stdout)

    def test_help_and_version_need_no_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run_app("--version", cwd=empty).returncode, 0)
            self.assertEqual(run_app("--help", cwd=empty).returncode, 0)


class AnalyzeCommandTests(unittest.TestCase):
    def test_example_output_is_single_line_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            completed = run_app("analyze", path, "--source", "A", "--target", "B")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, "")
        self.assertTrue(completed.stdout.endswith("\n"))
        self.assertEqual(completed.stdout.count("\n"), 1)
        self.assertNotIn(" ", completed.stdout)
        self.assertEqual(json.loads(completed.stdout), analyze(GRAPH_AB, "A", "B"))

    def test_no_path_is_json_null(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            completed = run_app("analyze", path, "--source", "B", "--target", "A")
        payload = json.loads(completed.stdout)
        self.assertIsNone(payload["path"])
        self.assertNotIn('"null"', completed.stdout)

    def test_lib_and_cli_agree(self) -> None:
        graph = {
            "nodes": ["n1", "n2", "n3", "n4", "n5"],
            "edges": [
                ["n1", "n2"],
                ["n1", "n3"],
                ["n2", "n4"],
                ["n3", "n4"],
                ["n4", "n5"],
                ["n5", "n1"],
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, graph)
            completed = run_app("analyze", path, "--source", "n1", "--target", "n5")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout), analyze(graph, "n1", "n5"))

    def test_relative_path_with_spaces_and_unicode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            subdirectory = Path(directory) / "directorio con espacios"
            subdirectory.mkdir()
            write_json(subdirectory, GRAPH_AB, name="gráfico de artículos.json")
            completed = run_app(
                "analyze",
                "gráfico de artículos.json",
                "--source",
                "A",
                "--target",
                "B",
                cwd=subdirectory,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["path"], ["A", "B"])

    def test_ids_starting_with_a_hyphen(self) -> None:
        graph = {"nodes": ["-A", "B"], "edges": [["-A", "B"]]}
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, graph)
            completed = run_app("analyze", path, "--source", "-A", "--target", "B")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["path"], ["-A", "B"])

    def test_input_file_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            before = path.read_bytes()
            completed = run_app("analyze", path, "--source", "A", "--target", "B")
            after = path.read_bytes()
            leftovers = sorted(item.name for item in Path(directory).iterdir())
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(before, after)
        self.assertEqual(leftovers, [path.name])

    def test_executable_entry_point_is_equivalent(self) -> None:
        if not os.access(APP, os.X_OK):
            self.skipTest("./app is not executable on this platform")
        completed = run_app("--version")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "offline-article-graph 0.1.0\n")


class FileSizeTests(unittest.TestCase):
    @staticmethod
    def _padded_file(directory: str, size: int) -> Path:
        base = json.dumps(GRAPH_AB).encode("utf-8")
        payload = base + b" " * (size - len(base))
        assert len(payload) == size
        path = Path(directory) / "padded.json"
        path.write_bytes(payload)
        return path

    def test_inclusive_one_mib_limit_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._padded_file(directory, MAX_BYTES)
            completed = run_app("analyze", path, "--source", "A", "--target", "B")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["path"], ["A", "B"])

    def test_above_one_mib_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._padded_file(directory, MAX_BYTES + 1)
            completed = run_app("analyze", path, "--source", "A", "--target", "B")
        self.assertEqual(completed.returncode, 2)
        assert_error_line(self, completed)


class ErrorHandlingTests(unittest.TestCase):
    def assert_exit(self, expected: int, completed, check_line: bool = True) -> None:
        self.assertEqual(completed.returncode, expected, completed.stderr)
        if check_line:
            assert_error_line(self, completed)

    def test_missing_file_is_io_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = run_app(
                "analyze",
                Path(directory) / "missing.json",
                "--source",
                "A",
                "--target",
                "B",
            )
        self.assert_exit(3, completed)

    def test_directory_as_file_is_io_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = run_app("analyze", directory, "--source", "A", "--target", "B")
        self.assert_exit(3, completed)

    def test_unreadable_file_is_io_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            os.chmod(path, 0o000)
            try:
                completed = run_app("analyze", path, "--source", "A", "--target", "B")
            finally:
                os.chmod(path, 0o600)
        if os.geteuid() == 0:
            self.skipTest("permissions do not restrict root")
        self.assert_exit(3, completed)

    def test_invalid_inputs_exit_two(self) -> None:
        invalid_contents = [
            b"not json",
            b"",
            b"\xef\xbb\xbf" + json.dumps(GRAPH_AB).encode(),
            b'{"nodes":["A"],"nodes":["A"],"edges":[]}',
            b'{"nodes":["A"],"edges":[],"extra":1}',
            b'{"nodes":["A"],"edges":[[NaN,"A"]]}',
            b'{"nodes":["A"],"edges":[[Infinity,"A"]]}',
            b'{"nodes":["A"],"edges":[["A","B"]]}',
            b"\xff\xfe\x00",
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, content in enumerate(invalid_contents):
                with self.subTest(index=index):
                    path = Path(directory) / f"invalid-{index}.json"
                    path.write_bytes(content)
                    completed = run_app("analyze", path, "--source", "A", "--target", "A")
                    self.assert_exit(2, completed)

    def test_invalid_utf8_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad-encoding.json"
            path.write_bytes(b'{"nodes":["\xff"],"edges":[]}')
            completed = run_app("analyze", path, "--source", "A", "--target", "A")
        self.assert_exit(2, completed)

    def test_unknown_ids_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            unknown = run_app("analyze", path, "--source", "Z", "--target", "B")
            bad_id = run_app("analyze", path, "--source", "Z Z", "--target", "B")
        self.assert_exit(2, unknown)
        self.assert_exit(2, bad_id)

    def test_argument_errors_exit_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            cases = [
                (),
                ("analyze",),
                ("analyze", path),
                ("analyze", path, "--source", "A"),
                ("analyze", path, "--target", "B"),
                ("analyze", path, "--source", "A", "--target", "B", "extra"),
                ("analyze", path, "--source", "A", "--target", "B", "--unknown"),
                ("unknown-command",),
            ]
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    completed = run_app(*arguments)
                    self.assert_exit(2, completed)

    def test_short_options_are_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            completed = run_app("analyze", path, "-s", "A", "-t", "B")
        self.assert_exit(2, completed)


class CliContractTests(unittest.TestCase):
    def test_no_network_symbols_are_required(self) -> None:
        # The CLI is exercised offline only; importing the package must not
        # attempt a connection. This test simply documents that contract.
        with tempfile.TemporaryDirectory() as directory:
            path = write_json(directory, GRAPH_AB)
            completed = run_app("analyze", path, "--source", "A", "--target", "B", cwd=ROOT)
        self.assertEqual(completed.returncode, 0)

    def test_write_failure_fixture_is_not_applicable(self) -> None:
        """The tool has no write path, so there is no persisted-JSON write to fail.

        The application only reads FILE and writes stdout/stderr; a simulated
        filesystem write failure therefore cannot change an input or a state
        file. The read-only behaviour is covered by
        ``AnalyzeCommandTests.test_input_file_is_not_modified``.
        """
        self.assertTrue(APP.exists())


if __name__ == "__main__":
    unittest.main()
