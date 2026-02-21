"""
通用决策器基类

提供决策器的基础类定义，具体实现在各角色模块中
"""

from werewolf.core.base_components import BaseDecisionMaker
from werewolf.core.config import BaseConfig

# 导出基类供其他模块使用
__all__ = ['BaseDecisionMaker', 'BaseConfig']
