### Autopilot-stack

Run the Autopilot-full playbook, but do not merge.

1. **Run Autopilot-full's owners, minus the landing.** Owners report STACK-READY in place of merge-ready. They never rebase onto another branch, trunk included, and never retarget, merge, close a PR, or arm auto-merge, because the root owns the chain's topology and the operator owns the landing. When an item depends on another, its owner branches from that item's branch, not from trunk.
2. **Give the topology one writer.** Owners push only their own branches and report each tip and its intended parent. Only you rebase or retarget a link, because two writers on one chain undo each other. Append each clean PR in dependency order, with its base set to its parent's branch (`gh pr edit <pr> --base <parent-branch>`). Never require `gt`. An owner takes your push as its new base and lease, and on a conflict resolves its own slice for you to push.
3. **Absorb drift at the root.** Until landing starts, apply Autopilot-full step 5's test to each link and rebase the chain bottom-up where it calls for one. Then apply the patch-id rule link by link, since a link's base is its parent.
4. **Deliver the chain, then keep your hands off it.** Each link carries its verdict in its PR. Once landing starts, nobody writes to the chain except the post-merge retarget that `playbooks/shipping.md` sanctions, because a second writer breaks a landing in flight. A mid-landing problem goes through you to the operator, and any fix waits for the operator's go.

Stop when every link is verified and green at its current head. Hand the chain to the operator, then nobody pushes without the operator's go. Every audit tick names this file so the no-merge rule stays explicit.

**Reply:** list each PR with its verdict, in place of what merged.
