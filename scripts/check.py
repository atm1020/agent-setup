#!/usr/bin/env python3
"""Validate repository text and run each upstream port's local checks."""

import argparse
import subprocess
import sys
from pathlib import Path
import re

REPO = Path(__file__).resolve().parent.parent
SKIP = {".git", "node_modules", "__pycache__", ".venv"}
MARKER = re.compile(r"^(?:<{7}(?: .*)?|={7}|>{7}(?: .*)?|\|{7}(?: .*)?)$")


def conflict_errors(source):
    errors = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if SKIP.intersection(relative.parts) or path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        for number, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
            if MARKER.fullmatch(line):
                errors.append(f"{relative}:{number}: unresolved merge marker")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO, help="repository to validate")
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / "skills").is_dir():
        parser.error(f"{source} has no skills directory")
    errors = conflict_errors(source)
    for error in errors:
        print(error, file=sys.stderr)
    failed = bool(errors)
    # Layout and harness rules belong to the port, not the shared checker.
    for checker in sorted((source / ".agents/skills").glob("port-*/check.py")):
        result = subprocess.run([sys.executable, str(checker), "--source", str(source)])
        failed = failed or result.returncode != 0
    if failed:
        print("Validation failed; resolve the findings before installing.", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
