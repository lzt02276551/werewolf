# -*- coding: utf-8 -*-
"""
预言家代理人决策器模块

实现各种决策功能：投票、检查、警长选举等
符合企业级标准，所有决策器继承BaseDecisionMaker
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from .config import SeerConfig
from .analyzers import WolfProbabilityEstimator, VotingPatternAnalyzer
import re


class VoteDecisionMaker(BaseDecisionMaker):
    """投票决策器"""
    
    def __init__(self, config: SeerConfig, wolf_prob_estimator: WolfProbabilityEstimator,
                 voting_pattern_analyzer: VotingPatternAnalyzer):
        super().__init__(config)
        self.wolf_prob_estimator = wolf_prob_estimator
        self.voting_pattern_analyzer = voting_pattern_analyzer
    
    def decide(self, candidates: List[str], my_name: str, context: Dict[str, Any]) -> Tuple[str, str, Dict[str, float]]:
        """
        投票决策
        
        Args:
            candidates: 候选人列表
            my_name: 自己的名字
            context: 上下文信息
            
        Returns:
            (目标玩家, 原因, 分数字典)
        """
        try:
            valid_candidates = [c for c in candidates if c != my_name]
            if not valid_candidates:
                fallback = candidates[0] if candidates else "No.1"
                return (fallback, 'No valid candidates', {})
            
            checked_players = context.get('checked_players', {})
            trust_scores = context.get('trust_scores', {})
            game_state = context.get('game_state', {})
            night_count = context.get('night_count', 0)
            
            # 第一层：已验证的狼人
            wolf_checks = [c for c in valid_candidates 
                          if c in checked_players and checked_players[c].get('is_wolf')]
            if wolf_checks:
                target = wolf_checks[0]
                return (target, 'Your wolf check - confirmed wolf (Priority ★★★★★)', {target: 100.0})
            
            # 第二层：排除已验证的好人
            good_checks = [c for c in valid_candidates 
                          if c in checked_players and not checked_players[c].get('is_wolf')]
            unchecked = [c for c in valid_candidates if c not in checked_players]
            
            if not unchecked:
                fallback = valid_candidates[0] if valid_candidates else "No.1"
                return (fallback, 'All candidates are verified good', {})
            
            # 第三层：综合评分
            vote_scores = {}
            for candidate in unchecked:
                dimensions = {
                    'wolf_probability': 0.0,
                    'trust_inverse': 0.0,
                    'strategic_value': 0.0,
                    'risk_assessment': 0.0
                }
                
                # 狼人概率
                wolf_prob = self.wolf_prob_estimator.estimate(candidate, context)
                dimensions['wolf_probability'] = wolf_prob
                
                # 信任度倒数
                trust = trust_scores.get(candidate, 50)
                trust_normalized = max(-100, min(100, trust))
                dimensions['trust_inverse'] = (100 - trust_normalized) / 200
                
                # 战略价值
                player_data = context.get('player_data', {}).get(candidate, {})
                strategic_score = 0.5
                
                if night_count <= 2:
                    if player_data.get('malicious_injection'):
                        strategic_score = 0.95
                    elif player_data.get('false_quotes'):
                        strategic_score = 0.90
                else:
                    wolves_dead = game_state.get('wolves_dead', 0)
                    goods_dead = game_state.get('goods_dead', 0)
                    if wolves_dead == 0 and goods_dead >= 2:
                        strategic_score = wolf_prob
                    else:
                        strategic_score = (wolf_prob + dimensions['trust_inverse']) / 2
                
                dimensions['strategic_value'] = strategic_score
                
                # 风险评估
                if trust > 70:
                    dimensions['risk_assessment'] = 0.2
                elif trust > 40:
                    dimensions['risk_assessment'] = 0.5
                elif trust > 0:
                    dimensions['risk_assessment'] = 0.7
                else:
                    dimensions['risk_assessment'] = 0.9
                
                # 加权求和
                weights = {
                    'wolf_probability': 0.40,
                    'trust_inverse': 0.30,
                    'strategic_value': 0.20,
                    'risk_assessment': 0.10
                }
                
                final_score = sum(dimensions[dim] * weights[dim] for dim in dimensions) * 100
                vote_scores[candidate] = max(0.0, min(100.0, final_score))
            
            if not vote_scores:
                fallback = valid_candidates[0] if valid_candidates else "No.1"
                return (fallback, 'No vote scores calculated', {})
            
            # 选择最高分
            sorted_candidates = sorted(vote_scores.items(), key=lambda x: x[1], reverse=True)
            target = sorted_candidates[0][0]
            score = sorted_candidates[0][1]
            
            # 生成原因
            reason = self._generate_reason(target, score, context)
            
            return (target, reason, vote_scores)
        except Exception as e:
            self.logger.error(f"Vote decision failed: {e}")
            fallback = candidates[0] if candidates else "No.1"
            return (fallback, f"Decision error: {e}", {})
    
    def _generate_reason(self, target: str, score: float, context: Dict[str, Any]) -> str:
        """生成投票原因"""
        trust_scores = context.get('trust_scores', {})
        player_data = context.get('player_data', {}).get(target, {})
        
        reasons = []
        
        if score >= 80:
            reasons.append(f"Extremely suspicious (score: {score:.0f})")
        elif score >= 65:
            reasons.append(f"Highly suspicious (score: {score:.0f})")
        elif score >= 50:
            reasons.append(f"Suspicious (score: {score:.0f})")
        else:
            reasons.append(f"Most suspicious among candidates (score: {score:.0f})")
        
        trust = trust_scores.get(target, 50)
        if trust < 20:
            reasons.append("very low trust")
        
        if player_data.get('malicious_injection'):
            reasons.append("injection attack detected")
        if player_data.get('false_quotes'):
            reasons.append("false quotation detected")
        
        vote_pattern = self.voting_pattern_analyzer.analyze_pattern(target, context)
        if vote_pattern == 'wolf_protecting':
            reasons.append("wolf-protecting voting pattern")
        
        return ", ".join(reasons)
    



class CheckDecisionMaker(BaseDecisionMaker):
    """检查决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str]:
        """
        检查决策
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            (目标玩家, 原因)
        """
        try:
            if not candidates:
                return ('No.1', 'No candidates available')
            
            return (candidates[0], 'First available candidate')
        except Exception as e:
            self.logger.error(f"Check decision failed: {e}")
            return ('No.1', f"Decision error: {e}")


