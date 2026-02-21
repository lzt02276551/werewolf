# -*- coding: utf-8 -*-
"""
猎人代理人分析器模块
实现各种分析器，使用继承和多态
"""

# 导入重构后的组件
from werewolf.core.base_components import BaseAnalyzer, BaseMemoryDAO
from werewolf.common.utils import DataValidator, CacheManager
from .config import HunterConfig
from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
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
        """
        获取内存中的值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            存储的值或默认值
        """
        return self.memory.load_variable(key) if hasattr(self.memory, 'load_variable') else default
    
    def set(self, key: str, value):
        """
        设置内存中的值
        
        Args:
            key: 键名
            value: 要存储的值
        """
        if hasattr(self.memory, 'set_variable'):
            self.memory.set_variable(key, value)
    
    def get_my_name(self) -> str:
        """获取自己的名字"""
        return self.get("name", "Unknown")
    
    def get_can_shoot(self) -> bool:
        """获取是否可以开枪"""
        return self.get("can_shoot", True)
    
    def set_can_shoot(self, can_shoot: bool):
        """设置是否可以开枪"""
        self.set("can_shoot", can_shoot)
    
    def get_trust_scores(self) -> Dict[str, float]:
        """获取信任分数字典"""
        return self.get("trust_scores", {})
    
    def set_trust_scores(self, scores: Dict[str, float]):
        """设置信任分数字典"""
        self.set("trust_scores", scores)
    
    def get_trust_history(self) -> Dict[str, List[float]]:
        """获取信任分数历史"""
        return self.get("trust_history", {})
    
    def set_trust_history(self, history: Dict[str, List[float]]):
        """设置信任分数历史"""
        self.set("trust_history", history)
    
    def get_voting_history(self) -> Dict[str, List[str]]:
        """获取投票历史"""
        return self.get("voting_history", {})
    
    def get_voting_results(self) -> Dict[str, List[Tuple[str, bool]]]:
        """获取投票结果（包含是否是狼人的信息）"""
        return self.get("voting_results", {})
    
    def set_voting_results(self, results: Dict[str, List[Tuple[str, bool]]]):
        """设置投票结果"""
        self.set("voting_results", results)
    
    def get_speech_history(self) -> Dict[str, List[str]]:
        """获取发言历史"""
        return self.get("speech_history", {})
    
    def set_speech_history(self, history: Dict[str, List[str]]):
        """设置发言历史"""
        self.set("speech_history", history)
    
    def get_injection_attempts(self) -> List[Dict[str, Any]]:
        """获取注入尝试记录"""
        return self.get("injection_attempts", [])
    
    def get_false_quotations(self) -> List[Dict[str, Any]]:
        """获取虚假引用记录"""
        return self.get("false_quotations", [])
    
    def get_dead_players(self) -> set:
        """获取死亡玩家集合"""
        return self.get("dead_players", set())
    
    def get_sheriff(self) -> Optional[str]:
        """获取当前警长"""
        return self.get("sheriff", None)
    
    def get_history(self) -> List[str]:
        """获取游戏历史记录"""
        if hasattr(self.memory, 'load_history'):
            return self.memory.load_history()
        return []


# ==================== 信任分数分析器 ====================

