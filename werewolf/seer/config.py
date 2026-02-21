"""
Seer (预言家) 配置

符合企业级标准的配置类，包含完整的验证和文档
"""

from dataclasses import dataclass
from typing import ClassVar
from werewolf.core.base_good_config import BaseGoodConfig


@dataclass
class SeerConfig(BaseGoodConfig):
    """
    预言家配置类
    
    继承自BaseGoodConfig，提供预言家特定的配置参数
    
    预言家特有配置:
        check_strategy: 验人策略(suspicious/random/strategic)
        reveal_threshold: 跳预言家阈值（第几天）
        trust_check_result: 是否完全信任验人结果
        check_priority_weights: 检查优先级权重配置
        
    继承自BaseGoodConfig的配置:
        - 信任分数调整常量（TRUST_*）
        - 游戏阶段配置（EARLY_GAME_MAX_DAY, MID_GAME_MAX_DAY, ENDGAME_ALIVE_THRESHOLD）
        - ML配置（ML_ENABLED, ML_MODEL_DIR, ML_RETRAIN_INTERVAL, ML_FUSION_RATIO）
        - 发言配置（MAX_SPEECH_LENGTH, MIN_SPEECH_LENGTH）
        - 决策配置（DECISION_MODE, VOTE_STRATEGY）
        - 检测器配置（*_DETECTION_ENABLED）
    """
    
    # 预言家特定配置
    check_strategy: str = "suspicious"  # suspicious: 优先检查可疑玩家, strategic: 战略检查, random: 随机检查
    reveal_threshold: int = 2  # 第几天考虑跳预言家（如果有狼人检查）
    trust_check_result: bool = True  # 是否完全信任验人结果（应该为True）
    
    # 检查优先级权重配置
    check_priority_weights: dict = None  # 将在__post_init__中初始化
    
    def __post_init__(self):
        """初始化后处理"""
        if self.check_priority_weights is None:
            self.check_priority_weights = {
                # 最高优先级威胁
                'malicious_injection': 98,
                'fake_seer': 96,
                'false_quotes': 95,
                
                # 高优先级可疑行为
                'wolf_protecting_votes': 85,
                'contradictions': 75,
                'opposed_dead_good': 70,
                'aggressive_bandwagon': 70,
                
                # 中优先级
                'swing_votes': 60,
                'defensive_behavior': 55,
                
                # 战略加成
                'sheriff_bonus': 10,
                'strong_speaker_bonus': 5,
                'first_night_sheriff_candidate_bonus': 15,
                
                # 信任分数阈值
                'trust_extreme_low': 20,  # <20 → 优先级90+
                'trust_low': 40,  # <40 → 优先级70+
            }
    
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
        
        if self.reveal_threshold > 10:
            raise ValueError(
                f"reveal_threshold must be <= 10, got {self.reveal_threshold}"
            )
        
        # 验证检查优先级权重
        if self.check_priority_weights:
            required_keys = [
                'malicious_injection', 'fake_seer', 'false_quotes',
                'wolf_protecting_votes', 'contradictions'
            ]
            for key in required_keys:
                if key not in self.check_priority_weights:
                    raise ValueError(f"check_priority_weights missing required key: {key}")
                
                value = self.check_priority_weights[key]
                if not isinstance(value, (int, float)):
                    raise ValueError(f"check_priority_weights[{key}] must be numeric, got {type(value)}")
                
                if value < 0 or value > 100:
                    raise ValueError(f"check_priority_weights[{key}] must be between 0 and 100, got {value}")
        
        return True
