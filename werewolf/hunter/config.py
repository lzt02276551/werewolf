"""
Hunter (猎人) 配置

符合企业级标准的配置类，包含完整的参数验证和文档
"""

from dataclasses import dataclass
from typing import Dict, Any
from werewolf.core.config import BaseConfig


@dataclass
class HunterConfig(BaseConfig):
    """
    猎人配置类
    
    继承BaseConfig，添加猎人特定的配置参数
    
    Attributes:
        shoot_threshold: 开枪决策阈值 (0.0-1.0)
        protect_self_priority: 自保优先级 (1-10)
        revenge_mode: 复仇模式 ("aggressive" | "conservative")
        max_speech_length: 最大发言长度
        min_speech_length: 最小发言长度
        early_game_reveal_threshold: 早期游戏暴露身份阈值
        late_game_day_threshold: 晚期游戏天数阈值
        critical_alive_threshold: 危急存活人数阈值
        high_trust_threshold: 高信任度阈值
        low_trust_threshold: 低信任度阈值
        wolf_probability_threshold: 狼人概率阈值
    """
    
    # 猎人特定配置
    shoot_threshold: float = 0.7
    protect_self_priority: int = 5
    revenge_mode: str = "aggressive"  # aggressive, conservative
    
    # 发言长度控制
    MAX_SPEECH_LENGTH: int = 1400
    MIN_SPEECH_LENGTH: int = 900
    OPTIMAL_SPEECH_LENGTH: int = 1300
    
    # 游戏阶段阈值
    early_game_reveal_threshold: int = 3  # Day 1-3不轻易暴露
    late_game_day_threshold: int = 6  # Day 6+为晚期
    critical_alive_threshold: int = 6  # ≤6人为危急阶段
    
    # 信任度阈值
    high_trust_threshold: int = 75
    low_trust_threshold: int = 30
    
    # 决策阈值
    wolf_probability_threshold: float = 0.6
    shoot_confidence_threshold: float = 0.4
    vote_score_threshold: float = 35.0
    
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
        
        # 验证shoot_threshold
        if not (0 <= self.shoot_threshold <= 1):
            raise ValueError("shoot_threshold must be between 0 and 1")
        
        # 验证protect_self_priority
        if not (1 <= self.protect_self_priority <= 10):
            raise ValueError("protect_self_priority must be between 1 and 10")
        
        # 验证revenge_mode
        if self.revenge_mode not in ["aggressive", "conservative"]:
            raise ValueError("revenge_mode must be 'aggressive' or 'conservative'")
        
        # 验证发言长度
        if self.MIN_SPEECH_LENGTH >= self.MAX_SPEECH_LENGTH:
            raise ValueError("MIN_SPEECH_LENGTH must be less than MAX_SPEECH_LENGTH")
        
        if not (self.MIN_SPEECH_LENGTH <= self.OPTIMAL_SPEECH_LENGTH <= self.MAX_SPEECH_LENGTH):
            raise ValueError("OPTIMAL_SPEECH_LENGTH must be between MIN and MAX")
        
        # 验证阈值
        if self.early_game_reveal_threshold < 1:
            raise ValueError("early_game_reveal_threshold must be at least 1")
        
        if self.late_game_day_threshold <= self.early_game_reveal_threshold:
            raise ValueError("late_game_day_threshold must be greater than early_game_reveal_threshold")
        
        if self.critical_alive_threshold < 3:
            raise ValueError("critical_alive_threshold must be at least 3")
        
        # 验证信任度阈值
        if not (0 <= self.low_trust_threshold < self.high_trust_threshold <= 100):
            raise ValueError("Invalid trust thresholds")
        
        # 验证概率阈值
        if not (0 <= self.wolf_probability_threshold <= 1):
            raise ValueError("wolf_probability_threshold must be between 0 and 1")
        
        if not (0 <= self.shoot_confidence_threshold <= 1):
            raise ValueError("shoot_confidence_threshold must be between 0 and 1")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        base_dict = super().to_dict()
        hunter_dict = {
            'shoot_threshold': self.shoot_threshold,
            'protect_self_priority': self.protect_self_priority,
            'revenge_mode': self.revenge_mode,
            'MAX_SPEECH_LENGTH': self.MAX_SPEECH_LENGTH,
            'MIN_SPEECH_LENGTH': self.MIN_SPEECH_LENGTH,
            'OPTIMAL_SPEECH_LENGTH': self.OPTIMAL_SPEECH_LENGTH,
            'early_game_reveal_threshold': self.early_game_reveal_threshold,
            'late_game_day_threshold': self.late_game_day_threshold,
            'critical_alive_threshold': self.critical_alive_threshold,
            'high_trust_threshold': self.high_trust_threshold,
            'low_trust_threshold': self.low_trust_threshold,
            'wolf_probability_threshold': self.wolf_probability_threshold,
            'shoot_confidence_threshold': self.shoot_confidence_threshold,
            'vote_score_threshold': self.vote_score_threshold,
        }
        base_dict.update(hunter_dict)
        return base_dict
