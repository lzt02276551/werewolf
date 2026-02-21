# -*- coding: utf-8 -*-
"""
预言家代理人分析器模块

实现各种分析功能：信任分数、狼人概率、投票模式等
符合企业级标准，所有分析器继承BaseAnalyzer或BaseTrustManager
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseAnalyzer, BaseTrustManager
from werewolf.core.game_state import GamePhase
from .config import SeerConfig
import math


class TrustScoreManager(BaseTrustManager):
    """
    信任分数管理器
    
    管理所有玩家的信任分数，使用非线性衰减算法
    """
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def initialize_players(self, players: List[str]) -> None:
        """
        初始化玩家信任分数
        
        Args:
            players: 玩家列表
        """
        for player in players:
            if player not in self.trust_scores:
                self.trust_scores[player] = float(self.config.trust_score_default)
    
    def update_score(self, player: str, delta: float, reason: str = "") -> float:
        """
        更新玩家信任分数（使用优化的Sigmoid衰减算法）
        
        Args:
            player: 玩家名称
            delta: 分数变化
            reason: 更新原因
            
        Returns:
            更新后的分数
        
        验证需求：AC-1.3.1
        """
        # 导入优化的信任分数更新算法
        from werewolf.optimization.algorithms.trust_score import update_trust_score
        
        current = self.trust_scores.get(player, self.config.trust_score_default)
        
        # 使用优化的Sigmoid衰减算法
        config = {
            'decay_steepness': 0.1,
            'decay_midpoint': 50.0
        }
        
        new_score = update_trust_score(current, delta, config)
        self.trust_scores[player] = new_score
        
        if reason:
            self.logger.debug(f"信任分数更新: {player} {current:.0f} -> {new_score:.0f} ({reason}) [Sigmoid衰减]")
        
        return new_score
    
    def get_score(self, player: str) -> float:
        """
        获取玩家信任分数
        
        Args:
            player: 玩家名称
            
        Returns:
            信任分数
        """
        return self.trust_scores.get(player, self.config.trust_score_default)
    
    def update(self, player: str, delta: int, confidence: float, 
               source_reliability: float, trust_scores: Dict[str, int],
               trust_history: Dict[str, List[Dict]]) -> int:
        """
        企业级信任分数更新算法 - 非线性衰减机制
        
        Args:
            player: 玩家名称
            delta: 基础变化量
            confidence: 证据置信度 (0.0-1.0)
            source_reliability: 来源可靠性 (0.0-1.0)
            trust_scores: 信任分数字典
            trust_history: 信任历史字典
        
        Returns:
            更新后的信任分数
        """
        current_score = trust_scores.get(player, 50)
        
        # 1. 应用置信度和来源可靠性权重
        weighted_delta = delta * confidence * source_reliability
        
        # 2. 非线性衰减
        def smooth_decay_factor(score: float, target_direction: int) -> float:
            """计算平滑衰减系数"""
            if target_direction > 0:
                normalized_score = (score + 100) / 200
                decay = 1 / (1 + math.exp(10 * (normalized_score - 0.75)))
                return max(0.05, decay)
            else:
                normalized_score = (score + 100) / 200
                decay = 1 / (1 + math.exp(-10 * (normalized_score - 0.25)))
                return max(0.05, decay)
        
        direction = 1 if weighted_delta > 0 else -1
        decay = smooth_decay_factor(current_score, direction)
        adjusted_delta = weighted_delta * decay
        
        # 3. 历史一致性检查
        if player not in trust_history:
            trust_history[player] = []
        
        player_history = trust_history[player]
        
        if len(player_history) >= 2:
            weights = [0.5, 0.3, 0.2]
            recent_deltas = [h['delta'] for h in player_history[-3:]]
            
            weighted_trend = 0
            for i, delta_val in enumerate(recent_deltas):
                weight = weights[i] if i < len(weights) else 0.1
                weighted_trend += (1 if delta_val > 0 else -1) * weight
            
            current_direction = 1 if adjusted_delta > 0 else -1
            
            if abs(weighted_trend) > 0.3 and weighted_trend * current_direction < 0:
                adjusted_delta *= 0.6
                self.logger.debug(f"趋势反转检测: {player}, 减弱delta 40%")
        
        # 4. 应用变化
        new_score = self.clamp(int(current_score + adjusted_delta))
        trust_scores[player] = new_score
        
        # 5. 记录历史
        player_history.append({
            'delta': adjusted_delta,
            'confidence': confidence,
            'source_reliability': source_reliability,
            'old_score': current_score,
            'new_score': new_score,
            'decay_factor': decay
        })
        if len(player_history) > 10:
            player_history.pop(0)
        trust_history[player] = player_history
        
        self.logger.debug(
            f"信任分数更新: {player} {current_score} -> {new_score} "
            f"(base: {delta:+d}, weighted: {weighted_delta:+.1f}, "
            f"adjusted: {adjusted_delta:+.1f}, decay: {decay:.2f})"
        )
        return new_score
    
    def clamp(self, score: int) -> int:
        """确保信任分数在有效范围内"""
        return max(-100, min(100, score))
    
    def calculate(self, player_name: str, context: Dict[str, Any]) -> int:
        """
        企业级信任分数算法 - 多维度加权评分系统
        
        Args:
            player_name: 玩家名称
            context: 上下文信息
            
        Returns:
            信任分数 (-100 to +100)
        """
        base_score = 50
        checked_players = context.get('checked_players', {})
        player_data = context.get('player_data', {}).get(player_name, {})
        
        # 已验证玩家 - 绝对优先级
        if player_name in checked_players:
            return -100 if checked_players[player_name].get('is_wolf') else 100
        
        # 多维度评分
        dimensions = {
            'injection_attacks': 0,
            'speech_quality': 0,
            'voting_accuracy': 0,
            'behavioral_consistency': 0,
            'social_signals': 0
        }
        
        # 1. 注入攻击维度 (30%)
        if player_data.get('malicious_injection'):
            dimensions['injection_attacks'] -= 35
        if player_data.get('false_quotes'):
            dimensions['injection_attacks'] -= 25
        if player_data.get('benign_injection'):
            dimensions['injection_attacks'] += 8
        
        # 2. 发言质量维度 (25%)
        if player_data.get('logical_speech'):
            dimensions['speech_quality'] += 20
        if player_data.get('contradictions'):
            dimensions['speech_quality'] -= 18
        if player_data.get('suspicious_speech'):
            dimensions['speech_quality'] -= 12
        
        # 3. 投票准确度维度 (25%)
        voting_results = context.get('voting_results', {})
        player_vote_results = voting_results.get(player_name, [])
        if player_vote_results and len(player_vote_results) >= 2:
            correct_votes = sum(1 for _, was_wolf in player_vote_results if was_wolf)
            total_votes = len(player_vote_results)
            accuracy_rate = correct_votes / total_votes if total_votes > 0 else 0.5
            
            if accuracy_rate >= 0.75:
                dimensions['voting_accuracy'] += 25
            elif accuracy_rate >= 0.5:
                dimensions['voting_accuracy'] += 10
            elif accuracy_rate >= 0.25:
                dimensions['voting_accuracy'] -= 10
            else:
                dimensions['voting_accuracy'] -= 25
        
        # 4. 行为一致性维度 (10%)
        speech_history = context.get('speech_history', {}).get(player_name, [])
        voting_history = context.get('voting_history', {}).get(player_name, [])
        if speech_history and voting_history and len(voting_history) >= 3:
            unique_targets = len(set(voting_history))
            if unique_targets == len(voting_history):
                dimensions['behavioral_consistency'] -= 15
            elif unique_targets <= len(voting_history) // 2:
                dimensions['behavioral_consistency'] += 10
        
        # 5. 社交信号维度 (10%)
        if player_data.get('night_kill_victim'):
            dimensions['social_signals'] += 30
        if player_data.get('voted_out'):
            dimensions['social_signals'] -= 20
        if player_data.get('sheriff_candidate'):
            dimensions['social_signals'] += 12
        if player_data.get('accurate_votes'):
            dimensions['social_signals'] += 10
        
        # 加权求和
        weights = {
            'injection_attacks': 0.30,
            'speech_quality': 0.25,
            'voting_accuracy': 0.25,
            'behavioral_consistency': 0.10,
            'social_signals': 0.10
        }
        
        weighted_delta = sum(dimensions[dim] * weights[dim] for dim in dimensions)
        final_score = self.clamp(int(base_score + weighted_delta))
        
        return final_score
    
    def _get_default_result(self) -> float:
        return float(self.config.trust_score_default)


class WolfProbabilityEstimator(BaseAnalyzer):
    """狼人概率估算器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def _do_analyze(self, player: str, context: Dict[str, Any]) -> float:
        """
        估算玩家是狼人的概率
        
        Args:
            player: 玩家名称
            context: 上下文信息
            
        Returns:
            狼人概率 (0.0-1.0)
        """
        trust_scores = context.get('trust_scores', {})
        trust_score = trust_scores.get(player, 50)
        
        # 检查是否已验证
        checked_players = context.get('checked_players', {})
        if player in checked_players:
            check_result = checked_players[player]
            if isinstance(check_result, dict) and 'is_wolf' in check_result:
                return 1.0 if check_result['is_wolf'] else 0.0
        
        # Sigmoid函数映射
        def sigmoid(x: float, center: float = 50, steepness: float = 0.05) -> float:
            return 1 / (1 + math.exp(steepness * (x - center)))
        
        prior_prob = sigmoid(trust_score, center=50, steepness=0.05)
        
        # 证据收集
        evidence_factors = []
        player_data = context.get('player_data', {}).get(player, {})
        
        # 注入攻击证据
        if player_data.get('malicious_injection'):
            evidence_factors.append(('malicious_injection', 0.95, 0.95))
        if player_data.get('false_quotes'):
            evidence_factors.append(('false_quotes', 0.90, 0.90))
        
        # 投票准确度证据
        voting_results = context.get('voting_results', {})
        player_vote_results = voting_results.get(player, [])
        
        if player_vote_results and len(player_vote_results) >= 2:
            correct_votes = sum(1 for _, was_wolf in player_vote_results if was_wolf)
            total_votes = len(player_vote_results)
            accuracy_rate = correct_votes / total_votes if total_votes > 0 else 0.5
            
            if accuracy_rate <= 0.3:
                evidence_factors.append(('wolf_protecting', 0.85, 0.85))
            elif accuracy_rate >= 0.7:
                evidence_factors.append(('accurate_voter', 0.20, 0.85))
        
        # 发言质量证据
        if player_data.get('contradictions'):
            evidence_factors.append(('contradictions', 0.75, 0.70))
        if player_data.get('logical_speech'):
            evidence_factors.append(('logical_speech', 0.25, 0.70))
        
        # 社交信号证据
        if player_data.get('night_kill_victim'):
            evidence_factors.append(('night_kill_victim', 0.10, 0.80))
        if player_data.get('voted_out'):
            evidence_factors.append(('voted_out', 0.70, 0.60))
        
        # 贝叶斯更新
        posterior_prob = prior_prob
        for evidence_name, evidence_prob, evidence_weight in evidence_factors:
            posterior_prob = posterior_prob * (1 - evidence_weight) + evidence_prob * evidence_weight
            posterior_prob = max(0.0, min(1.0, posterior_prob))
        
        return posterior_prob
    
    def _get_default_result(self) -> float:
        return 0.5
    
    def estimate(self, player: str, context: Dict[str, Any]) -> float:
        """公共接口：估算狼人概率"""
        return self.analyze(player, context)






