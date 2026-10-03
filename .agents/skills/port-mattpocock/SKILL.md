---
name: port-mattpocock
description: Sync Matt Pocock's skills (github.com/mattpocock/skills) into the agent-setup repo, keeping the user's local edits to them. Use when the user asks to add, update, pull or re-sync the mattpocock skills, check what changed upstream, or fix a failed sync.
---

# Port mattpocock/skills

The agent-setup repo keeps its own copy of Matt's skills in `skills/mattpocock/<name>/`, plus his `README.md` and `LICENSE` as `skills/mattpocock/README.md` and `skills/mattpocock/LICENSE`, so the user can edit them. This port pulls upstream changes into those copies. It's a project-local skill of the agent-setup repo (`.agents/skills/`), not installed globally. `scripts/port-mattpocock` next to this file fetches the repo, reads the published skills from `.claude-plugin/plugin.json` (they're nested upstream as `skills/engineering/tdd` and so on), and hands them to the repo's `scripts/vendor_sync.py`.

`skills/mattpocock/upstream.json` records the upstream commit last synced, where each skill lives upstream, and which skills the user dropped.

## Sync

1. `.agents/skills/port-mattpocock/scripts/port-mattpocock --dry-run`, from the repo root. Show the user the summary: skills added, files updated or merged, conflicts.
2. The same without `--dry-run`. For each file it merges three versions: the last-synced commit, the new upstream, and the local copy.
   - Untouched locally: takes upstream.
   - Edited locally, untouched upstream: keeps the edit.
   - Edited on both sides: merges, and leaves `<<<<<<< local` / `>>>>>>> upstream` markers where they clash.
3. If it exits 1, resolve every conflict it lists. Keep the user's intent and take upstream's other improvements; ask when unsure.
4. Show `git diff --stat`, then offer to commit, and to run `./install.sh` so the agents pick up the changes.

## Drop or keep skills

- To drop a skill, delete its `skills/mattpocock/<name>/` folder. The next sync records it as excluded and never re-adds it. To bring it back, remove it from `excluded` in the lock.
- New skills upstream are added automatically.
- Skills removed upstream are deleted if unmodified, otherwise kept.

## When it breaks

The script stops if `.claude-plugin/plugin.json` is missing or a listed folder has no `SKILL.md`: upstream changed its layout. Look at the clone in `~/.cache/agent-setup/upstream/mattpocock` and update this script's skill listing. Leave `vendor_sync.py` alone; it's shared by every port.
