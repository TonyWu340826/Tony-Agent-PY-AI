# config/__init__.py
"""
config 包的入口文件
用于简化导入：from config import config
"""
from .config import config  # 从当前包的 config.py 中导入 config 实例
from .config import settings

__all__ = ["settings"]