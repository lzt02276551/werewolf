"""
守卫分析器模块 - 企业级实现

遵循单一职责原则，每个分析器只负责一种分析任务
"""
from typing import Dict, Any, List, Tuple, Optional
from agent_build_sdk.utils.logger import logger
from .config import GuardConfig
from .validators import MemoryValidator


class WolfProbabilityAnalyzer:
    """
    狼人概率分析器
    
    基于多种因素计算玩家是狼人的概率
    """
    
    def __init__(self, config: GuardConfig, memory, trust_manager):
        """
        初始化分析器
        
        Args:
            config: 守卫配置
            memory: 记忆系统
            trust_manager: 信任分数管理器
        """
        self.config = config
        self.memory = memory
        self.trust_manager = trust_manager
    
    def analyze(self, player: str) -> float:
        """
        分析玩家是狼人的概率
        
        Args:
            player: 玩家名称
            
        Returns:
            狼人概率 (0.0-1.0)
        """
        if not player:
            return 0.5
        
        # 基础概率（基于信任分数）
        trust_score = self.trust_manager.get_score(player)
        base_prob = 1.0 - (trust_score / 100.0)  # 信任分数越低，狼人概率越高
        
        # 注入攻击加成
        injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
        if player in injection_suspects:
            injection_type = injection_suspects[player]
            if injection_type == "system_fake":
                base_prob += 0.30
            elif injection_type == "status_fake":
                base_prob += 0.20
        
        # 虚假引用加成
        false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
        for fq in false_quotations:
            if isinstance(fq, dict) and fq.get("accuser") == player:
                base_prob += 0.15
                break
        
        # 状态矛盾加成
        player_status_claims = MemoryValidator.safe_load_dict(self.memory, "player_status_claims")
        if player in player_status_claims and player_status_claims[player]:
            base_prob += 0.25
        
        # 投票模式分析
        voting_pattern = self._analyze_voting_pattern(player)
        if voting_pattern == "protecting_wolves":
            base_prob += 0.25
        elif voting_pattern == "charging":
            base_prob += 0.15
        elif voting_pattern == "swaying":
            base_prob += 0.10
        elif voting_pattern == "accurate":
            base_prob -= 0.20
        
        # 限制在0-1范围
        return max(0.0, min(1.0, base_prob))
    
    def _analyze_voting_pattern(self, player: str) -> str:
        """
        分析投票模式
        
        Args:
            player: 玩家名称
            
        Returns:
            投票模式类型
        """
        voting_results = MemoryValidator.safe_load_dict(self.memory, "voting_results")
        
        if player not in voting_results or not voting_results[player]:
            return "unknown"
        
        results = voting_results[player]
        
        if len(results) < self.config.VOTING_MIN_SAMPLES:
            return "unknown"
        
        # 计算准确率
        total_votes = len(results)
        wolf_hits = 0
        
        # 安全解包
        for result in results:
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                _, was_wolf = result[0], result[1]
                if was_wolf:
                    wolf_hits += 1
        
        accuracy = wolf_hits / total_votes if total_votes > 0 else 0
        
        if accuracy >= self.config.VOTING_ACCURACY_HIGH:
            return "accurate"
        elif accuracy <= self.config.VOTING_ACCURACY_LOW:
            return "protecting_wolves"
        else:
            return "unknown"


class VotingPatternAnalyzer:
    """
    投票模式分析器
    
    分析玩家的投票行为模式
    """
    
    def __init__(self, config: GuardConfig, memory):
        """
        初始化分析器
        
        Args:
            config: 守卫配置
            memory: 记忆系统
        """
        self.config = config
        self.memory = memory
    
    def analyze(self, player: str) -> str:
        """
        分析投票模式
        
        Args:
            player: 玩家名称
            
        Returns:
            投票模式类型: "protecting_wolves", "charging", "swaying", "accurate", "unknown"
        """
        voting_results = MemoryValidator.safe_load_dict(self.memory, "voting_results")
        
        if player not in voting_results or not voting_results[player]:
            return "unknown"
        
        results = voting_results[player]
        
        if len(results) < self.config.VOTING_MIN_SAMPLES:
            return "unknown"
        
        # 计算准确率
        total_votes = len(results)
        wolf_hits = 0
        
        # 安全解包
        for result in results:
            if isinstance(result, (tuple, list)) and len(result) >= 2:
                _, was_wolf = result[0], result[1]
                if was_wolf:
                    wolf_hits += 1
        
        accuracy = wolf_hits / total_votes if total_votes > 0 else 0
        
        if accuracy >= self.config.VOTING_ACCURACY_HIGH:
            return "accurate"
        elif accuracy <= self.config.VOTING_ACCURACY_LOW:
            return "protecting_wolves"
        else:
            # 检查是否是冲锋狼（总是第一个投票）
            # 简化版本：需要更多数据来判断
            return "unknown"


