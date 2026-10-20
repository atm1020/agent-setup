#!/usr/bin/env python3
"""Check the vendored Cursor instructions against this port's OpenCode adaptations."""

import argparse
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[3]
RULES = {
    "cursor-task": re.compile(r"\bTask(?:`| tool| calls?\b| spawn\b)|\bsubagent_type\b|\bgeneralPurpose\b|\brun_in_background\b"),
    "cursor-path": re.compile(r"agent-transcripts/|(?:~?/)?\.cursor/(?:skills|projects|plugins)/|pstack-models\.mdc"),
    "unsupported-model": re.compile(r"\b(?:grok|cursor-grok|claude-opus|composer)-[\w.-]+"),
    "deleted-workflow": re.compile(r"\bwatch-pr\b|playbooks/opening-a-pr\.md|\bOpening a PR\b|\bmake-bot-ui\b"),
    "origin-cli": re.compile(r"\borigin pr\b|--forge origin\b"),
    "cursor-loop": re.compile(r"\b(?:arm|run|use|start|re-arm)\s+`?/loop\b", re.I),
    "cloud-worker": re.compile(r"environment:\s*[\"']cloud[\"']|\b(?:a|each|as) (?:Cursor )?cloud agent\b", re.I),
}
REMOVED = (
    "poteto-mode/playbooks/opening-a-pr.md",
    "poteto-mode/scripts/watch-pr",
    "poteto-mode/references/bugbot-triage.md",
    "make-bot-ui",
)


def errors(source):
    root = source / "skills/cursor"
    if not root.exists():
        return []
    findings = []
    for name in REMOVED:
        if (root / name).exists():
            findings.append(f"skills/cursor/{name}: deleted workflow was restored")
    # README is upstream provenance, not an installed instruction. Code can retain
    # optional forge adapters; the workflow instructions must use GitHub only.
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if len(relative.parts) == 1:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            for rule, pattern in RULES.items():
                if pattern.search(line):
                    findings.append(f"{path.relative_to(source)}:{number}: {rule}: {line.strip()}")
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO)
    args = parser.parse_args()
    findings = errors(args.source.resolve())
    for finding in findings:
        print(finding, file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
