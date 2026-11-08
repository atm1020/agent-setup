# Setup and development

> **Proof of concept.** This repo tests using [pstack](https://github.com/cursor/plugins) and [Matt Pocock's skills](https://github.com/mattpocock/skills) mainly with **OpenCode**. Claude Code and Pi are supported but come second. Expect rough edges and breaking changes.

My curated agent setup: original configuration and tooling alongside adapted third-party skills, installed into **OpenCode 2**, **Pi** and **Claude Code**. This is not an original skills library or an official distribution from the upstream authors. See [sources, credits, and license boundaries](../THIRD_PARTY.md). Clone it on any machine and run one script.

```bash
git clone https://github.com/atm1020/agent-setup ~/workspace/agent-setup
cd ~/workspace/agent-setup
./install.sh --dry-run   # see what would change
./install.sh             # install / update; safe to re-run
```

Needs `git` and `python3`.

## Layout

| Path | What | Installed to |
|---|---|---|
| `skills/<name>/SKILL.md` | my own skills | `~/.claude/skills`, `~/.agents/skills` |
| `skills/<upstream>/<name>/SKILL.md` | my copies of an upstream repo's skills | same, flattened to `<name>` |
| `skills/<upstream>/README.md` | that upstream's README, kept in sync | not installed |
| `skills/<upstream>/upstream.json` | sync state: upstream URL, last-synced commit, dropped skills | not installed |
| `.agents/skills/port-<upstream>/` | project-local skill + script that ports and updates that upstream (`.claude/skills` links here) | not installed; only agents working in this repo see it |
| `agents/<name>.md` | my subagents | `~/.claude/agents`, `~/.config/opencode/agents` |
| `config/AGENTS.md` | global instructions (optional) | `~/.claude/CLAUDE.md`, `~/.config/opencode/AGENTS.md`, `~/.pi/agent/AGENTS.md` |
| `config/herd/AGENTS.md` | the scheduler control room's instructions: which repos may be scheduled | `~/herd/AGENTS.md` (plus a `CLAUDE.md` shim) |

Third-party skills are **copied into `skills/<upstream>/`** so I can edit them, and kept in sync with their upstream by a port skill per repo. So far: [mattpocock/skills](https://github.com/mattpocock/skills) in `skills/mattpocock/`, and from [cursor/plugins](https://github.com/cursor/plugins) the `pstack` plugin (skills and subagents) plus the `cursor-team-kit` skills it uses, in `skills/cursor/`, and the agent skill from [herdrdev/herdr](https://github.com/herdrdev/herdr) (pinned to its release tag) in `skills/herdr/`.

Who reads what:

- **Claude Code** reads `~/.claude/skills` and `~/.claude/agents`.
- **Pi** reads `~/.agents/skills`. Pi has no subagents.
- **OpenCode** reads `~/.claude/skills`, `~/.agents/skills` and `~/.config/opencode/agents`. Because skills sit in both skill dirs, it logs a harmless "duplicate skill name" warning per skill. Set `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` to silence it.

Skills are symlinked by default, so editing a skill here is live everywhere. Use `--copy` for a snapshot.

`install.sh` keeps a manifest (`.cursor-plugins-port.json`) in each target dir:

- It never overwrites files it didn't create.
- `--prune` (always on) removes skills you dropped from the repo.
- `./install.sh --uninstall` removes everything it installed.

If `herdr` is on PATH, it also installs Herdr's integrations for opencode, pi and claude (skip with `--no-herdr`).

## Adding things

- **Skill:** `skills/<name>/SKILL.md` with `name` (lowercase-hyphen, same as the folder) and `description` frontmatter, then `./install.sh`.
- **Subagent:** `agents/<name>.md`, then `./install.sh`.
- **Global instructions:** `config/AGENTS.md`, then `./install.sh`.
- **A repo the scheduler may schedule into:** add a row to the table in `config/herd/AGENTS.md`. No install needed; it is symlinked.
- **Third-party skills:** write a `.agents/skills/port-<repo>/` skill whose script fetches the repo and lists its skills, then calls `scripts/vendor_sync.py --name <repo>`. Copy `.agents/skills/port-mattpocock` as the template.

### Herdr task scheduling

The original `herdr-scheduler` skill adds a lightweight, FirstMate-inspired queue over Herdr. For example: “Use herdr-scheduler to investigate the login failure, then fix it once I approve the findings; also audit the docs.” It checks authorization and dependencies, starts fresh agents for ready work, and verifies results. It defaults to two workers. Investigation runs in a tab on the existing checkout; anything that writes code gets its own Git worktree and branch through `herdr worktree`, so concurrent writers cannot collide and a verified task leaves a branch for you to merge, PR or drop. Workers write their full result to a `report.md` and return only its path, keeping the coordinator's context small. The coordinator stays in its original, scheduler-labeled tab, and nothing steals focus.

To schedule across several repos, run the coordinator in its own control room instead of inside one of them: `config/herd/AGENTS.md` installs to `~/herd/AGENTS.md`, and a session started there (`opencode ~/herd`, `cd ~/herd && pi`, or `cd ~/herd && claude`) reads it, loads the skill, and keeps one queue at `~/herd/queue.md` covering every repo. Workers still run in the real repos, each in its own tab with that repo as its working directory. The charter is thin on purpose: a repo table, the queue location, and what needs approval. Nothing is schedulable until it has a row in that table, so putting a repo in scope means editing `config/herd/AGENTS.md` (symlinked, so the edit is live at once). `~/herd` is deliberately not a git repo, so queue state is never committed. Pi asks once whether to trust the directory's files; `pi --append-system-prompt ~/herd/AGENTS.md` works from anywhere instead.

For a single project, queue state defaults to `.herdr-scheduler/queue.md` in it. Ask to “resume the Herdr queue” to reconcile existing workers before dispatching more. It requires a Herdr-managed session and the selected worker CLI. Workers default to the coordinator's harness (Pi, OpenCode, or Claude Code); explicit queue-wide or per-task choices can mix supported harnesses. Prompts and results pass through Herdr, with the coordinator relaying between workers. It does not install FirstMate, a persistent watcher, or timed/unattended execution. Install it through the normal installer; no separate service setup is needed.

## Syncing upstream skills

```bash
.agents/skills/port-mattpocock/scripts/port-mattpocock --dry-run   # what would change
.agents/skills/port-mattpocock/scripts/port-mattpocock             # pull upstream changes into skills/mattpocock/
.agents/skills/port-cursor/scripts/port-cursor                     # same for skills/cursor/ (pstack)
.agents/skills/port-herdr/scripts/port-herdr                       # same for skills/herdr/ (--ref vX.Y.Z to move releases)
git diff --stat && ./install.sh
```

Or, from an agent session in this repo, ask it to "sync the mattpocock skills". Each file, skills and README alike, is 3-way merged against the upstream commit recorded in `skills/<upstream>/upstream.json`:

- Files I haven't touched take upstream's version.
- My edits are kept.
- Where we both changed the same lines, it leaves `<<<<<<< local` / `>>>>>>> upstream` markers and exits 1.

New upstream skills are added. To drop one for good, delete its folder; the next sync records it as excluded.

A non-dry sync runs `scripts/check.py` after writing the files. A failed check leaves the changes for repair and exits nonzero. The installer runs the same check before writing or pruning tool folders, including in `--dry-run`; uninstall remains available. Since installed skills are symlinks by default, this gate does not quarantine sync edits. Use a scratch repo to review changes before making them live.

## Verification

The installer and repository checker need only git, Python 3 and bash:

```bash
python3 scripts/check.py
python3 -m unittest discover -s tests
bash -n install.sh .agents/skills/*/scripts/*
./install.sh --dry-run --no-herdr
python3 scripts/port.py --source . --project "$(mktemp -d)" --target claude,opencode,agents
```

The checker rejects unresolved merge markers. Each port owns its additional validation in `.agents/skills/port-<repo>/check.py`. Cursor's check rejects incompatible tool names, model defaults, paths, restored deleted workflows, and instructions to use unsupported services. Upstream READMEs are provenance, not installed instructions, so Cursor's harness rules do not scan them. These checks are not a security audit or a semantic review.

Vendored script tests additionally require **Bun at the exact version in `.bun-version`**, **Node.js 20 or newer**, and network access to the npm registry:

```bash
python3 scripts/test-vendored.py
```

The runner copies `skills/cursor/poteto-mode/scripts/` into a temporary directory, fetches the exact commander version from its lockfile, verifies SHA-512 integrity, and runs its `test` script. It runs no package installation or lifecycle scripts and needs no npm or pip packages. HOME, XDG directories and temporary state are disposable; the runner removes them on success or failure. A changed dependency set or missing runtime fails explicitly rather than skipping tests. This is filesystem isolation for repeatable tests, not a sandbox for untrusted code.

`.github/workflows/check.yml` runs repository validation, Python tests, syntax checks, an isolated install, and the vendored script tests. Bun and Node are test prerequisites only, not installer dependencies.

## License

The root [MIT license](../LICENSE) covers this repo's original contributions only. Vendored content keeps its upstream licenses and copyright notices: MIT for `skills/mattpocock/` and `skills/cursor/`, Apache-2.0 for `skills/herdr/`. Local adaptations do not replace those terms. See [THIRD_PARTY.md](../THIRD_PARTY.md) for authors, source links, license files, and notice requirements.
