# -*- coding: utf-8 -*-
"""
预言家代理人分析器模块

实现预言家特有的分析功能：
- CheckPriorityCalculator: 验人优先级计算

SeerAgent继承自BaseGoodAgent，使用villager模块的通用分析器。
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseAnalyzer
from .config import SeerConfig


class CheckPriorityCalculator(BaseAnalyzer):
    """
    检查优先级计算器（预言家特有）
    
    根据多维度评分计算验人优先级：
    - 嫌疑程度
    - 战略价值
    - 信息增益
    - 风险评估
    """
    
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


__all__ = ['CheckPriorityCalculator']

logger.info("✓ Seer analyzers module loaded (CheckPriorityCalculator)")
