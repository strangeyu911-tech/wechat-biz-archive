import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wechat_biz_archive.analyze import dedupe, detect_phases, monthly_counts, overview
from wechat_biz_archive.models import Article

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sample():
    return [
        Article.from_url("https://mp.weixin.qq.com/s?__biz=X&mid=100&idx=1&sn=a", "A", "2022-09-09 18:30"),
        Article.from_url("https://mp.weixin.qq.com/s?__biz=X&mid=101&idx=1&sn=b", "B", "2022-09-11 20:00"),
        Article.from_url("https://mp.weixin.qq.com/s?__biz=X&mid=102&idx=1&sn=c", "C", "2025-10-26 12:18"),
        Article.from_url("https://mp.weixin.qq.com/s?__biz=X&mid=100&idx=1&sn=a", "A", "2022-09-09 18:30"),
    ]


class AnalyzeTest(unittest.TestCase):
    def test_from_url_parses_mid(self):
        self.assertEqual(sample()[0].mid, "100")

    def test_dedupe(self):
        self.assertEqual(len(dedupe(sample())), 3)

    def test_monthly(self):
        self.assertEqual(monthly_counts(sample()), {"2022-09": 3, "2025-10": 1})

    def test_phases_split_on_gap(self):
        phases = detect_phases(dedupe(sample()), gap_months=2)
        self.assertEqual(len(phases), 2)
        self.assertEqual(phases[0]["start"], "2022-09")
        self.assertEqual(phases[1]["start"], "2025-10")

    def test_overview(self):
        ov = overview(dedupe(sample()))
        self.assertEqual(ov["total"], 3)
        self.assertEqual(ov["earliest"], "2022-09-09 18:30")
        self.assertEqual(ov["latest"], "2025-10-26 12:18")


class ExtrasParseTest(unittest.TestCase):
    """只测解析逻辑，不触碰任何进程。"""

    def test_parse_credentials(self):
        import importlib.util
        path = os.path.join(ROOT, "extras", "collect_session.py")
        spec = importlib.util.spec_from_file_location("collect_session", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        url = (b"https://mp.weixin.qq.com/s?__biz=EXAMPLE&mid=1&idx=1&sn=abc"
               b"&key=deadbeef&uin=TEST%3D%3D&pass_ticket=TOKEN%3D%3D"
               b"&appmsg_token=AAtz%252Bfake&wxtoken=777")
        cred = mod.parse_credentials(url)
        self.assertEqual(cred["key"], "deadbeef")
        self.assertEqual(cred["appmsg_token"], "AAtz%252Bfake")
        self.assertEqual(cred["wxtoken"], "777")
        self.assertIsNone(mod.parse_credentials(b"https://example.com/?a=1"))


if __name__ == "__main__":
    unittest.main()
