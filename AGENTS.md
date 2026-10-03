# agent-setup

The home of all the user's own skills, subagents and agent configs (global instructions), plus the installer that puts them into Claude Code, OpenCode 2 and Pi. Third-party skills are copied into `skills/<upstream>/`, so the user can modify them, and kept in sync with upstream by one `port-<repo>` skill per upstream repo. One repo, cloned on every machine, run with `./install.sh`. See README.md for the user-facing story.

## Layout

- `skills/<name>/SKILL.md`: the user's own skills.
- `skills/<repo>/`: everything from one upstream repo:
  - `<name>/SKILL.md`: vendored skills (installed flat, as `<name>`; `port.py` treats a folder without `SKILL.md` as a group and looks inside).
  - `README.md`: the upstream README, synced like the skills.
  - `agents/<plugin>/*.md`: vendored subagents, synced like a skill. `port.py` installs them like `agents/`.
  - `upstream.json`: the sync lock: `url`, `ref`, `commit`, `files` and `skills` (local name -> upstream path), `excluded`.
- `.agents/skills/port-<repo>/`: the port skill for each upstream, project-local so only agents working in this repo load it (`.claude/skills` is a symlink to `.agents/skills` for Claude Code; OpenCode and Pi read `.agents/skills` directly). `install.sh` never installs it. Its `scripts/port-<repo>` fetches the repo (a `--filter=blob:none` clone in `~/.cache/agent-setup/upstream/<repo>`, full history so old commits can be merge bases), works out which folders are skills, and passes them to `scripts/vendor_sync.py`. Flags: `--dry-run`, `--ref`, `--no-pull`, `--list`.
- `scripts/vendor_sync.py`: the shared sync engine. 3-way merges each file of each skill and each extra `--file` (base = commit in the lock, theirs = new upstream, ours = `skills/<repo>/...`), adds new upstream skills, excludes skills deleted locally, refuses to overwrite untracked local folders, and writes `skills/<repo>/upstream.json`. Exits 1 on conflicts.
- `agents/<name>.md`: the user's subagents (empty for now).
- `config/AGENTS.md`: the user's **global** instructions, symlinked to `~/.claude/CLAUDE.md`, `~/.config/opencode/AGENTS.md` and `~/.pi/agent/AGENTS.md` when present. Not instructions for this repo.
- `install.sh`: entry point. It fetches nothing; it installs this repo only:
  1. Calls `scripts/port.py --source <repo>`.
  2. Links the files listed in its `LINKS` array, skipping sources that don't exist.
  3. Installs Herdr integrations when `herdr` is on PATH.
- `scripts/port.py`: the installer engine. Stdlib-only Python with no YAML dependency (a small frontmatter parser is built in).
  - Finds plugins in each `--source`. A `.cursor-plugin/plugin.json` marks a plugin; a plain `skills/` + `agents/` folder counts as one.
  - Copies or symlinks skills, and rewrites agents into the Claude Code and OpenCode formats.
  - Records what it installed in `.cursor-plugins-port.json` inside each target folder.

## Rules

- **This repo is the source of truth for the user's own skills and agents.** New or edited skills go in `skills/<name>/`, subagents in `agents/`, global instructions in `config/AGENTS.md`. Never author them in the tool folders or elsewhere.
- **Third-party skills arrive only through their port.** Don't hand-copy them in; run (or write) the `port-<repo>` skill so the lock knows the merge base. Local edits to vendored skills are expected and must survive a sync.
- **Repo-specific layout knowledge lives in the port script**, not in `vendor_sync.py` or `port.py`.
- **After a sync with conflicts, resolve every marker before committing.** Keep the user's edit's intent; ask when unsure.
- **Respect the manifest contract.** `port.py` never overwrites a path it didn't install unless `--force` is passed, and `--prune` and `--uninstall` only touch paths in the manifest. `install.sh` links only when the destination is missing or is already a link into this repo. Keep both guarantees.
- **Generated tool folders are not edited by hand.** `~/.claude/{skills,agents}`, `~/.config/opencode/agents` and `~/.agents/skills` are outputs; fix the source or the porter instead.
- **Know who reads which folder:**
  - Claude Code: `~/.claude/skills` and `~/.claude/agents`.
  - Pi: `~/.agents/skills`. Pi has no subagents.
  - OpenCode: `~/.claude/skills`, `~/.agents/skills` and `~/.config/opencode/agents`. Don't also install skills into `~/.config/opencode/skills`, or OpenCode loads them three times.
- **Skill names must be lowercase-hyphen and match their folder.** OpenCode rejects any other name. `port.py` slugs bad names and rewrites the copy's frontmatter.
- **Keep dependencies at git, python3 and bash.** Nothing to `pip` or `npm install`.
- **Match the existing style:** short scripts with a `usage()` block, `set -euo pipefail`, `die()` for errors, and long flags.

## Verify changes

Never test against the real home folders when a scratch project will do.

```bash
bash -n install.sh .agents/skills/*/scripts/*   # syntax
.agents/skills/port-mattpocock/scripts/port-mattpocock --dry-run   # what a sync would change
python3 -m py_compile scripts/port.py
python3 -m unittest discover -s tests           # every upstream ships its LICENSE
./install.sh --dry-run                          # touches nothing
python3 scripts/port.py --source . --project "$(mktemp -d)" --target claude,opencode,agents   # isolated install
```

- **Check what OpenCode sees:** OpenCode v2 has no `debug skill`. `opencode debug config` lists config sources and `opencode debug agents` the agents.
- **Test sync/merge changes on a copy:** `cp -r . "$S/repo"` and run the port from there with `AGENT_SETUP_CACHE` pointing at a temp dir. Sync once with `--ref <old full sha>`, edit some skills, then sync to `main` and check merges, conflicts and exclusions.
- **Ask before** running `./install.sh` for real (it prunes), and before pushing.
