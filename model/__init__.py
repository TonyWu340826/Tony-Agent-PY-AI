# model/__init__.py 或 dependencies.py
from fastapi import Depends
from .dashscope_model import DashScopeModel

def get_dashscope_model() -> DashScopeModel:
    return DashScopeModel()