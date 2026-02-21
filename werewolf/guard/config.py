"""
守卫代理人配置类（重构版 - 继承BaseGoodConfig）

继承BaseGoodConfig获得所有共享配置，只定义守卫特有配置
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from werewolf.core.base_good_config import BaseGoodConfig


@dataclass
class GuardConfig(BaseGoodConfig):
    """
    守卫代理人配置（重构版 - 继承BaseGoodConfig）
    
    继承所有共享配置，只定义守卫特有配置：
    - 守护优先级
    - 击杀预测概率
    - 守护策略
    """
    
    # ==================== 守卫优先级分数 ====================
    GUARD_PRIORITY_CONFIRMED_SEER: int = 90
    GUARD_PRIORITY_LIKELY_SEER: int = 70
    GUARD_PRIORITY_SHERIFF: int = 65
    GUARD_PRIORITY_WITCH: int = 60
    GUARD_PRIORITY_HIGH_TRUST: int = 55
    GUARD_PRIORITY_HUNTER_MAX: int = 30
    GUARD_PRIORITY_WOLF_TARGET_BONUS: int = 25
    
    # ==================== 狼人击杀预测 ====================
    KILL_PROB_CONFIRMED_SEER: float = 0.80
    KILL_PROB_LIKELY_SEER: float = 0.60
    KILL_PROB_SHERIFF_HIGH_TRUST: float = 0.50
    KILL_PROB_SHERIFF_LOW_TRUST: float = 0.30
    KILL_PROB_WITCH: float = 0.45
    KILL_PROB_STRONG_VILLAGER: float = 0.40
    KILL_PROB_HUNTER: float = 0.10
    
    # ==================== 投票决策配置 ====================
    VOTE_BONUS_PROTECTING_WOLVES: int = 30
    VOTE_BONUS_CHARGING: int = 20
    VOTE_BONUS_SWAYING: int = 15
    VOTE_PENALTY_ACCURATE: int = -25
    VOTE_BONUS_SYSTEM_FAKE: int = 40
    VOTE_BONUS_STATUS_FAKE: int = 30
    VOTE_PENALTY_BENIGN: int = -15
    VOTE_BONUS_FALSE_QUOTATION: int = 25
    VOTE_BONUS_STATUS_CONTRADICTION: int = 35
    
    # 信任分数阈值
    TRUST_VERY_LOW: int = 20
    TRUST_LOW: int = 40
    
    # 狼人概率阈值
    WOLF_PROB_VERY_HIGH: float = 0.85
    WOLF_PROB_HIGH: float = 0.70
    
    # 投票分析配置
    VOTING_MIN_SAMPLES: int = 3
    VOTING_ACCURACY_HIGH: float = 0.67
    VOTING_ACCURACY_LOW: float = 0.33
    
    # 角色特定配置
    role_specific: Dict[str, Any] = field(default_factory=lambda: {
        "first_night_strategy": "empty_guard",
        "protect_same_twice": False,
        "priority_神职": True,
        "avoid_hunter": True
    })
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
        """
        # 调用父类验证
        if not super().validate():
            return False
        
        # 守卫特定验证
        if not (0 <= self.GUARD_PRIORITY_HUNTER_MAX <= 100):
            from agent_build_sdk.utils.logger import logger
            logger.error(f"GUARD_PRIORITY_HUNTER_MAX must be 0-100, got {self.GUARD_PRIORITY_HUNTER_MAX}")
            return False
        
        # 验证概率范围
        prob_fields = [
            ('KILL_PROB_CONFIRMED_SEER', self.KILL_PROB_CONFIRMED_SEER),
            ('KILL_PROB_HUNTER', self.KILL_PROB_HUNTER),
            ('KILL_PROB_LIKELY_SEER', self.KILL_PROB_LIKELY_SEER),
            ('KILL_PROB_SHERIFF_HIGH_TRUST', self.KILL_PROB_SHERIFF_HIGH_TRUST),
            ('KILL_PROB_SHERIFF_LOW_TRUST', self.KILL_PROB_SHERIFF_LOW_TRUST),
            ('KILL_PROB_WITCH', self.KILL_PROB_WITCH),
            ('KILL_PROB_STRONG_VILLAGER', self.KILL_PROB_STRONG_VILLAGER)
        ]
        
        from agent_build_sdk.utils.logger import logger
        for field_name, field_value in prob_fields:
            if not (0 <= field_value <= 1):
                logger.error(f"{field_name} must be 0-1, got {field_value}")
                return False
        
        # 验证守卫优先级的逻辑顺序
        if not (self.GUARD_PRIORITY_CONFIRMED_SEER > self.GUARD_PRIORITY_LIKELY_SEER):
            logger.error("GUARD_PRIORITY_CONFIRMED_SEER must be > GUARD_PRIORITY_LIKELY_SEER")
            return False
        
        if not (self.GUARD_PRIORITY_LIKELY_SEER > self.GUARD_PRIORITY_SHERIFF):
            logger.error("GUARD_PRIORITY_LIKELY_SEER must be > GUARD_PRIORITY_SHERIFF")
            return False
        
        # 验证击杀概率的逻辑顺序
        if not (self.KILL_PROB_CONFIRMED_SEER > self.KILL_PROB_LIKELY_SEER):
            logger.error("KILL_PROB_CONFIRMED_SEER must be > KILL_PROB_LIKELY_SEER")
            return False
        
        if not (self.KILL_PROB_HUNTER < self.KILL_PROB_STRONG_VILLAGER):
            logger.error("KILL_PROB_HUNTER should be < KILL_PROB_STRONG_VILLAGER (hunters are bait)")
            return False
        
        # 验证角色特定配置
        if not isinstance(self.role_specific, dict):
            logger.error("role_specific must be a dictionary")
            return False
        
        required_keys = ['first_night_strategy', 'protect_same_twice']
        for key in required_keys:
            if key not in self.role_specific:
                logger.error(f"role_specific missing required key: {key}")
                return False
        
        # 验证首夜策略
        if self.role_specific['first_night_strategy'] not in ['empty_guard', 'random', 'high_trust']:
            logger.error(f"Invalid first_night_strategy: {self.role_specific['first_night_strategy']}")
            return False
        
        logger.info("✓ GuardConfig validation passed")
        return True
    
    def get_guard_priority(self, role_type: str) -> int:
        """
        获取角色守卫优先级
        
        Args:
            role_type: 角色类型
            
        Returns:
            优先级分数
        """
        priority_map = {
            "confirmed_seer": self.GUARD_PRIORITY_CONFIRMED_SEER,
            "likely_seer": self.GUARD_PRIORITY_LIKELY_SEER,
            "sheriff": self.GUARD_PRIORITY_SHERIFF,
            "witch": self.GUARD_PRIORITY_WITCH,
            "high_trust": self.GUARD_PRIORITY_HIGH_TRUST,
            "hunter": self.GUARD_PRIORITY_HUNTER_MAX
        }
        return priority_map.get(role_type, 50)
