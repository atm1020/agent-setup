#!/usr/bin/env python3
"""Install skills and subagents from one or more source trees into Claude Code, OpenCode and Pi.

A source is either a tree of Cursor-style plugins (any dir containing
.cursor-plugin/plugin.json, e.g. a cursor/plugins checkout) or a plain dir with
skills/<name>/SKILL.md and agents/*.md (treated as one plugin named after the dir).

Skills already follow the Agent Skills format, so they are copied (or symlinked
with --link) unchanged, except names that are not lowercase-hyphen get fixed.
Agents are rewritten into each tool's native subagent format.

  claude    skills -> ~/.claude/skills/<name>/   agents -> ~/.claude/agents/<name>.md
  opencode  skills -> ~/.config/opencode/skills/ agents -> ~/.config/opencode/agents/<name>.md
  agents    skills -> ~/.agents/skills/<name>/   (shared dir read by Pi, OpenCode, Codex)

OpenCode also reads ~/.claude/skills and ~/.agents/skills, so its own skills dir
is only used when neither claude nor agents is targeted.

Every install is recorded in .cursor-plugins-port.json in the target root.
Files this script did not create are never overwritten without --force,
--prune removes previously installed items that are no longer selected, and
--uninstall removes everything it installed.

Examples:
  port.py --source ~/src/cursor-plugins --list
  port.py --source ~/src/cursor-plugins --plugins pstack --source . --link --prune
  port.py --uninstall --target claude,opencode,agents
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST = ".cursor-plugins-port.json"
TARGETS = ("claude", "opencode", "agents")

# Cursor "readonly: true" agents get these tools in Claude Code.
CLAUDE_READONLY_TOOLS = "Read, Grep, Glob, Bash, WebFetch, WebSearch"
# Cursor model aliases -> Claude Code subagent model aliases. Anything else is dropped (inherits).
CLAUDE_MODEL_MAP = {"fast": "haiku", "inherit": "inherit"}


@dataclass
class Skill:
    plugin: str
    name: str
    path: Path


@dataclass
class Agent:
    plugin: str
    name: str
    path: Path
    meta: dict
    body: str


@dataclass
class Plugin:
    name: str
    root: Path
    skills: list[Skill] = field(default_factory=list)
    agents: list[Agent] = field(default_factory=list)
    rules: list[Path] = field(default_factory=list)
    has_hooks: bool = False
    has_mcp: bool = False


# --- frontmatter -----------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML frontmatter parser: flat `key: value` pairs plus `>`/`|` block scalars."""
    if not text.startswith("---"):
        return {}, text
    end = re.search(r"^---\s*$", text[3:], re.M)
    if not end:
        return {}, text
    raw = text[3 : 3 + end.start()]
    body = text[3 + end.end() :].lstrip("\n")
    meta: dict = {}
    key = None
    block: list[str] | None = None
    fold = False
    for line in raw.splitlines():
        if block is not None and (line.startswith((" ", "\t")) or not line.strip()):
            block.append(line.strip())
            continue
        if block is not None:
            meta[key] = (" " if fold else "\n").join(x for x in block if x).strip()
            block = None
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", "|", "|-"):
            block, fold = [], val.startswith(">")
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        meta[key] = {"true": True, "false": False}.get(val, val)
    if block is not None:
        meta[key] = (" " if fold else "\n").join(x for x in block if x).strip()
    return meta, body


def yaml_scalar(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val)
    if s == "" or re.search(r"[:#\[\]{}&*!|>'\"%@`]|^\s|\s$|^-", s):
        return json.dumps(s)
    return s


