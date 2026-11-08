---
name: herdr-scheduler
description: "Coordinate a task queue through Herdr: check project state, dispatch ready agents, supervise results, and resume interrupted work. Use when the user asks for FirstMate-style scheduling, asks to schedule agents to do several tasks, or asks to check and advance an existing Herdr queue."
---

# Herdr scheduler

A session-scoped coordinator, not a daemon. Turn the user's authorized work into a queue, run independent tasks in visible Herdr panes, and verify their outcomes. Scheduling means dependency-based dispatch while this session is active, not timed execution or automatic wake-up after the session ends.

## 1. Establish scope

Read the installed `herdr` skill and follow its environment gate, CLI discovery, targeting, and safety rules. If Herdr is unavailable, report the limitation without creating a queue or starting workers. Use the installed CLI as the authority; this skill needs no FirstMate installation.

Resolve the project and the user's intended deliverables. A request to check, investigate, or propose work authorizes a read-only result, not implementation. Checks may discover candidate tasks; put those in `proposed` until the user approves implementation. Existing project instructions and the user's approval boundaries remain in force.

Read repository instructions, working-tree status, and relevant existing evidence. Preserve user changes. Prefer the project's existing task record; otherwise use `.herdr-scheduler/queue.md` at its root, telling the user where local state is kept. Do not commit state or change ignore rules automatically. If the project is read-only, agree on a writable state location first.

The coordinator's working directory may instead be a control directory holding no code of its own, scheduling work across several repos. Then the schedulable repos come from the coordinator's own instructions or the user, never inferred from the working directory, and a repo without such a record is a question rather than an assumption. Each task names its own repo, and the queue is `queue.md` in the control directory, covering every repo. Each repo's own instructions still govern work inside it. Keep queue state out of the project repos, and read each task's repo instructions and working-tree status before queueing work there.

Read [QUEUE.md](QUEUE.md) when creating or resuming the queue. Use one coordinator per queue; if another live coordinator owns it, report that fact and stop mutations. An unavailable or ambiguous owner needs user confirmation before takeover. This is a recorded ownership convention, not a locking service.

Anchor the queue to the coordinator's live pane and its tab, resolved through Herdr rather than the UI's focused tab. Record the session/socket, workspace, tab ID, and coordinator pane ID in the queue. Make the grouping visible with `herdr tab rename <tab-id> "<existing-label> · scheduler"` (use `<project or control directory> · scheduler` for an unnamed tab) and `herdr pane rename <coordinator-pane-id> "Coordinator · <project or control directory>"`. Preserve the original labels in the queue and avoid appending the scheduler suffix twice. This labels the existing tab; it does not create or move tabs.

Completion: project, authorized outcomes, queue location, and a single visibly identified coordinator tab are established.

## 2. Check and queue

For each task, record an outcome, type (`investigate` or `implement`), authorization, its repo, dependencies, writable scope, and observable acceptance checks. Include only checks relevant to the requested work, expressed in that repo's own commands. Use stable task IDs and explicit priorities when supplied; otherwise preserve request order.

Default to two active workers for the whole queue, not per repo, unless the user sets another limit. An unresolved human decision is `blocked`; waiting for capacity or dependencies is `queued`. A dependency is satisfied only by a verified `done` result. If a dependency fails or is cancelled, keep its dependents queued with the reason visible; ask whether to revise or cancel them. Surface dependency cycles rather than waiting forever.

Isolation follows the task type. An `investigate` task reads the repo as it stands, so it runs in a new tab in the coordinator's workspace on the existing checkout. An `implement` task gets its own Git worktree through `herdr worktree create`, on its own branch, so concurrent writers cannot collide at all. Fall back to a shared-checkout tab for an implement task only when a worktree is impossible, such as a repo that is not a Git checkout or one whose build cannot run outside its original path, and record that reason in the task.

Isolation removes most scope adjudication, but not all of it, so each task still records its writable scope. Separate worktrees do not separate shared external resources: a database, a port, a package registry, a published artifact, or the same external environment is shared across them, and concurrent writers to one of those serialize. Read-only tasks share the original checkout with anything running there, so they can overlap a writer only while their evidence stays valid; otherwise schedule them once the changes settle. Where a worktree was impossible and writers fall back to one checkout, dispatch them concurrently only with disjoint writable scopes and no shared mutation of the index, lockfiles, or migrations. Serialize uncertain overlap.

Use another working directory or a different Herdr topology only when explicitly requested. Worktree setup follows repository instructions and the Herdr skill, not FirstMate's Treehouse tooling.