class CheckPriorityCalculator(BaseAnalyzer):
    """检查优先级计算器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def _do_analyze(self, player_name: str, context: Dict[str, Any]) -> float:
        """
        计算检查优先级
        
        Args:
            player_name: 玩家名称
            context: 上下文信息
            
        Returns:
            优先级分数 (0-100)
        """
        player_data = context.get('player_data', {}).get(player_name, {})
        game_state = context.get('game_state', {})
        night_count = context.get('night_count', 0)
        
        # 紧急检查
        emergency_score = 0.0
        if player_data.get('malicious_injection'):
            emergency_score = 0.98
        elif player_data.get('false_quotes'):
            emergency_score = 0.95
        elif game_state.get('fake_seer_name') == player_name:
            emergency_score = 0.96
        
        if emergency_score > 0:
            return emergency_score * 100
        
        # 多维度评分
        dimensions = {
            'suspicion_level': 0.0,
            'strategic_value': 0.0,
            'information_gain': 0.0,
            'risk_assessment': 0.0
        }
        
        # 1. 嫌疑程度
        suspicion_factors = []
        if player_data.get('wolf_protecting_votes'):
            suspicion_factors.append(0.85)
        if player_data.get('contradictions'):
            suspicion_factors.append(0.75)
        if player_data.get('opposed_dead_good'):
            suspicion_factors.append(0.70)
        if player_data.get('aggressive_bandwagon'):
            suspicion_factors.append(0.70)
        if player_data.get('swing_votes'):
            suspicion_factors.append(0.60)
        
        dimensions['suspicion_level'] = max(suspicion_factors) if suspicion_factors else 0.3
        
        # 2. 战略价值
        strategic_factors = []
        if player_data.get('is_sheriff'):
            strategic_factors.append(0.90)
        if player_data.get('strong_speaker'):
            strategic_factors.append(0.75)
        if player_data.get('high_influence'):
            strategic_factors.append(0.70)
        
        if player_data.get('is_edge_player'):
            dimensions['strategic_value'] = 0.20
        else:
            dimensions['strategic_value'] = max(strategic_factors) if strategic_factors else 0.40
        
        # 3. 信息增益
        if night_count <= 2:
            dimensions['information_gain'] = dimensions['strategic_value'] * 0.8
        else:
            dimensions['information_gain'] = dimensions['suspicion_level'] * 0.8
        
        # 4. 风险评估
        trust_scores = context.get('trust_scores', {})
        trust = trust_scores.get(player_name, 50)
        if trust < 20:
            dimensions['risk_assessment'] = 0.90
        elif trust < 40:
            dimensions['risk_assessment'] = 0.70
        elif trust > 70:
            dimensions['risk_assessment'] = 0.30
        else:
            dimensions['risk_assessment'] = 0.50
        
        # 动态权重
        if night_count <= 2:
            weights = {
                'suspicion_level': 0.30,
                'strategic_value': 0.40,
                'information_gain': 0.20,
                'risk_assessment': 0.10
            }
        else:
            weights = {
                'suspicion_level': 0.45,
                'strategic_value': 0.25,
                'information_gain': 0.15,
                'risk_assessment': 0.15
            }
        
        decision_tree_score = sum(dimensions[dim] * weights[dim] for dim in dimensions)
        return decision_tree_score * 100
    
    def _get_default_result(self) -> float:
        return 50.0
    
    def calculate(self, player_name: str, context: Dict[str, Any]) -> float:
        """公共接口：计算检查优先级"""
        return self.analyze(player_name, context)
