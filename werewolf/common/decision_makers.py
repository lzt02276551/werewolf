"""
通用决策器

提供投票决策、警长决策等通用决策功能
"""

from typing import Dict, Any, List, Tuple, Optional
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.core.config import BaseConfig
from werewolf.optimization.utils.safe_math import safe_divide
from .analyzers import TrustAnalyzer, WolfProbabilityAnalyzer


class VoteDecisionMaker(BaseDecisionMaker):
    """
    投票决策器
    
    基于信任分数和狼人概率做出投票决策
    """
    
    def __init__(
        self,
        config: BaseConfig,
        trust_analyzer: TrustAnalyzer,
        wolf_analyzer: WolfProbabilityAnalyzer
    ):
        """
        初始化决策器
        
        Args:
            config: 配置对象
            trust_analyzer: 信任分析器
            wolf_analyzer: 狼人概率分析器
        """
        super().__init__(config)
        self.trust_analyzer = trust_analyzer
        self.wolf_analyzer = wolf_analyzer
    
    def decide(
        self,
        candidates: List[str],
        my_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        做出投票决策
        
        Args:
            candidates: 候选人列表
            my_name: 自己的名称
            context: 上下文信息
            
        Returns:
            决策结果字典
        """
        try:
            if not candidates:
                return self._get_default_result()
            
            # 移除自己
            valid_candidates = [c for c in candidates if c != my_name]
            if not valid_candidates:
                return self._get_default_result()
            
            # 计算每个候选人的得分
            scores = self._calculate_scores(valid_candidates, context)
            
            # 选择得分最高的
            target = max(scores.items(), key=lambda x: x[1])[0]
            target_score = scores[target]
            
            # 生成推理
            reasoning = self._generate_reasoning(target, target_score, context)
            
            # 计算置信度
            confidence = self._calculate_confidence(scores, target_score)
            
            return {
                'action': 'vote',
                'target': target,
                'reasoning': reasoning,
                'confidence': confidence,
                'scores': scores
            }
            
        except Exception as e:
            return self._handle_error(e, "decide")
    
    def _calculate_scores(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        计算候选人得分
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            候选人->得分字典
        """
        scores = {}
        
        for candidate in candidates:
            # 基础分数:狼人概率
            wolf_prob = self.wolf_analyzer.analyze(candidate, context)
            
            # 信任分数影响
            trust_score = self.trust_analyzer.get_score(candidate)
            trust_factor = 1.0 - safe_divide(trust_score, 100.0, default=0.5)
            
            # 综合得分
            score = wolf_prob * 0.7 + trust_factor * 0.3
            
            # 考虑游戏阶段
            phase = context.get('phase', 'mid')
            if phase == 'critical':
                # 关键期更激进
                score *= 1.2
            
            scores[candidate] = score
        
        return scores
    
    def _generate_reasoning(
        self,
        target: str,
        score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        生成投票推理
        
        Args:
            target: 目标玩家
            score: 得分
            context: 上下文信息
            
        Returns:
            推理文本
        """
        trust_score = self.trust_analyzer.get_score(target)
        wolf_prob = self.wolf_analyzer.analyze(target, context)
        
        reasoning_parts = [
            f"投票给{target}",
            f"信任分数: {trust_score:.1f}",
            f"狼人概率: {wolf_prob:.2f}",
        ]
        
        # 添加具体原因
        if context.get('has_injection', {}).get(target, False):
            reasoning_parts.append("检测到注入行为")
        
        if trust_score < 30:
            reasoning_parts.append("信任度极低")
        
        return ", ".join(reasoning_parts)
    
    def _calculate_confidence(
        self,
        scores: Dict[str, float],
        target_score: float
    ) -> float:
        """
        计算决策置信度
        
        Args:
            scores: 所有得分
            target_score: 目标得分
            
        Returns:
            置信度(0-1)
        """
        if not scores or len(scores) == 1:
            return 0.5
        
        # 计算得分差距
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) < 2:
            return 0.7
        
        top_score = sorted_scores[0]
        second_score = sorted_scores[1]
        
        # 差距越大,置信度越高
        gap = top_score - second_score
        confidence = 0.5 + min(gap, 0.5)
        
        return confidence


class SheriffDecisionMaker(BaseDecisionMaker):
    """
    警长决策器
    
    决定是否竞选警长
    """
    
    def __init__(
        self,
        config: BaseConfig,
        trust_analyzer: TrustAnalyzer
    ):
        """
        初始化决策器
        
        Args:
            config: 配置对象
            trust_analyzer: 信任分析器
        """
        super().__init__(config)
        self.trust_analyzer = trust_analyzer
    
    def decide(
        self,
        my_name: str,
        context: Dict[str, Any],
        role_type: str = "villager"
    ) -> Dict[str, Any]:
        """
        决定是否竞选警长
        
        Args:
            my_name: 自己的名称
            context: 上下文信息
            role_type: 角色类型
            
        Returns:
            决策结果字典
        """
        try:
            # 获取自己的信任分数
            my_trust = self.trust_analyzer.get_score(my_name)
            
            # 根据角色类型决定
            should_run = self._should_run_for_sheriff(
                role_type,
                my_trust,
                context
            )
            
            # 生成推理
            reasoning = self._generate_reasoning(
                should_run,
                role_type,
                my_trust
            )
            
            return {
                'action': 'run_for_sheriff' if should_run else 'skip',
                'target': None,
                'reasoning': reasoning,
                'confidence': 0.7 if should_run else 0.5
            }
            
        except Exception as e:
            return self._handle_error(e, "decide")
    
    def _should_run_for_sheriff(
        self,
        role_type: str,
        trust_score: float,
        context: Dict[str, Any]
    ) -> bool:
        """
        判断是否应该竞选警长
        
        Args:
            role_type: 角色类型
            trust_score: 信任分数
            context: 上下文信息
            
        Returns:
            是否竞选
        """
        # 神职角色更倾向于竞选
        if role_type in ['seer', 'witch', 'hunter']:
            return trust_score >= 50
        
        # 狼人一般不竞选(除非伪装)
        if role_type in ['wolf', 'wolf_king']:
            return trust_score >= 70  # 只有信任度很高时才竞选
        
        # 普通村民根据信任度决定
        return trust_score >= 60
    
    def _generate_reasoning(
        self,
        should_run: bool,
        role_type: str,
        trust_score: float
    ) -> str:
        """
        生成推理
        
        Args:
            should_run: 是否竞选
            role_type: 角色类型
            trust_score: 信任分数
            
        Returns:
            推理文本
        """
        if should_run:
            return f"竞选警长,信任分数: {trust_score:.1f},可以为好人阵营做贡献"
        else:
            return f"不竞选警长,信任分数: {trust_score:.1f},让更合适的人当选"


class TargetSelectionMaker(BaseDecisionMaker):
    """
    目标选择决策器
    
    用于选择守卫、击杀等目标
    """
    
    def __init__(
        self,
        config: BaseConfig,
        trust_analyzer: TrustAnalyzer
    ):
        """
        初始化决策器
        
        Args:
            config: 配置对象
            trust_analyzer: 信任分析器
        """
        super().__init__(config)
        self.trust_analyzer = trust_analyzer
    
    def decide(
        self,
        candidates: List[str],
        strategy: str = "protect_high_trust",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        选择目标
        
        Args:
            candidates: 候选人列表
            strategy: 策略("protect_high_trust", "attack_high_trust"等)
            context: 上下文信息
            
        Returns:
            决策结果字典
        """
        try:
            if not candidates:
                return self._get_default_result()
            
            context = context or {}
            
            # 根据策略选择目标
            if strategy == "protect_high_trust":
                target = self._select_high_trust(candidates)
            elif strategy == "attack_high_trust":
                target = self._select_high_trust(candidates)
            elif strategy == "attack_low_trust":
                target = self._select_low_trust(candidates)
            else:
                target = candidates[0]  # 默认选第一个
            
            reasoning = f"选择{target},策略: {strategy}"
            
            return {
                'action': 'select',
                'target': target,
                'reasoning': reasoning,
                'confidence': 0.7
            }
            
        except Exception as e:
            return self._handle_error(e, "decide")
    
    def _select_high_trust(self, candidates: List[str]) -> str:
        """选择信任度最高的"""
        scores = {
            c: self.trust_analyzer.get_score(c)
            for c in candidates
        }
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _select_low_trust(self, candidates: List[str]) -> str:
        """选择信任度最低的"""
        scores = {
            c: self.trust_analyzer.get_score(c)
            for c in candidates
        }
        return min(scores.items(), key=lambda x: x[1])[0]
