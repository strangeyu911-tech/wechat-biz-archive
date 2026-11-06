"""Markdown 报告生成。"""
from .analyze import monthly_counts, overview, sorted_articles


def _bar(n, peak, width=28):
    if peak <= 0:
        return ""
    return "#" * max(1, round(n / peak * width))


def render(articles, source="", earliest_n=15):
    items = sorted_articles(articles)
    ov = overview(items)
    monthly = monthly_counts(items)
    lines = [
        "# 公众号内容归档报告", "",
        "> 由 wechat-biz-archive 生成 · 仅包含公开文章元信息（标题 / 日期 / 链接）", "",
        "## 概览", "",
        "| 指标 | 值 |", "|---|---|",
        "| 文章总数 | %d |" % ov["total"],
        "| 有发布时间 | %d |" % ov["with_date"],
        "| 有可打开链接 | %d |" % ov["with_url"],
        "| 最早 | %s |" % (ov["earliest"] or "—"),
        "| 最新 | %s |" % (ov["latest"] or "—"),
        "| 覆盖月份 | %d |" % ov["months"],
    ]
    if source:
        lines += ["| 输入源 | %s |" % source]
    lines += ["", "## 月度分布", "", "```"]

    peak = max(monthly.values()) if monthly else 0
    for m, n in monthly.items():
        lines.append("%s  %3d  %s" % (m, n, _bar(n, peak)))
    if not monthly:
        lines.append("（无日期信息）")
    lines += ["```", ""]

    from .analyze import detect_phases
    phases = detect_phases(items)
    if phases:
        lines += ["## 活跃阶段", "", "| 起 | 止 | 月份数 | 篇数 | 月均 |", "|---|---|---|---|---|"]
        for p in phases:
            lines.append("| %s | %s | %d | %d | %s |" %
                         (p["start"], p["end"], p["months"], p["count"], p["per_month"]))
        lines.append("")

    lines += ["## 最早 %d 篇" % min(earliest_n, len(items)), "",
              "| # | 发布时间 | 标题 | 链接 |", "|---|---|---|---|"]
    for i, a in enumerate(items[:earliest_n], 1):
        link = "[打开](%s)" % a.url if a.url else "—"
        title = a.title.replace("|", "\\|") or "（无标题）"
        lines.append("| %d | %s | %s | %s |" % (i, a.date or "—", title, link))
    lines += ["", "---", "", "*本报告不含文章正文。正文请通过链接在原文阅读。*", ""]
    return "\n".join(lines)


def to_csv(articles, path):
    import csv
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "title", "url", "mid"])
        for a in sorted_articles(articles):
            w.writerow([a.date, a.title, a.url, a.mid])


def to_json(articles, path):
    import json
    from dataclasses import asdict
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(a) for a in sorted_articles(articles)], f,
                  ensure_ascii=False, indent=2)
