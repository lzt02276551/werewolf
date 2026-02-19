# -*- coding: utf-8 -*-
"""
平民代理人决策器模块
实现各种决策功能：投票、警长选举、警长投票等
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.common.utils import DataValidator
from .config import VillagerConfig
from .analyzers import TrustScoreCalculator, VotingPatternAnalyzer
import re


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


class VoteDecisionMaker(BaseDecisionMaker):
    """投票决策器"""
    
    def __init__(self, config: VillagerConfig, trust_calculator: TrustScoreCalculator,
                 pattern_analyzer: VotingPatternAnalyzer):
        super().__init__(config)
        self.trust_calculator = trust_calculator
        self.pattern_analyzer = pattern_analyzer
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'vote',
            'target': 'No.1',
            'reasoning': 'No candidates available',
            'confidence': 0.0,
            'scores': {}
        }
    
    @safe_execute(default_return=("No.1", "No candidates available", {}))
    def decide(self, candidates: List[str], my_name: str, context: Dict) -> Tuple[str, str, Dict]:
        """
        投票目标选择决策
        
        Returns:
            (target, reason, scores_dict)
        """
        # 边界检查
        if not candidates or not isinstance(candidates, list):
            logger.warning(f"Invalid candidates: {candidates}")
            return (my_name if my_name else "No.1", "No candidates available", {})
        
        if not DataValidator.validate_player_name(my_name):
            logger.warning(f"Invalid my_name: {my_name}")
            return (candidates[0] if candidates else "No.1", "Invalid my_name", {})
        
        valid_candidates = [c for c in candidates if c != my_name]
        if not valid_candidates:
            return (candidates[0], "No valid candidates", {})
        
        # Calculate vote priority for each candidate
        vote_scores = {}
        for candidate in valid_candidates:
            score = self._calculate_vote_priority(candidate, context)
            vote_scores[candidate] = score
        
        # Sort and select highest score
        sorted_candidates = sorted(vote_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_candidates:
            return (valid_candidates[0] if valid_candidates else my_name, "No scores calculated", {})
        
        target = sorted_candidates[0][0]
        score = sorted_candidates[0][1]
        
        # Generate reason
        reason = self._generate_vote_reason(target, score, context)
        
        logger.info(f"[DECISION TREE] Vote target: {target} (score: {score:.1f})")
        return (target, reason, vote_scores)
    
    def _calculate_vote_priority(self, player_name: str, context: Dict) -> float:
        """计算投票优先级分数"""
        # 1. 基础优先级：基于信任分数
        trust_score = self.trust_calculator.analyze(player_name, context)
        
        # 非线性转换
        normalized_trust = trust_score / 100.0
        base_priority = 100.0 * (1.0 - normalized_trust)
        
        # 对极端值进行增强
        if trust_score < -50:
            base_priority += (abs(trust_score) - 50) * 0.5
        elif trust_score > 50:
            base_priority -= (trust_score - 50) * 0.5
        
        # 2. 投票特定加成
        vote_bonus = 0.0
        
        player_data_dict = DataValidator.safe_get_dict(context.get("player_data"))
        player_data = DataValidator.safe_get_dict(player_data_dict.get(player_name))
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        
        current_day = DataValidator.safe_get_int(game_state.get("current_day", 0))
        alive_count = DataValidator.safe_get_int(game_state.get("alive_count", 12), 12)
        
        # A. 紧急程度加成
        urgency_multiplier = 1.0
        if alive_count <= 6:
            urgency_multiplier = self.config.VOTE_URGENCY_MULTIPLIER_ENDGAME
            if trust_score < 0:
                urgency_bonus = abs(trust_score) * 0.4
                vote_bonus += urgency_bonus
        elif alive_count <= 8:
            urgency_multiplier = self.config.VOTE_URGENCY_MULTIPLIER_MIDLATE
            if trust_score < -20:
                urgency_bonus = abs(trust_score + 20) * 0.2
                vote_bonus += urgency_bonus
        
        # B. 早期注入攻击加成
        if current_day <= 2 and player_data.get("malicious_injection"):
            injection_count = DataValidator.safe_get_int(player_data.get("injection_count", 1), 1)
            early_injection_bonus = 35 + min(20, injection_count * 12)
            vote_bonus += early_injection_bonus
        
        # C. 预言家查杀加成
        seer_checks = DataValidator.safe_get_dict(context.get("seer_checks"))
        if player_name in seer_checks:
            result = seer_checks[player_name]
            if isinstance(result, str):
                if "wolf" in result.lower():
                    vote_bonus += 200
                else:
                    vote_bonus -= 200
        
        # D. 投票模式加成
        vote_pattern = self.pattern_analyzer.analyze(player_name, context)
        pattern_bonus = 0.0
        
        if vote_pattern == "protect_wolf":
            pattern_bonus = 28
        elif vote_pattern == "charge":
            pattern_bonus = 18
        elif vote_pattern == "swing":
            pattern_bonus = 12
        elif vote_pattern == "abstain":
            pattern_bonus = 15
        elif vote_pattern == "accurate":
            pattern_bonus = -22
        
        pattern_bonus *= urgency_multiplier
        vote_bonus += pattern_bonus
        
        # 3. 计算最终优先级
        final_priority = base_priority + vote_bonus
        final_priority = max(final_priority, 0.0)
        
        logger.debug(f"[VOTE PRIORITY] {player_name}: "
                    f"Base={base_priority:.1f} (trust={trust_score:.1f}), "
                    f"Bonus={vote_bonus:.1f}, Urgency={urgency_multiplier:.1f}x, "
                    f"Final={final_priority:.1f}")
        
        return final_priority
    
    def _generate_vote_reason(self, target: str, score: float, context: Dict) -> str:
        """生成投票理由"""
        trust_score = self.trust_calculator.analyze(target, context)
        reasons = []
        
        if score >= 150:
            reasons.append(f"Extremely suspicious (score: {score:.0f})")
        elif score >= 120:
            reasons.append(f"Highly suspicious (score: {score:.0f})")
        elif score >= 90:
            reasons.append(f"Suspicious (score: {score:.0f})")
        else:
            reasons.append(f"Most suspicious among candidates (score: {score:.0f})")
        
        if trust_score < 20:
            reasons.append("very low trust")
        
        player_data = DataValidator.safe_get_dict(context.get("player_data", {})).get(target, {})
        if player_data.get("malicious_injection"):
            reasons.append("injection attack detected")
        if player_data.get("false_quotes"):
            reasons.append("false quotation detected")
        
        vote_pattern = self.pattern_analyzer.analyze(target, context)
        if vote_pattern == "protect_wolf":
            reasons.append("wolf-protecting voting pattern")
        elif vote_pattern == "charge":
            reasons.append("charging voting pattern")
        
        return ", ".join(reasons)


class SheriffElectionDecisionMaker(BaseDecisionMaker):
    """警长选举决策器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'sheriff_election',
            'target': None,
            'reasoning': 'Error in decision',
            'confidence': 0.0
        }
    
    @safe_execute(default_return=(False, "Error in decision"))
    def decide(self, context: Dict) -> Tuple[bool, str]:
        """
        决定是否竞选警长
        
        Returns:
            (should_run, reason)
        """
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        player_data = DataValidator.safe_get_dict(context.get("player_data"))
        my_name = context.get("my_name", "")
        
        score = 0
        reasons = []
        
        # Check if already sheriff
        if game_state.get("sheriff") == my_name:
            return (False, "Already sheriff")
        
        # Check if神职 are running
        sheriff_candidates = DataValidator.safe_get_list(game_state.get("sheriff_candidates"))
        for candidate in sheriff_candidates:
            candidate_data = DataValidator.safe_get_dict(player_data.get(candidate))
            if candidate_data.get("claimed_seer") or candidate_data.get("claimed_witch"):
                score -= 50
                reasons.append("神职 running - let them be sheriff")
                break
        
        # Check if strong villager
        my_data = DataValidator.safe_get_dict(player_data.get(my_name))
        if my_data.get("logical_speech") and my_data.get("accurate_votes"):
            score += 40
            reasons.append("strong villager with logical speech and accurate votes")
        
        # Check faction situation
        wolves_dead = DataValidator.safe_get_int(game_state.get("wolves_dead", 0))
        goods_dead = DataValidator.safe_get_int(game_state.get("goods_dead", 0))
        if wolves_dead == 0 and goods_dead >= 2:
            score += 30
            reasons.append("good faction disadvantage - need leadership")
        elif wolves_dead >= 2:
            score -= 20
            reasons.append("good faction advantage - no need to expose")
        
        should_run = score >= 20
        reason = f"Score: {score} - " + ", ".join(reasons)
        logger.info(f"[DECISION TREE] Sheriff election: {should_run} ({reason})")
        
        return (should_run, reason)


