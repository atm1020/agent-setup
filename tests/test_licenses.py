"""Every vendored upstream ships its license, synced through its lock, and the repo has its own."""
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class LicenseTest(unittest.TestCase):
    def test_repo_has_license(self):
        self.assertTrue((REPO / "LICENSE").is_file(), "no LICENSE at the repo root")

    def test_each_upstream_syncs_its_license(self):
        locks = sorted(REPO.glob("skills/*/upstream.json"))
        self.assertTrue(locks, "no skills/*/upstream.json found")
        for lock in locks:
            with self.subTest(upstream=lock.parent.name):
                files = json.loads(lock.read_text())["files"]
                licenses = [name for name in files if name.startswith("LICENSE")]
                self.assertTrue(licenses, f"{lock} syncs no LICENSE; add --file LICENSE=... to its port script")
                for name in licenses:
                    self.assertTrue((lock.parent / name).is_file(), f"{lock.parent / name} is in the lock but missing")


if __name__ == "__main__":
    unittest.main()