class RoleEstimator:
    """
    角色估计器
    
    估计玩家可能的角色
    """
    
    def __init__(self, config: GuardConfig, memory, trust_manager):
        """
        初始化估计器
        
        Args:
            config: 守卫配置
            memory: 记忆系统
            trust_manager: 信任分数管理器
        """
        self.config = config
        self.memory = memory
        self.trust_manager = trust_manager
    
    def is_confirmed_seer(self, player: str) -> bool:
        """检查是否是确认的预言家"""
        # 简化版本：需要更复杂的逻辑
        trust_score = self.trust_manager.get_score(player)
        return trust_score >= self.config.TRUST_VERY_HIGH
    
    def is_likely_seer(self, player: str) -> bool:
        """检查是否可能是预言家"""
        trust_score = self.trust_manager.get_score(player)
        return trust_score >= self.config.TRUST_HIGH
    
    def is_sheriff(self, player: str) -> bool:
        """检查是否是警长"""
        # 需要从游戏状态中获取
        return False
    
    def is_likely_witch(self, player: str) -> bool:
        """检查是否可能是女巫"""
        trust_score = self.trust_manager.get_score(player)
        return trust_score >= self.config.TRUST_HIGH
    
    def is_likely_hunter(self, player: str) -> bool:
        """检查是否可能是猎人"""
        # 简化版本
        return False


class WolfKillPredictor:
    """
    狼人击杀目标预测器
    
    预测狼人可能击杀的目标
    """
    
    def __init__(self, config: GuardConfig, memory, trust_manager, role_estimator):
        """
        初始化预测器
        
        Args:
            config: 守卫配置
            memory: 记忆系统
            trust_manager: 信任分数管理器
            role_estimator: 角色估计器
        """
        self.config = config
        self.memory = memory
        self.trust_manager = trust_manager
        self.role_estimator = role_estimator
    
    def predict_single(self, player: str, context: Dict[str, Any]) -> float:
        """
        预测单个玩家被击杀的概率
        
        Args:
            player: 玩家名称
            context: 上下文信息
            
        Returns:
            被击杀概率 (0.0-1.0)
        """
        if not player:
            return 0.0
        
        kill_prob = 0.0
        
        # 确认的预言家
        if self.role_estimator.is_confirmed_seer(player):
            kill_prob = self.config.KILL_PROB_CONFIRMED_SEER
        # 可能的预言家
        elif self.role_estimator.is_likely_seer(player):
            kill_prob = self.config.KILL_PROB_LIKELY_SEER
        # 警长
        elif self.role_estimator.is_sheriff(player):
            trust_score = self.trust_manager.get_score(player)
            if trust_score >= self.config.TRUST_HIGH:
                kill_prob = self.config.KILL_PROB_SHERIFF_HIGH_TRUST
            else:
                kill_prob = self.config.KILL_PROB_SHERIFF_LOW_TRUST
        # 可能的女巫
        elif self.role_estimator.is_likely_witch(player):
            kill_prob = self.config.KILL_PROB_WITCH
        # 可能的猎人
        elif self.role_estimator.is_likely_hunter(player):
            kill_prob = self.config.KILL_PROB_HUNTER
        # 强力村民
        else:
            trust_score = self.trust_manager.get_score(player)
            if trust_score >= self.config.TRUST_HIGH:
                kill_prob = self.config.KILL_PROB_STRONG_VILLAGER
        
        return kill_prob


class GuardPriorityCalculator:
    """
    守卫优先级计算器
    
    计算守卫目标的优先级
    """
    
    def __init__(self, config: GuardConfig, memory, trust_manager, role_estimator):
        """
        初始化计算器
        
        Args:
            config: 守卫配置
            memory: 记忆系统
            trust_manager: 信任分数管理器
            role_estimator: 角色估计器
        """
        self.config = config
        self.memory = memory
        self.trust_manager = trust_manager
        self.role_estimator = role_estimator
    
    def calculate(self, player: str, context: Dict[str, Any]) -> float:
        """
        计算守卫优先级
        
        Args:
            player: 玩家名称
            context: 上下文信息
            
        Returns:
            优先级分数 (0-100)
        """
        if not player:
            return 0.0
        
        priority = 0.0
        
        # 确认的预言家
        if self.role_estimator.is_confirmed_seer(player):
            priority = self.config.GUARD_PRIORITY_CONFIRMED_SEER
        # 可能的预言家
        elif self.role_estimator.is_likely_seer(player):
            priority = self.config.GUARD_PRIORITY_LIKELY_SEER
        # 警长
        elif self.role_estimator.is_sheriff(player):
            priority = self.config.GUARD_PRIORITY_SHERIFF
        # 可能的女巫
        elif self.role_estimator.is_likely_witch(player):
            priority = self.config.GUARD_PRIORITY_WITCH
        # 可能的猎人（低优先级）
        elif self.role_estimator.is_likely_hunter(player):
            priority = self.config.GUARD_PRIORITY_HUNTER_MAX
        # 高信任玩家
        else:
            trust_score = self.trust_manager.get_score(player)
            if trust_score >= self.config.TRUST_HIGH:
                priority = self.config.GUARD_PRIORITY_HIGH_TRUST
            else:
                priority = trust_score * 0.5  # 基于信任分数
        
        return priority
