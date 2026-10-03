---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
disable-model-invocation: true
---

# Reflect

Mine the current conversation for durable learnings, then route them into skill edits.

## When to invoke

Invoke when the user says "reflect" or "/reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

The parent exports its own session to a file before fanning out. Run this from the workspace root, so it lists this project's sessions only. Never read other projects' sessions.

```bash
opencode session list --format json -n 10           # this chat is the most recently updated
opencode session export <sessionID> > "$(mktemp -d)/transcript.json"
```

The export is JSON: `info` plus `messages`. Subagent runs are separate sessions with this one as parent.

For each candidate, read the first JSONL line and check that `message.content[0].text` contains the conversation's opening user prompt. Take the matching path. If no path resolves, write a tight digest of the session and pass that instead.

### 2. Spawn three reviewers in parallel

One message, three `subagent` calls, `agent: "general"`, with `model` set as below. Reviewers need MCP access for context lookups (tickets, chat threads, observability traces referenced in the transcript). Readonly strips MCPs.

Each reviewer and the synthesizer name a role line in the `~/.config/opencode/pstack-models.md` config and a default. Set `model` to that line's value, or to the default if the file or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the `subagent` tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message.

**Ask before astra.** `openai/gpt-6-astra` is very expensive. Before any `subagent` call on it, with or without a `#effort` suffix, ask the user with `question`: run it on astra, or on `openai/gpt-6.1-sol` instead. Ask once per task, naming every astra spawn the task will make, and reuse the answer for the rest of the task. If nobody can answer (an unattended or autonomous run), use `openai/gpt-6.1-sol` and say so.

| Lens | Role line | Default `model` | Prompt template |
|---|---|---|---|
| Judgment | `reflect judgment, divergent, synthesizer` | `openai/gpt-6-astra` | `references/judgment-reviewer.md` |
| Tooling | `reflect tooling` | `openai/gpt-6.1-sol` | `references/tooling-reviewer.md` |
| Divergent | `reflect judgment, divergent, synthesizer` | `openai/gpt-6-astra` | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in the `subagent` result body.

### 3. Synthesize

One `subagent` call, `agent: "general"`, with `model` from the `reflect judgment, divergent, synthesizer` line (default `openai/gpt-6-astra`). The synthesizer's quality check includes spot-verifying citations, which can require MCP access. Readonly strips MCPs. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. The synthesizer returns a structured Accepted / Rejected / Backlog list.

### 4. Structural enforcement check

Sanity-check the synthesizer's Accepted list. For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog. See the **encode-lessons-in-structure** principle skill.

### 5. Apply

Before applying any Accepted edit, present the synthesizer's full Accepted/Rejected/Backlog output to the user and wait for explicit approval. The user picks which subset to apply and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

Backlog items file to whatever devex / backlog tracker your team uses automatically. Only the Accepted list waits for approval.

For each approved Accepted item, follow the Routing field exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): parent does directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): draft it per the **writing-for-agents** skill, then test it on the case that prompted it.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): rewrite its `description` so it names the words and situations that should have triggered it.
- `new skill: <kebab-name>`: author it per the **writing-for-agents** skill, in the agent-setup repo. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done. Skip this step if it doesn't.

### 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
