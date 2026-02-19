"""
Villager (村民) 配置
"""

from dataclasses import dataclass
from werewolf.core.config import BaseConfig


@dataclass
class VillagerConfig(BaseConfig):
    """
    村民配置
    
    Attributes:
        vote_strategy: 投票策略(trust_based/majority/random)
        speech_style: 发言风格(analytical/emotional/neutral)
        sheriff_ambition: 竞选警长的积极性(0-10)
        max_speech_length: 最大发言长度
        min_speech_length: 最小发言长度
        decision_mode: 决策模式(hybrid/code_only/llm_only)
        early_game_max_day: 早期游戏最大天数
        mid_game_max_day: 中期游戏最大天数
        endgame_alive_threshold: 残局存活人数阈值
        vote_urgency_multiplier_endgame: 残局投票紧急度乘数
        vote_urgency_multiplier_midlate: 中后期投票紧急度乘数
        max_trust_history_per_player: 每个玩家最大信任历史记录数
        max_trust_history_players: 最大信任历史玩家数
    """
    
    # 村民特定配置
    vote_strategy: str = "trust_based"  # trust_based, majority, random
    speech_style: str = "analytical"  # analytical, emotional, neutral
    sheriff_ambition: int = 5  # 0-10
    
    # 发言配置
    MAX_SPEECH_LENGTH: int = 1400  # 绝对最大长度
    MIN_SPEECH_LENGTH: int = 900  # 最小长度
    max_speech_length: int = 1400  # 向后兼容
    min_speech_length: int = 900  # 向后兼容
    
    # 决策模式
    DECISION_MODE: str = "hybrid"  # hybrid, code_only, llm_only
    decision_mode: str = "hybrid"  # 向后兼容
    
    # 游戏阶段配置
    EARLY_GAME_MAX_DAY: int = 2  # 早期游戏：第1-2天
    MID_GAME_MAX_DAY: int = 5  # 中期游戏：第3-5天
    ENDGAME_ALIVE_THRESHOLD: int = 6  # 残局：≤6人存活
    
    # 投票紧急度配置
    VOTE_URGENCY_MULTIPLIER_ENDGAME: float = 1.5  # 残局紧急度乘数
    VOTE_URGENCY_MULTIPLIER_MIDLATE: float = 1.2  # 中后期紧急度乘数
    
    # 信任分数历史管理配置
    MAX_TRUST_HISTORY_PER_PLAYER: int = 10  # 每个玩家保留最近10次信任变化
    MAX_TRUST_HISTORY_PLAYERS: int = 50  # 最多跟踪50个玩家的历史
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        if not super().validate():
            return False
        
        # 验证投票策略
        if self.vote_strategy not in ["trust_based", "majority", "random"]:
            raise ValueError("vote_strategy must be 'trust_based', 'majority', or 'random'")
        
        # 验证发言风格
        if self.speech_style not in ["analytical", "emotional", "neutral"]:
            raise ValueError("speech_style must be 'analytical', 'emotional', or 'neutral'")
        
        # 验证警长野心
        if not (0 <= self.sheriff_ambition <= 10):
            raise ValueError("sheriff_ambition must be between 0 and 10")
        
        # 验证决策模式
        decision_mode = self.DECISION_MODE if hasattr(self, 'DECISION_MODE') else self.decision_mode
        if decision_mode not in ["hybrid", "code_only", "llm_only"]:
            raise ValueError("decision_mode must be 'hybrid', 'code_only', or 'llm_only'")
        
        # 验证发言长度
        if self.MIN_SPEECH_LENGTH >= self.MAX_SPEECH_LENGTH:
            raise ValueError("MIN_SPEECH_LENGTH must be less than MAX_SPEECH_LENGTH")
        
        if self.MIN_SPEECH_LENGTH < 50:
            raise ValueError("MIN_SPEECH_LENGTH must be at least 50")
        
        if self.MAX_SPEECH_LENGTH > 2000:
            raise ValueError("MAX_SPEECH_LENGTH must not exceed 2000")
        
        # 验证游戏阶段配置
        if self.EARLY_GAME_MAX_DAY < 1:
            raise ValueError("EARLY_GAME_MAX_DAY must be at least 1")
        
        if self.MID_GAME_MAX_DAY <= self.EARLY_GAME_MAX_DAY:
            raise ValueError("MID_GAME_MAX_DAY must be greater than EARLY_GAME_MAX_DAY")
        
        if self.ENDGAME_ALIVE_THRESHOLD < 3:
            raise ValueError("ENDGAME_ALIVE_THRESHOLD must be at least 3")
        
        # 验证紧急度乘数
        if self.VOTE_URGENCY_MULTIPLIER_ENDGAME < 1.0:
            raise ValueError("VOTE_URGENCY_MULTIPLIER_ENDGAME must be at least 1.0")
        
        if self.VOTE_URGENCY_MULTIPLIER_MIDLATE < 1.0:
            raise ValueError("VOTE_URGENCY_MULTIPLIER_MIDLATE must be at least 1.0")
        
        # 验证历史管理配置
        if self.MAX_TRUST_HISTORY_PER_PLAYER < 5:
            raise ValueError("MAX_TRUST_HISTORY_PER_PLAYER must be at least 5")
        
        if self.MAX_TRUST_HISTORY_PLAYERS < 10:
            raise ValueError("MAX_TRUST_HISTORY_PLAYERS must be at least 10")
        
        return True
