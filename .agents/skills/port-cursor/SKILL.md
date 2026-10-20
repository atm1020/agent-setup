---
name: port-cursor
description: Sync the chosen plugins from Cursor's plugin marketplace (github.com/cursor/plugins), currently pstack plus the cursor-team-kit skills it uses, into the agent-setup repo, keeping the user's local edits. Use when the user asks to add, update, pull or re-sync pstack or other cursor plugins, add another cursor plugin or skill, check what changed upstream, or fix a failed sync.
---

# Port cursor/plugins

`cursor/plugins` is a marketplace of many plugins. The agent-setup repo vendors only a chosen subset into `skills/cursor/`, so the user can edit it. `scripts/port-cursor` next to this file fetches the repo and picks what to sync. It then hands the result to the repo's `scripts/vendor_sync.py`. This is a project-local skill (`.agents/skills/`) and is never installed globally.

What gets synced is set by two arrays at the top of the script:

- `WHOLE`: plugins taken in full (now `pstack`). Every folder under the plugin's `skills/` dir is synced, and so are new skills that appear upstream. Its agents folder becomes `skills/cursor/agents/<plugin>/`, which `port.py` installs as subagents. Its README becomes `README.<plugin>.md` and its license `LICENSE.<plugin>`.
- `PICKS`: single skills from other plugins, as `<plugin>/<skill>`. Right now these are `deslop`, `control-cli` and `control-ui` from `cursor-team-kit`. pstack's README lists them under "not shipped here", and `poteto-mode` calls them.

To add a plugin or skill, edit those arrays, then sync. Before adding a whole plugin, check its README and skills for skills it uses from other plugins, and add those to `PICKS`.

`skills/cursor/upstream.json` records the upstream commit last synced, where each skill lives upstream, and which skills the user dropped.

## Sync

1. From the repo root, run `.agents/skills/port-cursor/scripts/port-cursor --dry-run`, or `--list` to see only the selection. Show the user the summary: skills added, files updated or merged, conflicts.
2. Run the same command without `--dry-run`. For each file it merges three versions: the last-synced commit, the new upstream, and the local copy.
   - Untouched locally: takes upstream.
   - Edited locally, untouched upstream: keeps the edit.
   - Edited on both sides: merges, and leaves `<<<<<<< local` / `>>>>>>> upstream` markers where they clash.
3. If it exits 1, resolve every conflict it lists. Keep the user's intent and take upstream's other improvements. Ask when unsure.
4. Show `git diff --stat`. Then offer to commit, and to run `./install.sh` so the agents pick up the changes.

## Drop or keep skills

- To drop a skill, delete its `skills/cursor/<name>/` folder. The next sync records it as excluded and never re-adds it. To bring it back, remove it from `excluded` in the lock. Removing a name from `PICKS` alone stops its updates but leaves the copy in place.
- Skills are installed flat by name, so a name used by another upstream collides. `port.py` keeps the first one in sorted path order (`skills/cursor/` before `skills/mattpocock/`) and warns about the other. Delete the copy you don't want so the choice is explicit. Or rename it with the script's `RENAME` map (pstack's `tdd` and `teach` are `poteto-tdd` and `poteto-teach`), then rename its folder, its `name:` and its key in `upstream.json` to match.

## Adapted for OpenCode v2

Upstream targets Cursor. The local copies are edited to run in OpenCode v2, which is the user's main harness, and to use mostly GPT models. Keep these edits when resolving conflicts, and apply them to new upstream text:

- Subagents: `Task` → the `subagent` tool. `subagent_type: generalPurpose` → `agent: "general"`, and read-only → `agent: "explore"`. `run_in_background` → `background: true`. `Comment Sicko` → `comment-sicko`.
- Models are `provider/model[#effort]`. Code and explorer roles use `openai/gpt-6.1-sol`. Judgment, prose and synthesizer roles use `openai/gpt-6-astra`. Cross-model panels are `openai/gpt-6-astra`, `openai/gpt-6.1-sol`, `openai/gpt-5.6-sol`. The user has no Grok or Claude access, so never add them. "A different model family" upstream means a different GPT model here. Every skill that can spawn `openai/gpt-6-astra` carries the **Ask before astra** paragraph (ask once per task, fall back to `openai/gpt-6.1-sol` when unattended). New upstream spawn points need it too. Per-role overrides live in `~/.config/opencode/pstack-models.md` (written by `setup-pstack`), not `~/.cursor/rules/pstack-models.mdc`.
- Transcripts: `opencode session list --format json` / `opencode session export <id>` from the workspace root, not `agent-transcripts/`. `worktree-audit.sh` reads session directories from `~/.local/share/opencode/opencode.db`.
- No cloud agents: workers are local background subagents, each in its own git worktree.
- No `/loop`: a "wake loop" is a background watcher subagent that blocks (`gh pr checks --watch`, `sleep`) and returns. See `poteto-mode/playbooks/autonomous-run.md` step 2.
- The agent store → `~/.local/share/pstack/<repo-name>/`.
- `AskQuestion` → `question`, `TodoWrite` → `todowrite`. Cursor's `create-skill` → the `writing-for-agents` skill (from mattpocock). New personal skills go in this repo.
- `.cursor/skills/` → `.agents/skills/`.
- `make-bot-ui` (Cursor's Grok Bot) is deleted, so syncs exclude it.
- Origin (Cursor's internal git host) and Bugbot (Cursor's PR review bot) are stripped: PR steps use `gh` only, review-bot comments are triaged per `poteto-mode/playbooks/babysit.md` step 8, and `references/bugbot-triage.md` is deleted.
- The `opening-a-pr` playbook and `scripts/watch-pr` are deleted, so syncs drop their upstream updates. Playbooks no longer end with "Run **Opening a PR**". `babysit` and `shipping` read PR state with `gh pr view` / `gh pr checks --watch`, with no watcher verdicts (`READY`, `WAITING`, `ADVANCE`, `COMPLETE`). Verify script edits with `python3 scripts/test-vendored.py`; it uses a scratch copy and the prerequisites documented in `docs/setup.md#verification`. Non-dry syncs and installs run `scripts/check.py`, which includes this port's `check.py` compatibility rules.

After a sync, `grep -rniE 'cursor|Task\b|subagent_type|agent-transcripts|/loop|grok|claude-opus|bugbot|origin pr' skills/cursor` shows new upstream text that needs the same treatment.

## When it breaks

The script stops when a plugin's `.cursor-plugin/plugin.json` is missing, or when a listed skill has no `SKILL.md`. Either means upstream changed its layout. Look at the clone in `~/.cache/agent-setup/upstream/cursor` and fix this script. Leave `vendor_sync.py` alone, because every port shares it.