class TrustScoreAnalyzer(BaseAnalyzer):
    """信任分数分析器"""
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    def _get_default_result(self) -> float:
        """返回默认的狼人概率"""
        return 0.5
    
    def _validate_input(self, player_name: str, *args, **kwargs) -> bool:
        return self.validator.validate_player_name(player_name)
    
    def _do_analyze(self, player_name: str, *args, **kwargs) -> float:
        """分析玩家的信任分数，返回狼人概率(0-1)"""
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(player_name, 50)
        
        # 非线性映射：信任度越低，狼人概率越高
        wolf_prob = max(0.0, min(1.0, (100 - trust_score) / 100.0))
        return wolf_prob
    
    def update_trust_score(
        self, 
        player_name: str, 
        delta: float, 
        reason: str = "",
        confidence: float = 1.0,
        source_reliability: float = 1.0
    ):
        """
        更新信任分数（使用优化的Sigmoid衰减算法）
        
        Args:
            player_name: 玩家名称
            delta: 分数变化量
            reason: 更新原因
            confidence: 信息置信度(0.0-1.0)
            source_reliability: 信息来源可靠度(0.0-1.0)
        
        验证需求：AC-1.3.1
        """
        # 导入优化的信任分数更新算法
        from werewolf.optimization.algorithms.trust_score import update_trust_score
        
        if not self.validator.validate_player_name(player_name):
            logger.warning(f"[TRUST UPDATE] Invalid player_name: {player_name}")
            return
        
        trust_scores = self.memory_dao.get_trust_scores()
        trust_history = self.memory_dao.get_trust_history()
        
        # 初始化历史记录
        if player_name not in trust_history:
            trust_history[player_name] = []
        
        if player_name in trust_scores:
            old_score = trust_scores[player_name]
            
            # 应用置信度和来源可靠性权重
            evidence_impact = delta * confidence * source_reliability
            
            # 历史一致性检查
            if len(trust_history[player_name]) >= 3:
                recent_changes = trust_history[player_name][-3:]
                avg_trend = sum(recent_changes) / len(recent_changes)
                
                if (avg_trend > 0 and evidence_impact < 0) or (avg_trend < 0 and evidence_impact > 0):
                    evidence_impact *= 0.5
                    logger.debug(f"[TRUST] {player_name}: Trend reversal detected, dampening change")
            
            # 使用优化的Sigmoid衰减算法
            config = {
                'decay_steepness': 0.1,
                'decay_midpoint': 50.0
            }
            
            new_score = update_trust_score(old_score, evidence_impact, config)
            trust_scores[player_name] = new_score
            
            # 记录历史
            trust_history[player_name].append(evidence_impact)
            if len(trust_history[player_name]) > 10:
                trust_history[player_name] = trust_history[player_name][-10:]
            
            logger.info(
                f"Trust: {player_name} {old_score:.1f} -> {new_score:.1f} "
                f"(Δ{evidence_impact:.1f}, conf:{confidence:.2f}) - {reason} [Sigmoid衰减]"
            )
        else:
            # 初始化
            evidence_impact = delta * confidence * source_reliability
            
            # 使用优化的Sigmoid衰减算法从默认分数50开始
            config = {
                'decay_steepness': 0.1,
                'decay_midpoint': 50.0
            }
            
            initial_score = update_trust_score(50.0, evidence_impact, config)
            trust_scores[player_name] = initial_score
            trust_history[player_name].append(evidence_impact)
            
            logger.info(f"Trust: {player_name} = {initial_score:.1f} ({reason}) [Sigmoid衰减]")
        
        self.memory_dao.set_trust_scores(trust_scores)
        self.memory_dao.set_trust_history(trust_history)


# ==================== 投票模式分析器 ====================

