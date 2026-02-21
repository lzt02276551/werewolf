"""
通用检测器基类

提供检测器的基础类定义，具体实现在各角色模块中
"""

from werewolf.core.base_components import BaseDetector
from werewolf.core.config import BaseConfig

# 导出基类供其他模块使用
__all__ = ['BaseDetector', 'BaseConfig']
