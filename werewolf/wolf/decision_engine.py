"""
Wolf Decision Engine - 狼人决策引擎

提供击杀和投票决策逻辑，符合企业级标准
"""

from typing import Dict, List, Tuple, Optional
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.wolf.config import WolfConfig
from werewolf.optimization.utils.safe_math import safe_divide


class WolfDecisionEngine(BaseDecisionMaker):
    """
    狼人决策引擎
    
    职责:
    1. 基于威胁等级和可突破值决定击杀目标
    2. 基于威胁等级和队友关系决定投票目标
    3. 提供决策推理过程
    
    Attributes:
        config: Wolf配置对象
        memory_dao: 内存数据访问对象
    """
    
    def __init__(self, config: WolfConfig, memory_dao):
        """
        初始化决策引擎
        
        Args:
            config: Wolf配置对象
            memory_dao: 内存数据访问对象
        """
        super().__init__(config)
        self.memory_dao = memory_dao
    
    def decide(self, decision_type: str, candidates: List[str], context: Dict) -> Dict[str, any]:
        """
        执行决策(BaseDecisionMaker要求的接口)
        
        Args:
            decision_type: 决策类型("kill"或"vote")
            candidates: 候选人列表
            context: 决策上下文
            
        Returns:
            决策结果字典,包含:
            - action: str, 行动类型
            - target: str, 目标玩家
            - reasoning: str, 推理过程
            - confidence: float, 置信度(0-1)
        """
        try:
            if decision_type == "kill":
                target, reason, score = self.decide_kill_target(candidates, context)
            elif decision_type == "vote":
                target, reason, score = self.decide_vote_target(candidates, context)
            else:
                self.logger.error(f"Unknown decision type: {decision_type}")
                return self._get_default_result()
            
            return {
                'action': decision_type,
                'target': target,
                'reasoning': reason,
                'confidence': score
            }
        except Exception as e:
            return self._handle_error(e, f"decide_{decision_type}")
    
    def decide_kill_target(self, candidates: List[str], context: Dict) -> Tuple[str, str, float]:
        """
        决定击杀目标 - 集成ML预测
        
        Args:
            candidates: 候选人列表
            context: 决策上下文,包含:
                - teammates: List[str], 队友列表
                - threat_levels: Dict[str, int], 威胁等级
                - breakthrough_values: Dict[str, int], 可突破值
                - identified_roles: Dict[str, str], 已识别角色
                - ml_predictions: Dict[str, float], ML预测的狼人概率（可选）
            
        Returns:
            Tuple[target, reason, confidence]:
            - target: str, 目标玩家名称
            - reason: str, 决策理由
            - confidence: float, 置信度(0-1)
        """
        if not candidates:
            self.logger.warning("[KILL] No candidates provided")
            return "", "No candidates", 0.0
        
        teammates = context.get("teammates", [])
        # 过滤掉队友
        valid_candidates = [c for c in candidates if c not in teammates]
        
        if not valid_candidates:
            self.logger.warning("[KILL] No valid kill targets (all teammates)")
            return "", "All teammates", 0.0
        
        # 选择威胁最高的
        threat_levels = context.get("threat_levels", {})
        identified_roles = context.get("identified_roles", {})
        ml_predictions = context.get("ml_predictions", {})
        
        # 计算每个候选人的击杀分数
        scores = {}
        for candidate in valid_candidates:
            base_threat = threat_levels.get(candidate, 50)
            role = identified_roles.get(candidate, "unknown")
            
            # 角色加成
            role_bonus = self._get_role_threat_bonus(role)
            
            # ML预测加成（如果可用）
            ml_bonus = 0
            if ml_predictions and candidate in ml_predictions:
                # ML预测为好人的概率越高，威胁越高（因为我们是狼人）
                good_prob = 1 - ml_predictions[candidate]
                ml_bonus = good_prob * 20  # 最多加20分
                self.logger.debug(f"[KILL] {candidate} ML bonus: {ml_bonus:.1f} (good_prob: {good_prob:.3f})")
            
            final_score = min(100, base_threat + role_bonus + ml_bonus)
            scores[candidate] = final_score
        
        # 选择分数最高的
        target = max(scores.items(), key=lambda x: x[1])[0]
        score = scores[target]
        
        reason = self._generate_kill_reason(target, score, context)
        confidence = safe_divide(score, 100.0, default=0.5)
        
        self.logger.info(f"[KILL] {target}: {score:.1f}/100 - {reason}")
        return target, reason, confidence
    
    def decide_vote_target(self, candidates: List[str], context: Dict) -> Tuple[str, str, float]:
        """
        决定投票目标 - 集成ML预测
        
        Args:
            candidates: 候选人列表
            context: 决策上下文（包含ml_predictions）
            
        Returns:
            Tuple[target, reason, confidence]:
            - target: str, 目标玩家名称
            - reason: str, 决策理由
            - confidence: float, 置信度(0-1)
        """
        if not candidates:
            self.logger.warning("[VOTE] No candidates provided")
            return "", "No candidates", 0.0
        
        teammates = context.get("teammates", [])
        ml_predictions = context.get("ml_predictions", {})
        
        # 优先投非队友
        non_teammates = [c for c in candidates if c not in teammates]
        
        if not non_teammates:
            # 如果都是队友，投威胁最低的队友
            threat_levels = context.get("threat_levels", {})
            scores = {c: threat_levels.get(c, 50) for c in candidates}
            target = min(scores.items(), key=lambda x: x[1])[0]
            score = scores[target]
            reason = f"Teammate with lowest threat (threat: {score:.1f})"
            confidence = safe_divide(score, 100.0, default=0.5)
            self.logger.info(f"[VOTE] {target}: {score:.1f}/100 - {reason}")
            return target, reason, confidence
        
        # 投威胁最高的非队友（结合ML预测）
        threat_levels = context.get("threat_levels", {})
        scores = {}
        
        for candidate in non_teammates:
            base_threat = threat_levels.get(candidate, 50)
            
            # ML预测加成
            ml_bonus = 0
            if ml_predictions and candidate in ml_predictions:
                # ML预测为好人的概率越高，越应该投票（因为我们是狼人）
                good_prob = 1 - ml_predictions[candidate]
                ml_bonus = good_prob * 15  # 最多加15分
                self.logger.debug(f"[VOTE] {candidate} ML bonus: {ml_bonus:.1f}")
            
            scores[candidate] = base_threat + ml_bonus
        
        target = max(scores.items(), key=lambda x: x[1])[0]
        score = scores[target]
        
        reason = f"Non-teammate with highest threat (threat: {score:.1f})"
        if ml_predictions and target in ml_predictions:
            reason += f", ML good_prob: {(1-ml_predictions[target]):.2f}"
        
        confidence = min(1.0, safe_divide(score, 100.0, default=0.5))
        
        self.logger.info(f"[VOTE] {target}: {score:.1f}/100 - {reason}")
        return target, reason, confidence
    
    def _get_role_threat_bonus(self, role: str) -> int:
        """
        获取角色威胁加成
        
        Args:
            role: 角色类型
            
        Returns:
            威胁加成分数
        """
        role_bonuses = {
            "seer": self.config.ROLE_THREAT_SEER - self.config.trust_score_default,
            "likely_seer": self.config.ROLE_THREAT_LIKELY_SEER - self.config.trust_score_default,
            "witch": self.config.ROLE_THREAT_WITCH - self.config.trust_score_default,
            "guard": self.config.ROLE_THREAT_GUARD - self.config.trust_score_default,
            "strong_villager": self.config.ROLE_THREAT_STRONG_VILLAGER - self.config.trust_score_default,
            "hunter": self.config.ROLE_THREAT_HUNTER - self.config.trust_score_default,
        }
        return role_bonuses.get(role, 0)
    
    def _generate_kill_reason(self, target: str, score: float, context: Dict) -> str:
        """
        生成击杀理由
        
        Args:
            target: 目标玩家
            score: 击杀分数
            context: 决策上下文
            
        Returns:
            击杀理由字符串
        """
        threat_levels = context.get("threat_levels", {})
        identified_roles = context.get("identified_roles", {})
        
        threat = threat_levels.get(target, 50)
        role = identified_roles.get(target, "unknown")
        
        reasons = []
        
        # 角色相关理由
        if role in ["seer", "likely_seer"]:
            reasons.append("Identified as Seer")
        elif role == "witch":
            reasons.append("Identified as Witch")
        elif role == "guard":
            reasons.append("Identified as Guard")
        elif role == "strong_villager":
            reasons.append("Strong analytical player")
        
        # 威胁等级理由
        if threat >= self.config.THREAT_VERY_HIGH:
            reasons.append(f"Very high threat ({threat:.0f})")
        elif threat >= self.config.THREAT_HIGH:
            reasons.append(f"High threat ({threat:.0f})")
        elif threat >= self.config.THREAT_MEDIUM:
            reasons.append(f"Medium threat ({threat:.0f})")
        
        return ", ".join(reasons) if reasons else f"Threat level: {threat:.0f}"
    
    def _get_default_result(self) -> Dict[str, any]:
        """
        获取默认决策结果
        
        Returns:
            默认决策结果字典
        """
        return {
            'action': 'none',
            'target': None,
            'reasoning': 'Decision failed, using default action',
            'confidence': 0.0
        }
