"""
通用分析器基类

提供分析器的基础类定义，具体实现在各角色模块中
"""

from werewolf.core.base_components import BaseAnalyzer, BaseTrustManager
from werewolf.core.config import BaseConfig

# 导出基类供其他模块使用
__all__ = ['BaseAnalyzer', 'BaseTrustManager', 'BaseConfig']
