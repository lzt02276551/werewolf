"""
Guard 分析器模块

提供守卫决策所需的分析功能：
- RoleEstimator: 角色估计器
- WolfKillPredictor: 狼人击杀预测器
- GuardPriorityCalculator: 守卫优先级计算器
"""

from werewolf.core.base_components import BaseAnalyzer
from werewolf.guard.config import GuardConfig
from typing import Dict, Any, Optional, List
from agent_build_sdk.utils.logger import logger


class RoleEstimator(BaseAnalyzer):
    """
    角色估计器 - 估计玩家的角色
    
    基于以下信息估计玩家角色：
    - 信任分数
    - 发言内容
    - 投票行为
    - 游戏进程
    
    注意：状态持久化到memory，避免重启后丢失
    """
    
    def __init__(self, config: GuardConfig, memory=None):
        super().__init__(config)
        self.memory = memory
        # 从memory加载状态（如果可用）
        if memory:
            self.confirmed_seers = set(memory.load_variable("confirmed_seers") or [])
            self.likely_seers = set(memory.load_variable("likely_seers") or [])
            self.sheriff = memory.load_variable("sheriff")
        else:
            self.confirmed_seers = set()
            self.likely_seers = set()
            self.sheriff = None
    
    def _do_analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析玩家角色
        
        Args:
            data: 包含 player 和 context 的字典
            
        Returns:
            角色估计结果
        """
        player = data.get('player')
        context = data.get('context', {})
        
        if not player:
            return self._get_default_result()
        
        # 获取信任分数
        trust_scores = context.get('trust_scores', {})
        trust_score = trust_scores.get(player, 50.0)
        
        # 获取警长信息
        sheriff = context.get('sheriff')
        if sheriff:
            self.sheriff = sheriff
        
        # 基于信任分数估计角色
        is_confirmed_seer = player in self.confirmed_seers
        is_likely_seer = player in self.likely_seers or trust_score > 80
        is_sheriff = player == self.sheriff
        
        # 计算置信度
        confidence = 0.5
        if is_confirmed_seer:
            confidence = 0.95
        elif is_likely_seer:
            confidence = 0.7
        elif is_sheriff:
            confidence = 0.6
        
        result = {
            'player': player,
            'is_confirmed_seer': is_confirmed_seer,
            'is_likely_seer': is_likely_seer,
            'is_sheriff': is_sheriff,
            'trust_score': trust_score,
            'confidence': confidence
        }
        
        logger.debug(f"[RoleEstimator] {player}: seer={is_likely_seer}, sheriff={is_sheriff}, trust={trust_score:.1f}")
        
        return result
    
    def is_confirmed_seer(self, player: str) -> bool:
        """检查是否是确认的预言家"""
        return player in self.confirmed_seers
    
    def is_likely_seer(self, player: str) -> bool:
        """检查是否可能是预言家"""
        return player in self.likely_seers or player in self.confirmed_seers
    
    def is_sheriff(self, player: str) -> bool:
        """检查是否是警长"""
        return player == self.sheriff
    
    def mark_as_seer(self, player: str, confirmed: bool = False):
        """标记玩家为预言家（并持久化到memory）"""
        if confirmed:
            self.confirmed_seers.add(player)
            self.likely_seers.discard(player)
        else:
            self.likely_seers.add(player)
        
        # 持久化到memory
        if self.memory:
            self.memory.set_variable("confirmed_seers", list(self.confirmed_seers))
            self.memory.set_variable("likely_seers", list(self.likely_seers))
    
    def _get_default_result(self) -> Dict[str, Any]:
        """返回默认结果"""
        return {
            'player': None,
            'is_confirmed_seer': False,
            'is_likely_seer': False,
            'is_sheriff': False,
            'trust_score': 50.0,
            'confidence': 0.0
        }


class WolfKillPredictor(BaseAnalyzer):
    """
    狼人击杀预测器 - 预测狼人可能击杀的目标
    
    基于以下因素预测：
    - 威胁等级（信任分数）
    - 角色重要性（预言家、警长）
    - 游戏阶段
    - 历史击杀模式
    """
    
    def __init__(self, config: GuardConfig):
        super().__init__(config)
    
    def _do_analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        预测狼人击杀目标
        
        Args:
            data: 包含 candidates 和 context 的字典
            
        Returns:
            击杀概率预测结果
        """
        candidates = data.get('candidates', [])
        context = data.get('context', {})
        
        if not candidates:
            return {'predictions': {}}
        
        predictions = {}
        for candidate in candidates:
            threat_level = self._calculate_threat_level(candidate, context)
            predictions[candidate] = threat_level
        
        logger.debug(f"[WolfKillPredictor] Predictions: {predictions}")
        
        return {'predictions': predictions}
    
    def predict_single(self, player: str, context: Dict[str, Any]) -> float:
        """
        预测单个玩家被击杀的概率
        
        Args:
            player: 玩家名称
            context: 游戏上下文
            
        Returns:
            被击杀概率 (0.0-1.0)
        """
        threat_level = self._calculate_threat_level(player, context)
        return threat_level / 100.0  # 转换为概率
    
    def _calculate_threat_level(self, player: str, context: Dict[str, Any]) -> float:
        """
        计算威胁等级
        
        Args:
            player: 玩家名称
            context: 游戏上下文
            
        Returns:
            威胁等级 (0-100)
        """
        # 基础威胁 = 信任分数
        trust_scores = context.get('trust_scores', {})
        threat = trust_scores.get(player, 50.0)
        
        # 警长加成
        sheriff = context.get('sheriff')
        if player == sheriff:
            threat += 20
        
        # 角色加成（如果有角色估计器）
        role_checker = context.get('role_checker')
        if role_checker:
            if role_checker.is_confirmed_seer(player):
                threat += 30  # 确认预言家威胁最高
            elif role_checker.is_likely_seer(player):
                threat += 20  # 疑似预言家
        
        # 游戏阶段调整
        night_count = context.get('night_count', 1)
        if night_count <= 2:
            # 前期：狼人可能击杀高调玩家
            if threat > 70:
                threat *= 1.1
        else:
            # 后期：狼人更倾向击杀关键角色
            if role_checker and (role_checker.is_likely_seer(player) or player == sheriff):
                threat *= 1.2
        
        # 限制在 0-100 范围内
        return min(max(threat, 0.0), 100.0)
    
    def _get_default_result(self) -> Dict[str, Any]:
        """返回默认结果"""
        return {'predictions': {}}


