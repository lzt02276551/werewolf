# -*- coding: utf-8 -*-
"""
猎人代理人高级验证器

提供企业级的数据验证和完整性检查
"""

from typing import Any, Dict, List, Optional, Tuple
from agent_build_sdk.utils.logger import logger


class DataValidator:
    """
    高级数据验证器
    
    提供全面的数据验证功能
    """
    
    @staticmethod
    def validate_player_name(name: Any) -> bool:
        """
        验证玩家名称
        
        Args:
            name: 玩家名称
            
        Returns:
            是否有效
        """
        if not name or not isinstance(name, str):
            return False
        
        # 检查格式：No.X 或 PlayerX
        if name.startswith("No."):
            try:
                num = int(name[3:])
                return 1 <= num <= 20  # 支持1-20号玩家
            except ValueError:
                return False
        
        # 允许其他格式的玩家名
        return len(name) > 0 and len(name) <= 50
    
    @staticmethod
    def validate_trust_score(score: Any) -> bool:
        """
        验证信任分数
        
        Args:
            score: 信任分数
            
        Returns:
            是否有效
        """
        if not isinstance(score, (int, float)):
            return False
        
        return 0 <= score <= 100
    
    @staticmethod
    def validate_probability(prob: Any) -> bool:
        """
        验证概率值
        
        Args:
            prob: 概率值
            
        Returns:
            是否有效
        """
        if not isinstance(prob, (int, float)):
            return False
        
        return 0.0 <= prob <= 1.0
    
    @staticmethod
    def validate_voting_record(record: Any) -> bool:
        """
        验证投票记录
        
        Args:
            record: 投票记录
            
        Returns:
            是否有效
        """
        if not isinstance(record, (tuple, list)):
            return False
        
        if len(record) < 2:
            return False
        
        target, was_wolf = record[0], record[1]
        
        if not isinstance(target, str) or not isinstance(was_wolf, bool):
            return False
        
        return DataValidator.validate_player_name(target)
    
    @staticmethod
    def validate_game_phase(phase: Any) -> bool:
        """
        验证游戏阶段
        
        Args:
            phase: 游戏阶段
            
        Returns:
            是否有效
        """
        if not isinstance(phase, str):
            return False
        
        return phase in ["early", "mid", "late", "critical"]
    
    @staticmethod
    def validate_decision_scores(scores: Dict[str, float]) -> Tuple[bool, Optional[str]]:
        """
        验证决策分数字典
        
        Args:
            scores: 分数字典
            
        Returns:
            (是否有效, 错误信息)
        """
        if not isinstance(scores, dict):
            return (False, "Scores must be a dictionary")
        
        if not scores:
            return (False, "Scores dictionary is empty")
        
        for player, score in scores.items():
            if not DataValidator.validate_player_name(player):
                return (False, f"Invalid player name: {player}")
            
            if not isinstance(score, (int, float)):
                return (False, f"Invalid score type for {player}: {type(score)}")
            
            if not (-100 <= score <= 200):
                return (False, f"Score out of range for {player}: {score}")
        
        return (True, None)
    
    @staticmethod
    def sanitize_player_name(name: Any) -> Optional[str]:
        """
        清理玩家名称
        
        Args:
            name: 原始名称
            
        Returns:
            清理后的名称，无效则返回None
        """
        if not name:
            return None
        
        # 转换为字符串
        name_str = str(name).strip()
        
        # 验证
        if DataValidator.validate_player_name(name_str):
            return name_str
        
        return None
    
    @staticmethod
    def sanitize_trust_score(score: Any) -> float:
        """
        清理信任分数
        
        Args:
            score: 原始分数
            
        Returns:
            清理后的分数（限制在0-100范围内）
        """
        try:
            score_float = float(score)
            return max(0.0, min(100.0, score_float))
        except (ValueError, TypeError):
            logger.warning(f"Invalid trust score: {score}, using default 50.0")
            return 50.0
    
    @staticmethod
    def sanitize_probability(prob: Any) -> float:
        """
        清理概率值
        
        Args:
            prob: 原始概率
            
        Returns:
            清理后的概率（限制在0-1范围内）
        """
        try:
            prob_float = float(prob)
            return max(0.0, min(1.0, prob_float))
        except (ValueError, TypeError):
            logger.warning(f"Invalid probability: {prob}, using default 0.5")
            return 0.5


