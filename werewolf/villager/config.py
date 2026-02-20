"""
Villager (村民) 配置
"""

from dataclasses import dataclass
from werewolf.core.base_good_config import BaseGoodConfig


@dataclass
class VillagerConfig(BaseGoodConfig):
    """
    村民配置
    
    继承 BaseGoodConfig，添加村民特有配置
    
    Attributes:
        speech_style: 发言风格(analytical/emotional/neutral)
        sheriff_ambition: 竞选警长的积极性(0-10)
    """
    
    # 村民特定配置
    speech_style: str = "analytical"  # analytical, emotional, neutral
    sheriff_ambition: int = 5  # 0-10
    
    # 向后兼容的属性（已在 BaseGoodConfig 中定义，这里保留以兼容旧代码）
    @property
    def vote_strategy(self) -> str:
        return self.VOTE_STRATEGY
    
    @property
    def max_speech_length(self) -> int:
        return self.MAX_SPEECH_LENGTH
    
    @property
    def min_speech_length(self) -> int:
        return self.MIN_SPEECH_LENGTH
    
    @property
    def decision_mode(self) -> str:
        return self.DECISION_MODE
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        # 调用父类验证（BaseGoodConfig 已经验证了大部分配置）
        if not super().validate():
            return False
        
        # 验证村民特有配置
        
        # 验证发言风格
        if self.speech_style not in ["analytical", "emotional", "neutral"]:
            raise ValueError("speech_style must be 'analytical', 'emotional', or 'neutral'")
        
        # 验证警长野心
        if not (0 <= self.sheriff_ambition <= 10):
            raise ValueError("sheriff_ambition must be between 0 and 10")
        
        return True