Completion: each task has a justified state, dependencies are acyclic, and every ready task has a safe execution scope.

## 3. Dispatch ready work

Take authorized `queued` tasks in priority order whose dependencies are done and whose scope fits the free capacity. Keep the coordinator in its original pane and tab; each worker gets its own new tab, not a split of the coordinator pane. Resolve the recorded coordinator pane's live tab and workspace before dispatch; reconcile unexpected moves with the user.

Resolve the worker harness before creating a worker tab:

1. Use an explicit per-task agent choice, otherwise the user's queue-wide choice.
2. Otherwise match the coordinator's harness: Pi launches Pi, OpenCode launches OpenCode, and Claude Code launches Claude Code. Identify the coordinator from its known runtime and Herdr's agent record for the caller pane. If the evidence conflicts or the harness is unknown, ask which harness to use.
3. Discover the exact supported `--kind` and launch options through the installed `herdr agent` command group; verify that harness's CLI is available. If unsupported or unavailable, ask rather than silently switching.

Create an investigate task's endpoint with `herdr tab create --workspace <coordinator-workspace-id> --cwd <task-repo-path> --label "<repo> · <task-id>" --no-focus`. Use the task's own repo path; a control directory holding the queue is never a worker's working directory. Read its tab ID and root pane ID from the response, record both immediately, and verify the pane belongs to that new tab in the coordinator's workspace. Label the root pane `Worker · <task-id>` with `herdr pane rename`. Use explicit IDs so a changed UI focus cannot redirect work; keep focus unchanged. This separate-tab topology overrides the Herdr skill's usual sibling-split default.

Create an implement task's endpoint with `herdr worktree create`, passing the repo as `--cwd`, a task-specific `--branch`, the repo's default branch as `--base`, a `"<repo> · <task-id>"` label, and `--no-focus`. Resolve the exact options and what the response returns through the installed `herdr worktree` command group before the first use, rather than assuming: Herdr's worktree helpers are workspace-backed, so this may hand back a new workspace rather than a tab in the coordinator's. Record whatever identifiers come back, including the branch, the base, the checkout path, and the workspace or tab the pane belongs to, and verify the pane's working directory is the new worktree and not the original checkout. Report the resulting topology to the user, since a separate workspace is something they have to switch to rather than glance at.

Start with `herdr agent start <unique-name> --kind <resolved-kind> --pane <returned-root-pane-id>`. Use a fresh conversation, without resume or continuation flags, and the selected harness's configured model unless the user explicitly chooses another. Verify explicit model options against that harness's CLI; model identifiers and flags are not portable between harnesses. Record the resolved kind and any explicit model choice in the task before startup.

The coordinator may run in any harness that can follow this workflow, and a queue may mix worker harnesses when requested. Use Herdr's agent prompt, wait, and read surfaces for all workers; relay findings and follow-up instructions through the coordinator, without relying on harness-native subagent tools or shared conversation history.

Before each mutation, save the task as `starting`. Record the returned tab and root pane IDs immediately after creation and the unique agent name after startup. Bind them to the current Herdr session/socket identity; labels alone are not ownership evidence. A crash during startup requires reconciliation, not a duplicate launch.

Give each worker a self-contained prompt containing:

- Task ID, outcome, its repo path and default branch, relevant sources, and user decisions.
- Read-only or explicit writable scope, existing changes to preserve, and concurrent work to avoid.
- Acceptance checks, and the instruction to write the full result to `notes/<task-id>/report.md` beside the queue: findings or changed files, checks actually run with their output, evidence, and blockers.
- The required return in the pane: the report's path, a one-line outcome, and any blocker. Detail belongs in the file, not in the reply, so the coordinator reads the report only when it needs the detail and its context stays small enough to supervise the whole queue.
- For an implement task, the instruction to commit to its own worktree branch as it goes, so no result exists only as uncommitted state in a checkout that may later be removed. Pushing, PRs, and merging into the base branch stay with the coordinator.
- Any skill the worker should load for the task, named explicitly, since its catalog may not surface the right one.
- A boundary keeping queue edits, further delegation, commits, pushes, PRs, merges, dependency changes, and external writes with the coordinator unless explicitly authorized and safely scoped.

Submit through `herdr agent prompt` without waiting when dispatching a parallel batch. Confirm observed activity before marking `running`. If startup or submission is ambiguous, inspect that exact agent and pane before retrying; timeouts do not prove non-delivery.

