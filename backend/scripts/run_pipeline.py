"""One entrypoint for the full batch pipeline (spec 007 FR-005): ingest → flag → dbt build → train.

The deployed **scheduled Fargate task** (`infra/ecs.tf`) runs this single command; it mirrors what
`make ingest flag dbt-build train` do locally, fail-fast, so the schedule has exactly one thing to
invoke and the same governed sequence runs unattended in the cloud (reading RDS + S3 via env).

Reference entrypoint for the deploy: paths assume the backend is the working tree in the image; a
credentialed session should confirm the image WORKDIR + that `dbt`/`python` are on PATH.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent

# (label, argv, cwd). Fixed, trusted commands — no user input (S603/S607 are false positives).
STEPS: list[tuple[str, list[str], Path]] = [
    ("pull WDI", [sys.executable, "scripts/pull_wdi.py"], BACKEND),
    ("load WDI", [sys.executable, "scripts/load_wdi.py"], BACKEND),
    ("flag quality", [sys.executable, "scripts/flag_quality.py"], BACKEND),
    ("dbt build", ["dbt", "build", "--profiles-dir", "."], BACKEND / "dbt"),
    ("train", [sys.executable, "-m", "ml.train"], BACKEND),
]


def main() -> int:
    for label, argv, cwd in STEPS:
        print(f"=== {label}: {' '.join(argv)} (cwd={cwd})", flush=True)
        result = subprocess.run(argv, cwd=cwd)  # noqa: S603
        if result.returncode != 0:
            print(f"pipeline halted at '{label}' (exit {result.returncode})", file=sys.stderr)
            return result.returncode
    print("pipeline complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
