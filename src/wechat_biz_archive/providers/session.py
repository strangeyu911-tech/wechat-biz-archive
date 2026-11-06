"""完整历史输入源（--full）。

只负责加载使用者自备的会话凭证并交给 history 模块。
**本仓库不包含凭证获取实现**，获取方法见 docs/SESSION_PROVIDER.md。
"""
import json
import os

from ..history import fetch_full_history
from .base import Provider, register


def load_credentials(path=None):
    if path:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    else:
        raw = os.environ.get("WECHAT_BIZ_CREDENTIALS")
        if not raw:
            raise ValueError(
                "完整历史模式需要会话凭证：--credentials <文件> "
                "或环境变量 WECHAT_BIZ_CREDENTIALS。见 docs/SESSION_PROVIDER.md"
            )
        doc = json.loads(raw)
    if isinstance(doc, dict):
        return doc.get("credentials", [doc])
    return doc


@register
class SessionProvider(Provider):
    name = "session"
    description = "完整历史（需本人客户端会话凭证，见 docs/SESSION_PROVIDER.md）"
    requires_credentials = True

    def fetch(self, biz="", credentials=None, on_page=None, **kwargs):
        if not biz:
            raise ValueError("完整历史模式需要 --biz <公众号 __biz>")
        creds = load_credentials(credentials)
        return fetch_full_history(biz, creds, on_page=on_page)
