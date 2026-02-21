"""
BaseGoodConfig - 好人阵营基类配置

定义所有好人角色的共享配置项
"""

from dataclasses import dataclass
from werewolf.core.config import BaseConfig


@dataclass
class BaseGoodConfig(BaseConfig):
    """
    好人阵营基类配置
    
    包含所有好人角色的共享配置项：
    - 检测器配置
    - 信任分数配置
    - ML配置
    - 发言配置
    - 决策配置
    
    子类可以继承并添加角色特有配置
    """
    
    # ==================== 检测器配置 ====================
    INJECTION_DETECTION_ENABLED: bool = True
    FALSE_QUOTE_DETECTION_ENABLED: bool = True
    MESSAGE_PARSING_ENABLED: bool = True
    SPEECH_QUALITY_EVALUATION_ENABLED: bool = True
    
    # ==================== 信任分数配置 ====================
    # 预言家验证
    TRUST_WOLF_CHECK: int = -50  # 被验为狼人
    TRUST_GOOD_CHECK: int = 50   # 被验为好人
    
    # 恶意行为
    TRUST_INJECTION_ATTACK: int = -30  # 注入攻击（通用）
    TRUST_INJECTION_ATTACK_SYSTEM: int = -40  # 系统伪造注入
    TRUST_INJECTION_ATTACK_STATUS: int = -35  # 状态伪造注入
    TRUST_FALSE_QUOTATION: int = -20   # 虚假引用
    
    # 良好行为
    TRUST_LOGICAL_SPEECH: int = 10     # 逻辑发言
    TRUST_ACCURATE_VOTING: int = 15    # 准确投票（投中狼人）
    TRUST_INACCURATE_VOTING: int = -15 # 不准确投票（投错好人）
    
    # 信任分数范围
    TRUST_SCORE_MIN: int = 0
    TRUST_SCORE_MAX: int = 100
    TRUST_SCORE_DEFAULT: int = 50
    
    # 信任历史管理
    MAX_TRUST_HISTORY_PER_PLAYER: int = 10  # 每个玩家保留最近10次信任变化
    MAX_TRUST_HISTORY_PLAYERS: int = 50     # 最多跟踪50个玩家的历史
    
    # ==================== ML配置 ====================
    ML_ENABLED: bool = True
    ML_MODEL_DIR: str = "./ml_models"
    ML_RETRAIN_INTERVAL: int = 5  # 每5局游戏重新训练
    ML_FUSION_RATIO: float = 0.4  # ML预测权重40%，决策树60%
    
    # ==================== 发言配置 ====================
    MAX_SPEECH_LENGTH: int = 1400  # 绝对最大长度
    MIN_SPEECH_LENGTH: int = 900   # 最小长度
    
    # ==================== 决策配置 ====================
    DECISION_MODE: str = "hybrid"  # hybrid, code_only, llm_only
    VOTE_STRATEGY: str = "trust_based"  # trust_based, majority, random
    
    # ==================== 游戏阶段配置 ====================
    EARLY_GAME_MAX_DAY: int = 2  # 早期游戏：第1-2天
    MID_GAME_MAX_DAY: int = 5    # 中期游戏：第3-5天
    ENDGAME_ALIVE_THRESHOLD: int = 6  # 残局：≤6人存活
    
    # 投票紧急度配置
    VOTE_URGENCY_MULTIPLIER_ENDGAME: float = 1.5  # 残局紧急度乘数
    VOTE_URGENCY_MULTIPLIER_MIDLATE: float = 1.2  # 中后期紧急度乘数
    
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
        
        # 验证决策模式
        if self.DECISION_MODE not in ["hybrid", "code_only", "llm_only"]:
            raise ValueError("DECISION_MODE must be 'hybrid', 'code_only', or 'llm_only'")
        
        # 验证投票策略
        if self.VOTE_STRATEGY not in ["trust_based", "majority", "random"]:
            raise ValueError("VOTE_STRATEGY must be 'trust_based', 'majority', or 'random'")
        
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
        
        # 验证信任分数范围
        if self.TRUST_SCORE_MIN >= self.TRUST_SCORE_MAX:
            raise ValueError("TRUST_SCORE_MIN must be less than TRUST_SCORE_MAX")
        
        if not (self.TRUST_SCORE_MIN <= self.TRUST_SCORE_DEFAULT <= self.TRUST_SCORE_MAX):
            raise ValueError("TRUST_SCORE_DEFAULT must be between MIN and MAX")
        
        # 验证ML配置
        if not (0.0 <= self.ML_FUSION_RATIO <= 1.0):
            raise ValueError("ML_FUSION_RATIO must be between 0.0 and 1.0")
        
        if self.ML_RETRAIN_INTERVAL < 1:
            raise ValueError("ML_RETRAIN_INTERVAL must be at least 1")
        
        # 验证信任分数配置
        trust_penalties = [
            self.TRUST_INJECTION_ATTACK,
            self.TRUST_INJECTION_ATTACK_SYSTEM,
            self.TRUST_INJECTION_ATTACK_STATUS,
            self.TRUST_FALSE_QUOTATION,
            self.TRUST_INACCURATE_VOTING,
            self.TRUST_WOLF_CHECK  # 被验为狼人也是惩罚
        ]
        if not all(-100 <= p <= 0 for p in trust_penalties):
            raise ValueError("All trust penalties (including WOLF_CHECK) must be between -100 and 0")
        
        # 验证正向奖励
        trust_bonuses = [
            self.TRUST_GOOD_CHECK,
            self.TRUST_LOGICAL_SPEECH,
            self.TRUST_ACCURATE_VOTING
        ]
        if not all(0 < b <= 100 for b in trust_bonuses):
            raise ValueError("Trust bonuses (GOOD_CHECK, LOGICAL_SPEECH, ACCURATE_VOTING) must be between 0 and 100")
        
        return True
