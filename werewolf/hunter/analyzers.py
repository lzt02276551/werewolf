# -*- coding: utf-8 -*-
"""
猎人代理人分析器模块

实现猎人特有的分析器：
- MemoryDAO: Hunter专用的内存数据访问对象
- ThreatLevelAnalyzer: 威胁等级分析器
- WolfProbabilityCalculator: 狼人概率计算器

HunterAgent继承自BaseGoodAgent，使用villager模块的通用分析器。
"""

from werewolf.core.base_components import BaseAnalyzer, BaseMemoryDAO
from werewolf.common.utils import DataValidator, CacheManager
from .config import HunterConfig
from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger


class MemoryDAO(BaseMemoryDAO):
    """
    Hunter专用的内存数据访问对象
    
    封装对Agent内存的所有访问操作，提供类型安全的接口
    """
    
    def __init__(self, memory):
        """
        初始化MemoryDAO
        
        Args:
            memory: Agent的内存对象
        """
        super().__init__(memory)
    
    def get(self, key: str, default=None):
        """获取内存中的值"""
        return self.memory.load_variable(key) or default
    
    def set(self, key: str, value):
        """设置内存中的值"""
        self.memory.set_variable(key, value)
    
    def get_my_name(self) -> str:
        """获取自己的名字"""
        return self.memory.load_variable("name") or ""
    
    def get_can_shoot(self) -> bool:
        """获取是否可以开枪"""
        return self.memory.load_variable("can_shoot") or False
    
    def set_can_shoot(self, can_shoot: bool):
        """设置是否可以开枪"""
        self.memory.set_variable("can_shoot", can_shoot)
    
    def get_trust_scores(self) -> Dict[str, float]:
        """获取信任分数"""
        return self.memory.load_variable("trust_scores") or {}
    
    def set_trust_scores(self, scores: Dict[str, float]):
        """设置信任分数"""
        self.memory.set_variable("trust_scores", scores)
    
    def get_trust_history(self) -> Dict[str, List[float]]:
        """获取信任历史"""
        return self.memory.load_variable("trust_history") or {}
    
    def set_trust_history(self, history: Dict[str, List[float]]):
        """设置信任历史"""
        self.memory.set_variable("trust_history", history)
    
    def get_voting_history(self) -> Dict[str, List[str]]:
        """获取投票历史"""
        return self.memory.load_variable("voting_history") or {}
    
    def get_voting_results(self) -> Dict[str, List[Tuple[str, bool]]]:
        """获取投票结果"""
        return self.memory.load_variable("voting_results") or {}
    
    def set_voting_results(self, results: Dict[str, List[Tuple[str, bool]]]):
        """设置投票结果"""
        self.memory.set_variable("voting_results", results)
    
    def get_speech_history(self) -> Dict[str, List[str]]:
        """获取发言历史"""
        return self.memory.load_variable("speech_history") or {}
    
    def set_speech_history(self, history: Dict[str, List[str]]):
        """设置发言历史"""
        self.memory.set_variable("speech_history", history)
    
    def get_injection_attempts(self) -> List[Dict[str, Any]]:
        """获取注入攻击记录"""
        return self.memory.load_variable("injection_attempts") or []
    
    def get_false_quotations(self) -> List[Dict[str, Any]]:
        """获取虚假引用记录"""
        return self.memory.load_variable("false_quotations") or []
    
    def get_dead_players(self) -> set:
        """获取已死亡玩家"""
        dead = self.memory.load_variable("dead_players") or []
        return set(dead) if isinstance(dead, list) else dead
    
    def get_sheriff(self) -> Optional[str]:
        """获取警长"""
        return self.memory.load_variable("sheriff")
    
    def get_history(self) -> List[str]:
        """获取历史记录"""
        return self.memory.load_variable("history") or []


# ==================== 猎人特有分析器 ====================


