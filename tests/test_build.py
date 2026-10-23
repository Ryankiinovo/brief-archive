import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.tmp.name)
        for name in ("build_site.py", "site", "content"):
            src = ROOT / name
            dst = cls.work / name
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, dst)
        cls.result = subprocess.run(
            [sys.executable, "build_site.py"],
            cwd=cls.work,
            text=True,
            capture_output=True,
            timeout=120,
        )
        cls.index = (cls.work / "dist/index.html").read_text(encoding="utf-8")
        cls.about = (cls.work / "dist/about.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_succeeds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        self.assertIn("Built ", self.result.stdout)
        self.assertIn("Pages: index=1 about=1", self.result.stdout)
        self.assertGreater(len(list((ROOT / "content" / "briefs").glob("*.md"))), 0)

    def test_latest_brief_is_rendered(self):
        newest = max(p.stem for p in (ROOT / "content" / "briefs").glob("*.md"))
        month, day = int(newest[5:7]), int(newest[8:10])
        self.assertIn(f"{month}月{day}日新闻简报", self.index)
        self.assertIn('id="archiveSelect"', self.index)
        for section in ("今日重磅", "AI", "市场", "社会"):
            self.assertIn(section, self.index)

    def test_site_is_single_topic(self):
        self.assertFalse((self.work / "dist/reading.html").exists())
        self.assertNotIn('href="reading.html"', self.index)
        self.assertNotIn("读书", self.index)

    def test_about_page_exists(self):
        self.assertIn('id="aboutTitle"', self.about)
        self.assertIn("关于", self.about)

    def test_public_output_has_no_private_markers(self):
        joined = self.index + self.about
        for marker in ("/Users/", "陈昕冉", "18912744188", "124.220.199.205", "小昕札记"):
            self.assertNotIn(marker, joined)


if __name__ == "__main__":
    unittest.main()