class IntegrityChecker:
    """
    数据完整性检查器
    
    检查数据的一致性和完整性
    """
    
    @staticmethod
    def check_player_consistency(
        alive_players: List[str],
        dead_players: set,
        all_players: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        检查玩家列表一致性
        
        Args:
            alive_players: 存活玩家列表
            dead_players: 死亡玩家集合
            all_players: 所有玩家列表
            
        Returns:
            (是否一致, 错误列表)
        """
        errors = []
        
        # 检查重复
        if len(alive_players) != len(set(alive_players)):
            errors.append("Duplicate players in alive_players")
        
        # 检查交集
        overlap = set(alive_players) & dead_players
        if overlap:
            errors.append(f"Players in both alive and dead: {overlap}")
        
        # 检查总数
        total = len(set(alive_players) | dead_players)
        expected = len(all_players)
        if total != expected:
            errors.append(f"Total player count mismatch: {total} != {expected}")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def check_trust_scores_integrity(
        trust_scores: Dict[str, float],
        alive_players: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        检查信任分数完整性
        
        Args:
            trust_scores: 信任分数字典
            alive_players: 存活玩家列表
            
        Returns:
            (是否完整, 警告列表)
        """
        warnings = []
        
        # 检查是否所有存活玩家都有信任分数
        for player in alive_players:
            if player not in trust_scores:
                warnings.append(f"Missing trust score for {player}")
        
        # 检查信任分数范围
        for player, score in trust_scores.items():
            if not DataValidator.validate_trust_score(score):
                warnings.append(f"Invalid trust score for {player}: {score}")
        
        return (len(warnings) == 0, warnings)
    
    @staticmethod
    def check_decision_integrity(
        target: str,
        candidates: List[str],
        scores: Dict[str, float]
    ) -> Tuple[bool, Optional[str]]:
        """
        检查决策完整性
        
        Args:
            target: 决策目标
            candidates: 候选人列表
            scores: 分数字典
            
        Returns:
            (是否有效, 错误信息)
        """
        # 检查目标是否在候选人中
        if target not in candidates and target != "Do Not Shoot":
            return (False, f"Target {target} not in candidates")
        
        # 检查分数字典
        valid, error = DataValidator.validate_decision_scores(scores)
        if not valid:
            return (False, error)
        
        # 检查目标是否有分数
        if target != "Do Not Shoot" and target not in scores:
            return (False, f"No score for target {target}")
        
        return (True, None)


class PerformanceValidator:
    """
    性能验证器
    
    验证性能指标是否在合理范围内
    """
    
    # 性能阈值（毫秒）
    THRESHOLDS = {
        'wolf_probability_calculation': 10.0,
        'threat_level_analysis': 10.0,
        'shoot_decision': 50.0,
        'vote_decision': 30.0,
        'speech_generation': 2000.0
    }
    
    @staticmethod
    def validate_execution_time(
        operation: str,
        execution_time: float
    ) -> Tuple[bool, Optional[str]]:
        """
        验证执行时间
        
        Args:
            operation: 操作名称
            execution_time: 执行时间（秒）
            
        Returns:
            (是否在阈值内, 警告信息)
        """
        threshold = PerformanceValidator.THRESHOLDS.get(operation, 100.0)
        execution_time_ms = execution_time * 1000
        
        if execution_time_ms > threshold:
            warning = (
                f"Performance warning: {operation} took {execution_time_ms:.2f}ms "
                f"(threshold: {threshold:.2f}ms)"
            )
            return (False, warning)
        
        return (True, None)
    
    @staticmethod
    def validate_memory_usage(
        current_usage: int,
        max_usage: int = 100 * 1024 * 1024  # 100MB
    ) -> Tuple[bool, Optional[str]]:
        """
        验证内存使用
        
        Args:
            current_usage: 当前内存使用（字节）
            max_usage: 最大内存使用（字节）
            
        Returns:
            (是否在限制内, 警告信息)
        """
        if current_usage > max_usage:
            warning = (
                f"Memory warning: Current usage {current_usage / 1024 / 1024:.2f}MB "
                f"exceeds limit {max_usage / 1024 / 1024:.2f}MB"
            )
            return (False, warning)
        
        return (True, None)


__all__ = [
    'DataValidator',
    'IntegrityChecker',
    'PerformanceValidator'
]