class ThreatLevelAnalyzer(BaseAnalyzer):
    """
    威胁等级分析器（猎人特有）
    
    评估玩家的威胁等级，用于开枪决策
    """
    
    def __init__(self, config: HunterConfig, memory_dao, cache_manager: CacheManager):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.cache_manager = cache_manager
        self.validator = DataValidator()
    
    def _get_default_result(self) -> float:
        """返回默认威胁等级"""
        return 0.5
    
    def _validate_input(self, player_name: str, current_day: int = 1, alive_count: int = 12, *args, **kwargs) -> bool:
        """验证输入参数"""
        return (
            self.validator.validate_player_name(player_name) and
            isinstance(current_day, int) and current_day > 0 and
            isinstance(alive_count, int) and alive_count > 0
        )
    
    def _do_analyze(self, player_name: str, current_day: int = 1, alive_count: int = 12, *args, **kwargs) -> float:
        """
        分析玩家的威胁等级
        
        Args:
            player_name: 玩家名称
            current_day: 当前天数
            alive_count: 存活人数
            
        Returns:
            威胁等级 (0.0-1.0)
        """
        # 检查缓存
        cache_key = f"threat_{player_name}_{current_day}_{alive_count}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            return cached
        
        # 多维度威胁评估
        dimensions = {
            'wolf_probability': 0.0,
            'social_influence': 0.0,
            'strategic_value': 0.0,
            'immediate_danger': 0.0
        }
        
        # 1. 狼人概率（基础威胁）
        trust_scores = self.memory_dao.get_trust_scores()
        trust = trust_scores.get(player_name, 50)
        dimensions['wolf_probability'] = max(0.0, min(1.0, (100 - trust) / 100.0))
        
        # 2. 社会影响力
        dimensions['social_influence'] = self._calculate_social_influence(player_name)
        
        # 3. 战略价值
        sheriff = self.memory_dao.get_sheriff()
        if sheriff == player_name:
            dimensions['strategic_value'] = 0.9
        else:
            dimensions['strategic_value'] = 0.5
        
        # 4. 即时危险（根据游戏阶段）
        if alive_count <= 6:
            # 后期，威胁更高
            dimensions['immediate_danger'] = 0.8
        elif alive_count <= 9:
            # 中期
            dimensions['immediate_danger'] = 0.5
        else:
            # 前期
            dimensions['immediate_danger'] = 0.3
        
        # 动态权重
        if current_day <= 2:
            weights = {
                'wolf_probability': 0.40,
                'social_influence': 0.30,
                'strategic_value': 0.20,
                'immediate_danger': 0.10
            }
        elif current_day >= 6:
            weights = {
                'wolf_probability': 0.50,
                'social_influence': 0.20,
                'strategic_value': 0.15,
                'immediate_danger': 0.15
            }
        else:
            weights = {
                'wolf_probability': 0.45,
                'social_influence': 0.25,
                'strategic_value': 0.20,
                'immediate_danger': 0.10
            }
        
        # 计算综合威胁等级
        threat_level = sum(dimensions[dim] * weights[dim] for dim in dimensions)
        
        # 缓存结果
        self.cache_manager.set(cache_key, threat_level, ttl=60)
        
        return threat_level
    
    def _calculate_social_influence(self, player_name: str) -> float:
        """计算社会影响力"""
        speech_history = self.memory_dao.get_speech_history()
        player_speeches = speech_history.get(player_name, [])
        
        if not player_speeches:
            return 0.3
        
        # 发言次数越多，影响力越大
        speech_count = len(player_speeches)
        if speech_count >= 5:
            return 0.8
        elif speech_count >= 3:
            return 0.6
        else:
            return 0.4