def render(meta: dict, body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            lines.extend(f"  {sk}: {yaml_scalar(sv)}" for sk, sv in v.items())
        else:
            lines.append(f"{k}: {yaml_scalar(v)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# --- discovery -------------------------------------------------------------


def discover(source: Path) -> list[Plugin]:
    manifests = [m for m in sorted(source.glob("**/.cursor-plugin/plugin.json")) if ".git" not in m.parts]
    if manifests:
        found = [(m.parent.parent, json.loads(m.read_text())) for m in manifests]
    else:
        found = [(source, {"name": source.name})]
    return [load_plugin(root, data) for root, data in found]


def skill_files(skills_dir: Path) -> list[Path]:
    """SKILL.md of every skill under skills_dir. A folder without a SKILL.md is a group
    (e.g. skills/<upstream>/<skill>) and is searched; a skill's own subfolders are not."""
    if not skills_dir.is_dir():
        return []
    found = []
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        found += [d / "SKILL.md"] if (d / "SKILL.md").is_file() else skill_files(d)
    return found


def load_plugin(root: Path, data: dict) -> Plugin:
    p = Plugin(name=data.get("name", root.name), root=root)
    skills_dir = root / str(data.get("skills", "skills")).strip("./").rstrip("/")
    for sk in skill_files(skills_dir):
        meta, _ = parse_frontmatter(sk.read_text())
        p.skills.append(Skill(p.name, slug(str(meta.get("name") or sk.parent.name)), sk.parent))
    agents_dir = root / str(data.get("agents", "agents")).strip("./").rstrip("/")
    agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    # Vendored upstreams keep their agents in skills/<upstream>/agents/<plugin>/.
    for group in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not (p / "SKILL.md").exists()) if skills_dir.is_dir() else []:
        agent_files += sorted((group / "agents").glob("**/*.md"))
    for ag in agent_files:
        meta, body = parse_frontmatter(ag.read_text())
        p.agents.append(Agent(p.name, slug(str(meta.get("name") or ag.stem)), ag, meta, body))
    p.rules = sorted((root / "rules").glob("*.mdc")) if (root / "rules").is_dir() else []
    p.has_hooks = (root / "hooks" / "hooks.json").exists()
    p.has_mcp = (root / "mcp.json").exists() or (root / ".mcp.json").exists()
    return p


# --- agent conversion ------------------------------------------------------


def to_claude_agent(a: Agent) -> str:
    meta = {"name": a.name, "description": a.meta.get("description", "")}
    model = CLAUDE_MODEL_MAP.get(str(a.meta.get("model", "")))
    if model:
        meta["model"] = model
    if a.meta.get("readonly") is True:
        meta["tools"] = CLAUDE_READONLY_TOOLS
    return render(meta, a.body)


def to_opencode_agent(a: Agent) -> str:
    meta: dict = {"description": a.meta.get("description", ""), "mode": "subagent"}
    if a.meta.get("readonly") is True:
        meta["permission"] = {"edit": "deny"}
    return render(meta, a.body)


def skill_rename(s: Skill) -> str | None:
    """Agent Skills names must be lowercase-hyphen and match the dir; fix ones like 'X MCP guide'."""
    meta, _ = parse_frontmatter((s.path / "SKILL.md").read_text())
    return s.name if str(meta.get("name", "")) != s.name else None


# --- install plan ----------------------------------------------------------


@dataclass
class Op:
    kind: str  # "skill" | "agent"
    dest: Path
    src: Path | None = None  # skill dir to copy/link
    rename: str | None = None  # rewrite SKILL.md `name:` to this (forces copy)
    content: str | None = None  # rendered agent file


def target_roots(base: Path, project: bool) -> dict[str, Path]:
    if project:
        return {"claude": base / ".claude", "opencode": base / ".opencode", "agents": base / ".agents"}
    return {
        "claude": base / ".claude",
        "opencode": base / ".config" / "opencode",
        "agents": base / ".agents",
    }


def opencode_agents_dir(root: Path) -> Path:
    # OpenCode accepts both; reuse the legacy singular dir if that's what the user already has.
    if (root / "agent").is_dir() and not (root / "agents").is_dir():
        return root / "agent"
    return root / "agents"


def plan(plugins: list[Plugin], targets: list[str], roots: dict[str, Path], want_skills: bool, want_agents: bool):
    ops: dict[str, list[Op]] = {t: [] for t in targets}
    warnings: list[str] = []

    seen_skill: dict[str, str] = {}
    skills: list[Skill] = []
    for p in plugins:
        for s in p.skills:
            if s.name in seen_skill:
                warnings.append(f"skill '{s.name}' from {p.name} skipped: already provided by {seen_skill[s.name]}")
                continue
            seen_skill[s.name] = p.name
            skills.append(s)
    seen_agent: dict[str, str] = {}
    agents: list[Agent] = []
    for p in plugins:
        for a in p.agents:
            if a.name in seen_agent:
                warnings.append(f"agent '{a.name}' from {p.name} skipped: already provided by {seen_agent[a.name]}")
                continue
            seen_agent[a.name] = p.name
            agents.append(a)

    for t in targets:
        root = roots[t]
        skill_dir = {"claude": root / "skills", "opencode": root / "skills", "agents": root / "skills"}[t]
        install_skills = want_skills and not (t == "opencode" and ({"claude", "agents"} & set(targets)))
        if install_skills:
            ops[t] += [Op("skill", skill_dir / s.name, src=s.path, rename=skill_rename(s)) for s in skills]
        if want_agents and t == "claude":
            ops[t] += [Op("agent", root / "agents" / f"{a.name}.md", content=to_claude_agent(a)) for a in agents]
        if want_agents and t == "opencode":
            d = opencode_agents_dir(root)
            ops[t] += [Op("agent", d / f"{a.name}.md", content=to_opencode_agent(a)) for a in agents]

    mcp = [p.name for p in plugins if p.has_mcp]
    if mcp:
        warnings.append(f"{len(mcp)} plugin(s) ship mcp.json, not ported (add servers to your MCP config by hand): {', '.join(mcp)}")
    for p in plugins:
        if p.rules:
            warnings.append(f"{p.name}: {len(p.rules)} Cursor rule(s) (.mdc) not ported: {', '.join(r.name for r in p.rules)}")
        if p.has_hooks:
            warnings.append(f"{p.name}: Cursor hooks not ported (hooks/hooks.json)")
    return ops, warnings


# --- manifest + filesystem -------------------------------------------------


def load_manifest(root: Path) -> set[str]:
    f = root / MANIFEST
    try:
        return set(json.loads(f.read_text()).get("paths", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_manifest(root: Path, paths: set[str]) -> None:
    f = root / MANIFEST
    if not paths:
        f.unlink(missing_ok=True)
        return
    root.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"paths": sorted(paths)}, indent=2) + "\n")


def remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def apply(target: str, root: Path, ops: list[Op], link: bool, force: bool, dry: bool, prune: bool) -> tuple[int, int]:
    owned = load_manifest(root)
    done = skipped = 0
    if prune:
        wanted = {str(op.dest.relative_to(root)) for op in ops}
        for rel in sorted(owned - wanted):
            print(f"  prune {root / rel}")
            if not dry:
                remove(root / rel)
            owned.discard(rel)
    for op in ops:
        rel = str(op.dest.relative_to(root))
        exists = op.dest.exists() or op.dest.is_symlink()
        if exists and rel not in owned and not force:
            print(f"  skip  {op.dest}  (exists, not installed by this script; --force to overwrite)")
            skipped += 1
            continue
        do_link = op.kind == "skill" and link and not op.rename
        verb = "link" if do_link else "write" if op.kind == "agent" else "copy"
        print(f"  {verb:5} {op.dest}")
        done += 1
        if dry:
            continue
        if exists:
            remove(op.dest)
        op.dest.parent.mkdir(parents=True, exist_ok=True)
        if op.kind == "skill":
            if do_link:
                op.dest.symlink_to(op.src, target_is_directory=True)
            else:
                shutil.copytree(op.src, op.dest, symlinks=True)
                if op.rename:
                    md = op.dest / "SKILL.md"
                    md.write_text(re.sub(r"^name:.*$", f"name: {op.rename}", md.read_text(), count=1, flags=re.M))
        else:
            op.dest.write_text(op.content)
        owned.add(rel)
    if not dry:
        save_manifest(root, owned)
    return done, skipped


def uninstall(root: Path, dry: bool) -> int:
    owned = load_manifest(root)
    for rel in sorted(owned):
        p = root / rel
        print(f"  rm    {p}")
        if not dry:
            remove(p)
    if not dry:
        save_manifest(root, set())
    return len(owned)


# --- cli -------------------------------------------------------------------


