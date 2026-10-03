---
name: pticket
description: "Implement a prepared ticket in poteto-mode. /pticket [number or path]."
disable-model-invocation: true
---

Read `~/.agents/skills/poteto-mode/SKILL.md` in full, including its Principles index, and work in poteto-mode for the rest of this task.

Run its Ticket playbook, `~/.agents/skills/poteto-mode/playbooks/ticket.md`. The target is the ticket number or path given with this command, resolved against the repo's tracker as the playbook describes. With none given, the playbook's step 1 picks it.
