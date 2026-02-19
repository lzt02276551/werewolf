# -*- coding: utf-8 -*-
"""
Wolf King (狼王) 配置类

继承WolfConfig并添加狼王特定配置
"""

from dataclasses import dataclass
from typing import Dict, Any
from werewolf.wolf.config import WolfConfig


@dataclass
class WolfKingConfig(WolfConfig):
    """
    狼王配置
    
    继承狼人配置，添加狼王特定配置
    
    Attributes:
        shoot_on_death: 死亡时是否开枪
        shoot_priority: 开枪目标优先级策略
    """
    
    # 狼王特定配置
    shoot_on_death: bool = True
    shoot_priority: str = "high_threat"  # high_threat, god_role, random
    
    # 开枪策略常量
    SHOOT_PRIORITY_HIGH_THREAT = "high_threat"
    SHOOT_PRIORITY_GOD_ROLE = "god_role"
    SHOOT_PRIORITY_RANDOM = "random"
    
    def validate(self) -> bool:
        """
        验证狼王配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        # 先验证基类配置
        if not super().validate():
            return False
        
        # 验证开枪优先级
        valid_priorities = [
            self.SHOOT_PRIORITY_HIGH_THREAT,
            self.SHOOT_PRIORITY_GOD_ROLE,
            self.SHOOT_PRIORITY_RANDOM
        ]
        if self.shoot_priority not in valid_priorities:
            raise ValueError(
                f"shoot_priority must be one of {valid_priorities}, "
                f"got: {self.shoot_priority}"
            )
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            'shoot_on_death': self.shoot_on_death,
            'shoot_priority': self.shoot_priority,
        })
        return base_dict
