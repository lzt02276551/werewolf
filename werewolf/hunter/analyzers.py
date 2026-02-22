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
from .performance import monitor_performance
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
        try:
            return self.memory.load_variable(key)
        except (KeyError, AttributeError):
            return default
    
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
    
    @monitor_performance
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
        # 使用更高效的缓存策略（LRU缓存，自动淘汰旧数据）
        import time
        from functools import lru_cache
        
        game_id = int(time.time() / 3600)  # 每小时一个游戏ID
        cache_key = f"threat_{game_id}_{player_name}_{current_day}_{alive_count}"
        
        if self.cache_manager:
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                return cached
        
        # 多维度威胁评估（优化：使用字典推导式提高性能）
        dimensions = {
            'wolf_probability': self._calculate_wolf_probability(player_name),
            'social_influence': self._calculate_social_influence(player_name),
            'strategic_value': self._calculate_strategic_value(player_name),
            'immediate_danger': self._calculate_immediate_danger(current_day, alive_count)
        }
        
        # 动态权重（优化：预计算权重避免重复计算）
        weights = self._get_dynamic_weights(current_day)
        
        # 计算综合威胁等级（优化：使用生成器表达式减少内存占用）
        threat_level = sum(dimensions[dim] * weights[dim] for dim in dimensions)
        
        # 缓存结果（带安全检查）
        if self.cache_manager:
            try:
                self.cache_manager.set(cache_key, threat_level, ttl=60)
            except Exception as e:
                logger.debug(f"Failed to cache threat level: {e}")
        
        return threat_level
    
    def _calculate_wolf_probability(self, player_name: str) -> float:
        """计算狼人概率维度"""
        trust_scores = self.memory_dao.get_trust_scores()
        trust = trust_scores.get(player_name, 50)
        return max(0.0, min(1.0, (100 - trust) / 100.0))
    
    def _calculate_strategic_value(self, player_name: str) -> float:
        """计算战略价值维度"""
        sheriff = self.memory_dao.get_sheriff()
        return 0.9 if sheriff == player_name else 0.5
    
    def _calculate_immediate_danger(self, current_day: int, alive_count: int) -> float:
        """计算即时危险维度"""
        if alive_count <= 6:
            return 0.8  # 后期，威胁更高
        elif alive_count <= 9:
            return 0.5  # 中期
        else:
            return 0.3  # 前期
    
    def _get_dynamic_weights(self, current_day: int) -> Dict[str, float]:
        """
        获取动态权重（优化：缓存权重配置 + 更精细的阶段划分）
        
        权重策略：
        - 早期（Day 1-2）：重视狼人概率和社会影响力
        - 中期（Day 3-5）：平衡各维度
        - 晚期（Day 6+）：重视狼人概率和即时危险
        
        Args:
            current_day: 当前天数
            
        Returns:
            权重字典
        """
        # 早期游戏（Day 1-2）
        if current_day <= 2:
            return {
                'wolf_probability': 0.40,
                'social_influence': 0.30,
                'strategic_value': 0.20,
                'immediate_danger': 0.10
            }
        # 晚期游戏（Day 6+）
        elif current_day >= 6:
            return {
                'wolf_probability': 0.50,
                'social_influence': 0.20,
                'strategic_value': 0.15,
                'immediate_danger': 0.15
            }
        # 中期游戏（Day 3-5）
        else:
            return {
                'wolf_probability': 0.45,
                'social_influence': 0.25,
                'strategic_value': 0.20,
                'immediate_danger': 0.10
            }
    
    def _calculate_social_influence(self, player_name: str) -> float:
        """
        计算社会影响力（企业级五星版 - 增强类型安全和边界检查）
        
        社会影响力评估维度：
        1. 发言次数（基础权重60%）
        2. 发言质量（权重20%）- 长度、逻辑性
        3. 互动频率（权重20%）- 被引用、被回应
        
        Args:
            player_name: 玩家名称
            
        Returns:
            社会影响力（0.0-1.0）
        """
        speech_history = self.memory_dao.get_speech_history()
        
        # 类型验证
        if not isinstance(speech_history, dict):
            logger.warning(f"speech_history is not dict: {type(speech_history)}")
            return 0.3
        
        player_speeches = speech_history.get(player_name, [])
        
        if not isinstance(player_speeches, list):
            logger.warning(f"player_speeches for {player_name} is not list: {type(player_speeches)}")
            return 0.3
        
        if not player_speeches:
            return 0.3
        
        # 1. 发言次数影响力（60%权重）
        speech_count = len(player_speeches)
        
        # 使用非线性映射（更符合实际影响力分布）
        if speech_count >= 8:
            count_score = 0.9
        elif speech_count >= 5:
            count_score = 0.8
        elif speech_count >= 3:
            count_score = 0.6
        elif speech_count >= 1:
            count_score = 0.4
        else:
            count_score = 0.3
        
        # 2. 发言质量影响力（20%权重）
        quality_score = self._calculate_speech_quality(player_speeches)
        
        # 3. 互动频率影响力（20%权重）
        interaction_score = self._calculate_interaction_frequency(player_name, speech_history)
        
        # 综合评分
        influence = count_score * 0.6 + quality_score * 0.2 + interaction_score * 0.2
        
        return max(0.0, min(1.0, influence))
    
    def _calculate_speech_quality(self, speeches: List[str]) -> float:
        """
        计算发言质量分数
        
        Args:
            speeches: 发言列表
            
        Returns:
            质量分数（0.0-1.0）
        """
        if not speeches:
            return 0.3
        
        # 计算平均发言长度
        total_length = sum(len(s) for s in speeches if isinstance(s, str))
        avg_length = total_length / len(speeches)
        
        # 长度映射到质量分数（100-500字符为最佳）
        if 100 <= avg_length <= 500:
            return 0.9
        elif 50 <= avg_length < 100 or 500 < avg_length <= 800:
            return 0.7
        elif avg_length < 50:
            return 0.4
        else:
            return 0.6
    
    def _calculate_interaction_frequency(self, player_name: str, speech_history: Dict) -> float:
        """
        计算互动频率分数
        
        Args:
            player_name: 玩家名称
            speech_history: 发言历史
            
        Returns:
            互动频率分数（0.0-1.0）
        """
        # 统计其他玩家提到该玩家的次数
        mention_count = 0
        
        for other_player, speeches in speech_history.items():
            if other_player == player_name:
                continue
            
            if not isinstance(speeches, list):
                continue
            
            for speech in speeches:
                if not isinstance(speech, str):
                    continue
                
                # 检查是否提到该玩家
                if player_name.lower() in speech.lower():
                    mention_count += 1
        
        # 映射到分数
        if mention_count >= 5:
            return 0.9
        elif mention_count >= 3:
            return 0.7
        elif mention_count >= 1:
            return 0.5
        else:
            return 0.3


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
    
    @monitor_performance
    def calculate(self, player_name: str, game_phase: str = "mid") -> float:
        """
        计算狼人概率（0.0-1.0）- 企业级五星算法
        
        使用多维度加权评估：
        1. 信任分数基础（35%权重）
        2. 投票模式分析（25-40%权重，动态调整）
        3. 发言质量评估（5%权重）
        4. 注入攻击检测（10-15%权重）
        5. 虚假引用检测（10-15%权重）
        
        Args:
            player_name: 玩家名称
            game_phase: 游戏阶段 ("early", "mid", "late")
        
        Returns:
            狼人概率（0.0-1.0）
        """
        # 验证输入（增强）
        if not player_name or not isinstance(player_name, str):
            logger.error(f"Invalid player_name: {player_name}, returning default 0.5")
            return 0.5
        
        if game_phase not in ["early", "mid", "late"]:
            logger.warning(f"Invalid game_phase: {game_phase}, using 'mid'")
            game_phase = "mid"
        
        # Component 1: 信任分数（基础权重35%）
        trust_scores = self.memory_dao.get_trust_scores()
        if not isinstance(trust_scores, dict):
            logger.warning(f"trust_scores is not dict: {type(trust_scores)}, using empty dict")
            trust_scores = {}
        
        trust_score = trust_scores.get(player_name, 50)
        # 类型安全检查
        if not isinstance(trust_score, (int, float)):
            logger.warning(f"Invalid trust_score type for {player_name}: {type(trust_score)}, using 50")
            trust_score = 50
        
        # 信任分数转换为狼人概率（线性映射）
        trust_component = max(0.0, min(1.0, (100 - trust_score) / 100.0))
        trust_weight = 0.35
        
        # Component 2: 投票模式（权重25%-40%，根据数据可靠性动态调整）
        voting_modifier = self._get_voting_modifier(player_name)
        voting_confidence = self._get_voting_confidence(player_name)
        voting_weight = 0.25 + voting_confidence * 0.15
        
        # 投票模式组件：基于信任分数+投票修正
        voting_component = max(0.0, min(1.0, trust_component + voting_modifier))
        
        # Component 3: 发言质量（权重5%）
        speech_modifier = self._get_speech_modifier(player_name)
        speech_weight = 0.05
        
        # 发言质量组件：基于信任分数+发言修正
        speech_component = max(0.0, min(1.0, trust_component + speech_modifier))
        
        # Component 4: 注入攻击（权重10%-15%，游戏后期权重更高）
        injection_component = self._get_injection_component(player_name)
        injection_weight = 0.10 if game_phase == "early" else 0.15
        
        # Component 5: 虚假引用（权重10%-15%，游戏后期权重更高）
        false_quote_component = self._get_false_quote_component(player_name)
        false_quote_weight = 0.10 if game_phase == "early" else 0.15
        
        # 归一化权重（确保总和为1.0）
        total_weight = trust_weight + voting_weight + speech_weight + injection_weight + false_quote_weight
        trust_weight /= total_weight
        voting_weight /= total_weight
        speech_weight /= total_weight
        injection_weight /= total_weight
        false_quote_weight /= total_weight
        
        # 计算综合概率（使用加权平均）
        # 每个组件都是独立的概率估计，通过加权平均得到最终概率
        wolf_prob = (
            trust_component * trust_weight +
            voting_component * voting_weight +
            speech_component * speech_weight +
            injection_component * injection_weight +
            false_quote_component * false_quote_weight
        )
        
        # 确保结果在有效范围内（双重保险）
        wolf_prob = max(0.0, min(1.0, wolf_prob))
        
        # 调试日志（仅在开发模式）
        if logger.level <= 10:  # DEBUG level
            logger.debug(
                f"[WOLF_PROB] {player_name}: "
                f"trust={trust_component:.2f}(w={trust_weight:.2f}), "
                f"voting={voting_component:.2f}(w={voting_weight:.2f}), "
                f"speech={speech_component:.2f}(w={speech_weight:.2f}), "
                f"injection={injection_component:.2f}(w={injection_weight:.2f}), "
                f"false_quote={false_quote_component:.2f}(w={false_quote_weight:.2f}), "
                f"final={wolf_prob:.2f}"
            )
        
        return wolf_prob
    
    def _get_voting_modifier(self, player_name: str) -> float:
        """获取投票模式修正值（增强类型安全）"""
        voting_results = self.memory_dao.get_voting_results()
        
        # 类型验证
        if not isinstance(voting_results, dict):
            logger.warning(f"voting_results is not dict: {type(voting_results)}")
            return 0.0
        
        if player_name not in voting_results:
            return 0.0
        
        results = voting_results[player_name]
        
        if not isinstance(results, list) or len(results) < 2:
            return 0.0
        
        # 计算准确率（带类型检查）
        from werewolf.optimization.utils.safe_math import safe_divide
        
        wolf_votes = 0
        valid_votes = 0
        
        for result in results:
            # 验证结果格式
            if not isinstance(result, (tuple, list)) or len(result) < 2:
                logger.debug(f"Skipping invalid voting result: {result}")
                continue
            
            target, was_wolf = result[0], result[1]
            
            # 类型检查
            if not isinstance(was_wolf, bool):
                logger.debug(f"Skipping non-boolean was_wolf: {was_wolf}")
                continue
            
            valid_votes += 1
            if was_wolf:
                wolf_votes += 1
        
        if valid_votes == 0:
            return 0.0
        
        accuracy_rate = safe_divide(wolf_votes, valid_votes, default=0.5)
        
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
        """获取投票数据的置信度（增强类型安全）"""
        voting_results = self.memory_dao.get_voting_results()
        
        # 类型验证
        if not isinstance(voting_results, dict):
            logger.warning(f"voting_results is not dict: {type(voting_results)}")
            return 0.0
        
        if player_name not in voting_results:
            return 0.0
        
        results = voting_results[player_name]
        
        if not isinstance(results, list):
            logger.warning(f"voting results for {player_name} is not list: {type(results)}")
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
        """获取发言质量修正值（增强类型安全）"""
        speech_history = self.memory_dao.get_speech_history()
        
        # 类型验证
        if not isinstance(speech_history, dict):
            logger.warning(f"speech_history is not dict: {type(speech_history)}")
            return 0.0
        
        player_speeches = speech_history.get(player_name, [])
        
        if not isinstance(player_speeches, list):
            logger.warning(f"player_speeches for {player_name} is not list: {type(player_speeches)}")
            return 0.0
        
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
        """获取注入攻击组件（增强类型安全）"""
        injection_attempts = self.memory_dao.get_injection_attempts()
        
        # 类型验证
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not list: {type(injection_attempts)}")
            return 0.0
        
        player_injections = []
        for attempt in injection_attempts:
            # 验证每个attempt的格式
            if not isinstance(attempt, dict):
                logger.debug(f"Skipping non-dict injection attempt: {type(attempt)}")
                continue
            
            # 检查player_name字段
            attempt_player = attempt.get('player_name')
            if attempt_player == player_name:
                player_injections.append(attempt)
        
        if not player_injections:
            return 0.0
        
        # 有注入攻击，高度可疑
        return 0.9
    
    def _get_false_quote_component(self, player_name: str) -> float:
        """获取虚假引用组件（增强类型安全）"""
        false_quotations = self.memory_dao.get_false_quotations()
        
        # 类型验证
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not list: {type(false_quotations)}")
            return 0.0
        
        player_quotes = []
        for quote in false_quotations:
            # 验证每个quote的格式
            if not isinstance(quote, dict):
                logger.debug(f"Skipping non-dict false quotation: {type(quote)}")
                continue
            
            # 检查player_name字段
            quote_player = quote.get('player_name')
            if quote_player == player_name:
                player_quotes.append(quote)
        
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
