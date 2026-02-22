# -*- coding: utf-8 -*-
"""
猎人代理人智能决策优化器

使用机器学习和统计方法优化决策质量
"""

from typing import Dict, List, Tuple, Optional
from collections import deque
import numpy as np
from agent_build_sdk.utils.logger import logger


class DecisionOptimizer:
    """
    决策优化器
    
    功能：
    1. 学习历史决策的成功率
    2. 动态调整决策阈值
    3. 提供决策建议和置信度
    """
    
    def __init__(self, history_size: int = 100):
        """
        初始化决策优化器
        
        Args:
            history_size: 历史记录大小
        """
        self.history_size = history_size
        
        # 决策历史：(决策类型, 目标, 分数, 是否成功)
        self.decision_history: deque = deque(maxlen=history_size)
        
        # 成功率统计
        self.success_rates: Dict[str, Dict[str, float]] = {
            'shoot': {'total': 0, 'success': 0, 'rate': 0.0},
            'vote': {'total': 0, 'success': 0, 'rate': 0.0}
        }
        
        # 动态阈值
        self.thresholds: Dict[str, float] = {
            'shoot_min_score': 35.0,
            'shoot_min_confidence': 0.4,
            'vote_min_score': 30.0
        }
    
    def record_decision(
        self, 
        decision_type: str, 
        target: str, 
        score: float, 
        success: bool
    ):
        """
        记录决策结果
        
        Args:
            decision_type: 决策类型（shoot/vote）
            target: 目标玩家
            score: 决策分数
            success: 是否成功
        """
        self.decision_history.append((decision_type, target, score, success))
        
        # 更新成功率
        if decision_type in self.success_rates:
            stats = self.success_rates[decision_type]
            stats['total'] += 1
            if success:
                stats['success'] += 1
            stats['rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 0.0
        
        # 动态调整阈值
        self._adjust_thresholds()
    
    def _adjust_thresholds(self):
        """
        动态调整决策阈值
        
        策略：
        - 如果成功率高，降低阈值（更激进）
        - 如果成功率低，提高阈值（更保守）
        """
        for decision_type, stats in self.success_rates.items():
            if stats['total'] < 10:
                continue  # 样本太少，不调整
            
            rate = stats['rate']
            
            if decision_type == 'shoot':
                # 开枪决策阈值调整
                if rate >= 0.8:
                    # 成功率高，降低阈值
                    self.thresholds['shoot_min_score'] = max(30.0, self.thresholds['shoot_min_score'] - 2.0)
                    self.thresholds['shoot_min_confidence'] = max(0.3, self.thresholds['shoot_min_confidence'] - 0.05)
                elif rate <= 0.5:
                    # 成功率低，提高阈值
                    self.thresholds['shoot_min_score'] = min(50.0, self.thresholds['shoot_min_score'] + 2.0)
                    self.thresholds['shoot_min_confidence'] = min(0.6, self.thresholds['shoot_min_confidence'] + 0.05)
            
            elif decision_type == 'vote':
                # 投票决策阈值调整
                if rate >= 0.8:
                    self.thresholds['vote_min_score'] = max(25.0, self.thresholds['vote_min_score'] - 2.0)
                elif rate <= 0.5:
                    self.thresholds['vote_min_score'] = min(40.0, self.thresholds['vote_min_score'] + 2.0)
    
    def get_threshold(self, threshold_name: str) -> float:
        """
        获取当前阈值
        
        Args:
            threshold_name: 阈值名称
            
        Returns:
            阈值值
        """
        return self.thresholds.get(threshold_name, 0.0)
    
    def get_success_rate(self, decision_type: str) -> float:
        """
        获取决策成功率
        
        Args:
            decision_type: 决策类型
            
        Returns:
            成功率（0.0-1.0）
        """
        if decision_type in self.success_rates:
            return self.success_rates[decision_type]['rate']
        return 0.0
    
    def get_recommendation(
        self, 
        decision_type: str, 
        score: float, 
        confidence: float
    ) -> Tuple[bool, str]:
        """
        获取决策建议
        
        Args:
            decision_type: 决策类型
            score: 决策分数
            confidence: 置信度
            
        Returns:
            (是否建议执行, 建议理由)
        """
        if decision_type == 'shoot':
            min_score = self.thresholds['shoot_min_score']
            min_confidence = self.thresholds['shoot_min_confidence']
            
            if score >= min_score and confidence >= min_confidence:
                return (True, f"Score {score:.1f} >= {min_score:.1f}, Confidence {confidence:.2f} >= {min_confidence:.2f}")
            elif score < min_score:
                return (False, f"Score {score:.1f} < {min_score:.1f} (threshold)")
            else:
                return (False, f"Confidence {confidence:.2f} < {min_confidence:.2f} (threshold)")
        
        elif decision_type == 'vote':
            min_score = self.thresholds['vote_min_score']
            
            if score >= min_score:
                return (True, f"Score {score:.1f} >= {min_score:.1f}")
            else:
                return (False, f"Score {score:.1f} < {min_score:.1f} (threshold)")
        
        return (True, "No specific recommendation")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'decision_count': len(self.decision_history),
            'success_rates': self.success_rates.copy(),
            'thresholds': self.thresholds.copy(),
            'recent_decisions': list(self.decision_history)[-10:]
        }
    
    def reset(self):
        """重置优化器"""
        self.decision_history.clear()
        self.success_rates = {
            'shoot': {'total': 0, 'success': 0, 'rate': 0.0},
            'vote': {'total': 0, 'success': 0, 'rate': 0.0}
        }
        self.thresholds = {
            'shoot_min_score': 35.0,
            'shoot_min_confidence': 0.4,
            'vote_min_score': 30.0
        }


