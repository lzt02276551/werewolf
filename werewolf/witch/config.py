# -*- coding: utf-8 -*-
"""
女巫代理人配置类

提供女巫角色的所有配置参数
"""

from dataclasses import dataclass
from werewolf.core.base_good_config import BaseGoodConfig


@dataclass
class WitchConfig(BaseGoodConfig):
    """
    女巫代理人配置（继承BaseGoodConfig）
    
    继承所有共享配置，只定义女巫特有配置：
    - 解药使用策略
    - 毒药使用策略
    - 角色价值评分
    """
    
    # ==================== 解药使用阈值 ====================
    ANTIDOTE_SCORE_THRESHOLD: int = 50  # 解药使用最低分数
    ANTIDOTE_FIRST_NIGHT_ALWAYS: bool = True  # 首夜必救
    
    # ==================== 毒药使用阈值 ====================
    POISON_SCORE_THRESHOLD: int = 70  # 毒药使用最低分数
    
    # ==================== 角色价值评分 ====================
    ROLE_VALUE_SEER: int = 100
    ROLE_VALUE_GUARD: int = 85
    ROLE_VALUE_STRONG_VILLAGER: int = 70
    ROLE_VALUE_HUNTER: int = 55
    ROLE_VALUE_VILLAGER: int = 40
    ROLE_VALUE_WOLF: int = 0
    
    # ==================== 威胁等级评分 ====================
    THREAT_SHERIFF: int = 20
    THREAT_HIGH_SPEECH: int = 15
    THREAT_LEADS_DISCUSSION: int = 10
    THREAT_LOGICAL: int = 10
    
    # ==================== 首夜策略 ====================
    FIRST_NIGHT_STRATEGY_ALWAYS_SAVE: str = "always_save"
    FIRST_NIGHT_STRATEGY_OBSERVE: str = "observe_first"
    DEFAULT_FIRST_NIGHT_STRATEGY: str = "always_save"
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
        """
        if not super().validate():
            return False
        
        # 验证女巫特定配置
        if self.ANTIDOTE_SCORE_THRESHOLD < 0 or self.ANTIDOTE_SCORE_THRESHOLD > 100:
            raise ValueError("ANTIDOTE_SCORE_THRESHOLD must be between 0 and 100")
        
        if self.POISON_SCORE_THRESHOLD < 0 or self.POISON_SCORE_THRESHOLD > 100:
            raise ValueError("POISON_SCORE_THRESHOLD must be between 0 and 100")
        
        return True
