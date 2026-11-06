"""数据模型。

Article 只保存公开可核验的元信息：标题、发布时间、文章 URL、群发序号。
不保存正文、摘要、任何会话凭证或个人信息。
"""
from dataclasses import dataclass
from datetime import datetime
import html
import re


@dataclass
class Article:
    title: str = ""
    date: str = ""
    url: str = ""
    mid: str = ""
    digest: str = ""

    @property
    def dt(self):
        try:
            return datetime.strptime(self.date[:16], "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return None

    @property
    def month(self):
        return self.date[:7] if self.date else ""

    @classmethod
    def from_url(cls, url, title="", date="", digest=""):
        url = html.unescape(url).replace("\\/", "/")
        m = re.search(r"[?&]mid=(\d+)", url)
        return cls(
            title=html.unescape(title or "").strip(),
            date=(date or "").strip(),
            url=url,
            mid=m.group(1) if m else "",
            digest=html.unescape(digest or ""),
        )

    def key(self):
        return self.url or self.title


def normalize_url(url):
    """把历史接口 / 聊天卡片里的转义还原成可直接打开的链接。"""
    url = html.unescape(url or "").replace("\\/", "/")
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # 从 CSV 行或 XML 片段里截出来的 URL 常带着尾随分隔符
    return url.strip().rstrip(",;)\"'")