class SheriffVoteDecisionMaker(BaseDecisionMaker):
    """警长投票决策器"""
    
    def __init__(self, config: VillagerConfig, trust_calculator: TrustScoreCalculator):
        super().__init__(config)
        self.trust_calculator = trust_calculator
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'sheriff_vote',
            'target': 'No.1',
            'reasoning': 'No candidates',
            'confidence': 0.0
        }
    
    @safe_execute(default_return=("No.1", "No candidates"))
    def decide(self, candidates: List[str], context: Dict) -> Tuple[str, str]:
        """
        决定警长投票目标
        
        Returns:
            (target, reason)
        """
        if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
            logger.warning(f"Invalid candidates: {candidates}")
            return ("No.1", "No candidates")
        
        # Calculate trust scores for all candidates
        trust_scores = {}
        for candidate in candidates:
            trust = self.trust_calculator.analyze(candidate, context)
            trust_scores[candidate] = trust
        
        # Sort by trust score (highest first)
        sorted_candidates = sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_candidates:
            return (candidates[0] if candidates else "No.1", "No trust scores calculated")
        
        target = sorted_candidates[0][0]
        trust = sorted_candidates[0][1]
        
        # Generate reason
        player_data = DataValidator.safe_get_dict(context.get("player_data", {})).get(target, {})
        reasons = []
        
        if trust >= 80:
            reasons.append(f"Highest trust ({trust})")
        elif trust >= 60:
            reasons.append(f"High trust ({trust})")
        else:
            reasons.append(f"Best among candidates ({trust})")
        
        if player_data.get("claimed_seer"):
            reasons.append("claimed Seer")
        if player_data.get("logical_speech"):
            reasons.append("logical speech")
        if player_data.get("accurate_votes"):
            reasons.append("accurate voting")
        
        reason = ", ".join(reasons)
        logger.info(f"[DECISION TREE] Sheriff vote: {target} ({reason})")
        
        return (target, reason)


