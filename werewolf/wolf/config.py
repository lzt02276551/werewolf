# -*- coding: utf-8 -*-
"""
Wolf (狼人) 配置类

继承BaseWolfConfig并添加Wolf特定配置
"""

from dataclasses import dataclass
from typing import Dict, Any
from werewolf.core.base_wolf_config import BaseWolfConfig


@dataclass
class WolfConfig(BaseWolfConfig):
    """
    狼人代理人配置
    
    继承BaseWolfConfig，所有配置项已在基类中定义
    子类可以覆盖默认值或添加狼人特有配置
    """
    
    # 狼人可以覆盖基类的默认值（如果需要）
    # 例如：MAX_SPEECH_LENGTH = 1600
    
    pass  # 当前使用基类的所有默认配置
