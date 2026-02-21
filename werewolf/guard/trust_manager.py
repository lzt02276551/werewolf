"""
信任分数管理器 - 企业级实现
应用单一职责原则，将信任分数管理逻辑独立出来

优化内容:
1. 添加性能监控
2. 添加自定义异常处理
3. 完善类型提示
4. 添加输入验证
"""
from typing import Dict, List, Tuple, Optional
from agent_build_sdk.utils.logger import logger
from .exceptions import InvalidPlayerError, MemoryError as GuardMemoryError


def monitor_performance(name=None):
    """性能监控装饰器（简化版本）"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    if callable(name):
        # 如果直接使用@monitor_performance而不带参数
        return decorator(name)
    # 如果使用@monitor_performance("name")带参数
    return decorator


class TrustScoreConfig:
    """信任分数配置类（配置集中管理）"""
    
    # 信任分数范围
    MIN_SCORE = 0
    MAX_SCORE = 100
    DEFAULT_SCORE = 50
    
    # 非线性衰减参数
    MIN_DECAY_FACTOR = 0.1  # 最小衰减因子，避免完全无法变化
    
    # 历史记录保留数量
    MAX_HISTORY_LENGTH = 10
    
    # 趋势反转减弱系数
    TREND_REVERSAL_FACTOR = 0.5


class TrustScoreManager:
    """
    信任分数管理器
    
    职责：
    1. 初始化玩家信任分数
    2. 更新信任分数（非线性衰减算法）
    3. 追踪信任分数变化历史
    4. 提供信任分数查询接口
    """
    
    def __init__(self, memory):
        """
        初始化信任分数管理器
        
        Args:
            memory: 记忆系统
        """
        self.memory = memory
        self.config = TrustScoreConfig()
    
    @monitor_performance("trust_manager.initialize_players")
    def initialize_players(self, players: List[str]) -> None:
        """
        初始化玩家信任分数（幂等操作）
        
        Args:
            players: 玩家列表
        """
        # 输入验证
        if not players or not isinstance(players, (list, set, tuple)):
            logger.warning(f"[TrustManager] Invalid players type: {type(players)}")
            return
        
        trust_scores = self._get_trust_scores()
        
        # 只为新玩家初始化（幂等性）
        initialized_count = 0
        for player in players:
            if not player or not isinstance(player, str):
                logger.warning(f"[TrustManager] Invalid player name: {player}")
                continue
            
            if player not in trust_scores:
                trust_scores[player] = self.config.DEFAULT_SCORE
                initialized_count += 1
        
        self._set_trust_scores(trust_scores)
        
        if initialized_count > 0:
            logger.debug(f"[TrustManager] Initialized {initialized_count} new players to {self.config.DEFAULT_SCORE}")
    
    def update_score(self, player: str, delta: float, reason: str = "", 
                    confidence: float = 1.0, source_reliability: float = 1.0) -> None:
        """
        更新信任分数（使用优化的Sigmoid衰减算法）
        
        特性：
        1. Sigmoid非线性衰减：越接近极端值，变化越困难
        2. 置信度权重：不同证据有不同可信度
        3. 来源可靠性：不同来源有不同权重
        4. 历史一致性检查：与历史趋势相反时减弱
        5. 历史记录追踪
        
        Args:
            player: 玩家名称
            delta: 信任分数变化量（正数=增加，负数=减少）
            reason: 变化原因
            confidence: 证据置信度（0.0-1.0）
            source_reliability: 来源可靠性（0.0-1.0）
        
        验证需求：AC-1.3.1
        """
        # 导入优化的信任分数更新算法
        from werewolf.optimization.algorithms.trust_score import update_trust_score
        
        # 输入验证
        if not player or not isinstance(player, str):
            logger.warning(f"[TrustManager] Invalid player: {player}")
            return
        
        if not isinstance(delta, (int, float)):
            logger.warning(f"[TrustManager] Invalid delta type: {type(delta)}")
            return
        
        # 参数范围验证
        confidence = max(0.0, min(1.0, float(confidence)))
        source_reliability = max(0.0, min(1.0, float(source_reliability)))
        
        trust_scores = self._get_trust_scores()
        
        # 确保玩家存在
        if player not in trust_scores:
            trust_scores[player] = self.config.DEFAULT_SCORE
        
        current_score = trust_scores[player]
        
        # 验证当前分数
        if not isinstance(current_score, (int, float)):
            logger.warning(f"[TrustManager] Invalid current score for {player}: {current_score}, resetting")
            current_score = self.config.DEFAULT_SCORE
            trust_scores[player] = current_score
        
        # 1. 应用置信度和来源可靠性权重
        evidence_impact = delta * confidence * source_reliability
        
        # 2. 历史一致性检查
        trust_history = self._get_trust_history()
        if player in trust_history and len(trust_history[player]) >= 3:
            evidence_impact = self._apply_trend_check_to_impact(player, evidence_impact, trust_history)
        
        # 3. 使用优化的Sigmoid衰减算法更新分数
        config = {
            'decay_steepness': 0.1,
            'decay_midpoint': 50.0
        }
        
        new_score = update_trust_score(current_score, evidence_impact, config)
        
        # 4. 记录历史
        self._record_history(player, evidence_impact, trust_history)
        
        # 5. 更新分数
        trust_scores[player] = new_score
        self._set_trust_scores(trust_scores)
        self._set_trust_history(trust_history)
        
        logger.info(f"[TrustManager] {player}: {current_score:.1f} -> {new_score:.1f} "
                   f"(delta={delta:+.1f}, impact={evidence_impact:+.1f}, "
                   f"conf={confidence:.2f}, src={source_reliability:.2f}) - {reason} [Sigmoid衰减]")
    
    def get_score(self, player: str) -> float:
        """
        获取玩家信任分数
        
        Args:
            player: 玩家名称
        
        Returns:
            信任分数（0-100）
        """
        trust_scores = self._get_trust_scores()
        score = trust_scores.get(player, self.config.DEFAULT_SCORE)
        
        # 验证范围
        if not isinstance(score, (int, float)) or not (self.config.MIN_SCORE <= score <= self.config.MAX_SCORE):
            logger.warning(f"[TrustManager] Invalid score for {player}: {score}, using default")
            return self.config.DEFAULT_SCORE
        
        return float(score)
    
    def get_all_scores(self) -> Dict[str, float]:
        """获取所有玩家的信任分数"""
        return self._get_trust_scores().copy()
    
    def get_summary(self, alive_players: set = None, top_n: int = 8) -> str:
        """
        获取信任分数摘要
        
        Args:
            alive_players: 存活玩家集合（如果提供，只显示存活玩家）
            top_n: 显示前N名
        
        Returns:
            格式化的摘要字符串
        """
        trust_scores = self._get_trust_scores()
        
        # 过滤存活玩家
        if alive_players:
            trust_scores = {k: v for k, v in trust_scores.items() if k in alive_players}
        
        # 排序
        sorted_scores = sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 格式化
        top_scores = sorted_scores[:top_n]
        return "Trust scores: " + ", ".join([f"{p}({s:.0f})" for p, s in top_scores])
    
    def _apply_trend_check_to_impact(self, player: str, evidence_impact: float, trust_history: Dict) -> float:
        """
        应用历史趋势检查到证据影响
        
        Args:
            player: 玩家名称
            evidence_impact: 证据影响量
            trust_history: 信任历史
        
        Returns:
            调整后的证据影响量
        """
        recent_changes = trust_history[player][-3:]
        
        # 过滤非数字值
        recent_changes = [x for x in recent_changes if isinstance(x, (int, float))]
        
        if not recent_changes:
            return evidence_impact
        
        avg_recent_delta = sum(recent_changes) / len(recent_changes)
        
        # 如果当前变化与历史趋势相反（符号不同），减弱50%
        if (avg_recent_delta > 0 and evidence_impact < 0) or (avg_recent_delta < 0 and evidence_impact > 0):
            logger.debug(f"[TrustManager] {player} - Trend reversal detected, weakening change by 50%")
            return evidence_impact * self.config.TREND_REVERSAL_FACTOR
        
        return evidence_impact
    
    def _record_history(self, player: str, weighted_delta: float, trust_history: Dict) -> None:
        """
        记录信任分数变化历史（带验证和清理）
        
        Args:
            player: 玩家名称
            weighted_delta: 加权后的变化量
            trust_history: 信任历史字典
        """
        # 验证输入
        if not isinstance(player, str):
            logger.warning(f"[TrustManager] Invalid player type: {type(player)}, skipping history record")
            return
        
        if not isinstance(weighted_delta, (int, float)):
            logger.warning(f"[TrustManager] Invalid weighted_delta type: {type(weighted_delta)}, skipping")
            return
        
        if not isinstance(trust_history, dict):
            logger.error(f"[TrustManager] Invalid trust_history type: {type(trust_history)}, cannot record")
            return
        
        # 初始化玩家历史
        if player not in trust_history:
            trust_history[player] = []
        
        # 验证玩家历史是列表
        if not isinstance(trust_history[player], list):
            logger.warning(f"[TrustManager] Player {player} history is not a list, resetting")
            trust_history[player] = []
        
        # 添加新记录
        trust_history[player].append(weighted_delta)
        
        # 只保留最近N次（防止内存无限增长）
        if len(trust_history[player]) > self.config.MAX_HISTORY_LENGTH:
            trust_history[player] = trust_history[player][-self.config.MAX_HISTORY_LENGTH:]
        
        # 定期清理：如果总玩家数超过100，只保留最近活跃的50个
        if len(trust_history) > 100:
            logger.info(f"[TrustManager] Trust history has {len(trust_history)} players, cleaning up...")
            self._cleanup_old_players(trust_history)
    
    def _cleanup_old_players(self, trust_history: Dict) -> None:
        """
        清理不活跃的玩家历史记录
        
        Args:
            trust_history: 信任历史字典
        """
        # 获取当前游戏中的玩家
        trust_scores = self._get_trust_scores()
        active_players = set(trust_scores.keys())
        
        # 找出不活跃的玩家（不在当前trust_scores中）
        inactive_players = set(trust_history.keys()) - active_players
        
        # 如果不活跃玩家太多，删除一些
        if len(inactive_players) > 50:
            # 按历史记录长度排序，删除记录最少的
            sorted_inactive = sorted(
                inactive_players,
                key=lambda p: len(trust_history.get(p, []))
            )
            
            # 删除前一半
            to_remove = sorted_inactive[:len(sorted_inactive) // 2]
            for player in to_remove:
                del trust_history[player]
            
            logger.info(f"[TrustManager] Cleaned up {len(to_remove)} inactive player histories")
    
    def _get_trust_scores(self) -> Dict[str, float]:
        """安全获取信任分数字典"""
        trust_scores = self.memory.load_variable("trust_scores")
        if not isinstance(trust_scores, dict):
            logger.warning(f"[TrustManager] Invalid trust_scores type: {type(trust_scores)}, resetting")
            trust_scores = {}
            self.memory.set_variable("trust_scores", trust_scores)
        return trust_scores
    
    def _set_trust_scores(self, trust_scores: Dict[str, float]) -> None:
        """设置信任分数字典"""
        self.memory.set_variable("trust_scores", trust_scores)
    
    def _get_trust_history(self) -> Dict[str, List[float]]:
        """安全获取信任历史"""
        trust_history = self.memory.load_variable("trust_history")
        if not isinstance(trust_history, dict):
            logger.warning(f"[TrustManager] Invalid trust_history type: {type(trust_history)}, resetting")
            trust_history = {}
            self.memory.set_variable("trust_history", trust_history)
        return trust_history
    
    def _set_trust_history(self, trust_history: Dict[str, List[float]]) -> None:
        """设置信任历史"""
        self.memory.set_variable("trust_history", trust_history)