class WolfProbabilityCalculator:
    """
    狼人概率计算器（猎人特有）
    
    组合多个分析器计算狼人概率
    注意：使用BaseGoodAgent的分析器，通过适配器访问
    """
    
    def __init__(
        self, 
        config: HunterConfig,
        trust_calculator,  # BaseGoodAgent的trust_score_calculator
        voting_analyzer,   # BaseGoodAgent的voting_pattern_analyzer
        speech_evaluator,  # BaseGoodAgent的speech_quality_evaluator
        memory_dao
    ):
        self.config = config
        self.trust_calculator = trust_calculator
        self.voting_analyzer = voting_analyzer
        self.speech_evaluator = speech_evaluator
        self.memory_dao = memory_dao
    
    def calculate(self, player_name: str, game_phase: str = "mid") -> float:
        """
        计算狼人概率（0.0-1.0）
        
        Args:
            player_name: 玩家名称
            game_phase: 游戏阶段 ("early", "mid", "late")
        
        Returns:
            狼人概率
        """
        # 验证输入
        if not player_name or not isinstance(player_name, str):
            raise ValueError(f"Invalid player_name: {player_name}")
        # Component 1: 信任分数（基础权重35%）
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(player_name, 50)
        trust_component = max(0.0, min(1.0, (100 - trust_score) / 100.0))
        trust_weight = 0.35
        
        # Component 2: 投票模式（权重25%-40%，根据数据可靠性）
        voting_modifier = self._get_voting_modifier(player_name)
        voting_confidence = self._get_voting_confidence(player_name)
        voting_weight = 0.25 + voting_confidence * 0.15
        
        # Component 3: 发言质量（权重5%）
        speech_modifier = self._get_speech_modifier(player_name)
        speech_weight = 0.05
        
        # Component 4: 注入攻击（权重10%-20%）
        injection_component = self._get_injection_component(player_name)
        injection_weight = 0.10 if game_phase == "early" else 0.15
        
        # Component 5: 虚假引用（权重10%-15%）
        false_quote_component = self._get_false_quote_component(player_name)
        false_quote_weight = 0.10 if game_phase == "early" else 0.15
        
        # 归一化权重
        total_weight = trust_weight + voting_weight + speech_weight + injection_weight + false_quote_weight
        trust_weight /= total_weight
        voting_weight /= total_weight
        speech_weight /= total_weight
        injection_weight /= total_weight
        false_quote_weight /= total_weight
        
        # 计算综合概率
        wolf_prob = (
            trust_component * trust_weight +
            (trust_component + voting_modifier) * voting_weight +
            (trust_component + speech_modifier) * speech_weight +
            injection_component * injection_weight +
            false_quote_component * false_quote_weight
        )
        
        return max(0.0, min(1.0, wolf_prob))
    
    def _get_voting_modifier(self, player_name: str) -> float:
        """获取投票模式修正值"""
        voting_results = self.memory_dao.get_voting_results()
        
        if player_name not in voting_results:
            return 0.0
        
        results = voting_results[player_name]
        
        if not isinstance(results, list) or len(results) < 2:
            return 0.0
        
        # 计算准确率
        from werewolf.optimization.utils.safe_math import safe_divide
        wolf_votes = sum(1 for _, was_wolf in results if was_wolf)
        accuracy_rate = safe_divide(wolf_votes, len(results), default=0.5)
        
        # 映射到修正值
        if accuracy_rate >= 0.7:
            return -0.25
        elif accuracy_rate >= 0.6:
            return -0.15
        elif accuracy_rate >= 0.5:
            return 0.0
        elif accuracy_rate >= 0.4:
            return 0.15
        else:
            return 0.25
    
    def _get_voting_confidence(self, player_name: str) -> float:
        """获取投票数据的置信度"""
        voting_results = self.memory_dao.get_voting_results()
        
        if player_name not in voting_results:
            return 0.0
        
        results = voting_results[player_name]
        
        if not isinstance(results, list):
            return 0.0
        
        # 数据越多，置信度越高
        count = len(results)
        if count >= 5:
            return 1.0
        elif count >= 3:
            return 0.7
        elif count >= 2:
            return 0.4
        else:
            return 0.0
    
    def _get_speech_modifier(self, player_name: str) -> float:
        """获取发言质量修正值"""
        speech_history = self.memory_dao.get_speech_history()
        player_speeches = speech_history.get(player_name, [])
        
        if not player_speeches:
            return 0.0
        
        # 简单评估：发言越少，越可疑
        speech_count = len(player_speeches)
        if speech_count >= 5:
            return -0.1
        elif speech_count >= 3:
            return 0.0
        else:
            return 0.1
    
    def _get_injection_component(self, player_name: str) -> float:
        """获取注入攻击组件"""
        injection_attempts = self.memory_dao.get_injection_attempts()
        
        player_injections = [
            attempt for attempt in injection_attempts
            if attempt.get('player_name') == player_name
        ]
        
        if not player_injections:
            return 0.0
        
        # 有注入攻击，高度可疑
        return 0.9
    
    def _get_false_quote_component(self, player_name: str) -> float:
        """获取虚假引用组件"""
        false_quotations = self.memory_dao.get_false_quotations()
        
        player_quotes = [
            quote for quote in false_quotations
            if quote.get('player_name') == player_name
        ]
        
        if not player_quotes:
            return 0.0
        
        # 有虚假引用，高度可疑
        return 0.8


__all__ = [
    'MemoryDAO',
    'ThreatLevelAnalyzer',
    'WolfProbabilityCalculator'
]

logger.info("✓ Hunter analyzers module loaded (Hunter-specific components only)")
