"""本地聊天记录输入源。

读取 wechat-cli 等工具导出的聊天记录（JSON / 文本 / XML 混合都行），
抽取其中的公众号文章卡片 URL 与标题。全程只读本机文件，不联网。
"""
import glob
import os
import re

from ..models import Article, normalize_url
from .base import Provider, register

URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s\?[^\s\"'<>,;)\\]+")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2}[ T]\d{2}:\d{2})")


@register
class ChatLogProvider(Provider):
    name = "chatlog"
    description = "本地聊天记录导出的文章卡片（只读本机文件）"

    def fetch(self, path=None, **kwargs):
        if not path:
            raise ValueError("chatlog 输入源需要 --input 指定文件或目录")
        paths = []
        if os.path.isdir(path):
            for ext in ("*.json", "*.txt", "*.md", "*.xml", "*.csv"):
                paths.extend(glob.glob(os.path.join(path, "**", ext), recursive=True))
        elif os.path.exists(path):
            paths = [path]
        else:
            raise FileNotFoundError("找不到输入路径：%s" % path)

        out = []
        for p in paths:
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for m in URL_RE.finditer(text):
                before = text[max(0, m.start() - 1200):m.start()]
                titles = TITLE_RE.findall(before)
                dates = DATE_RE.findall(before)
                out.append(Article.from_url(
                    normalize_url(m.group()),
                    titles[-1] if titles else "",
                    dates[-1].replace("T", " ") if dates else "",
                ))
        return out