class SheriffElectionDecisionMaker(BaseDecisionMaker):
    """警长选举决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        警长选举决策
        
        Args:
            context: 上下文信息
            
        Returns:
            (是否参选, 原因)
        """
        try:
            checked_players = context.get('checked_players', {})
            game_state = context.get('game_state', {})
            night_count = context.get('night_count', 0)
            
            score = 50
            reasons = []
            
            # 强制参选情况
            wolf_checks = [p for p, data in checked_players.items() if data.get('is_wolf')]
            if wolf_checks:
                score += 100
                reasons.append(f"have wolf check ({', '.join(wolf_checks)}) - MUST guide voting")
            
            if game_state.get('fake_seer_present'):
                score += 100
                reasons.append(f"fake seer present - MUST counter-claim")
            
            wolves_dead = game_state.get('wolves_dead', 0)
            goods_dead = game_state.get('goods_dead', 0)
            if wolves_dead == 0 and goods_dead >= 3:
                score += 80
                reasons.append("good faction in crisis - MUST provide leadership")
            
            if len(checked_players) >= 2:
                score += 40
                reasons.append(f"have {len(checked_players)} checks - strong info to lead with")
            elif len(checked_players) == 1:
                score += 25
                reasons.append("have 1 check - can reveal and lead")
            
            if night_count == 1:
                score += 30
                reasons.append("Day 1 sheriff election - seer should actively participate")
            
            if wolves_dead >= 2 and goods_dead <= 1:
                score -= 10
                reasons.append("good faction has advantage - can be slightly cautious")
            
            should_run = score >= 45
            reason = f"Score: {score} - " + ", ".join(reasons)
            
            return (should_run, reason)
        except Exception as e:
            self.logger.error(f"Sheriff election decision failed: {e}")
            return (False, f"Decision error: {e}")


