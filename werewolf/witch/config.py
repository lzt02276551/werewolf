# -*- coding: utf-8 -*-
"""
女巫代理人配置类

提供女巫角色的所有配置参数
"""

from dataclasses import dataclass
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_good_config import BaseGoodConfig


@dataclass
class WitchConfig(BaseGoodConfig):
    """
    女巫代理人配置（继承BaseGoodConfig）- 企业级五星标准
    
    女巫规则：
    - 解药只能用一次，可以救任何被狼人杀死的玩家（包括自己）
    - 毒药只能用一次，可以毒死任何玩家
    - 策略：有人倒下基本都救，但要避免明显的自刀
    """
    
    # ==================== 解药使用阈值 ====================
    ANTIDOTE_SCORE_THRESHOLD: int = 45  # 解药使用最低分数（降低阈值，倾向于救人）
    ANTIDOTE_FIRST_NIGHT_MIN_TRUST: int = 15  # 首夜最低信任阈值（配置化）
    
    # ==================== 毒药使用阈值 ====================
    POISON_SCORE_THRESHOLD: int = 70  # 毒药使用最低分数
    POISON_ENDGAME_THRESHOLD: int = 80  # 残局毒药使用阈值（更谨慎）
    
    # ==================== 信任分数阈值（继承父类）====================
    # TRUST_VERY_LOW: int = 20  # 极低信任（继承）
    # TRUST_LOW: int = 35  # 低信任（继承）
    
    def __post_init__(self):
        """初始化后处理，确保继承的属性可用"""
        super().__post_init__() if hasattr(super(), '__post_init__') else None
        
        # 确保信任阈值存在（从父类继承）
        if not hasattr(self, 'TRUST_VERY_LOW'):
            self.TRUST_VERY_LOW = 20
        if not hasattr(self, 'TRUST_LOW'):
            self.TRUST_LOW = 35
    
    def validate(self) -> bool:
        """
        验证配置有效性（企业级五星标准）
        
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
        
        if self.POISON_ENDGAME_THRESHOLD < self.POISON_SCORE_THRESHOLD:
            raise ValueError("POISON_ENDGAME_THRESHOLD must be >= POISON_SCORE_THRESHOLD")
        
        # 验证首夜信任阈值
        if self.ANTIDOTE_FIRST_NIGHT_MIN_TRUST < 0 or self.ANTIDOTE_FIRST_NIGHT_MIN_TRUST > 50:
            raise ValueError("ANTIDOTE_FIRST_NIGHT_MIN_TRUST must be between 0 and 50")
        
        # 验证首夜信任阈值与TRUST_VERY_LOW的关系
        if self.ANTIDOTE_FIRST_NIGHT_MIN_TRUST < self.TRUST_VERY_LOW:
            logger.warning(
                f"ANTIDOTE_FIRST_NIGHT_MIN_TRUST ({self.ANTIDOTE_FIRST_NIGHT_MIN_TRUST}) "
                f"< TRUST_VERY_LOW ({self.TRUST_VERY_LOW}), may save self-knife"
            )
        
        return True
