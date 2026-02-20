# -*- coding: utf-8 -*-
"""
BaseWolfConfig - 狼人阵营基类配置

提供所有狼人角色的共享配置
"""

from dataclasses import dataclass
from typing import Dict, Any
from werewolf.core.config import BaseConfig


@dataclass
class BaseWolfConfig(BaseConfig):
    """
    狼人阵营基类配置
    
    提供所有狼人角色的共享配置项
    
    Attributes:
        # 发言长度控制
        MAX_SPEECH_LENGTH: 最大发言长度
        MIN_SPEECH_LENGTH: 最小发言长度
        
        # 队友智商评分阈值
        INTELLIGENCE_VERY_LOW: 极低智商阈值
        INTELLIGENCE_LOW: 低智商阈值
        INTELLIGENCE_MEDIUM: 中等智商阈值
        INTELLIGENCE_HIGH: 高智商阈值
        INTELLIGENCE_VERY_HIGH: 极高智商阈值
        
        # 威胁等级阈值
        THREAT_VERY_LOW: 极低威胁阈值
        THREAT_LOW: 低威胁阈值
        THREAT_MEDIUM: 中等威胁阈值
        THREAT_HIGH: 高威胁阈值
        THREAT_VERY_HIGH: 极高威胁阈值
        
        # 可突破值阈值
        BREAKTHROUGH_VERY_LOW: 极难突破阈值
        BREAKTHROUGH_LOW: 难突破阈值
        BREAKTHROUGH_MEDIUM: 中等可突破阈值
        BREAKTHROUGH_HIGH: 易突破阈值
        BREAKTHROUGH_VERY_HIGH: 极易突破阈值
        
        # 角色威胁评分
        ROLE_THREAT_SEER: 预言家威胁值
        ROLE_THREAT_WITCH: 女巫威胁值
        ROLE_THREAT_GUARD: 守卫威胁值
        ROLE_THREAT_HUNTER: 猎人威胁值
        ROLE_THREAT_STRONG_VILLAGER: 强势平民威胁值
        ROLE_THREAT_WEAK_VILLAGER: 弱势平民威胁值
        
        # 卖队友策略
        BETRAY_TEAMMATE_THRESHOLD: 卖队友智商阈值（低于此值考虑卖）
        BETRAY_GAIN_TRUST_BONUS: 卖队友获得的信任加成
    """
    
    # ==================== 发言长度控制 ====================
    MAX_SPEECH_LENGTH: int = 1500
    MIN_SPEECH_LENGTH: int = 1000
    OPTIMAL_SPEECH_LENGTH: int = 1300
    
    # ==================== 队友智商评分阈值 ====================
    INTELLIGENCE_VERY_LOW: int = 20
    INTELLIGENCE_LOW: int = 40
    INTELLIGENCE_MEDIUM: int = 60
    INTELLIGENCE_HIGH: int = 70
    INTELLIGENCE_VERY_HIGH: int = 80
    
    # ==================== 威胁等级阈值 ====================
    THREAT_VERY_LOW: int = 20
    THREAT_LOW: int = 40
    THREAT_MEDIUM: int = 60
    THREAT_HIGH: int = 70
    THREAT_VERY_HIGH: int = 80
    
    # ==================== 可突破值阈值 ====================
    BREAKTHROUGH_VERY_LOW: int = 20
    BREAKTHROUGH_LOW: int = 40
    BREAKTHROUGH_MEDIUM: int = 60
    BREAKTHROUGH_HIGH: int = 70
    BREAKTHROUGH_VERY_HIGH: int = 80
    
    # ==================== 角色威胁评分 ====================
    ROLE_THREAT_SEER: int = 100
    ROLE_THREAT_LIKELY_SEER: int = 85
    ROLE_THREAT_WITCH: int = 85
    ROLE_THREAT_GUARD: int = 75
    ROLE_THREAT_STRONG_VILLAGER: int = 70
    ROLE_THREAT_HUNTER: int = 60
    ROLE_THREAT_WEAK_VILLAGER: int = 30
    
    # ==================== 卖队友策略 ====================
    BETRAY_TEAMMATE_THRESHOLD: int = 30  # 队友智商低于30考虑卖
    BETRAY_GAIN_TRUST_BONUS: int = 20    # 卖队友获得20点信任加成
    BETRAY_ENABLED: bool = True          # 是否启用卖队友策略
    
    # ==================== 击杀策略 ====================
    KILL_STRATEGY_HIGH_THREAT: str = "high_threat"
    KILL_STRATEGY_EASY_BREAKTHROUGH: str = "easy_breakthrough"
    KILL_STRATEGY_BALANCED: str = "balanced"
    DEFAULT_KILL_STRATEGY: str = KILL_STRATEGY_BALANCED
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置参数无效时抛出
        """
        # 调用父类验证
        if not super().validate():
            return False
        
        # 验证发言长度
        if self.MIN_SPEECH_LENGTH >= self.MAX_SPEECH_LENGTH:
            raise ValueError("MIN_SPEECH_LENGTH must be less than MAX_SPEECH_LENGTH")
        
        if not (self.MIN_SPEECH_LENGTH <= self.OPTIMAL_SPEECH_LENGTH <= self.MAX_SPEECH_LENGTH):
            raise ValueError("OPTIMAL_SPEECH_LENGTH must be between MIN and MAX")
        
        # 验证智商阈值
        intelligence_thresholds = [
            self.INTELLIGENCE_VERY_LOW, self.INTELLIGENCE_LOW,
            self.INTELLIGENCE_MEDIUM, self.INTELLIGENCE_HIGH,
            self.INTELLIGENCE_VERY_HIGH
        ]
        if not all(0 <= t <= 100 for t in intelligence_thresholds):
            raise ValueError("All intelligence thresholds must be between 0 and 100")
        
        if not all(intelligence_thresholds[i] < intelligence_thresholds[i+1] 
                  for i in range(len(intelligence_thresholds)-1)):
            raise ValueError("Intelligence thresholds must be in ascending order")
        
        # 验证威胁等级阈值
        threat_thresholds = [
            self.THREAT_VERY_LOW, self.THREAT_LOW,
            self.THREAT_MEDIUM, self.THREAT_HIGH,
            self.THREAT_VERY_HIGH
        ]
        if not all(0 <= t <= 100 for t in threat_thresholds):
            raise ValueError("All threat thresholds must be between 0 and 100")
        
        # 验证角色威胁评分
        role_threats = [
            self.ROLE_THREAT_SEER, self.ROLE_THREAT_LIKELY_SEER,
            self.ROLE_THREAT_WITCH, self.ROLE_THREAT_GUARD,
            self.ROLE_THREAT_STRONG_VILLAGER, self.ROLE_THREAT_HUNTER,
            self.ROLE_THREAT_WEAK_VILLAGER
        ]
        if not all(0 <= t <= 100 for t in role_threats):
            raise ValueError("All role threat scores must be between 0 and 100")
        
        # 验证卖队友阈值
        if not (0 <= self.BETRAY_TEAMMATE_THRESHOLD <= 100):
            raise ValueError("BETRAY_TEAMMATE_THRESHOLD must be between 0 and 100")
        
        if not (0 <= self.BETRAY_GAIN_TRUST_BONUS <= 100):
            raise ValueError("BETRAY_GAIN_TRUST_BONUS must be between 0 and 100")
        
        # 验证击杀策略
        valid_strategies = [
            self.KILL_STRATEGY_HIGH_THREAT,
            self.KILL_STRATEGY_EASY_BREAKTHROUGH,
            self.KILL_STRATEGY_BALANCED
        ]
        if self.DEFAULT_KILL_STRATEGY not in valid_strategies:
            raise ValueError(f"Invalid kill strategy: {self.DEFAULT_KILL_STRATEGY}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        base_dict = super().to_dict()
        wolf_dict = {
            'MAX_SPEECH_LENGTH': self.MAX_SPEECH_LENGTH,
            'MIN_SPEECH_LENGTH': self.MIN_SPEECH_LENGTH,
            'OPTIMAL_SPEECH_LENGTH': self.OPTIMAL_SPEECH_LENGTH,
            'INTELLIGENCE_VERY_LOW': self.INTELLIGENCE_VERY_LOW,
            'INTELLIGENCE_LOW': self.INTELLIGENCE_LOW,
            'INTELLIGENCE_MEDIUM': self.INTELLIGENCE_MEDIUM,
            'INTELLIGENCE_HIGH': self.INTELLIGENCE_HIGH,
            'INTELLIGENCE_VERY_HIGH': self.INTELLIGENCE_VERY_HIGH,
            'THREAT_VERY_LOW': self.THREAT_VERY_LOW,
            'THREAT_LOW': self.THREAT_LOW,
            'THREAT_MEDIUM': self.THREAT_MEDIUM,
            'THREAT_HIGH': self.THREAT_HIGH,
            'THREAT_VERY_HIGH': self.THREAT_VERY_HIGH,
            'BREAKTHROUGH_VERY_LOW': self.BREAKTHROUGH_VERY_LOW,
            'BREAKTHROUGH_LOW': self.BREAKTHROUGH_LOW,
            'BREAKTHROUGH_MEDIUM': self.BREAKTHROUGH_MEDIUM,
            'BREAKTHROUGH_HIGH': self.BREAKTHROUGH_HIGH,
            'BREAKTHROUGH_VERY_HIGH': self.BREAKTHROUGH_VERY_HIGH,
            'ROLE_THREAT_SEER': self.ROLE_THREAT_SEER,
            'ROLE_THREAT_WITCH': self.ROLE_THREAT_WITCH,
            'ROLE_THREAT_GUARD': self.ROLE_THREAT_GUARD,
            'ROLE_THREAT_HUNTER': self.ROLE_THREAT_HUNTER,
            'ROLE_THREAT_STRONG_VILLAGER': self.ROLE_THREAT_STRONG_VILLAGER,
            'ROLE_THREAT_WEAK_VILLAGER': self.ROLE_THREAT_WEAK_VILLAGER,
            'BETRAY_TEAMMATE_THRESHOLD': self.BETRAY_TEAMMATE_THRESHOLD,
            'BETRAY_GAIN_TRUST_BONUS': self.BETRAY_GAIN_TRUST_BONUS,
            'BETRAY_ENABLED': self.BETRAY_ENABLED,
            'DEFAULT_KILL_STRATEGY': self.DEFAULT_KILL_STRATEGY,
        }
        base_dict.update(wolf_dict)
        return base_dict
