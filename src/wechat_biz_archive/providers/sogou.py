"""搜狗微信检索输入源（尽力而为）。

只用来补标题和日期，不依赖它的跳转链接（该跳转有反爬）。
任何网络异常都降级为空列表，不影响主流程。
"""
import datetime
import html
import re
import urllib.parse
import urllib.request

from ..models import Article
from .base import Provider, register

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
BASE = "https://weixin.sogou.com/weixin"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def _clean(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


@register
class SogouProvider(Provider):
    name = "sogou"
    description = "搜狗微信检索（仅补标题/日期，可能被反爬，失败自动降级）"

    def fetch(self, query="", account="", max_page=4, **kwargs):
        if not query:
            return []
        found = {}
        for page in range(1, int(max_page) + 1):
            params = {"type": "2", "query": query, "ie": "utf8", "page": str(page)}
            try:
                body = _get(BASE + "?" + urllib.parse.urlencode(params))
            except Exception:
                break
            items = re.findall(r'<li[^>]*id="sogou_vr_11002601_box_\d+".*?</li>', body, re.S)
            if not items:
                items = re.split(r'<li[^>]*id="sogou_vr_11002601_box_', body)[1:]
            for it in items:
                m = re.search(r"<h3>.*?<a[^>]*>(.*?)</a>", it, re.S)
                acct = re.search(r'class="all-time-y2">(.*?)</span>', it, re.S)
                ts = re.search(r"timeConvert\('(\d+)'\)", it)
                if not m:
                    continue
                name = _clean(acct.group(1)) if acct else ""
                if account and account not in name:
                    continue
                if not ts:
                    continue
                title = _clean(m.group(1))
                date = datetime.datetime.fromtimestamp(int(ts.group(1))).strftime("%Y-%m-%d %H:%M")
                found[title] = Article(title=title, date=date, url="")
        return sorted(found.values(), key=lambda a: a.date)
