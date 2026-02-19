"""
守卫代理人配置类 - 企业级配置管理

遵循企业级标准:
1. 使用dataclass减少样板代码
2. 继承BaseConfig统一配置体系
3. 提供配置验证方法
4. 集中管理所有魔法数字
"""
from dataclasses import dataclass, field
from typing import Dict, Any
import sys
import os

# 添加core路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.config import BaseConfig
except ImportError:
    # 如果core不存在,使用简化版本
    @dataclass
    class BaseConfig:
        log_level: str = "INFO"
        enable_ml: bool = False
        confidence_threshold: float = 0.6
        trust_threshold: float = 0.5
        suspicion_threshold: float = 0.4
        speech_weight: float = 0.3
        vote_weight: float = 0.3
        behavior_weight: float = 0.2
        ml_weight: float = 0.2
        role_specific: Dict[str, Any] = field(default_factory=dict)
        
        def validate(self) -> bool:
            return True


@dataclass
class GuardConfig(BaseConfig):
    """
    守卫代理人配置
    
    继承BaseConfig,添加守卫特定配置
    所有配置参数使用类型注解,提升代码质量
    """
    
    # ==================== 发言长度控制 ====================
    MAX_SPEECH_LENGTH: int = 1500
    MIN_SPEECH_LENGTH: int = 1000
    OPTIMAL_SPEECH_MIN: int = 900
    OPTIMAL_SPEECH_MAX: int = 1300
    MAX_VOTE_REASON_LENGTH: int = 200
    
    # ==================== 决策模式 ====================
    DECISION_MODE_HYBRID: str = "hybrid"
    DECISION_MODE_PURE_CODE: str = "pure_code"
    DEFAULT_DECISION_MODE: str = "hybrid"
    
    # ==================== 信任分数阈值 ====================
    TRUST_VERY_LOW: int = 20
    TRUST_LOW: int = 40
    TRUST_MEDIUM: int = 60
    TRUST_HIGH: int = 70
    TRUST_VERY_HIGH: int = 75
    
    # ==================== 狼人概率阈值 ====================
    WOLF_PROB_VERY_HIGH: float = 0.90
    WOLF_PROB_HIGH: float = 0.85
    WOLF_PROB_MEDIUM: float = 0.70
    WOLF_PROB_LOW: float = 0.30
    
    # ==================== 游戏阶段定义 ====================
    PHASE_EARLY_MAX_DAY: int = 2
    PHASE_MID_MAX_DAY: int = 5
    PHASE_ENDGAME_MAX_ALIVE: int = 4
    
    # ==================== 守卫优先级分数 ====================
    GUARD_PRIORITY_CONFIRMED_SEER: int = 90
    GUARD_PRIORITY_LIKELY_SEER: int = 70
    GUARD_PRIORITY_SHERIFF: int = 65
    GUARD_PRIORITY_WITCH: int = 60
    GUARD_PRIORITY_HIGH_TRUST: int = 55
    GUARD_PRIORITY_HUNTER_MAX: int = 30
    GUARD_PRIORITY_WOLF_TARGET_BONUS: int = 25
    
    # ==================== 投票分数加成 ====================
    VOTE_BONUS_PROTECTING_WOLVES: int = 30
    VOTE_BONUS_CHARGING: int = 20
    VOTE_BONUS_SWAYING: int = 15
    VOTE_PENALTY_ACCURATE: int = -25
    VOTE_BONUS_SYSTEM_FAKE: int = 40
    VOTE_BONUS_STATUS_FAKE: int = 30
    VOTE_PENALTY_BENIGN: int = -15
    VOTE_BONUS_FALSE_QUOTATION: int = 25
    VOTE_BONUS_STATUS_CONTRADICTION: int = 35
    
    # ==================== 信任分数调整值 ====================
    TRUST_DELTA_KILLED_AT_NIGHT: int = 20
    TRUST_DELTA_ELECTED_SHERIFF: int = 10
    TRUST_DELTA_VOTED_OUT: int = -30
    TRUST_DELTA_SHERIFF_CAMPAIGN: int = 5
    TRUST_DELTA_INJECTION_SYSTEM_FAKE: int = -25
    TRUST_DELTA_INJECTION_STATUS_FAKE: int = -15
    TRUST_DELTA_INJECTION_BENIGN: int = 5
    TRUST_DELTA_FALSE_QUOTATION: int = -10
    TRUST_DELTA_STATUS_CONTRADICTION: int = -20
    TRUST_DELTA_EXPOSE_IDENTITY: int = -5
    TRUST_DELTA_SHORT_SPEECH: int = -3
    TRUST_DELTA_GOOD_SPEECH: int = 5
    TRUST_DELTA_STRONG_LOGIC: int = 8
    
    # ==================== 置信度计算 ====================
    CONFIDENCE_BASE: int = 70
    CONFIDENCE_HIGH_THRESHOLD: int = 80
    CONFIDENCE_MEDIUM_THRESHOLD: int = 60
    
    # ==================== LLM检测配置 ====================
    LLM_DETECTION_TIMEOUT: int = 60
    LLM_DETECTION_TEMPERATURE: float = 0.1
    LLM_ROLE_CONFIDENCE_HIGH: float = 0.7
    LLM_ROLE_CONFIDENCE_MEDIUM: float = 0.6
    
    # ==================== 投票准确度阈值 ====================
    VOTING_ACCURACY_HIGH: float = 0.67
    VOTING_ACCURACY_LOW: float = 0.33
    VOTING_MIN_SAMPLES: int = 2
    
    # ==================== 狼人击杀预测 ====================
    KILL_PROB_CONFIRMED_SEER: float = 0.80
    KILL_PROB_LIKELY_SEER: float = 0.60
    KILL_PROB_SHERIFF_HIGH_TRUST: float = 0.50
    KILL_PROB_SHERIFF_LOW_TRUST: float = 0.30
    KILL_PROB_WITCH: float = 0.45
    KILL_PROB_STRONG_VILLAGER: float = 0.40
    KILL_PROB_HUNTER: float = 0.10
    
    # ==================== 发言质量分析 ====================
    SPEECH_LENGTH_TOO_SHORT: int = 20
    SPEECH_LENGTH_GOOD_MIN: int = 100
    SPEECH_LENGTH_GOOD_MAX: int = 500
    SPEECH_LOGICAL_KEYWORDS_MIN: int = 3
    
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
        if self.MAX_SPEECH_LENGTH < self.MIN_SPEECH_LENGTH:
            return False
        
        if self.OPTIMAL_SPEECH_MAX < self.OPTIMAL_SPEECH_MIN:
            return False
        
        if not (0 <= self.GUARD_PRIORITY_HUNTER_MAX <= 100):
            return False
        
        # 验证概率范围
        prob_fields = [
            self.WOLF_PROB_VERY_HIGH, self.WOLF_PROB_HIGH,
            self.WOLF_PROB_MEDIUM, self.WOLF_PROB_LOW,
            self.KILL_PROB_CONFIRMED_SEER, self.KILL_PROB_HUNTER
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


# 保持向后兼容
class PromptConfig:
    """提示词配置(保持向后兼容)"""
    
    CRITICAL_KEYWORDS = [
        "died", "killed", "eliminated", "shot", "shoot",
        "Seer", "verified", "checked", "gold water", "kill check",
        "voted", "vote result", "Sheriff",
        "System:", "Host:", "injection", "false quotation",
        "wolf", "werewolf", "Guard", "Witch", "Hunter"
    ]
    
    SYSTEM_FAKE_KEYWORDS = ["Host:", "System:", "Game Rule", "主持人:", "系统:", "游戏规则"]
    STATUS_FAKE_KEYWORDS = [
        "eliminated", "cannot be voted", "protected", "rule change",
        "已出局", "不能被投票", "受保护", "规则更新", "cannot vote"
    ]
    BENIGN_KEYWORDS = ["wolf", "werewolf", "suspicious", "suspect", "狼人", "可疑", "怀疑", "分析"]
    DEATH_CLAIM_KEYWORDS = [
        "I am eliminated", "I was voted out", "I'm dead",
        "我出局了", "我被投出", "我死了"
    ]
    LAST_WORDS_KEYWORDS = [
        "leaves their last words", "Last Words:", "'s last words",
        "遗言：", "的遗言"
    ]
    LOGICAL_KEYWORDS = [
        "because", "therefore", "analyze", "evidence", "suspect", "trust", "vote", "wolf",
        "因为", "所以", "分析", "证据", "怀疑", "相信", "投票", "狼人"
    ]


class RoleConfig:
    """角色配置(保持向后兼容)"""
    
    ROLE_GUARD = "Guard"
    ROLE_SEER = "Seer"
    ROLE_WITCH = "Witch"
    ROLE_HUNTER = "Hunter"
    ROLE_WOLF = "Wolf"
    ROLE_VILLAGER = "Villager"
    
    ROLE_GUARD_CN = "守卫"
    ROLE_SEER_CN = "预言家"
    ROLE_WITCH_CN = "女巫"
    ROLE_HUNTER_CN = "猎人"
    ROLE_WOLF_CN = "狼人"
    ROLE_VILLAGER_CN = "村民"
