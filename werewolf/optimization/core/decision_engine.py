"""
决策引擎模块

本模块实现了决策引擎，负责聚合多个评分维度并生成最终决策。
使用策略模式，支持灵活配置和扩展。

设计要点：
- 聚合多个评分维度的分数
- 使用加权平均计算最终分数
- 支持动态启用/禁用维度
- 使用 safe_divide 避免除零错误

验证需求：AC-1.4.1
"""

from typing import List, Dict, Optional
import logging

from werewolf.optimization.core.scoring_strategy import ScoringDimension
from werewolf.optimization.core.decision_context import DecisionContext
from werewolf.optimization.utils.safe_math import safe_divide

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    决策引擎，聚合多个评分维度
    
    决策引擎负责协调多个评分维度，计算每个候选人的综合分数，
    并选择最佳候选人。使用加权平均方法聚合各维度的分数。
    
    属性:
        dimensions: 启用的评分维度列表
    
    示例:
        >>> from werewolf.optimization.core.scoring_strategy import (
        ...     TrustScoreDimension,
        ...     WerewolfProbabilityDimension
        ... )
        >>> 
        >>> # 创建评分维度
        >>> dimensions = [
        ...     TrustScoreDimension({'weight': 2.0, 'enabled': True}),
        ...     WerewolfProbabilityDimension({'weight': 3.0, 'enabled': True})
        ... ]
        >>> 
        >>> # 创建决策引擎
        >>> engine = DecisionEngine(dimensions)
        >>> 
        >>> # 准备决策上下文
        >>> context = DecisionContext(
        ...     game_state={'seer_checked_werewolves': ['No.2']},
        ...     player_profiles={
        ...         'No.1': {'trust_score': 75.0},
        ...         'No.2': {'trust_score': 30.0}
        ...     }
        ... )
        >>> 
        >>> # 评估候选人
        >>> scores = engine.evaluate_candidate('No.1', context)
        >>> print(scores['final_score'])
        >>> 
        >>> # 选择最佳候选人
        >>> best = engine.select_best_candidate(['No.1', 'No.2'], context)
        >>> print(best)
    
    验证需求：AC-1.4.1
    """
    
    def __init__(self, dimensions: List[ScoringDimension]):
        """
        初始化决策引擎
        
        参数:
            dimensions: 评分维度列表，只有启用的维度会被使用
        """
        # 只保留启用的维度
        self.dimensions = [d for d in dimensions if d.enabled]
        
        logger.info(
            f"决策引擎初始化完成，启用 {len(self.dimensions)} 个评分维度: "
            f"{[d.get_name() for d in self.dimensions]}"
        )
    
    def evaluate_candidate(
        self,
        candidate: str,
        context: DecisionContext
    ) -> Dict[str, float]:
        """
        评估候选人
        
        计算候选人在各个评分维度上的分数，并使用加权平均计算最终分数。
        使用 safe_divide 避免总权重为零时的除零错误。
        
        参数:
            candidate: 候选人名称，例如 'No.1'
            context: 决策上下文，包含游戏状态和玩家档案
        
        返回:
            包含总分和各维度分数的字典，格式：
            {
                'dimension_name_1': score_1,
                'dimension_name_2': score_2,
                ...
                'final_score': weighted_average_score
            }
        
        示例:
            >>> engine = DecisionEngine([
            ...     TrustScoreDimension({'weight': 2.0, 'enabled': True}),
            ...     WerewolfProbabilityDimension({'weight': 3.0, 'enabled': True})
            ... ])
            >>> context = DecisionContext(
            ...     game_state={},
            ...     player_profiles={'No.1': {'trust_score': 80.0}}
            ... )
            >>> scores = engine.evaluate_candidate('No.1', context)
            >>> print(scores)
            {
                'trust_score': 80.0,
                'werewolf_probability': 25.0,
                'final_score': 46.0  # (80*2 + 25*3) / (2+3)
            }
        
        验证需求：AC-1.4.1
        """
        # 设置当前评估的目标玩家
        context.target_player = candidate
        
        scores = {}
        weighted_sum = 0.0
        total_weight = 0.0
        
        # 计算各维度的分数
        for dimension in self.dimensions:
            try:
                score = dimension.calculate_score(context)
                dimension_name = dimension.get_name()
                scores[dimension_name] = score
                
                # 累加加权分数
                weighted_sum += score * dimension.weight
                total_weight += dimension.weight
                
                logger.debug(
                    f"候选人 {candidate} 在维度 {dimension_name} 的分数: "
                    f"{score:.2f} (权重: {dimension.weight})"
                )
            except Exception as e:
                # 如果某个维度计算失败，记录错误但继续处理其他维度
                dimension_name = dimension.get_name()
                logger.error(
                    f"计算候选人 {candidate} 在维度 {dimension_name} 的分数时出错: {e}",
                    exc_info=True
                )
                # 使用默认分数 50.0（中性）
                scores[dimension_name] = 50.0
                weighted_sum += 50.0 * dimension.weight
                total_weight += dimension.weight
        
        # 计算加权平均，使用 safe_divide 避免除零错误
        final_score = safe_divide(
            weighted_sum,
            total_weight,
            default=50.0  # 如果总权重为零，返回中性分数
        )
        scores['final_score'] = final_score
        
        logger.info(
            f"候选人 {candidate} 的最终分数: {final_score:.2f} "
            f"(加权和: {weighted_sum:.2f}, 总权重: {total_weight:.2f})"
        )
        
        return scores
    
    def select_best_candidate(
        self,
        candidates: List[str],
        context: DecisionContext
    ) -> Optional[str]:
        """
        选择最佳候选人
        
        评估所有候选人，返回最终分数最高的候选人。
        如果候选人列表为空，返回 None。
        
        参数:
            candidates: 候选人列表，例如 ['No.1', 'No.2', 'No.3']
            context: 决策上下文，包含游戏状态和玩家档案
        
        返回:
            最佳候选人名称，如果候选人列表为空则返回 None
        
        示例:
            >>> engine = DecisionEngine([
            ...     TrustScoreDimension({'weight': 2.0, 'enabled': True})
            ... ])
            >>> context = DecisionContext(
            ...     game_state={},
            ...     player_profiles={
            ...         'No.1': {'trust_score': 80.0},
            ...         'No.2': {'trust_score': 60.0},
            ...         'No.3': {'trust_score': 90.0}
            ...     }
            ... )
            >>> best = engine.select_best_candidate(['No.1', 'No.2', 'No.3'], context)
            >>> print(best)  # 'No.3'
        
        验证需求：AC-1.4.1
        """
        if not candidates:
            logger.warning("候选人列表为空，无法选择最佳候选人")
            return None
        
        best_candidate = None
        best_score = -1.0
        
        logger.info(f"开始评估 {len(candidates)} 个候选人: {candidates}")
        
        for candidate in candidates:
            scores = self.evaluate_candidate(candidate, context)
            final_score = scores['final_score']
            
            if final_score > best_score:
                best_score = final_score
                best_candidate = candidate
        
        logger.info(
            f"选择最佳候选人: {best_candidate} (分数: {best_score:.2f})"
        )
        
        return best_candidate