class GuardPriorityCalculator(BaseAnalyzer):
    """
    守卫优先级计算器 - 计算守护目标的优先级
    
    综合考虑：
    - 信任分数
    - 角色重要性
    - 被击杀风险
    - 游戏阶段
    - 守护策略
    """
    
    def __init__(self, config: GuardConfig):
        super().__init__(config)
    
    def _do_analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算守护优先级
        
        Args:
            data: 包含 candidates 和 context 的字典
            
        Returns:
            优先级计算结果
        """
        candidates = data.get('candidates', [])
        context = data.get('context', {})
        
        if not candidates:
            return {'priorities': {}}
        
        priorities = {}
        for candidate in candidates:
            priority = self.calculate(candidate, context)
            priorities[candidate] = priority
        
        logger.debug(f"[GuardPriorityCalculator] Priorities: {priorities}")
        
        return {'priorities': priorities}
    
    def calculate(self, player: str, context: Dict[str, Any]) -> float:
        """
        计算单个玩家的守护优先级（优化版 - 动态权重 + 存活人数考虑）
        
        根据游戏阶段和存活人数动态调整各因素权重：
        - 早期：信任分数权重高
        - 中期：角色识别权重高
        - 后期/残局：被击杀风险权重高，更重视关键角色
        
        Args:
            player: 玩家名称
            context: 游戏上下文，必须包含：
                - trust_scores: Dict[str, float] 信任分数字典
                - night_count: int 夜晚编号
                - alive_players: set/list 存活玩家集合
                - sheriff: Optional[str] 警长名称
                - role_checker: Optional[RoleEstimator] 角色估计器
                - wolf_predictor: Optional[WolfKillPredictor] 狼人击杀预测器
            
        Returns:
            守护优先级 (0-100)
            
        Raises:
            ValueError: 当必需的上下文参数缺失时
        """
        # 验证必需参数
        if not isinstance(context, dict):
            raise ValueError(f"context must be a dict, got {type(context)}")
        
        if 'trust_scores' not in context:
            raise ValueError("context must contain 'trust_scores'")
        
        if 'night_count' not in context:
            raise ValueError("context must contain 'night_count'")
        # 基础优先级 = 信任分数
        trust_scores = context.get('trust_scores', {})
        priority = trust_scores.get(player, 50.0)
        
        # 获取游戏阶段和存活人数
        night_count = context.get('night_count', 1)
        alive_players = context.get('alive_players', set())
        alive_count = len(alive_players) if isinstance(alive_players, (set, list)) else 12
        
        # 动态权重（根据游戏阶段和存活人数）
        if night_count == 1:
            # 首夜：优先级大幅降低（通常空守）
            trust_weight = 0.3
            role_weight = 0.2
            risk_weight = 0.1
        elif alive_count <= 5:
            # 残局：更重视角色和风险
            trust_weight = 0.7
            role_weight = 1.5
            risk_weight = 2.0
            logger.debug(f"[GuardPriority] Endgame mode: {alive_count} players alive")
        elif night_count <= 2:
            # 前期：信任分数权重高
            trust_weight = 1.2
            role_weight = 0.8
            risk_weight = 0.5
        elif night_count <= 5:
            # 中期：角色识别权重高
            trust_weight = 1.0
            role_weight = 1.2
            risk_weight = 0.8
        else:
            # 后期：被击杀风险权重高
            trust_weight = 0.8
            role_weight = 1.0
            risk_weight = 1.5
        
        # 警长加成
        sheriff = context.get('sheriff')
        if player == sheriff:
            priority += 15 * role_weight
        
        # 角色加成
        role_checker = context.get('role_checker')
        if role_checker:
            if role_checker.is_confirmed_seer(player):
                priority += 30 * role_weight  # 确认预言家优先级最高
            elif role_checker.is_likely_seer(player):
                priority += 20 * role_weight  # 疑似预言家
        
        # 被击杀风险加成
        wolf_predictor = context.get('wolf_predictor')
        if wolf_predictor:
            kill_prob = wolf_predictor.predict_single(player, context)
            priority += kill_prob * 20 * risk_weight  # 被击杀概率越高，优先级越高
        
        # 限制在 0-100 范围内
        return min(max(priority, 0.0), 100.0)
    
    def _get_default_result(self) -> Dict[str, Any]:
        """返回默认结果"""
        return {'priorities': {}}


# 导出所有分析器
__all__ = [
    'RoleEstimator',
    'WolfKillPredictor',
    'GuardPriorityCalculator'
]
