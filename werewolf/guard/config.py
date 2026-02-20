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
            return False
        
        # 验证概率范围
        prob_fields = [
            self.KILL_PROB_CONFIRMED_SEER, self.KILL_PROB_HUNTER,
            self.KILL_PROB_LIKELY_SEER, self.KILL_PROB_SHERIFF_HIGH_TRUST,
            self.KILL_PROB_SHERIFF_LOW_TRUST, self.KILL_PROB_WITCH,
            self.KILL_PROB_STRONG_VILLAGER
        ]
        if not all(0 <= p <= 1 for p in prob_fields):
            return False
        
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
