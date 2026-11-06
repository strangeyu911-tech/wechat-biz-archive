"""可插拔输入源。

每个 provider 只负责「把某个来源变成 list[Article]」，彼此独立。
新增输入源：写一个继承 Provider 的类并加 @register 即可，无需改 CLI。
"""
from .base import Provider, get_provider, available_providers
from . import csv_provider, chatlog, sogou, session  # noqa: F401

__all__ = ["Provider", "get_provider", "available_providers"]