class AdaptiveLearner:
    """
    自适应学习器
    
    从游戏历史中学习最优策略
    """
    
    def __init__(self):
        """初始化自适应学习器"""
        self.game_outcomes: List[Dict] = []
        self.strategy_performance: Dict[str, Dict] = {}
    
    def record_game_outcome(
        self, 
        game_result: str, 
        strategies_used: Dict[str, any]
    ):
        """
        记录游戏结果
        
        Args:
            game_result: 游戏结果（win/lose）
            strategies_used: 使用的策略
        """
        self.game_outcomes.append({
            'result': game_result,
            'strategies': strategies_used
        })
        
        # 更新策略性能
        for strategy_name, strategy_value in strategies_used.items():
            if strategy_name not in self.strategy_performance:
                self.strategy_performance[strategy_name] = {
                    'total': 0,
                    'wins': 0,
                    'win_rate': 0.0
                }
            
            stats = self.strategy_performance[strategy_name]
            stats['total'] += 1
            if game_result == 'win':
                stats['wins'] += 1
            stats['win_rate'] = stats['wins'] / stats['total']
    
    def get_best_strategy(self, strategy_type: str) -> Optional[any]:
        """
        获取最佳策略
        
        Args:
            strategy_type: 策略类型
            
        Returns:
            最佳策略值
        """
        if strategy_type in self.strategy_performance:
            return self.strategy_performance[strategy_type]
        return None
    
    def get_learning_report(self) -> str:
        """
        生成学习报告
        
        Returns:
            格式化的学习报告
        """
        if not self.strategy_performance:
            return "No learning data available"
        
        lines = ["=" * 60, "Adaptive Learning Report", "=" * 60]
        lines.append(f"Total games: {len(self.game_outcomes)}")
        lines.append("")
        lines.append("Strategy Performance:")
        lines.append("-" * 60)
        
        for strategy_name, stats in self.strategy_performance.items():
            lines.append(
                f"{strategy_name:<30} "
                f"Games: {stats['total']:>4} "
                f"Wins: {stats['wins']:>4} "
                f"Win Rate: {stats['win_rate']:>6.1%}"
            )
        
        lines.append("=" * 60)
        return "\n".join(lines)


__all__ = [
    'DecisionOptimizer',
    'AdaptiveLearner'
]