class VotingPatternAnalyzer(BaseAnalyzer):
    """投票模式分析器"""
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    def _get_default_result(self) -> float:
        """返回默认的修正值"""
        return 0.0
    
    def _validate_input(self, player_name: str, *args, **kwargs) -> bool:
        return self.validator.validate_player_name(player_name)
    
    def _do_analyze(self, player_name: str, *args, **kwargs) -> float:
        """
        分析投票模式，返回狼人概率修正值（-0.3到0.3）
        
        准确率高 -> 负值（降低狼人概率）
        准确率低 -> 正值（提高狼人概率）
        """
        voting_results = self.memory_dao.get_voting_results()
        
        if player_name not in voting_results:
            return 0.0
        
        results = voting_results[player_name]
        
        if not isinstance(results, list) or len(results) < 2:
            return 0.0
        
        # 过滤有效记录
        valid_results = [r for r in results if self.validator.validate_voting_record(r)]
        
        if len(valid_results) < 2:
            return 0.0
        
        # 计算准确率
        wolf_votes = sum(1 for _, was_wolf in valid_results if was_wolf)
        accuracy_rate = wolf_votes / len(valid_results)
        
        # 映射到修正值
        if accuracy_rate >= 0.7:
            return -0.25  # 高准确率，可能是好人
        elif accuracy_rate >= 0.6:
            return -0.15
        elif accuracy_rate >= 0.5:
            return 0.0
        elif accuracy_rate >= 0.4:
            return 0.15
        elif accuracy_rate >= 0.3:
            return 0.20
        else:
            return 0.30  # 低准确率，可能是狼人
    
    def track_voting_accuracy(self, voter: str, target: str, was_wolf: bool):
        """
        跟踪投票准确率
        
        Args:
            voter: 投票者
            target: 被投票者
            was_wolf: 被投票者是否是狼人
        """
        if not all([
            self.validator.validate_player_name(voter),
            self.validator.validate_player_name(target),
            isinstance(was_wolf, bool)
        ]):
            logger.warning(f"[VOTING ACCURACY] Invalid input: {voter}, {target}, {was_wolf}")
            return
        
        voting_results = self.memory_dao.get_voting_results()
        
        if voter not in voting_results:
            voting_results[voter] = []
        
        # 检查是否已记录
        if voting_results[voter]:
            last_record = voting_results[voter][-1]
            if self.validator.validate_voting_record(last_record) and last_record[0] == target:
                logger.debug(f"[VOTING ACCURACY] Already recorded {voter} -> {target}")
                return
        
        # 添加新记录
        voting_results[voter].append((target, was_wolf))
        self.memory_dao.set_voting_results(voting_results)
        
        # 计算并记录准确率
        valid_history = [r for r in voting_results[voter] if self.validator.validate_voting_record(r)]
        if len(valid_history) >= 2:
            wolf_votes = sum(1 for _, is_wolf in valid_history if is_wolf)
            accuracy_rate = wolf_votes / len(valid_history)
            logger.info(f"[VOTING ACCURACY] {voter}: {wolf_votes}/{len(valid_history)} = {accuracy_rate:.0%}")


# ==================== 发言质量分析器 ====================

class SpeechQualityAnalyzer(BaseAnalyzer):
    """Speech quality analyzer"""
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.validator = DataValidator()
    
    def _get_default_result(self) -> float:
        """返回默认的修正值"""
        return 0.0
        
        # Pre-compiled regex patterns
        self._logical_keywords = {"because", "therefore", "analyze", "evidence", "suspect", "trust", "vote"}
        self._emotion_keywords = {"trust", "believe", "definitely", "absolutely"}
    
    def _validate_input(self, player_name: str, message: str = None, *args, **kwargs) -> bool:
        return self.validator.validate_player_name(player_name)
    
    def _do_analyze(self, player_name: str, message: str = None, *args, **kwargs) -> float:
        """
        Analyze speech quality, return wolf probability modifier (-0.15 to 0.20)
        
        High quality speech -> negative value (lower wolf probability)
        Low quality speech -> positive value (higher wolf probability)
        """
        speech_history = self.memory_dao.get_speech_history()
        
        if player_name not in speech_history:
            return 0.10  # No speech, slightly suspicious
        
        speeches = speech_history[player_name]
        if not speeches:
            return 0.10
        
        modifier = 0.0
        speech_count = len(speeches)
        
        # Speech frequency analysis
        if speech_count <= 1:
            modifier += 0.15  # Too few speeches
        elif speech_count >= 6:
            modifier -= 0.08  # Active speaker
        elif speech_count >= 3:
            modifier -= 0.03
        
        # Speech length analysis
        avg_length = sum(len(s) for s in speeches) / len(speeches)
        if avg_length < 50:
            modifier += 0.20  # Too short
        elif avg_length > 300:
            modifier -= 0.12  # Detailed
        elif avg_length > 150:
            modifier -= 0.05
        
        # Speech consistency analysis
        if len(speeches) >= 3:
            lengths = [len(s) for s in speeches]
            avg = sum(lengths) / len(lengths)
            variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
            std_dev = variance ** 0.5
            
            if avg > 0:
                cv = std_dev / avg  # Coefficient of variation
                if cv > 0.5:
                    modifier += 0.10  # Inconsistent
        
        # Logical keyword analysis (if message provided)
        if message:
            message_lower = message.lower()
            logic_count = sum(1 for kw in self._logical_keywords if kw in message_lower)
            if logic_count >= 3:
                modifier -= 0.08  # Strong logic
        
        return max(-0.15, min(0.20, modifier))


