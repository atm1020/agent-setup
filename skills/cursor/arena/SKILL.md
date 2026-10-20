---
name: arena
description: "Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape."
disable-model-invocation: true
---

# Arena

Open a todolist with one entry per phase (Frame, Fan out, Cross-judge, Pick, Graft, Verify) before launching anything.

## Phase A: Frame

**Ask before astra.** `openai/gpt-6-astra` is very expensive. Before any `subagent` call on it, with or without a `#effort` suffix, ask the user with `question`: run it on astra, or on `openai/gpt-6.1-sol` instead. Ask once per task, naming every astra spawn the task will make, and reuse the answer for the rest of the task. If nobody can answer (an unattended or autonomous run), use `openai/gpt-6.1-sol` and say so.

The N candidates will receive the same prompt, so the prompt is the contract.

1. State the artifact each candidate is producing.
2. Derive the rubric. State what success looks like for *this* task, then turn it into 3-6 concrete gradeable criteria. The rubric is the picker's tool in Phase D. Candidates only see the task.
3. Pick the runners. Use the `arena runners` line in `~/.config/opencode/pstack-models.md`. If the file or that line is missing, default to one each on `openai/gpt-6-astra`, `openai/gpt-6.1-sol`, `openai/gpt-5.6-sol`. An `auto` or `inherit-parent` entry in this line or the cross-judge line means the parent model, so omit `model` for it. If the `subagent` tool rejects a configured entry, run that seat on its table default and say so. If it rejects a default, use the closest valid slug of the same family from its error message. Spawn more when the arena covers multiple design directions. Same model N times when the work is generation-bound rather than judgment-sensitive. Ask before any astra seat, per **Ask before astra** above.
4. Assign output paths. Each candidate writes to its own location (a git worktree where possible, otherwise `/tmp/arena-<slug>/candidate-<n>/`), per the **separate-before-serializing-shared-state** principle skill.

## Phase B: Fan out

Spawn all N subagents in one message with `background: true`, each with the task, the path to the shared grounding, its own output path, and instructions to produce the artifact and a short rationale naming the alternatives considered and what it rejected. Pick each subagent's reasoning level for the job, per the Subagents section of the **poteto-mode** skill.

If a candidate produces no output, proceed with N-1 and note the dropout.

## Phase C: Cross-judge

After all Phase B candidates complete, choose one model from the `arena cross-judge pool` line in `~/.config/opencode/pstack-models.md`. If the file or that line is missing, choose from `openai/gpt-6-astra`, `openai/gpt-6.1-sol`, `openai/gpt-5.6-sol`. Prefer a different model from the parent's. Spawn one judge subagent with `agent: "explore"` (read-only) on that model. It sees the rubric and the candidates by path label, scores each criterion, and recommends a base with rationale. It runs in parallel with the parent's reading in Phase D, not with the candidates themselves. Don't spawn the judge while candidates are still writing. If that pick is astra, ask first, per **Ask before astra**.

## Phase D: Pick a base

Read every candidate end to end before picking. Score each against the rubric criterion by criterion, not on holistic feel, and compare with the cross-judge. Agreement on the base confirms the pick. Disagreement means one of you is biased or the rubric was ambiguous. Read both rationales before deciding.

Pick the base a future maintainer can extend most easily without breaking invariants. When two feel tied, prefer the cleaner boundary or smaller API, per the Laziness Protocol.

## Phase E: Graft

Walk each losing candidate once more for what is worth porting into the base, usually one or two things per candidate, not most of it. Fold each graft in by hand, per the **redesign-from-first-principles** principle skill, so the result stays coherent under one mental model. Don't paste mechanically.

If the candidates converge on one shape, that is strong agreement. Note it and ship the consensus shape. No graft is needed. If they wildly diverge, Phase A was under-specified. Reframe and re-run rather than averaging the divergence.

## Phase F: Verify

Verify the synthesized artifact like any other output, per the **prove-it-works** principle skill. If verification finds a problem the arena missed, either Phase A was wrong (re-frame and re-run) or a candidate caught it and you missed the graft (go back to Phase E). Don't paper over it.

## Outputs

One synthesized artifact, with a short synthesis note alongside naming the base and why, the cross-judge's verdict, each graft with its source candidate, what was rejected and why, any convergence or dropouts, and the verification result.
