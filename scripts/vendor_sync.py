#!/usr/bin/env python3
"""Sync vendored copies of upstream skills into skills/<upstream>/, keeping local edits.

Each port-<repo> skill fetches its upstream into a git clone and calls this with the
skills it publishes, plus extra files such as its README. skills/<upstream>/upstream.json
records the commit last synced and where each skill and file lives upstream. For every
file this does a 3-way merge between that commit (base), the new upstream commit (theirs)
and the copy in skills/<upstream>/ (ours):

  - unchanged locally    -> take upstream's version (including adds and deletes)
  - unchanged upstream   -> keep the local copy
  - changed on both      -> git merge-file; clashes are left as conflict markers

A tracked skill whose folder was deleted locally is recorded as excluded and never
re-added. New upstream skills are added. Skills removed upstream are deleted when
unmodified, otherwise kept and reported.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def git(clone: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, check=check)


def tree(clone: Path, commit: str | None, path: str | None) -> dict[str, tuple[str, str]]:
    """rel path -> (mode, blob sha) for every file under commit:path."""
    if not commit or not path:
        return {}
    r = git(clone, "ls-tree", "-r", "--full-tree", f"{commit}:{path}", check=False)
    if r.returncode:
        return {}
    out = {}
    for line in r.stdout.decode().splitlines():
        meta, rel = line.split("\t", 1)
        mode, kind, sha = meta.split()
        if kind == "blob":
            out[rel] = (mode, sha)
    return out


def blob(clone: Path, sha: str) -> bytes:
    return git(clone, "cat-file", "blob", sha).stdout


def local_files(dest: Path) -> dict[str, Path]:
    if not dest.is_dir():
        return {}
    return {str(p.relative_to(dest)): p for p in sorted(dest.rglob("*")) if p.is_file()}


def merge3(ours: bytes, base: bytes, theirs: bytes) -> tuple[bytes, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, data in (("ours", ours), ("base", base), ("theirs", theirs)):
            p = Path(tmp, name)
            p.write_bytes(data)
            paths.append(str(p))
        r = subprocess.run(
            ["git", "merge-file", "-p", "-L", "local", "-L", "base", "-L", "upstream", *paths],
            capture_output=True,
        )
        if r.returncode < 0 or r.returncode > 127:
            raise RuntimeError(r.stderr.decode())
        return r.stdout, r.returncode > 0


class Syncer:
    def __init__(self, clone: Path, base: str | None, new: str, dry: bool):
        self.clone, self.base, self.new, self.dry = clone, base, new, dry
        self.conflicts: list[str] = []
        self.stop = REPO / "skills"

    def write(self, path: Path, data: bytes, mode: str) -> None:
        if self.dry:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        os.chmod(path, 0o755 if mode == "100755" else 0o644)

    def delete(self, path: Path) -> None:
        if self.dry:
            return
        path.unlink()
        for parent in path.parents:
            if parent == self.stop or any(parent.iterdir()):
                break
            parent.rmdir()

    def sync_file(self, label: str, path: Path, b: tuple | None, t: tuple | None) -> str | None:
        """3-way merge one file. b and t are (mode, blob sha) at base and new, or None."""
        bb = blob(self.clone, b[1]) if b else None
        tt = blob(self.clone, t[1]) if t else None
        oo = path.read_bytes() if path.is_file() else None
        mode = (t or b or ("100644", ""))[0]
        if tt == bb or oo == tt:
            return None  # upstream unchanged, or local already matches upstream
        if oo == bb:  # unchanged locally: take upstream
            if tt is None:
                self.delete(path)
                return "delete"
            self.write(path, tt, mode)
            return "update" if oo is not None else "add"
        if None in (oo, bb, tt):  # modify/delete clash: keep local, report
            self.conflicts.append(f"{label} (changed on one side, deleted on the other; kept local)")
            return None
        merged, clash = merge3(oo, bb, tt)
        self.write(path, merged, mode)
        if clash:
            self.conflicts.append(label)
        return "merge (CONFLICT)" if clash else "merge"

    def sync_skill(self, name: str, dest: Path, base_path: str | None, new_path: str) -> list[str]:
        b, t, o = tree(self.clone, self.base, base_path), tree(self.clone, self.new, new_path), local_files(dest)
        notes = []
        for rel in sorted(set(b) | set(t) | set(o)):
            note = self.sync_file(f"{name}/{rel}", dest / rel, b.get(rel), t.get(rel))
            if note:
                notes.append(f"{note} {rel}")
        return notes

    def entry(self, commit: str | None, path: str | None) -> tuple | None:
        """(mode, blob sha) of a single file at commit, or None."""
        if not commit or not path:
            return None
        r = git(self.clone, "ls-tree", "--full-tree", commit, path, check=False)
        line = r.stdout.decode().strip()
        if r.returncode or not line:
            return None
        mode, kind, sha = line.split("\t", 1)[0].split()
        return (mode, sha) if kind == "blob" else None

    def remove_skill(self, name: str, dest: Path, base_path: str) -> str:
        b = tree(self.clone, self.base, base_path)
        o = local_files(dest)
        if set(b) == set(o) and all(blob(self.clone, b[r][1]) == o[r].read_bytes() for r in o):
            if not self.dry:
                shutil.rmtree(dest)
            return "removed upstream, deleted"
        return "removed upstream, kept (has local edits)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", required=True, help="upstream name; synced into skills/<name>/, lock in skills/<name>/upstream.json")
    ap.add_argument("--clone", required=True, type=Path, help="upstream git clone, checked out at the commit to sync")
    ap.add_argument("--url", required=True, help="upstream URL, recorded in the lock")
    ap.add_argument("--ref", required=True, help="branch or tag, recorded in the lock")
    ap.add_argument("--skill", action="append", default=[], metavar="NAME=PATH", help="a published skill and its folder in the clone")
    ap.add_argument("--file", action="append", default=[], metavar="DEST=PATH", help="an extra file (e.g. README.md=README.md) to keep in sync")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    group = REPO / "skills" / args.name
    lock_path = group / "upstream.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    tracked: dict[str, str] = lock.get("skills", {})
    tracked_files: dict[str, str] = lock.get("files", {})
    excluded: set[str] = set(lock.get("excluded", []))
    base = lock.get("commit")
    new = git(args.clone, "rev-parse", "HEAD").stdout.decode().strip()
    if base and git(args.clone, "cat-file", "-e", f"{base}^{{commit}}", check=False).returncode:
        sys.exit(f"base commit {base} not in {args.clone}; it needs full history (clone with --filter=blob:none)")

    upstream = dict(s.split("=", 1) for s in args.skill)
    files = dict(f.split("=", 1) for f in args.file)
    s = Syncer(args.clone, base, new, args.dry_run)
    s.stop = group
    prefix = "[dry-run] " if args.dry_run else ""
    print(f"{prefix}{args.name}: {base[:12] if base else '(first sync)'} -> {new[:12]}")

    for name, path in sorted(upstream.items()):
        dest = group / name
        if name in excluded:
            continue
        if name not in tracked:
            if dest.exists():
                s.conflicts.append(f"{name} (new upstream, but {dest.relative_to(REPO)} already exists; skipped)")
                continue
            notes = s.sync_skill(name, dest, None, path)
            print(f"  add     {name} ({len(notes)} files)")
            tracked[name] = path
            continue
        if not dest.exists():
            excluded.add(name)
            del tracked[name]
            print(f"  exclude {name} (deleted locally; won't be re-added)")
            continue
        notes = s.sync_skill(name, dest, tracked[name], path)
        tracked[name] = path
        for n in notes:
            print(f"  {name}: {n}")

    for name in sorted(set(tracked) - set(upstream)):
        dest = group / name
        print(f"  {name}: {s.remove_skill(name, dest, tracked[name]) if dest.exists() else 'removed upstream'}")
        del tracked[name]

    for dest_rel, path in sorted(files.items()):
        old = tracked_files.get(dest_rel)
        if old is None and (group / dest_rel).exists():
            s.conflicts.append(f"{dest_rel} (new upstream file, but it already exists locally; skipped)")
            continue
        note = s.sync_file(dest_rel, group / dest_rel, s.entry(base, old), s.entry(new, path))
        if note:
            print(f"  {dest_rel}: {note}")
        tracked_files[dest_rel] = path

    if not args.dry_run:
        group.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({
            "url": args.url, "ref": args.ref, "commit": new,
            "files": dict(sorted(tracked_files.items())),
            "skills": dict(sorted(tracked.items())), "excluded": sorted(excluded),
        }, indent=2) + "\n")

    for c in s.conflicts:
        print(f"  conflict {c}")
    if s.conflicts:
        print(f"{len(s.conflicts)} conflict(s): resolve the markers (<<<<<<< local / >>>>>>> upstream) before committing")
    if s.conflicts:
        return 1
    if not args.dry_run:
        # Each port owns its layout/harness policy. The shared gate only runs it.
        return subprocess.run([
            sys.executable, str(REPO / "scripts/check.py"), "--source", str(REPO),
        ]).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