class BadgeTransferDecisionMaker(BaseDecisionMaker):
    """警徽转移决策器"""
    
    def __init__(self, config: VillagerConfig, trust_calculator: TrustScoreCalculator):
        super().__init__(config)
        self.trust_calculator = trust_calculator
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'badge_transfer',
            'target': 'Destroy Badge',
            'reasoning': 'No suitable candidates',
            'confidence': 0.0
        }
    
    @safe_execute(default_return=("Destroy Badge", "No suitable candidates"))
    def decide(self, candidates: List[str], context: Dict) -> Tuple[str, str]:
        """
        决定警徽转移目标
        
        Returns:
            (target, reason)
        """
        if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
            logger.warning(f"Invalid candidates for badge transfer: {candidates}")
            return ("Destroy Badge", "No suitable candidates")
        
        seer_checks = DataValidator.safe_get_dict(context.get("seer_checks"))
        
        # Priority 1: Seer's good checks
        good_checks = [c for c in candidates if c in seer_checks and "good" in seer_checks[c].lower()]
        if good_checks:
            trust_scores = {c: self.trust_calculator.analyze(c, context) for c in good_checks}
            if trust_scores:
                target = max(trust_scores.items(), key=lambda x: x[1])[0]
                return (target, f"Seer good check (verified good)")
            else:
                return (good_checks[0], f"Seer good check (verified good)")
        
        # Priority 2: High trust players
        trust_scores = {}
        for candidate in candidates:
            trust = self.trust_calculator.analyze(candidate, context)
            trust_scores[candidate] = trust
        
        sorted_candidates = sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_candidates:
            return ("Destroy Badge", "No trust scores calculated")
        
        best_candidate = sorted_candidates[0]
        
        if best_candidate[1] < 50:
            return ("Destroy Badge", f"All candidates have low trust (highest: {best_candidate[1]})")
        
        target = best_candidate[0]
        reason = f"Highest trust score: {best_candidate[1]}"
        
        player_data = DataValidator.safe_get_dict(context.get("player_data", {})).get(target, {})
        if player_data.get("logical_speech"):
            reason += ", logical speaker"
        if player_data.get("accurate_votes"):
            reason += ", accurate voter"
        
        logger.info(f"[DECISION TREE] Badge transfer: {target} ({reason})")
        return (target, reason)


