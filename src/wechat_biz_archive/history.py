"""完整历史模式：调用公众号历史消息接口自动翻页。

本模块**只消费**会话凭证，不负责获取凭证。
凭证由使用者按 docs/SESSION_PROVIDER.md 在本机自备，通过
--credentials 文件或 WECHAT_BIZ_CREDENTIALS 环境变量传入。

凭证有效期通常只有几小时，请勿写入仓库或日志文件。
"""
import datetime
import html
import json
import re
import time
import urllib.parse
import urllib.request

from .models import Article, normalize_url

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
      "MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090a13) "
      "UnifiedPCWindowsWechat(0xf2541f38)")
ENDPOINT = "https://mp.weixin.qq.com/mp/profile_ext"


def normalize_credentials(cred):
    """兼容客户端请求里常见的多重 URL 编码。"""
    out = {}
    for k in ("uin", "key", "pass_ticket", "appmsg_token", "wxtoken"):
        v = cred.get(k) or ""
        times = 2 if k == "appmsg_token" else 1
        for _ in range(times):
            v = urllib.parse.unquote(v)
        out[k] = v
    return out


def build_url(cred, biz, offset=0, count=10):
    c = normalize_credentials(cred)
    params = {
        "action": "getmsg", "__biz": biz, "f": "json",
        "offset": str(offset), "count": str(count), "is_ok": "1", "scene": "124",
        "uin": c["uin"], "key": c["key"], "pass_ticket": c["pass_ticket"],
        "wxtoken": c["wxtoken"] or "777", "appmsg_token": c["appmsg_token"], "x5": "0",
    }
    return ENDPOINT + "?" + urllib.parse.urlencode(params)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def _parse_page(data):
    try:
        lst = json.loads(data.get("general_msg_list", "{}")).get("list", [])
    except (json.JSONDecodeError, AttributeError):
        return []
    out = []
    for m in lst:
        ts = m.get("comm_msg_info", {}).get("datetime")
        ext = m.get("app_msg_ext_info")
        if not ext:
            continue
        date = (datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                if ts else "")
        for it in [ext] + list(ext.get("multi_app_msg_item_list") or []):
            title = html.unescape(it.get("title") or "")
            url = normalize_url(it.get("content_url") or "")
            if title or url:
                out.append(Article.from_url(url, title, date,
                                            html.unescape(it.get("digest") or "")))
    return out


def probe(creds, biz):
    """逐组试探，返回第一个有效的凭证与首页数据。"""
    for cred in creds:
        try:
            data = json.loads(_get(build_url(cred, biz, 0)))
        except Exception:
            continue
        if data.get("ret") == 0:
            return cred, data
    return None, None


def fetch_full_history(biz, creds, max_pages=400, sleep=0.2, on_page=None):
    """自动翻到 can_msg_continue=0，返回按时间升序的 list[Article]。"""
    if isinstance(creds, dict):
        creds = creds.get("credentials", [creds])
    cred, data = probe(creds, biz)
    if cred is None:
        raise RuntimeError(
            "没有可用的会话凭证（全部返回 no session）。"
            "按 docs/SESSION_PROVIDER.md 重新获取后再试。"
        )

    all_items, seen = [], set()
    offset, page = 0, 0
    while data is not None and page < max_pages:
        items = _parse_page(data)
        for a in items:
            if a.key() not in seen:
                seen.add(a.key())
                all_items.append(a)
        page += 1
        if on_page:
            on_page(page, len(all_items))
        if not data.get("can_msg_continue"):
            break
        nxt = data.get("next_offset") or (offset + max(len(items), 1))
        if nxt <= offset:
            break
        offset = nxt
        time.sleep(sleep)
        try:
            data = json.loads(_get(build_url(cred, biz, offset)))
        except Exception:
            break
        if data.get("ret") != 0:
            break
    return sorted(all_items, key=lambda a: a.date)
