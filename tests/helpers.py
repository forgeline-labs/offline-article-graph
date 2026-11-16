"""Shared helpers for the black-box test suite."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def run_app(
    *arguments: object, cwd: str | os.PathLike[str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the CLI through the current interpreter and capture text output."""
    return subprocess.run(
        [sys.executable, str(APP), *(str(argument) for argument in arguments)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        check=False,
    )


def write_json(
    directory: str | os.PathLike[str], payload: object, name: str = "graph.json"
) -> Path:
    path = Path(directory) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
