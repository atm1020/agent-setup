# Third-party content

agent-setup is an independently maintained collection of agent configuration and adapted third-party skills. Inclusion does not imply endorsement by the upstream authors. The skills remain the work of their respective authors; this repository adds installation, cross-tool adaptations, upstream synchronization, and validation.

## Sources and licenses

| Local content | Upstream and credit | License retained here |
|---|---|---|
| `skills/cursor/`, pstack skills and subagents | [cursor/plugins, pstack](https://github.com/cursor/plugins/tree/main/pstack). Copyright 2026 Lauren Tan, as stated in the upstream license. | [MIT](skills/cursor/LICENSE.pstack) |
| `skills/cursor/`, selected cursor-team-kit skills | [cursor/plugins, cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit). Copyright 2026 Cursor. | [MIT](skills/cursor/LICENSE.cursor-team-kit) |
| `skills/mattpocock/` | [mattpocock/skills](https://github.com/mattpocock/skills). Copyright 2026 Matt Pocock. | [MIT](skills/mattpocock/LICENSE) |
| `skills/herdr/` | [herdrdev/herdr](https://github.com/herdrdev/herdr), the published agent skill. | [Apache-2.0](skills/herdr/LICENSE) |

Each group's `upstream.json` records the exact source URL, ref, commit, source paths, and exclusions. These locks identify the upstream versions, not a claim that the local copies are unchanged.

## Local adaptations

Local changes include OpenCode tool names, GPT model defaults and approval requirements, workspace-scoped session access, local worktrees instead of cloud workers, and GitHub-only workflow instructions. Some upstream workflows are deliberately excluded. The port skills under `.agents/skills/port-*/` describe these choices; git history records the local changes.

The root [MIT license](LICENSE) applies to this repository's original code and other original contributions. It does not replace the licenses or copyright notices attached to third-party material. Modified copies remain subject to their upstream license terms.

## Preserving notices

Retain the full upstream license and applicable copyright and attribution notices when redistributing vendored content. For Apache-2.0 material, preserve applicable upstream NOTICE content if supplied, and place a prominent modification notice in each locally changed file. The Herdr port includes root `NOTICE`, `NOTICE.txt`, or `NOTICE.md` files when upstream supplies them. A license file next to a group does not by itself satisfy every obligation for a modified file.

Before adding another upstream, check its license, preserve required notices through its port, and add its attribution here. Do not assume another repository's skills have the same license as the ones listed above.
