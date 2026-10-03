---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available OpenCode models and writes ~/.config/opencode/pstack-models.md, which pstack's skills read in place of their defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

Write `~/.config/opencode/pstack-models.md`, which sets pstack's model per role. pstack's skills read it each time they spawn a subagent, so it needs no other wiring.

## Steps

### 1. Detect available models

Run `opencode models`. It prints every `provider/model` you can pass as the `subagent` tool's `model`. If it fails, ask the user to paste the models they have access to. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.

### 2. Load current state

The default role-to-model mapping is the file shown in step 5 below. If `~/.config/opencode/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer `question` over free text. Offer these four options with these exact labels, and name the current budget when the file records one.

- `unlimited — xhigh reasoning`
- `large — high reasoning`
- `medium — medium reasoning`
- `small — low reasoning`

**(b) Apply it.** Build the working table from the defaults in step 5, and on a re-run keep any role the user changed (a different model, list, or alias `inherit-parent` / `auto`). OpenCode sets reasoning effort with a `#variant` suffix on the model: `openai/gpt-6.1-sol#high`. Set the suffix of every `openai/*` entry, panel entries included, to the budget's effort (`xhigh`, `high`, `medium` or `low`). Leave other providers' entries without a suffix unless the user names one. `inherit-parent` and `auto` do not change.

**(c) Show the roles and confirm.** Show every role with its model, marking any real slug not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, the model the user picked for the chat) as the options. Prefer `question` over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it that differs from the parent's model when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

Tell the user that pstack asks before every task that would spawn `openai/gpt-6-astra` (it is very expensive), so astra roles cost nothing until they approve. To never be asked, set those roles to `openai/gpt-6.1-sol`.

### 4. Validate

Every real model written must be in the `opencode models` list (ignore the `#variant` suffix when checking). `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.

### 5. Write the file

Write `~/.config/opencode/pstack-models.md` with a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels poteto-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit the `subagent` `model`). `#<effort>` sets reasoning effort. Alias entries in a panel list still count toward its fan-out.
# budget: unlimited (xhigh)
feature, refactoring: openai/gpt-6.1-sol#xhigh
bug-fix: openai/gpt-6.1-sol#xhigh
perf-issue: openai/gpt-6.1-sol#xhigh
hillclimb: openai/gpt-6.1-sol#xhigh
judgment and prose: openai/gpt-6-astra#xhigh
hardest tasks: openai/gpt-6-astra#xhigh
how explorer: openai/gpt-6.1-sol#xhigh
how explainer: openai/gpt-6-astra#xhigh
why investigators: openai/gpt-6.1-sol#xhigh
why synthesizer: openai/gpt-6-astra#xhigh
reflect tooling: openai/gpt-6.1-sol#xhigh
reflect judgment, divergent, synthesizer: openai/gpt-6-astra#xhigh
arena runners: openai/gpt-6-astra#xhigh, openai/gpt-6.1-sol#xhigh, openai/gpt-5.6-sol#xhigh
arena cross-judge pool: openai/gpt-6-astra#xhigh, openai/gpt-6.1-sol#xhigh, openai/gpt-5.6-sol#xhigh
swarm workers: openai/gpt-6.1-sol#xhigh
architect runners: openai/gpt-6-astra#xhigh, openai/gpt-6.1-sol#xhigh, openai/gpt-5.6-sol#xhigh
interrogate reviewers: openai/gpt-6-astra#xhigh, openai/gpt-6.1-sol#xhigh, openai/gpt-5.6-sol#xhigh
```

### 6. Confirm

Tell the user the file was written and that skills pick it up on their next spawn. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` . On no, move on without pushing.
