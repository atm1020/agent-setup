---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Multiple LLM reviewers challenge changes from independent angles."
disable-model-invocation: true
---

# Interrogate

Spawn one reviewer per configured model to adversarially review code changes. The adversarial signal comes from model diversity, not assigned personas. The deliverable is a synthesized verdict. Do NOT auto-apply changes.

## Step 1, Scope

Identify what to review from context:

- If the user points at specific files or a diff, use that.
- If on a feature branch, run `git diff main...HEAD` (or the appropriate base branch) for the full changeset.
- If the user's message references recent work, gather the relevant files.

Package the diff or file contents with any surrounding context files the reviewers need to understand the code.

## Step 2, Intent

Before spawning reviewers, state the intent in one clear paragraph from the user's message, commit messages, the PR description if one exists, and the code. If you're unsure about the intent, ask the user before proceeding.

## Step 3, Spawn Reviewers

Launch all reviewers in a single message using the `subagent` tool. Use the `interrogate reviewers` line in `~/.config/opencode/pstack-models.md`, one reviewer per entry, extending or shrinking the Reviewer A/B/C labels below to the configured entry count. If the file or that line is missing, use the table defaults.

| Subagent | Default model |
|----------|---------------|
| Reviewer A | `openai/gpt-6-astra` |
| Reviewer B | `openai/gpt-6.1-sol` |
| Reviewer C | `openai/gpt-5.6-sol` |

**Ask before astra.** `openai/gpt-6-astra` is very expensive. Before any `subagent` call on it, with or without a `#effort` suffix, ask the user with `question`: run it on astra, or on `openai/gpt-6.1-sol` instead. Ask once per task, naming every astra spawn the task will make, and reuse the answer for the rest of the task. If nobody can answer (an unattended or autonomous run), use `openai/gpt-6.1-sol` and say so.

For each reviewer:
- `agent`: `explore` (read-only)
- `model`: the configured `interrogate reviewers` entry, or the table default with no configured line. For an `auto` or `inherit-parent` entry, omit `model` so that reviewer runs on the parent model.

If the `subagent` tool rejects a configured entry, run that reviewer on its table default and say so. If it rejects a table default, check the valid slugs in the `subagent` tool's error message, pick the closest equivalent (prefer the highest-reasoning tier of the same family), spawn with it, and open a separate PR to update the default table. Do not block the review on the slug issue. Never treat an alias entry as a rejected slug or apply either fallback to it.

Read `references/reviewer-prompt.md` and fill in the same template for every reviewer with the stated intent, the diff or file contents, the rubric from `references/rubric.md`, and the code-quality lens from `references/code-quality-review.md`. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **poteto-mode** skill.

## Step 4, Synthesize

As results come back, build a unified picture. Parse every reviewer's findings. Merge findings that describe the same issue differently, and note which models raised each one. Findings two or more models raised independently are the highest signal. Read a lone model's finding, but weight it accordingly. Note disagreements. If one model flags something and another explicitly says the opposite, that is context for the verdict.

## Step 5, Lead Judgment

You are the lead reviewer, a pragmatic senior engineer, not a neutral aggregator. Read `references/lead-judgment.md` for the full framework. Put every finding in one of four buckets, with the model(s) that raised it and a one-line rationale.

- **Act on**. Real issues affecting correctness, security, or maintainability given the actual goals. They would block a real PR.
- **Consider**. Legitimate, but you're not sure they outweigh the cost of addressing them now. Worth the user's attention.
- **Noted**. Technically valid but not actionable. Context-dependent, premature optimization, or low-impact at this stage.
- **Dismissed**. Wrong, nitpicky, or missing context, with a brief reason.

## Output Format

### Intent
> [The stated intent paragraph from Step 2]

### Reviewers
- Reviewer [label]: [model name], [N findings] (one bullet per reviewer)

### Act On
[Each: description, which models raised it, why it matters.]

### Consider
[Each: description, which models raised it, the tradeoff.]

### Noted
[Brief list.]

### Dismissed
[Each with a brief rationale.]

### Agreement Map
[Where models agreed and diverged, and what that pattern tells us.]