class ThreatLevelAnalyzer(BaseAnalyzer):
    """威胁等级分析器"""
    
    def __init__(self, config: HunterConfig, memory_dao, cache_manager: CacheManager):
        super().__init__(config)
        self.memory_dao = memory_dao
        self.cache_manager = cache_manager
        self.validator = DataValidator()
    
    def _get_default_result(self) -> float:
        """返回默认的修正值"""
        return 0.0
    
    def _validate_input(self, player_name: str, current_day: int = 1, alive_count: int = 12, *args, **kwargs) -> bool:
        return self.validator.validate_player_name(player_name)
    
    def _do_analyze(self, player_name: str, current_day: int = 1, alive_count: int = 12, *args, **kwargs) -> float:
        """
        Calculate threat level (0.0-1.0)
        
        Factors considered:
        - Sheriff status
        - Speech frequency and influence
        - Voting participation and accuracy
        - Social influence
        - Game phase adjustment
        """
        # Check cache
        cache_key = f"threat_{player_name}_{current_day}"
        cached = self.cache_manager.get(cache_key, current_day)
        if cached is not None:
            return cached
        
        threat = 0.0
        
        # Factor 1: 警长身份
        sheriff = self.memory_dao.get_sheriff()
        if sheriff == player_name:
            if alive_count <= 6:
                threat += 0.40  # 后期警长威胁更大
            else:
                threat += 0.30
        
        # Factor 2: 发言频率
        speech_history = self.memory_dao.get_speech_history()
        if player_name in speech_history:
            speech_count = len(speech_history[player_name])
            
            if speech_count >= 7:
                threat += 0.25
            elif speech_count >= 5:
                threat += 0.20
            elif speech_count >= 3:
                threat += 0.12
            elif speech_count >= 2:
                threat += 0.05
            else:
                threat -= 0.10  # 边缘玩家
        
        # Factor 3: 投票参与度
        voting_results = self.memory_dao.get_voting_results()
        if player_name in voting_results:
            results = voting_results[player_name]
            vote_count = len(results) if isinstance(results, list) else 0
            
            base_threat = 0.15 if vote_count >= 4 else (0.08 if vote_count >= 2 else -0.08)
            
            # 投票准确性加成
            if isinstance(results, list) and len(results) >= 2:
                valid_results = [r for r in results if self.validator.validate_voting_record(r)]
                if valid_results:
                    wolf_votes = sum(1 for _, was_wolf in valid_results if was_wolf)
                    accuracy = wolf_votes / len(valid_results)
                    
                    if accuracy >= 0.7:
                        base_threat *= 1.5  # 准确的投票者威胁更大
                    elif accuracy <= 0.3:
                        base_threat *= 0.7
            
            threat += base_threat
        
        # Factor 4: 社交影响力
        social_influence = self._calculate_social_influence(player_name)
        threat += social_influence * 0.15
        
        # Factor 5: 游戏阶段调整
        if alive_count <= 5:
            threat *= 1.3  # 残局每个玩家都很关键
        elif current_day <= 2:
            threat *= 0.8  # 早期威胁评估不够准确
        
        # 归一化
        threat = max(0.0, min(1.0, threat))
        
        # 缓存结果
        self.cache_manager.set(cache_key, threat, current_day)
        
        logger.debug(f"[THREAT] {player_name}: {threat:.3f} (day={current_day}, alive={alive_count})")
        return threat
    
    def _calculate_social_influence(self, player_name: str) -> float:
        """计算社交影响力（0.0-1.0）"""
        speech_history = self.memory_dao.get_speech_history()
        
        # 被提及次数
        mentioned_count = sum(
            1 for p, speeches in speech_history.items()
            if p != player_name
            for s in speeches
            if player_name in s
        )
        
        # 提及他人次数
        mentions_others = 0
        if player_name in speech_history:
            mentions_others = sum(s.count("No.") for s in speech_history[player_name])
        
        # 影响力 = 被提及 + 主动互动
        influence = min(1.0, mentioned_count * 0.1 + mentions_others * 0.05)
        return influence


