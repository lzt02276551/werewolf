"""
Seer (预言家) 配置

符合企业级标准的配置类，包含完整的验证和文档
"""

from dataclasses import dataclass
from typing import ClassVar
from werewolf.core.config import BaseConfig


@dataclass
class SeerConfig(BaseConfig):
    """
    预言家配置类
    
    继承自BaseConfig，提供预言家特定的配置参数
    
    Attributes:
        check_strategy: 验人策略(suspicious/random/strategic)
        reveal_threshold: 跳预言家阈值（第几天）
        trust_check_result: 是否完全信任验人结果
        max_speech_length: 最大发言长度
        min_speech_length: 最小发言长度
        
    信任分数调整常量:
        TRUST_WOLF_CHECK: 检查到狼人的信任分数变化
        TRUST_GOOD_CHECK: 检查到好人的信任分数变化
        TRUST_KILLED_AT_NIGHT: 夜晚被杀的信任分数变化
        TRUST_INJECTION_ATTACK_SYSTEM: 系统伪造注入攻击的信任分数变化
        TRUST_INJECTION_ATTACK_STATUS: 状态伪造注入攻击的信任分数变化
        TRUST_FALSE_QUOTATION: 虚假引用的信任分数变化
        TRUST_LOGICAL_SPEECH: 逻辑发言的信任分数变化
        TRUST_VOTED_OUT: 被投票出局的信任分数变化
        TRUST_ACCURATE_VOTING: 准确投票的信任分数变化
        TRUST_INACCURATE_VOTING: 不准确投票的信任分数变化
        TRUST_ELECTED_SHERIFF: 当选警长的信任分数变化
        
    游戏阶段配置:
        EARLY_GAME_MAX_DAY: 早期游戏最大天数
        MID_GAME_MAX_DAY: 中期游戏最大天数
        ENDGAME_ALIVE_THRESHOLD: 终局存活人数阈值
        
    ML配置:
        ML_INITIAL_CONFIDENCE: ML初始置信度
        MAX_SPEECH_LENGTH: 最大发言长度（用于截断）
    """
    
    # 预言家特定配置
    check_strategy: str = "suspicious"
    reveal_threshold: int = 2
    trust_check_result: bool = True
    
    # 发言配置
    max_speech_length: int = 1400
    min_speech_length: int = 900
    
    # 信任分数调整常量（类变量）
    TRUST_WOLF_CHECK: ClassVar[int] = -100
    TRUST_GOOD_CHECK: ClassVar[int] = 100
    TRUST_KILLED_AT_NIGHT: ClassVar[int] = 25
    TRUST_INJECTION_ATTACK_SYSTEM: ClassVar[int] = -25
    TRUST_INJECTION_ATTACK_STATUS: ClassVar[int] = -15
    TRUST_FALSE_QUOTATION: ClassVar[int] = -15
    TRUST_LOGICAL_SPEECH: ClassVar[int] = 15
    TRUST_VOTED_OUT: ClassVar[int] = -35
    TRUST_ACCURATE_VOTING: ClassVar[int] = 8
    TRUST_INACCURATE_VOTING: ClassVar[int] = -12
    TRUST_ELECTED_SHERIFF: ClassVar[int] = 10
    
    # 游戏阶段配置
    EARLY_GAME_MAX_DAY: ClassVar[int] = 2
    MID_GAME_MAX_DAY: ClassVar[int] = 5
    ENDGAME_ALIVE_THRESHOLD: ClassVar[int] = 5
    
    # ML配置
    ML_INITIAL_CONFIDENCE: ClassVar[float] = 0.40
    MAX_SPEECH_LENGTH: ClassVar[int] = 1400
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        # 调用父类验证
        if not super().validate():
            return False
        
        # 验证检查策略
        valid_strategies = ["suspicious", "random", "strategic"]
        if self.check_strategy not in valid_strategies:
            raise ValueError(
                f"check_strategy must be one of {valid_strategies}, "
                f"got '{self.check_strategy}'"
            )
        
        # 验证揭示阈值
        if self.reveal_threshold < 1:
            raise ValueError(
                f"reveal_threshold must be >= 1, got {self.reveal_threshold}"
            )
        
        # 验证发言长度
        if self.min_speech_length <= 0:
            raise ValueError(
                f"min_speech_length must be positive, got {self.min_speech_length}"
            )
        
        if self.max_speech_length <= self.min_speech_length:
            raise ValueError(
                f"max_speech_length ({self.max_speech_length}) must be greater than "
                f"min_speech_length ({self.min_speech_length})"
            )
        
        return True
