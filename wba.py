"""零安装启动器：把 src 加进搜索路径后调用 CLI。

clone 下来直接 `python wba.py` 即可，不需要 pip install。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from wechat_biz_archive.cli import main  # noqa: E402

raise SystemExit(main())
