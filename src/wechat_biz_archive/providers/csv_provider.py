"""CSV / URL 清单输入源。

支持三种格式：
1. 带表头的 CSV（date,title,url,mid，列名大小写不敏感，缺列可留空）
2. 无表头 CSV（第一列当作 URL）
3. 纯文本文件，一行一个微信文章 URL
"""
import csv
import os
import re

from ..models import Article, normalize_url
from .base import Provider, register

URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s\?[^\s\"'<>,;)\\]+")


@register
class CsvProvider(Provider):
    name = "csv"
    description = "CSV 或纯文本 URL 清单（零配置，随仓库附示例数据）"

    def fetch(self, path=None, **kwargs):
        if not path:
            raise ValueError("csv 输入源需要 --input 指定文件")
        if not os.path.exists(path):
            raise FileNotFoundError("找不到输入文件：%s" % path)

        with open(path, encoding="utf-8-sig", errors="replace") as f:
            raw = f.read()

        # 纯文本 URL 清单
        if "mp.weixin.qq.com/s?" in raw and "\n" in raw and "," not in raw.split("\n")[0]:
            return [Article.from_url(normalize_url(u)) for u in URL_RE.findall(raw)]

        rows = list(csv.reader(raw.splitlines()))
        if not rows:
            return []
        header = [h.strip().lower() for h in rows[0]]
        known = {"date", "title", "url", "mid", "digest"}
        has_header = bool(known.intersection(header))
        idx = {k: header.index(k) for k in header if k in known} if has_header else {}

        out = []
        for row in rows[1:] if has_header else rows:
            if not row:
                continue
            if has_header:
                get = lambda k: row[idx[k]] if k in idx and idx[k] < len(row) else ""
                url, title = get("url"), get("title")
                date, digest = get("date"), get("digest")
                mid = get("mid")
            else:
                url, title, date, digest, mid = row[0], "", "", "", ""
            if not url or "mp.weixin.qq.com" not in url:
                continue
            a = Article.from_url(normalize_url(url), title, date, digest)
            if mid and not a.mid:
                a.mid = mid
            out.append(a)
        return out
