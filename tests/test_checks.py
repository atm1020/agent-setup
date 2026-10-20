"""Validation gates run before an installer can write to tool folders."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load(REPO / "scripts/check.py")
CURSOR = load(REPO / ".agents/skills/port-cursor/check.py")


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "skills").mkdir()

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        return target

    def test_all_merge_markers_report_line_numbers(self):
        for marker in ("<<<<<<< local", "=======", ">>>>>>> upstream", "||||||| base"):
            with self.subTest(marker=marker):
                self.put("skills/test/SKILL.md", "intro\n" + marker + "\n")
                errors = CHECK.conflict_errors(self.root)
                self.assertEqual(len(errors), 1)
                self.assertIn("skills/test/SKILL.md:2:", errors[0])

    def test_quoted_markers_binary_and_generated_files_are_not_conflicts(self):
        self.put("skills/test/SKILL.md", "Example: `<<<<<<< local`\n---\n")
        self.put("node_modules/fixture", "<<<<<<< local\n")
        self.put("skills/image", "\0<<<<<<< local\n")
        self.assertEqual(CHECK.conflict_errors(self.root), [])

    def test_cursor_rules_reject_incompatible_instructions(self):
        cases = {
            "cursor-task": 'Use Task tool with subagent_type: generalPurpose',
            "cursor-path": 'Read agent-transcripts/chat.jsonl',
            "unsupported-model": 'Use grok-4.7-xhigh-fast',
            "deleted-workflow": 'Read playbooks/opening-a-pr.md',
            "origin-cli": 'Run origin pr merge 1',
            "cursor-loop": 'Arm `/loop 1h`',
            "cloud-worker": 'Each worker is a Cursor cloud agent',
        }
        for rule, text in cases.items():
            with self.subTest(rule=rule):
                self.put("skills/cursor/test/SKILL.md", text)
                self.assertTrue(any(rule in error for error in CURSOR.errors(self.root)))

    def test_cursor_accepts_adaptations_and_upstream_provenance(self):
        self.put("skills/cursor/README.pstack.md", 'Use Task tool and grok-4.7')
        self.put("skills/cursor/test/SKILL.md", 'Use `subagent` with `openai/gpt-6.1-sol`. OpenCode has no cloud agents or `/loop`.')
        self.put("skills/cursor/test/tool.ts", 'const forge = "origin";')
        self.assertEqual(CURSOR.errors(self.root), [])

    def test_cursor_rejects_restored_deleted_workflow(self):
        self.put("skills/cursor/poteto-mode/scripts/watch-pr/watch-pr", "restored")
        self.assertTrue(any("deleted workflow was restored" in error for error in CURSOR.errors(self.root)))

    def test_shared_checker_runs_port_policy(self):
        target = self.root / ".agents/skills/port-cursor/check.py"
        target.parent.mkdir(parents=True)
        shutil.copy2(REPO / ".agents/skills/port-cursor/check.py", target)
        self.put("skills/cursor/test/SKILL.md", "Use grok-4.7")
        result = subprocess.run([sys.executable, str(REPO / "scripts/check.py"), "--source", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported-model", result.stderr)

    def test_install_blocks_before_home_writes(self):
        for name in ("install.sh", "scripts/check.py", "scripts/port.py"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
        self.put("skills/test/SKILL.md", "<<<<<<< local\n")
        home = self.root / "home"
        home.mkdir()
        env = {**os.environ, "HOME": str(home)}
        for flags in ([], ["--dry-run"]):
            with self.subTest(flags=flags):
                result = subprocess.run(["bash", str(self.root / "install.sh"), "--no-herdr", *flags], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn("unresolved merge marker", result.stderr)
                self.assertEqual(list(home.iterdir()), [])

    def test_uninstall_is_available_despite_conflicts(self):
        for name in ("install.sh", "scripts/port.py"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
        self.put("skills/test/SKILL.md", "<<<<<<< local\n")
        home = self.root / "home"
        home.mkdir()
        result = subprocess.run(["bash", str(self.root / "install.sh"), "--uninstall", "--dry-run"], env={**os.environ, "HOME": str(home)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
