#!/usr/bin/env python3
"""Run pstack's script tests in scratch space. Needs pinned Bun, Node >=20 and git.

Fetches only the locked commander runtime package, verifies its integrity, and
never installs packages or runs lifecycle scripts in this repository or HOME.
"""

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

REPO = Path(__file__).resolve().parent.parent


def die(message):
    raise RuntimeError(message)


def runtime(name):
    executable = shutil.which(name)
    if not executable:
        die(f"missing test prerequisite: {name}; see docs/setup.md#verification")
    return str(Path(executable).resolve())


def commander_archive(scripts):
    package = json.loads((scripts / "package.json").read_text())
    dependencies = package.get("dependencies", {})
    if set(dependencies) != {"commander"}:
        die("runtime dependencies changed; update the scratch runner before testing")
    version = dependencies["commander"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        die("commander must have an exact version")
    # Bun's text lock is JSON with trailing commas; these lock fields contain no
    # strings with comma-plus-closing-brace text.
    lock = json.loads(re.sub(r",(\s*[}\]])", r"\1", (scripts / "bun.lock").read_text()))
    entry = lock["packages"]["commander"]
    if entry[0] != f"commander@{version}" or entry[2]:
        die("commander lock mismatch or new transitive dependencies")
    integrity = entry[3]
    if not integrity.startswith("sha512-"):
        die("commander lock must supply sha512 integrity")
    url = f"https://registry.npmjs.org/commander/-/commander-{version}.tgz"
    print(f"Fetching locked commander@{version} for scratch tests", flush=True)
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()
    actual = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if actual != integrity:
        die("commander archive failed lockfile integrity verification")
    return data


def unpack(data, destination):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != "package" or ".." in parts:
                die(f"unsafe dependency archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile():
                die(f"unsafe dependency archive entry: {member.name}")
            target = destination.joinpath(*parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def run(source):
    bun, node = runtime("bun"), runtime("node")
    runtime("git")
    expected = (source / ".bun-version").read_text().strip()
    version = subprocess.check_output([bun, "--version"], text=True).strip()
    if version != expected:
        die(f"Bun {expected} required for tests, found {version}")
    node_version = subprocess.check_output([node, "--version"], text=True).strip()
    if int(node_version.lstrip("v").split(".")[0]) < 20:
        die(f"Node >=20 required for tests, found {node_version}")
    scripts = source / "skills/cursor/poteto-mode/scripts"
    data = commander_archive(scripts)
    with tempfile.TemporaryDirectory(prefix="agent-setup-tests-") as temporary:
        scratch = Path(temporary)
        work = scratch / "scripts"
        shutil.copytree(scripts, work, ignore=shutil.ignore_patterns("node_modules", ".git", "__pycache__"))
        unpack(data, work / "node_modules/commander")
        # Inherited git/store overrides could redirect test writes outside scratch.
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("GIT_", "ORCH_")) and key not in {"NODE_OPTIONS", "BUN_OPTIONS"}
        }
        for name, relative in {
            "HOME": "home", "XDG_CONFIG_HOME": "config", "XDG_DATA_HOME": "data",
            "XDG_CACHE_HOME": "cache", "BUN_INSTALL_CACHE_DIR": "bun-cache", "TMPDIR": "tmp",
        }.items():
            directory = scratch / relative
            directory.mkdir()
            env[name] = str(directory)
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        # Ensure child tests use the checked runtimes even when PATH used shims.
        env["PATH"] = os.pathsep.join([str(Path(bun).parent), str(Path(node).parent), env.get("PATH", "")])
        print(f"Testing scratch copy with Bun {version} and Node {node_version}", flush=True)
        return subprocess.run([bun, "run", "test"], cwd=work, env=env).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO, help="repository to test")
    args = parser.parse_args()
    try:
        return run(args.source.resolve())
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(f"test-vendored: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
