# -*- coding: utf-8 -*-
"""
Wolf (狼人) 配置类

继承BaseConfig并添加Wolf特定配置
"""

from dataclasses import dataclass
from typing import Dict, Any
from werewolf.core.config import BaseConfig


@dataclass
class WolfConfig(BaseConfig):
    """狼人代理人配置"""
    
    # ==================== 发言长度控制 ====================
    MAX_SPEECH_LENGTH = 1500
    MIN_SPEECH_LENGTH = 1000
    
    # ==================== 智商评分阈值 ====================
    INTELLIGENCE_VERY_LOW = 20
    INTELLIGENCE_LOW = 40
    INTELLIGENCE_MEDIUM = 60
    INTELLIGENCE_HIGH = 70
    INTELLIGENCE_VERY_HIGH = 80
    
    # ==================== 威胁等级阈值 ====================
    THREAT_VERY_LOW = 20
    THREAT_LOW = 40
    THREAT_MEDIUM = 60
    THREAT_HIGH = 70
    THREAT_VERY_HIGH = 80
    
    # ==================== 可突破值阈值 ====================
    BREAKTHROUGH_VERY_LOW = 20
    BREAKTHROUGH_LOW = 40
    BREAKTHROUGH_MEDIUM = 60
    BREAKTHROUGH_HIGH = 70
    BREAKTHROUGH_VERY_HIGH = 80
    
    # ==================== 角色威胁评分 ====================
    ROLE_THREAT_SEER = 100
    ROLE_THREAT_LIKELY_SEER = 85
    ROLE_THREAT_WITCH = 85
    ROLE_THREAT_GUARD = 75
    ROLE_THREAT_STRONG_VILLAGER = 70
    ROLE_THREAT_HUNTER = 60
    ROLE_THREAT_WEAK_VILLAGER = 30
    
    # ==================== 击杀策略 ====================
    KILL_STRATEGY_HIGH_THREAT = "high_threat"  # 优先击杀高威胁
    KILL_STRATEGY_EASY_BREAKTHROUGH = "easy_breakthrough"  # 优先突破易突破的
    KILL_STRATEGY_BALANCED = "balanced"  # 平衡策略
    DEFAULT_KILL_STRATEGY = KILL_STRATEGY_BALANCED
    
    def validate(self) -> bool:
        """
        验证Wolf配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        # 先验证基类配置
        if not super().validate():
            return False
        
        # 验证发言长度
        if self.MIN_SPEECH_LENGTH >= self.MAX_SPEECH_LENGTH:
            raise ValueError("MIN_SPEECH_LENGTH must be less than MAX_SPEECH_LENGTH")
        
        # 验证阈值范围
        thresholds = [
            self.INTELLIGENCE_VERY_LOW, self.INTELLIGENCE_LOW,
            self.INTELLIGENCE_MEDIUM, self.INTELLIGENCE_HIGH,
            self.INTELLIGENCE_VERY_HIGH
        ]
        if not all(0 <= t <= 100 for t in thresholds):
            raise ValueError("All intelligence thresholds must be between 0 and 100")
        
        if not all(thresholds[i] < thresholds[i+1] for i in range(len(thresholds)-1)):
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
        
        # 验证击杀策略
        valid_strategies = [
            self.KILL_STRATEGY_HIGH_THREAT,
            self.KILL_STRATEGY_EASY_BREAKTHROUGH,
            self.KILL_STRATEGY_BALANCED
        ]
        if self.DEFAULT_KILL_STRATEGY not in valid_strategies:
            raise ValueError(f"Invalid kill strategy: {self.DEFAULT_KILL_STRATEGY}")
        
        return True
