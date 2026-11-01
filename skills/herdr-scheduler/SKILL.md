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

Read [QUEUE.md](QUEUE.md) when creating or resuming the queue. Use one coordinator per queue; if another live coordinator owns it, report that fact and stop mutations. An unavailable or ambiguous owner needs user confirmation before takeover. This is a recorded ownership convention, not a locking service.

Completion: project, authorized outcomes, queue location, and a single coordinator are established.

## 2. Check and queue

For each task, record an outcome, type (`investigate` or `implement`), authorization, dependencies, writable scope, and observable acceptance checks. Include only checks relevant to the requested work. Use stable task IDs and explicit priorities when supplied; otherwise preserve request order.

Default to two active workers unless the user sets another limit. An unresolved human decision is `blocked`; waiting for capacity or dependencies is `queued`. A dependency is satisfied only by a verified `done` result. If a dependency fails or is cancelled, keep its dependents queued with the reason visible; ask whether to revise or cancel them. Surface dependency cycles rather than waiting forever.

Workers share the current checkout by default. Dispatch concurrent writers only when their writable scopes are disjoint and their operations do not mutate shared resources such as the index, lockfiles, migrations, or the same external environment. Serialize uncertain overlap. Read-only tasks can overlap writers only when their evidence remains valid; otherwise schedule them after the changes settle.

Use worktrees, another working directory, or a different Herdr topology only when explicitly requested. Worktree setup then follows repository instructions and the Herdr skill, not FirstMate's Treehouse tooling.

Completion: each task has a justified state, dependencies are acyclic, and every ready task has a safe execution scope.

## 3. Dispatch ready work

Take authorized `queued` tasks in priority order whose dependencies are done and whose scope fits the free capacity. Launch each in a fresh sibling pane in the current tab, with the current project cwd and `--no-focus`, following the Herdr skill's geometry rule. Default to a fresh Pi agent with its configured model; honor an explicitly requested supported agent or model. Verify CLI availability before creating a pane; ask if the requested agent is unavailable rather than silently switching.

The default worker launch is `herdr agent start <unique-name> --kind pi --pane <returned-pane-id>`. Use a new conversation, without resume or continuation flags. The coordinator itself may run in any harness that can follow this workflow.

Before each mutation, save the task as `starting`. Record the returned pane ID immediately after creation and the unique agent name after startup. Bind them to the current Herdr session/socket identity; labels alone are not ownership evidence. A crash during startup requires reconciliation, not a duplicate launch.

Give each worker a self-contained prompt containing:

- Task ID, outcome, project path, relevant sources, and user decisions.
- Read-only or explicit writable scope, existing changes to preserve, and concurrent work to avoid.
- Acceptance checks and the required return: findings or changed files, checks actually run, and blockers.
- A boundary keeping queue edits, further delegation, commits, pushes, PRs, merges, dependency changes, and external writes with the coordinator unless explicitly authorized and safely scoped.

Submit through `herdr agent prompt` without waiting when dispatching a parallel batch. Confirm observed activity before marking `running`. If startup or submission is ambiguous, inspect that exact agent and pane before retrying; timeouts do not prove non-delivery.

Completion: each started task has a recorded endpoint and confirmed activity, or a specific startup failure awaiting reconciliation.

## 4. Supervise and verify

Use bounded `herdr agent wait` calls and targeted state/output reads, not a tight polling loop. Rotate through active workers so one slow worker cannot hide another's question. After each meaningful transition, update the queue and fill free capacity with newly ready tasks.

- `working`: leave the worker alone unless the user changes its scope.
- `blocked`: inspect the question or approval and ask the user when authority is required. Keep the worker counted against capacity while its work remains live.
- `idle` or `done`: read the result; these are lifecycle hints, not acceptance evidence. Move a claimed completion to `verifying`.
- Unknown, missing, or timed out: inspect the recorded session, endpoint, output, and filesystem before deciding whether the task failed. Never automatically relaunch uncertain work.

For a result in `verifying`, check it against the acceptance criteria and source evidence. Inspect writer diffs and run relevant integration checks, serializing commands that mutate shared state. Worker test claims alone do not establish cross-task correctness. Mark `done` only after acceptance, or return a scoped correction to the same worker. Record actual failures as `failed`, with evidence and the next decision.

User steering supersedes the original brief within its authorization. Persist changes before relaying them to the affected worker. A cancellation request requires reconciling whether the worker has actually stopped; retain its capacity and scope reservation until then. Keep partial edits and report them rather than reverting them.

Completion: all authorized tasks are verified done, failed, cancelled, or waiting on an explicit user decision; remaining queued work has a recorded reason.

## 5. Pause, resume, and report

When asked to pause, stop new dispatches, record live workers, and clarify whether the user also wants them interrupted. Ending this coordinator turn or session does not stop workers. Before leaving live work, save the queue and explicitly state that supervision is paused and no automatic wake-up is installed.

On resume, inspect the recorded Herdr session and exact endpoints, then compare outputs and diffs with the ledger before dispatching anything. Do not reuse IDs in a different session or treat an unreachable session as proof of worker death. Ask before replacing uncertain workers or taking over an uncertain coordinator. Resume verified queued work without duplicating finished tasks.

Report outcomes, checks actually run, blockers needing decisions, and any still-live workers. Close only panes this run created after their results have been collected and the agents are no longer working; preserve panes the user wants to inspect. Preserve the queue for later reconciliation.

## Provenance and limits

This is an original lightweight workflow inspired by [FirstMate](https://github.com/kunchenguid/firstmate): one coordinator, bounded worker briefs, persistent task state, and verified completion. It does not vendor FirstMate's internal skills or runtime. It intentionally uses shared-checkout scope ownership instead of FirstMate's mandatory isolated worktrees, and has no watcher, stop hook, cron service, remote fleet, or autonomous publishing policy.