Completion: each started task has a recorded endpoint and confirmed activity, or a specific startup failure awaiting reconciliation.

## 4. Supervise and verify

Use bounded `herdr agent wait` calls and targeted state/output reads, not a tight polling loop. Rotate through active workers so one slow worker cannot hide another's question. After each meaningful transition, update the queue and fill free capacity with newly ready tasks.

- `working`: leave the worker alone unless the user changes its scope.
- `blocked`: inspect the question or approval and ask the user when authority is required. Keep the worker counted against capacity while its work remains live.
- `idle` or `done`: read the result; these are lifecycle hints, not acceptance evidence. Move a claimed completion to `verifying`. Take the result from the task's `report.md`, not by scrolling its pane; read the pane only when the report is missing or contradicts what the task did.
- Unknown, missing, or timed out: inspect the recorded session, endpoint, output, and filesystem before deciding whether the task failed. Never automatically relaunch uncertain work.

For a result in `verifying`, check it against the acceptance criteria and source evidence. Inspect writer diffs and run relevant integration checks in that task's checkout, using that repo's commands and serializing commands that mutate shared state. A worktree task's diff is its branch against its base; hand an oversized diff to a review subagent and take back findings rather than reading it all into the queue's context. Worker test claims alone do not establish cross-task correctness. Mark `done` only after acceptance, or return a scoped correction to the same worker. Record actual failures as `failed`, with evidence and the next decision.

User steering supersedes the original brief within its authorization. Persist changes before relaying them to the affected worker. A cancellation request requires reconciling whether the worker has actually stopped; retain its capacity and scope reservation until then. Keep partial edits and report them rather than reverting them.

Completion: all authorized tasks are verified done, failed, cancelled, or waiting on an explicit user decision; remaining queued work has a recorded reason.

## 5. Pause, resume, and report

When asked to pause, stop new dispatches, record live workers, and clarify whether the user also wants them interrupted. Ending this coordinator turn or session does not stop workers. Before leaving live work, save the queue and explicitly state that supervision is paused and no automatic wake-up is installed.

On resume, inspect the recorded Herdr session, coordinator tab, and exact endpoints, then compare outputs and diffs with the ledger before dispatching anything. Confirm the coordinator is in its recorded tab, each investigate worker is in its own recorded tab in the same workspace, and each implement worker's pane still sits in its recorded worktree checkout; reconcile moved panes with the user before new dispatches. Check recorded branches and worktrees against `herdr worktree list` and the repo's own worktree state, since a result can survive on a branch after its pane is gone. Do not reuse IDs in a different session or treat an unreachable session as proof of worker death. Ask before replacing uncertain workers or taking over an uncertain coordinator. Resume verified queued work without duplicating finished tasks.

A verified implement task leaves a branch in a worktree, not merged work. Integrating it is a separate step needing its own authorization: say which branches are ready, in which repos, and let the user choose merge, PR, or leave. Until a branch is integrated or the user drops it, its worktree holds the only copy of that work. Never remove a worktree with uncommitted changes, with a branch that is neither integrated nor explicitly abandoned, or with anything the user has not seen; `herdr worktree remove` is a last step after integration, never a cleanup reflex, and `--force` needs the user to ask for it by name.

Report outcomes, checks actually run, blockers needing decisions, and any still-live workers. Close only worker tabs this run created after their results have been collected and the agents are no longer working. Before closing a tab, verify it contains only the recorded worker pane and no unrelated work; otherwise leave it open. Preserve tabs the user wants to inspect and always keep the original coordinator tab. Preserve the queue for later reconciliation. Once no live workers remain, restore the saved tab and coordinator labels only if they still match the labels this run set; preserve any subsequent user renames.

## Provenance and limits

This is an original lightweight workflow inspired by [FirstMate](https://github.com/kunchenguid/firstmate): one coordinator, bounded worker briefs, persistent task state, file-based results, and verified completion. It does not vendor FirstMate's internal skills or runtime. Writers are isolated through Herdr's own `herdr worktree` helpers rather than FirstMate's Treehouse tooling, and readers stay on the shared checkout. It has no watcher, stop hook, cron service, remote fleet, or autonomous publishing policy.

The cost of having no watcher is that supervision is not free: the coordinator polls with bounded waits and targeted reads instead of being woken by an event, so an idle queue still spends tokens and context. Keeping results in report files and restarting the coordinator from the queue are the mitigations; a real event-driven wake-up would need a watcher this skill does not install.
