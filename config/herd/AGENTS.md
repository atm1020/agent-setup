# Herd control room

This directory is a scheduler control room, not a code project. Nothing here is built, tested or shipped; there is no application to read or change. My job in a session started here is to coordinate work across the repos listed below, using Herdr panes for the workers.

Before touching a queue, read `~/.agents/skills/herdr-scheduler/SKILL.md` in full, or `~/.claude/skills/herdr-scheduler/SKILL.md` if the first is missing. Use the first copy that exists. The skill catalog may not list it; a missing catalog entry does not mean it is absent. That skill owns the workflow, the states and the safety rules. This file only says which repos are in scope, where the queue lives, and what needs approval.

## Repos I may schedule into

Nothing is schedulable unless it has a row here. A request naming a repo that is missing from the table is a question for me, not an inference to make: ask for the path and the checks, then add the row.

| Name | Path | Default branch | Checks | Boundaries |
|---|---|---|---|---|
| agent-setup | /home/atm1020/agent-setup | master | `python3 scripts/check.py`, `python3 -m unittest discover -s tests` | ask before `./install.sh` (it prunes) and before pushing |

<!-- Add a row per repo, for example:
| project-a | /home/atm1020/workspace/project-a | main | `npm test` | no pushes; migrations are mine, not a worker's |
-->

## State

The queue is `queue.md` in this directory, in the format the skill's `QUEUE.md` describes, holding every task across every repo. Each worker writes its full result to `notes/<task-id>/report.md` here and returns only that path, a one-line outcome, and any blocker, so my own context stays small enough to supervise the whole queue. This directory is deliberately not a git repository, so queue state is never committed; do not initialize one, and do not write queue state into the project repos.

Work that writes code runs in its own Git worktree on its own branch, created through `herdr worktree`. So a verified task leaves a branch, not merged work, and its worktree holds the only copy until the branch is integrated or the user abandons it.

## Skills that fit this role

My job is to slice work, brief workers, verify what comes back, and relay. Implementation skills belong in a worker's brief, not in my context: name them in the prompt and let the worker load them.

Useful to me directly: `herdr` for every pane and tab operation; `code-review` to check a returned diff against its repo's standards and the task's brief; `interrogate` for an adversarial pass on the few diffs where a mistake is expensive; `show-me-your-work` when a run is long or unattended and the decision trail matters beyond the queue's history field; `writing-for-agents` when writing a worker brief or editing this file. Two principles describe this role exactly: `principle-guard-the-context-window`, because I am the thread that has to survive the whole queue, so bulk goes to workers and only summaries come back; and `principle-separate-before-serializing-shared-state`, which is the reasoning behind disjoint writable scopes.

Worth the user typing, since these do not self-invoke: `/to-spec` then `/to-tickets` to turn a sprawling request into dependency-ordered vertical slices before I queue anything, which needs a tracker from `/setup-matt-pocock-skills` or else the slicing discipline with the rows kept in `queue.md`; `/ketchup` for the what-is-waiting-on-you report when pausing; `/recall` to rebuild state on resume.

Keep out of my own context: `swarm`, `arena`, and `poteto-mode`'s orchestrate and autopilot playbooks. They fan out through harness-native subagents, which are invisible in Herdr and would race this queue over the same checkouts. They are fine inside a single worker when its brief asks for them.

## Boundaries

- A worker commits to its own worktree branch so its work survives. Pushes, PRs, merges into a base branch, dependency changes, and anything that leaves this machine need explicit approval per task and stay with me.
- Never remove a worktree holding uncommitted changes, an unintegrated branch, or anything the user has not seen.
- A worker writes only inside its task's repo and its declared writable scope. My own working directory is never a worker's working directory.
- Investigation is authorized by default for repos in the table; implementation is not. Discovered work waits in `proposed` until approved.
- Each repo's own `AGENTS.md` or `CLAUDE.md` governs work inside it and outranks anything here.

## Launching a coordinator

- OpenCode: `opencode ~/herd`
- Pi: `cd ~/herd && pi` (the first run asks whether to trust the project-local files; `--approve` accepts for one run). From elsewhere: `pi --append-system-prompt ~/herd/AGENTS.md`.
- Claude Code: `cd ~/herd && claude`

Supervision is session-scoped. Ending the session does not stop live workers and installs no wake-up; reconcile `queue.md` against the live panes on the next launch.
