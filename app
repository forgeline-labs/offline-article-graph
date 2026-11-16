#!/usr/bin/env python3
"""Command line entry point for the offline article graph explorer."""

from __future__ import annotations

import argparse
import json
import sys

from article_graph import analyze

VERSION = "offline-article-graph 0.1.0"
MAX_FILE_BYTES = 1024 * 1024


class InputError(Exception):
    """Invalid input content (exit code 2)."""


class FileReadError(Exception):
    """The input file could not be read (exit code 3)."""


class _Parser(argparse.ArgumentParser):
    """Argument parser that reports a single ``error:`` line on failure."""

    def error(self, message: str) -> None:  # type: ignore[override]
        raise SystemExit(_report(2, message))


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="app",
        description="Analyze a directed article graph from a local JSON snapshot.",
        epilog=(
            "commands:\n"
            "  analyze FILE --source ID --target ID\n"
            "\n"
            "options:\n"
            "  --help     show this help message and exit\n"
            "  --version  show the product version and exit"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version", action="version", version=VERSION, help="show the product version"
    )
    subcommands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    analyze_parser = subcommands.add_parser(
        "analyze",
        help="analyze a graph file",
        description="Analyze a graph file and print path, reachable nodes and degrees.",
        allow_abbrev=False,
    )
    analyze_parser.add_argument("file", metavar="FILE", help="graph JSON file (at most 1 MiB)")
    analyze_parser.add_argument("--source", required=True, metavar="ID", help="source node id")
    analyze_parser.add_argument("--target", required=True, metavar="ID", help="target node id")
    return parser


def _one_line(message: object) -> str:
    text = str(message).replace("\r", " ").replace("\n", " ").strip()
    return text or "unknown error"


def _report(exit_code: int, message: object) -> int:
    sys.stderr.write(f"error: {_one_line(message)}\n")
    return exit_code


def _reject_constant(value: str) -> None:
    raise InputError(f"invalid JSON constant: {value}")


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise InputError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _read_graph(path: str) -> object:
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
    except OSError as exc:
        raise FileReadError(exc.strerror or "cannot read input file") from exc

    if len(data) > MAX_FILE_BYTES:
        raise InputError(f"input file exceeds {MAX_FILE_BYTES} bytes")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"input file is not valid UTF-8 ({exc.reason})") from exc

    try:
        return json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_no_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}") from exc
    except RecursionError as exc:
        raise InputError("invalid JSON: nesting exceeds the recursion limit") from exc


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", newline="\n")
        except (AttributeError, ValueError):
            pass


_OPTION_STRINGS = {"-h", "--help", "--version", "--source", "--target"}


def _normalize_argv(argv: list[str]) -> list[str]:
    """Keep option values that start with ``-`` (valid IDs may do so)."""
    normalized: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ("--source", "--target") and index + 1 < len(argv):
            value = argv[index + 1]
            if value.startswith("-") and value not in _OPTION_STRINGS:
                normalized.append(f"{token}={value}")
                index += 2
                continue
        normalized.append(token)
        index += 1
    return normalized


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(_normalize_argv(raw_arguments))

    if args.command != "analyze":
        return _report(2, f"unknown command: {args.command}")

    try:
        graph = _read_graph(args.file)
        result = analyze(graph, args.source, args.target)
    except FileReadError as exc:
        return _report(3, f"cannot read input file: {exc}")
    except (InputError, ValueError) as exc:
        return _report(2, exc)

    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
