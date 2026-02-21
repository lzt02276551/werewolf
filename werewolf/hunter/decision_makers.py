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


def safe_execute(default_return=None):
    """装饰器：安全执行函数，捕获异常并返回默认值"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default_return if default_return is not None else None
        return wrapper
    return decorator


# ==================== 投票决策器 ====================

class VoteDecisionMaker(BaseDecisionMaker):
    """投票决策器"""
    
    def __init__(
        self,
        config: HunterConfig,
        wolf_prob_calculator,
        threat_analyzer,
        memory_dao
    ):
        super().__init__(config)
        self.wolf_prob_calculator = wolf_prob_calculator
        self.threat_analyzer = threat_analyzer
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    @safe_execute(default_return=("No.1", "Error occurred", {}))
    def decide(self, candidates: List[str], my_name: str, game_phase: str = "mid") -> Tuple[str, str, Dict[str, float]]:
        """
        决定投票目标
        
        Args:
            candidates: 候选人列表
            my_name: 自己的名称
            game_phase: 游戏阶段
        
        Returns:
            (目标, 理由, 所有候选人分数)
        """
        # 过滤有效候选人（增强类型验证）
        if not isinstance(candidates, list):
            logger.error(f"[VOTE] Invalid candidates type: {type(candidates)}, expected list")
            return (my_name, "Invalid candidates type", {})
        
        valid_candidates = [c for c in candidates if c != my_name and self.validator.validate_player_name(c)]
        
        if not valid_candidates:
            fallback = candidates[0] if candidates else my_name
            return (fallback, "No valid candidates", {})
        
        # 计算每个候选人的投票分数
        vote_scores = {}
        for candidate in valid_candidates:
            score = self._calculate_vote_score(candidate, game_phase)
            vote_scores[candidate] = score
        
        # 选择最高分
        sorted_candidates = sorted(vote_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_candidates:
            fallback = valid_candidates[0] if valid_candidates else my_name
            return (fallback, "No scores calculated", {})
        
        target = sorted_candidates[0][0]
        score = sorted_candidates[0][1]
        
        # 生成理由
        reason = self._generate_vote_reason(target, score)
        
        self.log_decision(target, reason)
        return (target, reason, vote_scores)
    
    def _calculate_vote_score(self, player: str, game_phase: str) -> float:
        """
        计算投票分数（企业级实现）
        
        Returns:
            投票分数（0-200+）
        """
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(player, 50)
        
        # 基础分：非线性映射
        if trust_score <= 20:
            base_score = 80 + (20 - trust_score) * 3
        elif trust_score <= 40:
            base_score = 60 + (40 - trust_score) * 1
        elif trust_score <= 60:
            base_score = 40 + (60 - trust_score) * 1
        else:
            base_score = max(0, 40 - (trust_score - 60) * 1)
        
        # 修正值
        wolf_prob = self.wolf_prob_calculator.calculate(player, game_phase)
        wolf_modifier = wolf_prob * 50  # 狼人概率贡献0-50分
        
        # 注入攻击和虚假引用（增强类型安全）
        injection_attempts = self.memory_dao.get_injection_attempts()
        false_quotations = self.memory_dao.get_false_quotations()
        
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not a list: {type(injection_attempts)}")
            injection_attempts = []
        
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not a list: {type(false_quotations)}")
            false_quotations = []
        
        injection_count = sum(
            1 for att in injection_attempts 
            if isinstance(att, dict) and att.get("player") == player
        )
        false_quote_count = sum(
            1 for fq in false_quotations 
            if isinstance(fq, dict) and fq.get("accuser") == player
        )
        
        injection_modifier = min(50, injection_count * 30)
        false_quote_modifier = min(40, false_quote_count * 25)
        
        # 社交孤立度
        isolation_score = self._calculate_isolation_score(player)
        isolation_modifier = isolation_score * 15
        
        # 总分
        total_score = base_score + wolf_modifier + injection_modifier + false_quote_modifier + isolation_modifier
        
        # 风险惩罚
        risk_penalty = self._calculate_vote_risk_penalty(player)
        total_score -= risk_penalty
        
        logger.debug(
            f"[VOTE SCORE] {player}: Base={base_score:.1f}, Wolf={wolf_modifier:.1f}, "
            f"Inject={injection_modifier:.1f}, Quote={false_quote_modifier:.1f}, "
            f"Risk=-{risk_penalty:.1f}, Total={total_score:.1f}"
        )
        
        return total_score
    
    def _calculate_isolation_score(self, player: str) -> float:
        """计算社交孤立度（0.0-1.0）"""
        speech_history = self.memory_dao.get_speech_history()
        
        mentioned_count = sum(
            1 for p, speeches in speech_history.items()
            if p != player
            for s in speeches
            if player in s
        )
        
        mentions_others = 0
        if player in speech_history:
            mentions_others = sum(s.count("No.") for s in speech_history[player])
        
        total_interaction = mentioned_count + mentions_others
        
        if total_interaction == 0:
            return 1.0
        elif total_interaction <= 2:
            return 0.7
        elif total_interaction <= 5:
            return 0.4
        else:
            return 0.1
    
    def _calculate_vote_risk_penalty(self, player: str) -> float:
        """计算投票风险惩罚（0-30）"""
        penalty = 0.0
        
        speech_history = self.memory_dao.get_speech_history()
        
        if player in speech_history:
            speeches = speech_history[player]
            combined_speech = " ".join(speeches).lower()
            
            if "checked" in combined_speech or "verified" in combined_speech or "seer" in combined_speech:
                penalty += 15
            
            if "saved" in combined_speech or "poison" in combined_speech or "witch" in combined_speech:
                penalty += 15
            
            if "protected" in combined_speech or "guard" in combined_speech:
                penalty += 10
        
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(player, 50)
        
        if trust_score >= 75:
            penalty += 10
        
        return min(30, penalty)
    
    def _generate_vote_reason(self, target: str, score: float) -> str:
        """生成投票理由"""
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(target, 50)
        
        reasons = []
        
        if score >= 120:
            reasons.append(f"Extremely suspicious (score: {score:.0f})")
        elif score >= 90:
            reasons.append(f"Highly suspicious (score: {score:.0f})")
        elif score >= 60:
            reasons.append(f"Suspicious (score: {score:.0f})")
        else:
            reasons.append(f"Most suspicious (score: {score:.0f})")
        
        if trust_score < 30:
            reasons.append("very low trust")
        
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
            reasons.append("injection attack")
        
        if any(isinstance(fq, dict) and fq.get("accuser") == target for fq in false_quotations):
            reasons.append("false quotation")
        
        return ", ".join(reasons)


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
    
    @safe_execute(default_return=("Do Not Shoot", "Error occurred", {}))
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
        # 过滤有效候选人（增强类型验证）
        if not isinstance(candidates, list):
            logger.error(f"[SHOOT] Invalid candidates type: {type(candidates)}, expected list")
            return ("Do Not Shoot", "Invalid candidates type", {})
        
        dead_players = self.memory_dao.get_dead_players()
        if not isinstance(dead_players, set):
            logger.warning(f"[SHOOT] dead_players is not a set, converting: {type(dead_players)}")
            dead_players = set(dead_players) if dead_players else set()
        
        valid_candidates = [
            c for c in candidates 
            if c != my_name and c not in dead_players and self.validator.validate_player_name(c)
        ]
        
        if not valid_candidates:
            return ("Do Not Shoot", "No valid targets", {})
        
        # 特殊情况处理
        special_target, special_reason = self._handle_special_situations(valid_candidates)
        if special_target:
            return (special_target, special_reason, {special_target: 200.0})
        
        # 计算每个候选人的开枪分数
        shoot_scores = {}
        confidence_scores = {}
        
        for candidate in valid_candidates:
            wolf_prob = self.wolf_prob_calculator.calculate(candidate, game_phase)
            threat_level = self.threat_analyzer.analyze(candidate, current_day, alive_count)
            confidence = self._calculate_shoot_confidence(candidate)
            risk_penalty = self._calculate_shoot_risk_penalty(candidate)
            
            base_score = wolf_prob * 70 + threat_level * 20
            final_score = base_score * confidence - risk_penalty
            
            shoot_scores[candidate] = final_score
            confidence_scores[candidate] = confidence
            
            logger.debug(
                f"[SHOOT EVAL] {candidate}: Wolf={wolf_prob:.2f}, Threat={threat_level:.2f}, "
                f"Conf={confidence:.2f}, Risk=-{risk_penalty:.1f}, Score={final_score:.1f}"
            )
        
        # 选择最高分
        sorted_candidates = sorted(shoot_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_candidates:
            return ("Do Not Shoot", "No valid targets", {})
        
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
        """处理特殊情况"""
        # TODO: 实现特殊情况处理（预言家查杀、投票领袖等）
        return (None, None)
    
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


# ==================== 警长选举决策器 ====================

class SheriffElectionDecisionMaker(BaseDecisionMaker):
    """警长选举决策器"""
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
    
    @safe_execute(default_return=(False, "Error occurred"))
    def decide(self, game_situation: str, current_round: int) -> Tuple[bool, str]:
        """
        决定是否竞选警长
        
        Args:
            game_situation: 游戏局势("advantage", "balanced", "disadvantage")
            current_round: 当前回合数
        
        Returns:
            (是否竞选, 理由)
        """
        score = 0
        reasons = []
        
        can_shoot = self.memory_dao.get_can_shoot()
        if can_shoot:
            score += 30
            reasons.append("can shoot (strong deterrence)")
        else:
            score += 10
            reasons.append("cannot shoot but can build trust")
        
        if game_situation == "advantage":
            score += 20
            reasons.append("good faction has advantage")
        elif game_situation == "balanced":
            score += 15
            reasons.append("balanced situation")
        else:
            score += 5
            reasons.append("disadvantage - need leadership")
        
        if current_round <= 2:
            score -= 30
            reasons.append("early game - stay hidden")
        
        if 3 <= current_round <= 5:
            score += 20
            reasons.append("mid game - good timing")
        
        should_run = score >= 30
        reason = f"Score: {score} - " + ", ".join(reasons)
        
        self.log_decision(should_run, reason)
        return (should_run, reason)


# ==================== 警长投票决策器 ====================

class SheriffVoteDecisionMaker(BaseDecisionMaker):
    """警长投票决策器"""
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    @safe_execute(default_return=("No.1", "Error occurred"))
    def decide(self, candidates: List[str]) -> Tuple[str, str]:
        """
        决定投票给哪个警长候选人
        
        Args:
            candidates: 候选人列表
        
        Returns:
            (目标, 理由)
        """
        if not candidates:
            return ("No.1", "No candidates available")
        
        trust_scores = self.memory_dao.get_trust_scores()
        
        # 计算综合分数
        candidate_scores = {}
        for candidate in candidates:
            score = 0
            
            # 信任分数（50%权重）
            trust = trust_scores.get(candidate, 50)
            score += trust * 0.5
            
            # 发言质量（20%权重）
            speech_history = self.memory_dao.get_speech_history()
            if candidate in speech_history and len(speech_history[candidate]) > 0:
                from werewolf.optimization.utils.safe_math import safe_divide
                avg_length = safe_divide(
                    sum(len(s) for s in speech_history[candidate]), 
                    len(speech_history[candidate]), 
                    default=100
                )
                if avg_length > 200:
                    score += 20 * 0.2
                elif avg_length > 100:
                    score += 15 * 0.2
                else:
                    score += 5 * 0.2
            
            # 投票准确性（20%权重）
            voting_results = self.memory_dao.get_voting_results()
            if candidate in voting_results:
                results = voting_results[candidate]
                if isinstance(results, list) and len(results) >= 2:
                    valid_results = [r for r in results if self.validator.validate_voting_record(r)]
                    if valid_results:
                        from werewolf.optimization.utils.safe_math import safe_divide
                        wolf_votes = sum(1 for _, was_wolf in valid_results if was_wolf)
                        accuracy_rate = safe_divide(wolf_votes, len(valid_results), default=0.5)
                        
                        if accuracy_rate >= 0.7:
                            score += 20 * 0.2
                        elif accuracy_rate >= 0.5:
                            score += 10 * 0.2
            
            # 领导力指标（10%权重）
            if candidate in speech_history and len(speech_history[candidate]) >= 3:
                score += 10 * 0.1
            
            candidate_scores[candidate] = score
        
        # 选择最高分
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_candidates:
            return (candidates[0], "No scores calculated")
        
        target = sorted_candidates[0][0]
        score = sorted_candidates[0][1]
        
        # 生成理由
        trust = trust_scores.get(target, 50)
        reasons = []
        
        if score >= 70:
            reasons.append(f"Excellent candidate (score: {score:.1f})")
        elif score >= 50:
            reasons.append(f"Good candidate (score: {score:.1f})")
        else:
            reasons.append(f"Best among candidates (score: {score:.1f})")
        
        if trust >= 70:
            reasons.append(f"high trust ({trust})")
        
        reason = ", ".join(reasons)
        
        self.log_decision(target, reason)
        return (target, reason)
