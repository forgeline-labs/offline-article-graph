# Changelog

All notable changes to this project are documented here. This project adheres
to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic
versioning.

## [0.1.0] - 2026-11-16

### Added

- `article_graph.analyze(graph, source, target)` public API: shortest directed
  path with lexicographic tie-breaking, reachable set and exact integer
  in/out degrees.
- `app` executable (also usable as `python app`) with `--version`, `--help` and
  `analyze FILE --source ID --target ID`.
- Schema, ID, size and limit validation with deterministic exit codes (`2` for
  content/argument errors, `3` for I/O errors).
- Public black-box test suite in `tests/` traceable to AC-1..AC-12.
- README, MIT license, runtime/dev manifests and CI for Ubuntu and macOS on
  Python 3.12.
