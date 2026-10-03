---
name: port-herdr
description: Sync the herdr agent skill (github.com/herdrdev/herdr, skills/herdr) into the agent-setup repo, keeping the user's local edits. Use when the user asks to add, update, pull or re-sync the herdr skill, move it to a new herdr release, check what changed upstream, or fix a failed sync.
---

# Port herdrdev/herdr

Herdr is a terminal multiplexer for coding agents, and its repo ships an agent skill in `skills/herdr/`. The agent-setup repo keeps its own copy in `skills/herdr/herdr/`, plus herdr's `LICENSE` (Apache-2.0; herdr's README isn't kept), so the user can edit it. `scripts/port-herdr` next to this file fetches the repo, takes every folder under `skills/`, and passes them to the repo's `scripts/vendor_sync.py`. This is a project-local skill (`.agents/skills/`) and is never installed globally.

The skill describes the `herdr` CLI, so it's pinned to a release tag, not `main`. The lock's `ref` is that tag (now `v0.9.3`). Keep it at the release the user runs (`herdr --version`). `herdr --skill` prints the skill bundled with the installed binary, which is a quick way to compare.

This skill is separate from `herdr integration install <agent>`, which `install.sh` runs. That sets up herdr's agent hooks, not this skill.

## Sync

1. From the repo root, run `.agents/skills/port-herdr/scripts/port-herdr --dry-run`. To move to a new release, add `--ref vX.Y.Z`. Show the user the summary.
2. Run the same command without `--dry-run`. Each file is 3-way merged between the last-synced commit, the new upstream and the local copy. Clashing edits are left as `<<<<<<< local` / `>>>>>>> upstream` markers.
3. If it exits 1, resolve every conflict it lists. Keep the user's intent. Ask when unsure.
4. Show `git diff --stat`. Then offer to commit, and to run `./install.sh` so the agents pick up the changes.

## Drop or keep skills

- To drop a skill, delete its `skills/herdr/<name>/` folder. The next sync records it as excluded.
- New skills under upstream's `skills/` are added automatically.

## When it breaks

The script stops when upstream has no `skills/` folder, or a folder there has no `SKILL.md`. Look at the clone in `~/.cache/agent-setup/upstream/herdr` and fix this script. Leave `vendor_sync.py` alone, because every port shares it.
