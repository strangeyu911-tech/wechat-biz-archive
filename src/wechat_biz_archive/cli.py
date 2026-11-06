"""命令行入口。

零配置体验：不带任何参数直接运行，会用仓库附带的示例数据生成一份报告。
"""
import argparse
import os
import sys

from .analyze import dedupe, overview
from .providers import available_providers, get_provider
from .report import render, to_csv, to_json

DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "examples", "demo_articles.csv",
)


def build_parser():
    p = argparse.ArgumentParser(
        prog="wechat-biz-archive",
        description="公众号内容归档与分析：从任意输入源得到时间线、阶段划分和报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python wba.py                          # 零配置，用示例数据出报告\n"
            "  python wba.py --input my.csv --out report.md\n"
            "  python wba.py --provider chatlog --input ./export\n"
            "  python wba.py --provider sogou --query '王赞 读研' --account 王赞\n"
            "  python wba.py --full --biz <__biz> --credentials creds.json\n"
        ),
    )
    p.add_argument("--input", help="输入文件或目录（csv / chatlog）")
    p.add_argument("--provider", default="csv", help="输入源，默认 csv")
    p.add_argument("--out", default="report.md", help="输出路径，默认 report.md")
    p.add_argument("--format", choices=["md", "csv", "json"], default="md")
    p.add_argument("--query", default="", help="sogou 模式的检索词")
    p.add_argument("--account", default="", help="sogou 模式的公众号名过滤")
    p.add_argument("--full", action="store_true", help="完整历史模式（需自备会话凭证）")
    p.add_argument("--biz", default="", help="完整历史模式的公众号 __biz")
    p.add_argument("--credentials", help="会话凭证 JSON 文件（切勿提交到仓库）")
    p.add_argument("--list-providers", action="store_true", help="列出可用输入源")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.list_providers:
        for name, desc in sorted(available_providers().items()):
            print("%-10s %s" % (name, desc))
        return 0

    provider_name = "session" if args.full else args.provider
    input_path = args.input
    source = provider_name
    using_demo = False

    if provider_name == "csv" and not input_path:
        input_path = DEMO
        using_demo = True
        source = "内置示例数据（examples/demo_articles.csv）"

    kwargs = {
        "path": input_path,
        "query": args.query,
        "account": args.account,
        "biz": args.biz,
        "credentials": args.credentials,
        "on_page": (lambda page, total: print("  已翻 %d 页 / %d 篇" % (page, total), flush=True)),
    }

    try:
        provider = get_provider(provider_name)
        articles = dedupe(provider.fetch(**kwargs))
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print("输入源失败：%s" % e, file=sys.stderr)
        if using_demo:
            raise
        return 2

    if not articles:
        print("输入源没有返回任何文章。", file=sys.stderr)
        if provider_name == "sogou":
            print("搜狗可能触发了反爬；可改用 --input 导入 URL 清单，或 --full 完整历史模式。",
                  file=sys.stderr)
        return 3

    if args.format == "md":
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(render(articles, source=source))
    elif args.format == "csv":
        to_csv(articles, args.out)
    else:
        to_json(articles, args.out)

    ov = overview(articles)
    print("输入源：%s" % source)
    print("文章 %d 篇 · %s ~ %s · 覆盖 %d 个月" %
          (ov["total"], ov["earliest"] or "?", ov["latest"] or "?", ov["months"]))
    print("报告已写入：%s" % os.path.abspath(args.out))
    return 0
