"""统计与阶段划分。"""
import collections
import datetime

from .models import Article


def dedupe(articles):
    seen, out = set(), []
    for a in articles:
        k = a.key()
        if k and k not in seen:
            seen.add(k)
            out.append(a)
    return out


def sorted_articles(articles):
    return sorted(articles, key=lambda a: (a.date or "0000", a.mid or ""))


def monthly_counts(articles):
    c = collections.Counter(a.month for a in articles if a.month)
    return dict(sorted(c.items()))


def _month_index(s):
    y, m = s.split("-")
    return int(y) * 12 + int(m)


def detect_phases(articles, gap_months=2, surge_factor=2.5,
                  surge_min=8, window=6, cooldown=6, min_segment=3):
    """切出活跃阶段。

    两段依据：
    1. 空档：相邻有文章的月份间隔 >= gap_months，视为断更，切开。
    2. 跃升：某月篇数显著高于此前 window 个月的均值，视为改版/转型，切开。

    只看空档会把「低频期 → 日更期」并成一段，所以第二条很关键。
    """
    counts = monthly_counts(articles)
    months = sorted(counts)
    if not months:
        return []

    groups, cur = [], [months[0]]
    for prev, now in zip(months, months[1:]):
        if _month_index(now) - _month_index(prev) >= gap_months:
            groups.append(cur)
            cur = [now]
        else:
            cur.append(now)
    groups.append(cur)

    segments = []
    for g in groups:
        start, last_cut = 0, -999
        for i in range(1, len(g)):
            # 冷却期与最短段长：避免日更期里每月都被判成一次新阶段
            if i - last_cut < cooldown or i - start < min_segment:
                continue
            prev = [counts[m] for m in g[max(0, i - window):i]]
            base = sum(prev) / len(prev) if prev else 0
            now = counts[g[i]]
            if base > 0 and now >= surge_factor * base and now >= surge_min:
                segments.append(g[start:i])
                start, last_cut = i, i
        segments.append(g[start:])

    out = []
    for g in segments:
        n = sum(counts[m] for m in g)
        out.append({
            "start": g[0], "end": g[-1], "months": len(g), "count": n,
            "per_month": round(n / max(len(g), 1), 1),
        })
    return out


def overview(articles):
    items = sorted_articles(articles)
    dated = [a for a in items if a.date]
    return {
        "total": len(items),
        "with_date": len(dated),
        "with_url": sum(1 for a in items if a.url),
        "earliest": dated[0].date if dated else "",
        "latest": dated[-1].date if dated else "",
        "months": len(monthly_counts(items)),
    }