def pair_sources(argv: list[str]) -> list[tuple[str, str | None]]:
    """Pair each --source with the --plugins that follows it (before the next --source)."""
    pairs: list[list] = []
    it = iter(range(len(argv)))
    for i in it:
        a = argv[i]
        key, _, val = a.partition("=")
        if key in ("--source", "--plugins"):
            if not val:
                val = argv[i + 1] if i + 1 < len(argv) else ""
                next(it, None)
            if key == "--source":
                pairs.append([val, None])
            else:
                if not pairs:
                    pairs.append([".", None])
                pairs[-1][1] = ",".join(x for x in (pairs[-1][1], val) if x)
    return [tuple(p) for p in pairs] or [(".", None)]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--source", action="append", metavar="DIR", help="source tree (repeatable; default: current dir)")
    ap.add_argument("--target", default="claude,opencode", help=f"comma list of {','.join(TARGETS)} (default: claude,opencode)")
    ap.add_argument("--plugins", action="append", help="comma list of plugin names to take from the preceding --source (default: all)")
    ap.add_argument("--project", metavar="DIR", help="install into DIR/.claude, DIR/.opencode, DIR/.agents instead of $HOME")
    ap.add_argument("--skills-only", action="store_true", help="port skills only")
    ap.add_argument("--agents-only", action="store_true", help="port agents only")
    ap.add_argument("--link", action="store_true", help="symlink skill dirs to this repo instead of copying (edits show up live)")
    ap.add_argument("--force", action="store_true", help="overwrite existing files not created by this script")
    ap.add_argument("--prune", action="store_true", help="remove previously installed items that are no longer selected")
    ap.add_argument("--dry-run", action="store_true", help="print what would happen without touching anything")
    ap.add_argument("--list", action="store_true", help="list plugins with their skills and agents, then exit")
    ap.add_argument("--uninstall", action="store_true", help="remove everything this script installed for the given targets")
    args = ap.parse_args()

    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    bad = [t for t in targets if t not in TARGETS]
    if bad:
        ap.error(f"unknown target(s): {', '.join(bad)}; choose from {', '.join(TARGETS)}")
    if args.skills_only and args.agents_only:
        ap.error("--skills-only and --agents-only are mutually exclusive")

    plugins: list[Plugin] = []
    for src, filt in pair_sources(sys.argv[1:]):
        found = discover(Path(src).expanduser().resolve())
        if filt:
            wanted = {x.strip() for x in filt.split(",") if x.strip()}
            unknown = wanted - {p.name for p in found}
            if unknown:
                ap.error(f"unknown plugin(s) in {src}: {', '.join(sorted(unknown))} (see --list)")
            found = [p for p in found if p.name in wanted]
        plugins += found

    if args.list:
        for p in plugins:
            if not (p.skills or p.agents):
                continue
            extras = [x for x, on in (("rules", p.rules), ("hooks", p.has_hooks), ("mcp", p.has_mcp)) if on]
            print(f"{p.name}  ({len(p.skills)} skills, {len(p.agents)} agents{', ' + '/'.join(extras) + ' not ported' if extras else ''})")
            for s in p.skills:
                print(f"    skill  {s.name}")
            for a in p.agents:
                print(f"    agent  {a.name}")
        return 0

    base = Path(args.project).expanduser().resolve() if args.project else Path.home()
    roots = target_roots(base, bool(args.project))
    prefix = "[dry-run] " if args.dry_run else ""

    if args.uninstall:
        for t in targets:
            print(f"{prefix}{t}: {roots[t]}")
            n = uninstall(roots[t], args.dry_run)
            print(f"  {n} item(s) removed")
        return 0

    ops, warnings = plan(plugins, targets, roots, not args.agents_only, not args.skills_only)
    for t in targets:
        print(f"{prefix}{t}: {roots[t]}")
        if t == "opencode" and {"claude", "agents"} & set(targets) and not args.agents_only:
            print("  (skills come from .claude/skills / .agents/skills, which OpenCode also reads)")
        done, skipped = apply(t, roots[t], ops[t], args.link, args.force, args.dry_run, args.prune)
        print(f"  {done} installed, {skipped} skipped")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
