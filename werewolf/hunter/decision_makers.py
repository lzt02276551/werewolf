# -*- coding: utf-8 -*-
"""
猎人代理人决策器模块
实现各种决策器，使用策略模式
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.common.utils import DataValidator
from .config import HunterConfig

if TYPE_CHECKING:
    from .analyzers import WolfProbabilityCalculator, ThreatLevelAnalyzer, MemoryDAO
else:
    # 运行时导入
    WolfProbabilityCalculator = None
    ThreatLevelAnalyzer = None
    MemoryDAO = None


# ==================== 开枪决策器 ====================

class ShootDecisionMaker(BaseDecisionMaker):
    """开枪决策器"""
    
    def __init__(
        self,
        config: HunterConfig,
        wolf_prob_calculator: WolfProbabilityCalculator,
        threat_analyzer: ThreatLevelAnalyzer,
        memory_dao
    ):
        super().__init__(config)
        self.wolf_prob_calculator = wolf_prob_calculator
        self.threat_analyzer = threat_analyzer
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    def decide(
        self, 
        candidates: List[str], 
        my_name: str, 
        game_phase: str = "mid",
        current_day: int = 1,
        alive_count: int = 12
    ) -> Tuple[str, str, Dict[str, float]]:
        """
        决定开枪目标
        
        Args:
            candidates: 候选人列表
            my_name: 自己的名称
            game_phase: 游戏阶段
            current_day: 当前天数
            alive_count: 存活人数
        
        Returns:
            (目标, 理由, 所有候选人分数)
        """
        # 验证输入
        if not isinstance(candidates, list):
            raise ValueError(f"Invalid candidates type: {type(candidates)}, expected list")
        
        if not candidates:
            return ("Do Not Shoot", "No candidates provided", {})
        
        # 过滤有效候选人
        dead_players = self.memory_dao.get_dead_players()
        if not isinstance(dead_players, set):
            dead_players = set(dead_players) if dead_players else set()
        
        valid_candidates = [
            c for c in candidates 
            if c != my_name and c not in dead_players and self.validator.validate_player_name(c)
        ]
        
        if not valid_candidates:
            return ("Do Not Shoot", "No valid targets after filtering", {})
        
        # 特殊情况处理
        special_target, special_reason = self._handle_special_situations(valid_candidates)
        if special_target:
            logger.info(f"[SHOOT SPECIAL] {special_target}: {special_reason}")
            return (special_target, special_reason, {special_target: 200.0})
        
        # 计算每个候选人的开枪分数
        shoot_scores = {}
        confidence_scores = {}
        
        for candidate in valid_candidates:
            # 计算狼人概率
            wolf_prob = self.wolf_prob_calculator.calculate(candidate, game_phase)
            
            # 计算威胁等级
            threat_level = self.threat_analyzer.analyze(candidate, current_day, alive_count)
            
            # 计算置信度
            confidence = self._calculate_shoot_confidence(candidate)
            
            # 计算风险惩罚
            risk_penalty = self._calculate_shoot_risk_penalty(candidate)
            
            # 综合评分
            base_score = wolf_prob * 70 + threat_level * 20
            final_score = base_score * confidence - risk_penalty
            
            shoot_scores[candidate] = final_score
            confidence_scores[candidate] = confidence
            
            logger.debug(
                f"[SHOOT EVAL] {candidate}: Wolf={wolf_prob:.2f}, Threat={threat_level:.2f}, "
                f"Conf={confidence:.2f}, Risk=-{risk_penalty:.1f}, Score={final_score:.1f}"
            )
        
        # 选择最高分
        if not shoot_scores:
            return ("Do Not Shoot", "No valid scores calculated", {})
        
        sorted_candidates = sorted(shoot_scores.items(), key=lambda x: x[1], reverse=True)
        target = sorted_candidates[0][0]
        score = sorted_candidates[0][1]
        confidence = confidence_scores[target]
        
        # 置信度和分数阈值检查（使用配置常量）
        min_confidence = self.config.shoot_confidence_threshold  # 0.4
        min_score = self.config.vote_score_threshold  # 35.0
        
        if confidence < min_confidence and score < min_score:
            return ("Do Not Shoot", f"Low confidence ({confidence:.2%}) and score ({score:.1f})", shoot_scores)
        
        if score < min_score:
            return ("Do Not Shoot", f"All scores below threshold (highest: {score:.1f})", shoot_scores)
        
        # 生成理由
        reason = self._generate_shoot_reason(target, score, confidence)
        
        self.log_decision(target, reason)
        return (target, reason, shoot_scores)
    
    def _handle_special_situations(self, candidates: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        处理特殊情况（与SKILL_PROMPT中的决策树一致）
        
        特殊情况包括：
        A) 预言家查杀的狼人还活着 → 优先射击（95%狼概率）
        B) 假预言家 vs 真预言家 → 射击假预言家（80%狼概率）
        C) 错误投票淘汰（被冤枉） → 射击投票领袖
        D) 狼王嫌疑 → 评估是否射击（狼王会反击）
        E) 多个高概率目标 → 比较威胁等级
        F) 所有候选人低概率 → 考虑放弃射击
        
        Args:
            candidates: 候选人列表
            
        Returns:
            (特殊目标, 特殊原因) 或 (None, None)
        """
        # A) 预言家查杀的狼人
        seer_checks = self.memory_dao.get("seer_checks") or {}
        for player, result in seer_checks.items():
            if player in candidates:
                # 检查是否被预言家验证为狼人
                is_wolf = False
                if isinstance(result, dict):
                    is_wolf = result.get("is_wolf", False)
                elif isinstance(result, str):
                    is_wolf = "wolf" in result.lower()
                
                if is_wolf:
                    return (player, f"Seer identified {player} as wolf (95% confidence)")
        
        # C) 错误投票淘汰 - 射击投票领袖
        # 获取最近的投票记录，找出谁推动了对我的投票
        voting_history = self.memory_dao.get_voting_history()
        my_name = self.memory_dao.get_my_name()
        
        # 分析投票领袖（谁最积极地推动投票）
        if voting_history and my_name:
            vote_leaders = self._identify_vote_leaders(voting_history, my_name, candidates)
            if vote_leaders:
                leader = vote_leaders[0]
                return (leader, f"Vote leader who pushed for my elimination (likely wolf)")
        
        return (None, None)
    
    def _identify_vote_leaders(
        self, 
        voting_history: Dict[str, List[str]], 
        target: str, 
        candidates: List[str]
    ) -> List[str]:
        """
        识别投票领袖
        
        Args:
            voting_history: 投票历史
            target: 被投票的目标
            candidates: 候选人列表
            
        Returns:
            投票领袖列表（按积极程度排序）
        """
        vote_counts = {}
        
        for voter, votes in voting_history.items():
            if voter in candidates and isinstance(votes, list):
                # 统计投票给目标的次数
                target_votes = sum(1 for v in votes if v == target)
                if target_votes > 0:
                    vote_counts[voter] = target_votes
        
        # 按投票次数排序
        sorted_leaders = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        return [leader for leader, _ in sorted_leaders]
    
    def _calculate_shoot_confidence(self, player: str) -> float:
        """计算开枪置信度（0.0-1.0）"""
        confidence = 0.5
        
        # 投票数据样本量
        voting_results = self.memory_dao.get_voting_results()
        if player in voting_results:
            results = voting_results[player]
            if isinstance(results, list):
                sample_count = len([r for r in results if self.validator.validate_voting_record(r)])
                confidence += min(0.3, sample_count * 0.06)
        
        # 发言数据样本量
        speech_history = self.memory_dao.get_speech_history()
        if player in speech_history:
            speech_count = len(speech_history[player])
            confidence += min(0.15, speech_count * 0.03)
        
        # 强证据
        injection_attempts = self.memory_dao.get_injection_attempts()
        false_quotations = self.memory_dao.get_false_quotations()
        
        # 类型安全检查
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not a list: {type(injection_attempts)}")
            injection_attempts = []
        
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not a list: {type(false_quotations)}")
            false_quotations = []
        
        has_strong_evidence = (
            any(isinstance(att, dict) and att.get("player") == player for att in injection_attempts) or
            any(isinstance(fq, dict) and fq.get("accuser") == player for fq in false_quotations)
        )
        
        if has_strong_evidence:
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _calculate_shoot_risk_penalty(self, player: str) -> float:
        """计算开枪风险惩罚（0-50）"""
        penalty = 0.0
        
        speech_history = self.memory_dao.get_speech_history()
        
        if player in speech_history:
            speeches = speech_history[player]
            combined_speech = " ".join(speeches).lower()
            
            if "checked" in combined_speech or "verified" in combined_speech:
                if "seer" in combined_speech or "i am" in combined_speech:
                    penalty += 30
                else:
                    penalty += 20
            
            if "saved" in combined_speech or "poison" in combined_speech:
                if "witch" in combined_speech or "i am" in combined_speech:
                    penalty += 25
                else:
                    penalty += 15
            
            if "protected" in combined_speech or "guard" in combined_speech:
                penalty += 15
        
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(player, 50)
        
        if trust_score >= 80:
            penalty += 20
        elif trust_score >= 70:
            penalty += 12
        
        return min(50, penalty)
    
    def _generate_shoot_reason(self, target: str, score: float, confidence: float) -> str:
        """生成开枪理由"""
        wolf_prob = self.wolf_prob_calculator.calculate(target)
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(target, 50)
        
        reasons = []
        
        if score >= 80:
            reasons.append(f"极高狼人概率 (score: {score:.0f})")
        elif score >= 60:
            reasons.append(f"高狼人概率(score: {score:.0f})")
        else:
            reasons.append(f"最高狼人概率(score: {score:.0f})")
        
        reasons.append(f"wolf={wolf_prob:.0%}")
        reasons.append(f"trust={trust_score:.0f}")
        reasons.append(f"conf={confidence:.0%}")
        
        injection_attempts = self.memory_dao.get_injection_attempts()
        false_quotations = self.memory_dao.get_false_quotations()
        
        # 类型安全检查
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not a list: {type(injection_attempts)}")
            injection_attempts = []
        
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not a list: {type(false_quotations)}")
            false_quotations = []
        
        if any(isinstance(att, dict) and att.get("player") == target for att in injection_attempts):
            reasons.append("注入攻击")
        
        if any(isinstance(fq, dict) and fq.get("accuser") == target for fq in false_quotations):
            reasons.append("虚假引用")
        
        sheriff = self.memory_dao.get_sheriff()
        if sheriff == target:
            reasons.append("Sheriff(高威胁)")
        
        return ", ".join(reasons)




