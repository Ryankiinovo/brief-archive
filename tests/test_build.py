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
        for name in ("build_site.py", "reading_archive.py", "site", "content"):
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
        cls.reading = (cls.work / "dist/reading.html").read_text(encoding="utf-8")
        cls.about = (cls.work / "dist/about.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_build_succeeds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        self.assertIn("Built 3 briefs", self.result.stdout)
        self.assertIn("reading=2 books/8 excerpts", self.result.stdout)

    def test_latest_brief_is_rendered(self):
        self.assertIn("10月20日新闻简报", self.index)
        self.assertIn("示例科技发布支持长上下文的模型", self.index)
        self.assertIn("5 条要闻", self.index)

    def test_reading_page_counts(self):
        self.assertEqual(len(re.findall(r'class="excerpt-card"', self.reading)), 8)
        self.assertEqual(len(re.findall(r'class="excerpt-note"', self.reading)), 3)
        self.assertIn("共 8 条摘录", self.reading)
        self.assertIn('id="excerptPager"', self.reading)

    def test_reading_page_has_no_broken_source_count(self):
        self.assertNotIn("源文件 0 个划线块", self.reading)
        self.assertNotIn("None 个划线块", self.reading)

    def test_about_page_exists(self):
        self.assertIn("关于这个项目", self.about)

    def test_public_output_has_no_private_markers(self):
        joined = self.index + self.reading + self.about
        for marker in ("/Users/", "陈昕冉", "18912744188", "124.220.199.205", "小昕札记"):
            self.assertNotIn(marker, joined)


if __name__ == "__main__":
    unittest.main()
