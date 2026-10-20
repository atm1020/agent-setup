"""The vendored test runner uses locked dependencies and disposable state."""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("vendored_runner", REPO / "scripts/test-vendored.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def archive(name="package/index.js", kind=tarfile.REGTYPE):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as result:
        item = tarfile.TarInfo(name)
        item.type = kind
        item.linkname = "/outside"
        content = b"export {};"
        item.size = len(content) if kind == tarfile.REGTYPE else 0
        result.addfile(item, io.BytesIO(content) if item.size else None)
    return output.getvalue()


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scripts = self.root / "skills/cursor/poteto-mode/scripts"
        self.scripts.mkdir(parents=True)
        (self.root / ".bun-version").write_text("1.3.14\n")
        self.data = archive()
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(self.data).digest()).decode()
        (self.scripts / "package.json").write_text(json.dumps({"dependencies": {"commander": "14.0.0"}, "scripts": {"test": "bun test orch check-plan.test.ts"}}))
        (self.scripts / "bun.lock").write_text(json.dumps({"packages": {"commander": ["commander@14.0.0", "", {}, integrity]}}))

    def executable(self, name, content):
        path = self.root / "bin" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("#!/bin/sh\n" + content)
        path.chmod(0o755)
        return str(path)

    def test_verified_archive_download(self):
        with patch.object(RUNNER.urllib.request, "urlopen", return_value=io.BytesIO(self.data)) as fetch:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(RUNNER.commander_archive(self.scripts), self.data)
            self.assertIn("commander-14.0.0.tgz", fetch.call_args.args[0])
            self.assertEqual(fetch.call_args.kwargs["timeout"], 30)

    def test_integrity_failure_is_fatal(self):
        with patch.object(RUNNER.urllib.request, "urlopen", return_value=io.BytesIO(b"wrong archive")):
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "integrity"):
                RUNNER.commander_archive(self.scripts)

    def test_dependency_changes_require_runner_update(self):
        (self.scripts / "package.json").write_text('{"dependencies":{"new-package":"1.0.0"}}')
        with self.assertRaisesRegex(RuntimeError, "dependencies changed"):
            RUNNER.commander_archive(self.scripts)

    def test_unpack_rejects_traversal_absolute_paths_and_links(self):
        for name, kind in (("package/../../escape", tarfile.REGTYPE), ("/escape", tarfile.REGTYPE), ("package/link", tarfile.SYMTYPE), ("package/link", tarfile.LNKTYPE)):
            with self.subTest(name=name, kind=kind):
                with self.assertRaisesRegex(RuntimeError, "unsafe"):
                    RUNNER.unpack(archive(name, kind), self.root / "dependency")
        self.assertFalse((self.root / "escape").exists())

    def test_missing_runtime_fails_with_actionable_message(self):
        with patch.object(RUNNER.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "missing test prerequisite: bun"):
                RUNNER.run(self.root)

    def test_wrong_bun_version_does_not_fetch_dependencies(self):
        bun = self.executable("bun", 'echo 0.0.0\n')
        with patch.object(RUNNER, "runtime", return_value=bun), patch.object(RUNNER, "commander_archive") as fetch:
            with self.assertRaisesRegex(RuntimeError, "Bun 1.3.14 required"):
                RUNNER.run(self.root)
            fetch.assert_not_called()

    def test_scratch_isolation_cleanup_and_exit_status(self):
        trace = self.root / "trace"
        bun = self.executable("bun", 'if [ "$1" = --version ]; then echo 1.3.14; exit; fi\n[ "$1 $2" = "run test" ] || exit 90\n[ -f node_modules/commander/index.js ] || exit 91\n[ -z "${GIT_DIR+x}${ORCH_STORE+x}${NODE_OPTIONS+x}" ] || exit 92\nprintf "%s\\n" "$PWD" "$HOME" "$TMPDIR" "$XDG_CONFIG_HOME" > "$TEST_TRACE"\nexit "$TEST_EXIT"\n')
        node = self.executable("node", 'echo v22.0.0\n')
        paths = {"bun": bun, "node": node, "git": "/usr/bin/git"}
        for code in (0, 7):
            with self.subTest(code=code):
                with patch.object(RUNNER, "runtime", side_effect=lambda name: paths[name]), patch.object(RUNNER, "commander_archive", return_value=self.data), patch.dict(os.environ, TEST_TRACE=str(trace), TEST_EXIT=str(code), GIT_DIR="/must-not-use", ORCH_STORE="/must-not-use", NODE_OPTIONS="--must-not-use"), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(RUNNER.run(self.root), code)
                for location in trace.read_text().splitlines():
                    self.assertNotEqual(location, str(self.scripts))
                    self.assertFalse(Path(location).exists(), location)
                self.assertFalse((self.scripts / "node_modules").exists())


if __name__ == "__main__":
    unittest.main()
