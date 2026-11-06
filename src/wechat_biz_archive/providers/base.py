"""Provider 接口定义。"""
from abc import ABC, abstractmethod

REGISTRY = {}


class Provider(ABC):
    name = "base"
    description = ""
    requires_credentials = False

    @abstractmethod
    def fetch(self, **kwargs):
        """返回 list[Article]。失败时应返回空列表或抛出可读异常，不要静默吞掉。"""
        raise NotImplementedError


def register(cls):
    REGISTRY[cls.name] = cls
    return cls


def available_providers():
    return {name: cls.description for name, cls in REGISTRY.items()}


def get_provider(name):
    if name not in REGISTRY:
        raise ValueError(
            "未知输入源 %r，可用：%s" % (name, ", ".join(sorted(REGISTRY)))
        )
    return REGISTRY[name]()
