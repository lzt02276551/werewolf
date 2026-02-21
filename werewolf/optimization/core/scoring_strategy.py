"""
评分策略模块

本模块实现了策略模式的评分维度接口，用于决策引擎的灵活扩展。
每个评分维度独立为一个类，符合单一职责原则。

设计要点：
- 使用抽象基类定义统一接口
- 支持配置化权重和启用/禁用
- 与DecisionContext集成实现缓存
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from werewolf.optimization.core.decision_context import DecisionContext


class ScoringDimension(ABC):
    """
    评分维度抽象基类
    
    所有具体的评分策略都应继承此类并实现抽象方法。
    
    属性:
        config: 配置字典，包含该维度的所有参数
        weight: 权重值，用于加权聚合
        enabled: 是否启用该维度
    
    示例:
        >>> class TrustScoreDimension(ScoringDimension):
        ...     def calculate_score(self, context):
        ...         return 75.0
        ...     def get_name(self):
        ...         return "trust_score"
        >>> 
        >>> config = {'weight': 2.0, 'enabled': True}
        >>> dimension = TrustScoreDimension(config)
        >>> dimension.weight
        2.0
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化评分维度
        
        参数:
            config: 配置字典，应包含以下键：
                - weight: 权重值（默认1.0）
                - enabled: 是否启用（默认True）
                - 其他维度特定的参数
        """
        self.config = config
        self.weight = config.get('weight', 1.0)
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def calculate_score(self, context: 'DecisionContext') -> float:
        """
        计算该维度的分数
        
        此方法应该实现具体的评分逻辑。建议使用context.get_cached()
        来缓存计算结果，避免重复计算。
        
        参数:
            context: 决策上下文，包含游戏状态、玩家档案和缓存
        
        返回:
            分数值，通常在0-100范围内
        
        示例:
            >>> def calculate_score(self, context):
            ...     player_name = context.target_player
            ...     # 使用缓存避免重复计算
            ...     score = context.get_cached(
            ...         f'trust_score_{player_name}',
            ...         lambda: self._compute_trust_score(context, player_name)
            ...     )
            ...     return score
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        返回维度名称
        
        维度名称用于日志记录、配置匹配和结果展示。
        应该使用小写字母和下划线的命名风格。
        
        返回:
            维度名称字符串
        
        示例:
            >>> def get_name(self):
            ...     return "trust_score"
        """
        pass


# ============================================================================
# 具体评分策略实现
# ============================================================================


class TrustScoreDimension(ScoringDimension):
    """
    信任分数评分维度
    
    基于玩家的信任分数进行评分。信任分数反映了对玩家身份的信任程度，
    分数越高表示越可信（越可能是好人），分数越低表示越不可信（越可能是狼人）。
    
    配置参数:
        weight: 权重值，默认 1.0
        enabled: 是否启用，默认 True
    
    示例:
        >>> config = {'weight': 2.0, 'enabled': True}
        >>> dimension = TrustScoreDimension(config)
        >>> context = DecisionContext(
        ...     game_state={},
        ...     player_profiles={'No.1': {'trust_score': 75.0}}
        ... )
        >>> context.target_player = 'No.1'
        >>> score = dimension.calculate_score(context)
        >>> print(score)  # 75.0
    
    验证需求: AC-1.4.1, AC-2.1.2
    """
    
    def calculate_score(self, context: 'DecisionContext') -> float:
        """
        计算信任分数
        
        从玩家档案中获取信任分数。使用缓存避免重复查询。
        如果玩家档案中没有信任分数，返回默认值 50.0（中性）。
        
        参数:
            context: 决策上下文
        
        返回:
            信任分数，范围 [0, 100]
        """
        player_name = context.target_player
        
        # 使用缓存避免重复计算
        trust_score = context.get_cached(
            f'trust_score_{player_name}',
            lambda: self._compute_trust_score(context, player_name)
        )
        
        return trust_score
    
    def get_name(self) -> str:
        """返回维度名称"""
        return "trust_score"
    
    def _compute_trust_score(
        self,
        context: 'DecisionContext',
        player_name: str
    ) -> float:
        """
        计算信任分数的内部方法
        
        参数:
            context: 决策上下文
            player_name: 玩家名称
        
        返回:
            信任分数，范围 [0, 100]
        """
        # 获取玩家档案
        player_profile = context.get_player_profile(player_name)
        
        # 获取信任分数，如果不存在则返回默认值 50.0（中性）
        trust_score = player_profile.get('trust_score', 50.0)
        
        return float(trust_score)


class WerewolfProbabilityDimension(ScoringDimension):
    """
    狼人概率评分维度
    
    基于贝叶斯推理计算玩家是狼人的概率，并转换为评分。
    概率越高，分数越高，表示越应该投票/击杀该玩家。
    
    配置参数:
        weight: 权重值，默认 1.0
        enabled: 是否启用，默认 True
        prior_probability: 先验概率，默认 0.25
    
    示例:
        >>> config = {
        ...     'weight': 3.0,
        ...     'enabled': True,
        ...     'prior_probability': 0.25
        ... }
        >>> dimension = WerewolfProbabilityDimension(config)
        >>> context = DecisionContext(
        ...     game_state={'seer_checked_werewolves': ['No.1']},
        ...     player_profiles={}
        ... )
        >>> context.target_player = 'No.1'
        >>> score = dimension.calculate_score(context)
        >>> print(score)  # 高分，因为被预言家查验为狼人
    
    验证需求: AC-1.4.1, AC-2.1.2
    """
    
    def calculate_score(self, context: 'DecisionContext') -> float:
        """
        计算狼人概率分数
        
        使用贝叶斯推理计算玩家是狼人的概率，然后转换为 0-100 的分数。
        使用缓存避免重复计算。
        
        参数:
            context: 决策上下文
        
        返回:
            狼人概率分数，范围 [0, 100]
        """
        player_name = context.target_player
        
        # 使用缓存避免重复计算
        werewolf_prob = context.get_cached(
            f'werewolf_prob_{player_name}',
            lambda: self._compute_werewolf_probability(context, player_name)
        )
        
        # 转换为 0-100 分数
        return werewolf_prob * 100.0
    
    def get_name(self) -> str:
        """返回维度名称"""
        return "werewolf_probability"
    
    def _compute_werewolf_probability(
        self,
        context: 'DecisionContext',
        player_name: str
    ) -> float:
        """
        计算狼人概率的内部方法
        
        使用贝叶斯推理引擎，基于各种证据计算玩家是狼人的概率。
        
        参数:
            context: 决策上下文
            player_name: 玩家名称
        
        返回:
            狼人概率，范围 [0, 1]
        """
        from ..algorithms.bayesian_inference import (
            BayesianInference,
            Evidence,
            EvidenceType
        )
        
        # 创建贝叶斯推理引擎
        bayesian_config = {
            'prior_probability': self.config.get('prior_probability', 0.25)
        }
        bayesian = BayesianInference(bayesian_config)
        
        # 收集证据
        evidences = []
        
        # 证据1：被预言家查验为狼人（独立证据，强证据）
        seer_checked_werewolves = context.game_state.get('seer_checked_werewolves', [])
        if player_name in seer_checked_werewolves:
            evidences.append(Evidence(
                name="seer_check_werewolf",
                likelihood_ratio=10.0,  # 强证据
                evidence_type=EvidenceType.INDEPENDENT
            ))
        
        # 证据2：被预言家查验为好人（独立证据，反向证据）
        seer_checked_villagers = context.game_state.get('seer_checked_villagers', [])
        if player_name in seer_checked_villagers:
            evidences.append(Evidence(
                name="seer_check_villager",
                likelihood_ratio=0.1,  # 反向证据，降低狼人概率
                evidence_type=EvidenceType.INDEPENDENT
            ))
        
        # 证据3：发言分析（相关证据组）
        player_profile = context.get_player_profile(player_name)
        speech_analysis = player_profile.get('speech_analysis', {})
        
        if speech_analysis.get('has_injection_attack', False):
            evidences.append(Evidence(
                name="injection_attack",
                likelihood_ratio=3.0,
                evidence_type=EvidenceType.CORRELATED
            ))
        
        if speech_analysis.get('has_false_reference', False):
            evidences.append(Evidence(
                name="false_reference",
                likelihood_ratio=2.5,
                evidence_type=EvidenceType.CORRELATED
            ))
        
        if speech_analysis.get('has_contradiction', False):
            evidences.append(Evidence(
                name="contradiction",
                likelihood_ratio=2.0,
                evidence_type=EvidenceType.CORRELATED
            ))
        
        # 计算后验概率
        posterior_prob = bayesian.calculate_posterior(evidences)
        
        return posterior_prob


class VotingAccuracyDimension(ScoringDimension):
    """
    投票准确率评分维度
    
    基于玩家的历史投票准确率进行评分。准确率越高，说明玩家的投票决策越可靠，
    可能是好人；准确率越低，可能是狼人在误导投票。
    
    配置参数:
        weight: 权重值，默认 1.0
        enabled: 是否启用，默认 True
        min_history_size: 最小历史记录数，默认 3
    
    示例:
        >>> config = {
        ...     'weight': 1.5,
        ...     'enabled': True,
        ...     'min_history_size': 3
        ... }
        >>> dimension = VotingAccuracyDimension(config)
        >>> context = DecisionContext(
        ...     game_state={},
        ...     player_profiles={
        ...         'No.1': {
        ...             'voting_history': [
        ...                 {'voted_for': 'No.2', 'was_werewolf': True},
        ...                 {'voted_for': 'No.3', 'was_werewolf': True},
        ...                 {'voted_for': 'No.4', 'was_werewolf': False}
        ...             ]
        ...         }
        ...     }
        ... )
        >>> context.target_player = 'No.1'
        >>> score = dimension.calculate_score(context)
        >>> print(score)  # 约 66.67，因为3次投票中2次正确
    
    验证需求: AC-1.4.1, AC-2.1.2
    """
    
    def calculate_score(self, context: 'DecisionContext') -> float:
        """
        计算投票准确率分数
        
        从玩家档案中获取投票历史，计算准确率。使用 safe_divide 避免除零错误。
        使用缓存避免重复计算。
        
        参数:
            context: 决策上下文
        
        返回:
            投票准确率分数，范围 [0, 100]
        """
        player_name = context.target_player
        
        # 使用缓存避免重复计算
        accuracy_score = context.get_cached(
            f'voting_accuracy_{player_name}',
            lambda: self._compute_voting_accuracy(context, player_name)
        )
        
        return accuracy_score
    
    def get_name(self) -> str:
        """返回维度名称"""
        return "voting_accuracy"
    
    def _compute_voting_accuracy(
        self,
        context: 'DecisionContext',
        player_name: str
    ) -> float:
        """
        计算投票准确率的内部方法
        
        参数:
            context: 决策上下文
            player_name: 玩家名称
        
        返回:
            投票准确率分数，范围 [0, 100]
        """
        from ..utils.safe_math import safe_divide
        
        # 获取玩家档案
        player_profile = context.get_player_profile(player_name)
        
        # 获取投票历史
        voting_history = player_profile.get('voting_history', [])
        
        # 检查历史记录是否足够
        min_history_size = self.config.get('min_history_size', 3)
        if len(voting_history) < min_history_size:
            # 历史记录不足，返回中性分数 50.0
            return 50.0
        
        # 计算准确率
        correct_votes = 0
        total_votes = len(voting_history)
        
        for vote in voting_history:
            # 检查投票是否正确（投给了狼人）
            if vote.get('was_werewolf', False):
                correct_votes += 1
        
        # 使用 safe_divide 避免除零错误
        accuracy = safe_divide(
            correct_votes,
            total_votes,
            default=0.5  # 默认返回 50%
        )
        
        # 转换为 0-100 分数
        return accuracy * 100.0
