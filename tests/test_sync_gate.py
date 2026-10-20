"""Non-dry syncs report validation failures; dry runs remain read-only."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent


class SyncGateTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.clone = self.root / "upstream"
        self.clone.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        for name in ("scripts/check.py", "scripts/vendor_sync.py", ".agents/skills/port-cursor/check.py"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.clone), *args], env=self.env, capture_output=True, check=True)

    def sync(self, content, dry=False):
        skill = self.clone / "example/SKILL.md"
        skill.parent.mkdir(exist_ok=True)
        skill.write_text(content)
        self.git("add", ".")
        self.git("commit", "-m", "upstream")
        args = [sys.executable, str(self.repo / "scripts/vendor_sync.py"), "--name", "cursor", "--clone", str(self.clone), "--url", "https://example.com/upstream", "--ref", "main", "--skill", "example=example"]
        if dry:
            args.append("--dry-run")
        return subprocess.run(args, env=self.env, capture_output=True, text=True)

    def test_clean_sync_passes_validation(self):
        result = self.sync("Use the subagent tool.\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Repository validation passed", result.stdout)
        self.assertTrue((self.repo / "skills/cursor/upstream.json").is_file())

    def test_incompatible_sync_fails_and_leaves_files_for_repair(self):
        result = self.sync("Use Task tool.\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cursor-task", result.stderr)
        self.assertEqual((self.repo / "skills/cursor/example/SKILL.md").read_text(), "Use Task tool.\n")

    def test_dry_run_writes_nothing(self):
        result = self.sync("Use Task tool.\n", dry=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Repository validation passed", result.stdout)
        self.assertFalse((self.repo / "skills").exists())


if __name__ == "__main__":
    unittest.main()
