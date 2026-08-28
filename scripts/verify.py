"""Run lint, tests, and evaluation thresholds for CI and local development."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERAGE_HTML = ROOT / "htmlcov" / "index.html"
COVERAGE_XML = ROOT / "coverage.xml"


def run(cmd: list[str]) -> int:
    print(f">>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    return result.returncode


def main() -> int:
    steps = [
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "python", "-m", "pytest", "-q"],
        ["uv", "run", "python", "scripts/evaluate.py"],
    ]
    for step in steps:
        code = run(step)
        if code != 0:
            return code

    print("All verification steps passed (including evaluation thresholds).")
    print(
        "Coverage: run `make coverage` or "
        "`uv run python -m coverage run -m pytest -q && uv run python -m coverage html` "
        f"to generate {COVERAGE_HTML.relative_to(ROOT)} "
        f"(or {COVERAGE_XML.name} with --cov-report=xml)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
