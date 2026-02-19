# -*- coding: utf-8 -*-
"""
女巫代理人配置类

提供女巫角色的所有配置参数
"""

from dataclasses import dataclass
from werewolf.core.config import BaseConfig


@dataclass
class WitchConfig(BaseConfig):
    """女巫代理人配置"""
    
    # ==================== 发言长度控制 ====================
    MAX_SPEECH_LENGTH = 1500
    MIN_SPEECH_LENGTH = 1000
    
    # ==================== 信任分数阈值 ====================
    TRUST_VERY_LOW = 20
    TRUST_LOW = 40
    TRUST_MEDIUM = 60
    TRUST_HIGH = 70
    TRUST_VERY_HIGH = 80
    
    # ==================== 狼人概率阈值 ====================
    WOLF_PROB_VERY_HIGH = 0.90
    WOLF_PROB_HIGH = 0.75
    WOLF_PROB_MEDIUM = 0.60
    
    # ==================== 解药使用阈值 ====================
    ANTIDOTE_SCORE_THRESHOLD = 50  # 解药使用最低分数
    ANTIDOTE_FIRST_NIGHT_ALWAYS = True  # 首夜必救
    
    # ==================== 毒药使用阈值 ====================
    POISON_SCORE_THRESHOLD = 70  # 毒药使用最低分数
    
    # ==================== 角色价值评分 ====================
    ROLE_VALUE_SEER = 100
    ROLE_VALUE_GUARD = 85
    ROLE_VALUE_STRONG_VILLAGER = 70
    ROLE_VALUE_HUNTER = 55
    ROLE_VALUE_VILLAGER = 40
    ROLE_VALUE_WOLF = 0
    
    # ==================== 威胁等级评分 ====================
    THREAT_SHERIFF = 20
    THREAT_HIGH_SPEECH = 15
    THREAT_LEADS_DISCUSSION = 10
    THREAT_LOGICAL = 10
    
    # ==================== 首夜策略 ====================
    FIRST_NIGHT_STRATEGY_ALWAYS_SAVE = "always_save"
    FIRST_NIGHT_STRATEGY_OBSERVE = "observe_first"
    DEFAULT_FIRST_NIGHT_STRATEGY = FIRST_NIGHT_STRATEGY_ALWAYS_SAVE
    
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