class SheriffVoteDecisionMaker(BaseDecisionMaker):
    """警长投票决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str]:
        """
        警长投票决策
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            (目标玩家, 原因)
        """
        try:
            if not candidates:
                return ("No.1", "No candidates available")
            
            checked_players = context.get('checked_players', {})
            trust_scores = context.get('trust_scores', {})
            game_state = context.get('game_state', {})
            
            # 优先投给已验证的好人
            good_checks = [c for c in candidates 
                          if c in checked_players and not checked_players[c].get('is_wolf')]
            if good_checks:
                target = good_checks[0]
                return (target, 'Your good check - verified good player (Priority ★★★★★)')
            
            # 排除假预言家
            fake_seer = game_state.get('fake_seer_name')
            filtered_candidates = [c for c in candidates if c != fake_seer] if fake_seer else candidates
            
            if not filtered_candidates:
                filtered_candidates = candidates
            
            # 选择最高信任度
            candidate_scores = {c: trust_scores.get(c, 50) for c in filtered_candidates}
            
            if not candidate_scores:
                return (candidates[0] if candidates else "No.1", "No valid candidates")
            
            sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
            target = sorted_candidates[0][0]
            trust = sorted_candidates[0][1]
            
            # 生成原因
            reasons = []
            if trust >= 80:
                reasons.append(f"Highest trust ({trust})")
            elif trust >= 60:
                reasons.append(f"High trust ({trust})")
            else:
                reasons.append(f"Best among candidates ({trust})")
            
            if target in checked_players:
                reasons.append("your good check")
            
            player_data = context.get('player_data', {}).get(target, {})
            if player_data.get('logical_speech'):
                reasons.append("logical speech")
            
            return (target, ", ".join(reasons))
        except Exception as e:
            self.logger.error(f"Sheriff vote decision failed: {e}")
            return (candidates[0] if candidates else "No.1", f"Decision error: {e}")


class BadgeTransferDecisionMaker(BaseDecisionMaker):
    """徽章转移决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        徽章转移决策
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            (目标玩家或None表示销毁, 原因)
        """
        try:
            if not candidates:
                return (None, 'No suitable candidates')
            
            checked_players = context.get('checked_players', {})
            trust_scores = context.get('trust_scores', {})
            
            # 优先转给已验证的好人
            good_checks = [c for c in candidates 
                          if c in checked_players and not checked_players[c].get('is_wolf')]
            if good_checks:
                scores = {c: trust_scores.get(c, 50) for c in good_checks}
                target = max(scores.items(), key=lambda x: x[1])[0] if scores else good_checks[0]
                return (target, 'Your good check - verified good player (Priority ★★★★★)')
            
            # 排除狼人检查
            wolf_checks = [c for c in checked_players if checked_players[c].get('is_wolf')]
            safe_candidates = [c for c in candidates if c not in wolf_checks]
            
            if not safe_candidates:
                return (None, 'All candidates are wolf checks')
            
            # 选择最高信任度
            candidate_scores = {c: trust_scores.get(c, 50) for c in safe_candidates}
            sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
            
            if not sorted_candidates:
                return (None, 'No valid candidates')
            
            best_candidate = sorted_candidates[0]
            
            if best_candidate[1] < 0:
                return (None, f'All candidates have negative trust (highest: {best_candidate[1]})')
            
            target = best_candidate[0]
            reason = f"Highest trust score: {best_candidate[1]}"
            
            player_data = context.get('player_data', {}).get(target, {})
            if player_data.get('logical_speech'):
                reason += ", logical speaker"
            
            return (target, reason)
        except Exception as e:
            self.logger.error(f"Badge transfer decision failed: {e}")
            return (None, f"Decision error: {e}")


class SpeechOrderDecisionMaker(BaseDecisionMaker):
    """发言顺序决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, context: Dict[str, Any]) -> Tuple[str, str]:
        """
        发言顺序决策
        
        Args:
            context: 上下文信息
            
        Returns:
            (发言顺序, 原因)
        """
        try:
            trust_scores = context.get('trust_scores', {})
            checked_players = context.get('checked_players', {})
            
            # 找到狼人检查
            wolf_checks = [p for p, data in checked_players.items() if data.get('is_wolf')]
            if wolf_checks:
                wolf_numbers = []
                for wolf in wolf_checks:
                    match = re.search(r"(\d+)", wolf)
                    if match:
                        wolf_numbers.append(int(match.group(1)))
                
                if wolf_numbers:
                    avg_wolf_num = sum(wolf_numbers) / len(wolf_numbers)
                    if avg_wolf_num > 6:
                        return ('Clockwise', 'Wolf check(s) in high numbers - let them speak first')
                    else:
                        return ('Counter-clockwise', 'Wolf check(s) in low numbers - let them speak first')
            
            # 找到高度可疑玩家
            suspects = [(p, score) for p, score in trust_scores.items() if score < 30]
            
            if suspects:
                suspect_numbers = []
                for suspect, _ in suspects:
                    match = re.search(r"(\d+)", suspect)
                    if match:
                        suspect_numbers.append(int(match.group(1)))
                
                if suspect_numbers:
                    avg_suspect_num = sum(suspect_numbers) / len(suspect_numbers)
                    
                    if avg_suspect_num > 6:
                        suspect_names = ', '.join([s[0] for s in suspects[:3]])
                        return ('Clockwise', f'Suspects in high numbers ({suspect_names}) - observe them first')
                    else:
                        suspect_names = ', '.join([s[0] for s in suspects[:3]])
                        return ('Counter-clockwise', f'Suspects in low numbers ({suspect_names}) - observe them first')
            
            return ('Clockwise', 'Standard order - no specific suspects to prioritize')
        except Exception as e:
            self.logger.error(f"Speech order decision failed: {e}")
            return ('Clockwise', f"Decision error: {e}")


class IdentityRevealDecisionMaker(BaseDecisionMaker):
    """身份揭示决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        身份揭示决策
        
        Args:
            context: 上下文信息
            
        Returns:
            (是否揭示, 原因)
        """
        try:
            checked_players = context.get('checked_players', {})
            game_state = context.get('game_state', {})
            
            # 有狼人检查 → 立即揭示
            for player, data in checked_players.items():
                if data.get('is_wolf'):
                    return (True, 'Have wolf check - must reveal to guide voting')
            
            # 假预言家出现 → 反击
            if game_state.get('fake_seer_present'):
                return (True, 'Fake seer appeared - must counter-claim')
            
            # 好人阵营劣势 → 必须揭示
            wolves_dead = game_state.get('wolves_dead', 0)
            goods_dead = game_state.get('goods_dead', 0)
            if wolves_dead == 0 and goods_dead >= 3:
                return (True, 'Good faction losing - must provide leadership')
            
            # 警长选举 → 考虑揭示
            if game_state.get('sheriff_election'):
                if len(checked_players) >= 2:
                    return (True, 'Sheriff election with multiple checks - good timing')
            
            return (False, 'Stay hidden to gather more information')
        except Exception as e:
            self.logger.error(f"Identity reveal decision failed: {e}")
            return (False, f"Decision error: {e}")