class SpeechOrderDecisionMaker(BaseDecisionMaker):
    """发言顺序决策器"""
    
    def __init__(self, config: VillagerConfig, trust_calculator: TrustScoreCalculator):
        super().__init__(config)
        self.trust_calculator = trust_calculator
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'speech_order',
            'target': None,
            'reasoning': 'Default order',
            'confidence': 0.0
        }
    
    @safe_execute(default_return=("Clockwise", "Default order"))
    def decide(self, context: Dict) -> Tuple[str, str]:
        """
        决定发言顺序
        
        Returns:
            (order, reason)
        """
        player_data = DataValidator.safe_get_dict(context.get("player_data"))
        
        # Find most suspicious players
        suspicious_players = []
        for player, data in player_data.items():
            if data.get("alive", True):
                trust = self.trust_calculator.analyze(player, context)
                if trust < 40:
                    suspicious_players.append((player, trust))
        
        if not suspicious_players:
            return ("Clockwise", "No specific suspects, using default order")
        
        # Extract player numbers
        suspicious_numbers = []
        for player, trust in suspicious_players:
            match = re.search(r"(\d+)", player)
            if match:
                suspicious_numbers.append(int(match.group(1)))
        
        if not suspicious_numbers:
            return ("Clockwise", "Default order")
        
        avg_suspicious = sum(suspicious_numbers) / len(suspicious_numbers)
        
        if avg_suspicious > 6:
            reason = f"Suspicious players (avg No.{avg_suspicious:.0f}) speak first - reduce coordination time"
            logger.info(f"[DECISION TREE] Speech order: Clockwise ({reason})")
            return ("Clockwise", reason)
        else:
            reason = f"Suspicious players (avg No.{avg_suspicious:.0f}) speak first - reduce coordination time"
            logger.info(f"[DECISION TREE] Speech order: Counter-clockwise ({reason})")
            return ("Counter-clockwise", reason)


class LastWordsGenerator(BaseDecisionMaker):
    """遗言生成器"""
    
    def __init__(self, config: VillagerConfig, trust_calculator: TrustScoreCalculator,
                 pattern_analyzer: VotingPatternAnalyzer):
        super().__init__(config)
        self.trust_calculator = trust_calculator
        self.pattern_analyzer = pattern_analyzer
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'last_words',
            'target': None,
            'reasoning': '',
            'confidence': 0.0
        }
    
    @safe_execute(default_return="")
    def decide(self, context: Dict) -> str:
        """
        生成遗言提示
        
        Returns:
            hints string with suspicious and trustworthy players
        """
        player_data = DataValidator.safe_get_dict(context.get("player_data"))
        
        suspicious = []
        trustworthy = []
        
        for player, data in player_data.items():
            if not isinstance(data, dict) or not data:
                continue
            if data.get("alive", True):
                trust = self.trust_calculator.analyze(player, context)
                
                # Collect evidence
                evidence = []
                if data.get("malicious_injection"):
                    evidence.append("injection attack")
                if data.get("false_quotes"):
                    evidence.append("false quotes")
                wolf_protecting_votes = DataValidator.safe_get_int(data.get("wolf_protecting_votes", 0))
                if wolf_protecting_votes >= 2:
                    evidence.append(f"wolf-protecting votes ({wolf_protecting_votes})")
                
                vote_pattern = self.pattern_analyzer.analyze(player, context)
                if vote_pattern == "protect_wolf":
                    evidence.append("protect-wolf pattern")
                elif vote_pattern == "charge":
                    evidence.append("charging pattern")
                
                if trust < 30:
                    suspicious.append({
                        "player": player,
                        "trust": trust,
                        "evidence": evidence
                    })
                elif trust > 70:
                    good_evidence = []
                    accurate_votes = DataValidator.safe_get_int(data.get("accurate_votes", 0))
                    if accurate_votes >= 2:
                        good_evidence.append(f"accurate votes ({accurate_votes})")
                    if data.get("logical_speech"):
                        good_evidence.append("logical speech")
                    
                    # Check Seer verification
                    seer_checks = DataValidator.safe_get_dict(context.get("seer_checks"))
                    if player in seer_checks and "good" in seer_checks[player].lower():
                        good_evidence.append("Seer good check")
                    
                    trustworthy.append({
                        "player": player,
                        "trust": trust,
                        "evidence": good_evidence
                    })
        
        # Sort
        suspicious.sort(key=lambda x: x["trust"])
        trustworthy.sort(key=lambda x: x["trust"], reverse=True)
        
        # Generate hints
        hints = "\n[LAST WORDS DATA]"
        
        if suspicious:
            hints += "\nSuspicious players:"
            for s in suspicious[:3]:
                evidence_str = ", ".join(s["evidence"]) if s["evidence"] else "low trust"
                hints += f"\n  {s['player']}: trust={s['trust']:.0f} ({evidence_str})"
        
        if trustworthy:
            hints += "\nTrustworthy players:"
            for t in trustworthy[:3]:
                evidence_str = ", ".join(t["evidence"]) if t["evidence"] else "high trust"
                hints += f"\n  {t['player']}: trust={t['trust']:.0f} ({evidence_str})"
        
        # Recommend primary vote target
        if suspicious:
            primary = suspicious[0]
            hints += f"\n[RECOMMENDED VOTE TARGET: {primary['player']} (trust={primary['trust']:.0f})]"
        
        logger.info(f"[DECISION TREE] Last words hints generated: {len(suspicious)} suspicious, {len(trustworthy)} trustworthy")
        return hints
