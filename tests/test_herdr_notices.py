"""The Herdr port preserves Apache notices through its sync lock."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent


class HerdrNoticeTest(unittest.TestCase):
    def test_port_preserves_optional_notice_files(self):
        for notices in ((), ("NOTICE", "NOTICE.txt", "NOTICE.md")):
            with self.subTest(notices=notices), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                repo = root / "repo"
                cache = root / "cache"
                clone = cache / "upstream/herdr"
                clone.mkdir(parents=True)
                env = {**os.environ, "AGENT_SETUP_CACHE": str(cache), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
                for args in (("init", "--initial-branch=main"), ("config", "user.name", "Test"), ("config", "user.email", "test@example.com"), ("config", "commit.gpgsign", "false")):
                    subprocess.run(["git", "-C", str(clone), *args], env=env, capture_output=True, check=True)
                skill = clone / "skills/herdr/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("---\nname: herdr\ndescription: Test fixture.\n---\n")
                (clone / "LICENSE").write_text("License fixture\n")
                for notice in notices:
                    (clone / notice).write_text(f"Upstream {notice} fixture\n")
                for args in (("add", "."), ("commit", "-m", "upstream")):
                    subprocess.run(["git", "-C", str(clone), *args], env=env, capture_output=True, check=True)
                script = ".agents/skills/port-herdr/scripts/port-herdr"
                for name in (script, "scripts/vendor_sync.py", "scripts/check.py"):
                    target = repo / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(REPO / name, target)
                result = subprocess.run(["bash", str(repo / script), "--no-pull", "--ref", "main"], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                group = repo / "skills/herdr"
                lock = json.loads((group / "upstream.json").read_text())
                self.assertEqual(set(lock["files"]), {"LICENSE", *notices})
                for notice in notices:
                    self.assertEqual((group / notice).read_bytes(), (clone / notice).read_bytes())


if __name__ == "__main__":
    unittest.main()