# ==================== 狼人概率计算器（组合多个分析器）====================

class WolfProbabilityCalculator:
    """狼人概率计算器，组合多个分析器"""
    
    def __init__(
        self, 
        config: HunterConfig,
        trust_analyzer: TrustScoreAnalyzer,
        voting_analyzer: VotingPatternAnalyzer,
        speech_analyzer: SpeechQualityAnalyzer,
        memory_dao
    ):
        self.config = config
        self.trust_analyzer = trust_analyzer
        self.voting_analyzer = voting_analyzer
        self.speech_analyzer = speech_analyzer
        self.memory_dao = memory_dao
    
    @safe_execute(default_return=0.5)
    def calculate(self, player_name: str, game_phase: str = "mid") -> float:
        """
        计算狼人概率（0.0-1.0）
        
        Args:
            player_name: 玩家名称
            game_phase: 游戏阶段 ("early", "mid", "late")
        
        Returns:
            狼人概率
        """
        # Component 1: 信任分数（基础权重35%）
        trust_component = self.trust_analyzer.analyze(player_name)
        trust_weight = 0.35
        
        # Component 2: 投票模式（权重25%-40%，根据数据可靠性）
        voting_modifier = self.voting_analyzer.analyze(player_name)
        voting_confidence = self._get_voting_confidence(player_name)
        voting_weight = 0.25 + voting_confidence * 0.15
        
        # Component 3: 发言质量（权重5%）
        speech_modifier = self.speech_analyzer.analyze(player_name)
        speech_weight = 0.05
        
        # Component 4: 注入攻击（权重20%）
        injection_component = self._get_injection_component(player_name)
        injection_weight = 0.20
        
        # Component 5: 虚假引用（权重15%）
        false_quote_component = self._get_false_quote_component(player_name)
        false_quote_weight = 0.15
        
        # 归一化权重
        total_weight = trust_weight + voting_weight + speech_weight + injection_weight + false_quote_weight
        trust_weight /= total_weight
        voting_weight /= total_weight
        speech_weight /= total_weight
        injection_weight /= total_weight
        false_quote_weight /= total_weight
        
        # 加权求和
        base_prob = (
            trust_component * trust_weight +
            (0.5 + voting_modifier) * voting_weight +
            (0.5 + speech_modifier) * speech_weight +
            injection_component * injection_weight +
            false_quote_component * false_quote_weight
        )
        
        # 游戏阶段调整
        if game_phase == "early":
            base_prob = 0.3 + base_prob * 0.4  # 早期更保守
        elif game_phase == "late":
            if base_prob > 0.6:
                base_prob = min(0.95, base_prob * 1.2)  # 后期放大差异
            elif base_prob < 0.4:
                base_prob = max(0.05, base_prob * 0.8)
        
        return max(0.0, min(1.0, base_prob))
    
    def _get_voting_confidence(self, player_name: str) -> float:
        """获取投票数据置信度"""
        voting_results = self.memory_dao.get_voting_results()
        
        if player_name not in voting_results:
            return 0.5
        
        results = voting_results[player_name]
        if isinstance(results, list):
            sample_count = len([r for r in results if isinstance(r, tuple) and len(r) == 2])
            return min(1.0, 0.3 + sample_count * 0.15)
        
        return 0.5
    
    def _get_injection_component(self, player_name: str) -> float:
        """获取注入攻击组件"""
        injection_attempts = self.memory_dao.get_injection_attempts()
        injection_count = sum(1 for att in injection_attempts if att.get("player") == player_name)
        return min(1.0, injection_count * 0.5)
    
    def _get_false_quote_component(self, player_name: str) -> float:
        """获取虚假引用组件"""
        false_quotations = self.memory_dao.get_false_quotations()
        false_quote_count = sum(1 for fq in false_quotations if fq.get("accuser") == player_name)
        return min(1.0, false_quote_count * 0.4)
