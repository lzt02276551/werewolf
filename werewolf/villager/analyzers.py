# -*- coding: utf-8 -*-
"""
平民代理人分析器模块
实现各种分析功能：信任分数、狼人概率、投票模式等
"""

from typing import Dict, List, Tuple, Optional
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseAnalyzer
from werewolf.common.utils import DataValidator
from .config import VillagerConfig
import math


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


class TrustScoreManager(BaseAnalyzer):
    """信任分数管理器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
        self.trust_history: Dict[str, List[Dict]] = {}
    
    def _get_default_result(self) -> int:
        """获取默认信任分数"""
        return 50
    
    def _do_analyze(self, player: str, delta: int, confidence: float, source_reliability: float,
                    trust_scores: Dict[str, int]) -> int:
        """执行信任分数更新(内部方法)"""
        return self._update_trust_score(player, delta, confidence, source_reliability, trust_scores)
    
    def clamp(self, score: int) -> int:
        """确保信任分数在有效范围内 (0-100)"""
        return max(0, min(100, score))
    
    @safe_execute(default_return=50)
    def analyze(self, player: str, delta: int, confidence: float, source_reliability: float,
                trust_scores: Dict[str, int]) -> int:
        """
        企业级信任分数更新算法 - 非线性衰减机制
        
        Args:
            player: 玩家名称
            delta: 基础变化量
            confidence: 证据置信度 (0.0-1.0)
            source_reliability: 来源可靠性 (0.0-1.0)
            trust_scores: 信任分数字典
        
        Returns:
            new_score: 更新后的信任分数
        """
        return self._update_trust_score(player, delta, confidence, source_reliability, trust_scores)
    
    def _update_trust_score(self, player: str, delta: int, confidence: float, 
                           source_reliability: float, trust_scores: Dict[str, int]) -> int:
        """
        内部方法: 企业级信任分数更新算法 - 非线性衰减机制
        
        Args:
            player: 玩家名称
            delta: 基础变化量
            confidence: 证据置信度 (0.0-1.0)
            source_reliability: 来源可靠性 (0.0-1.0)
            trust_scores: 信任分数字典
        
        Returns:
            new_score: 更新后的信任分数 (0-100)
        """
        current_score = trust_scores.get(player, 50)
        
        # 1. 应用置信度和来源可靠性权重
        weighted_delta = delta * confidence * source_reliability
        
        # 2. 非线性衰减：使用sigmoid函数
        def decay_factor(score, target_direction):
            """计算衰减系数（0-100范围）"""
            if target_direction > 0:
                # 向100靠近，衰减系数随分数增加而减小
                distance_to_max = 100 - score
                return max(0.1, distance_to_max / 100)
            else:
                # 向0靠近，衰减系数随分数减小而减小
                distance_to_min = score
                return max(0.1, distance_to_min / 100)
        
        direction = 1 if weighted_delta > 0 else -1
        decay = decay_factor(current_score, direction)
        adjusted_delta = weighted_delta * decay
        
        # 3. 历史一致性检查
        if player not in self.trust_history:
            self.trust_history[player] = []
        
        player_history = self.trust_history[player]
        
        # 检查趋势反转
        if len(player_history) >= 2:
            recent_deltas = [h['delta'] for h in player_history[-3:]]
            recent_trend = sum(1 if d > 0 else -1 for d in recent_deltas)
            current_direction = 1 if adjusted_delta > 0 else -1
            
            if (recent_trend > 1 and current_direction < 0) or (recent_trend < -1 and current_direction > 0):
                adjusted_delta *= 0.5
                logger.debug(f"Trust trend reversal detected for {player}, weakening delta by 50%")
        
        # 4. 应用变化
        new_score = self.clamp(int(current_score + adjusted_delta))
        trust_scores[player] = new_score
        
        # 5. 记录历史（保留最近10次）
        player_history.append({
            'delta': adjusted_delta,
            'confidence': confidence,
            'source_reliability': source_reliability,
            'old_score': current_score,
            'new_score': new_score
        })
        if len(player_history) > self.config.MAX_TRUST_HISTORY_PER_PLAYER:
            player_history.pop(0)
        
        # 6. 全局清理：限制总历史记录数（防止内存泄漏）
        if len(self.trust_history) > self.config.MAX_TRUST_HISTORY_PLAYERS:
            oldest_players = sorted(self.trust_history.keys())[:10]
            for old_player in oldest_players:
                self.trust_history.pop(old_player, None)
        
        logger.debug(f"Trust score updated: {player} {current_score} -> {new_score} "
                    f"(base_delta: {delta:+d}, weighted: {weighted_delta:+.1f}, "
                    f"adjusted: {adjusted_delta:+.1f}, decay: {decay:.2f})")
        return new_score


class TrustScoreCalculator(BaseAnalyzer):
    """信任分数计算器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
    
    def _get_default_result(self) -> int:
        """获取默认信任分数"""
        return 50
    
    def _do_analyze(self, player_name: str, context: Dict) -> int:
        """执行信任分数计算(内部方法)"""
        return self._calculate_trust_score(player_name, context)
    
    @safe_execute(default_return=50)
    def analyze(self, player_name: str, context: Dict) -> int:
        """
        计算玩家的信任分数 (0 to 100)
        
        企业级改进版本:
        1. 使用加权平均而非简单叠加
        2. 考虑时间衰减因子
        3. 考虑行为频率和一致性
        4. 平衡正负指标权重
        5. 添加上下文关联验证
        6. 使用非线性评分函数
        """
        return self._calculate_trust_score(player_name, context)
    
    def _calculate_trust_score(self, player_name: str, context: Dict) -> int:
        """
        内部方法: 计算玩家的信任分数 (0 to 100)
        
        Args:
            player_name: 玩家名称
            context: 游戏上下文
            
        Returns:
            信任分数 (0-100)
        """
        # 边界检查
        if not DataValidator.validate_player_name(player_name):
            logger.warning(f"[TRUST SCORE] Invalid player_name: {player_name}")
            return 50
        
        if not isinstance(context, dict):
            logger.warning(f"[TRUST SCORE] Invalid context type: {type(context)}")
            return 50
        
        # 安全获取数据
        player_data_dict = DataValidator.safe_get_dict(context.get("player_data"))
        player_data = DataValidator.safe_get_dict(player_data_dict.get(player_name))
        seer_checks = DataValidator.safe_get_dict(context.get("seer_checks"))
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        
        current_day = DataValidator.safe_get_int(game_state.get("current_day", 1), 1)

        # Seer verification (highest priority - 绝对真理)
        if player_name in seer_checks:
            result = seer_checks[player_name]
            if isinstance(result, str):
                if "wolf" in result.lower() or "werewolf" in result.lower():
                    return 0  # Confirmed wolf (最低信任)
                else:
                    return 100  # Confirmed good (最高信任)
        
        # 特殊情况：夜晚被杀（强好人信号）
        if player_data.get("killed_at_night"):
            logger.debug(f"[TRUST SCORE] {player_name} was killed at night - strong good signal")
            return 90
        
        # 特殊情况：多次注入攻击（明显狼人）
        injection_count = DataValidator.safe_get_int(player_data.get("injection_count", 0))
        if injection_count >= 3:
            logger.debug(f"[TRUST SCORE] {player_name} has {injection_count} injection attacks - obvious wolf")
            return 5  # 极低信任

        # === 企业级信任分数计算系统 ===
        
        # A. 发言行为评分 (-100 to +100)
        speech_score = 0.0
        speech_weight = 0.0
        
        # 恶意注入攻击 - 使用非线性惩罚函数
        if player_data.get("malicious_injection"):
            injection_count = DataValidator.safe_get_int(player_data.get("injection_count", 1), 1)
            # 非线性惩罚：1次=-45, 2次=-65, 3次=-80, 4次+=-85
            penalty = -45 - (35 * (1 - math.exp(-injection_count / 2)))
            speech_score += max(penalty, -85)
            speech_weight += 1.2
        
        # 虚假引用 - 渐进式惩罚
        if player_data.get("false_quotes"):
            false_quote_count = DataValidator.safe_get_int(player_data.get("false_quote_count", 1), 1)
            penalty = -35 - min(35, false_quote_count * 20)
            speech_score += penalty
            speech_weight += 1.0
        
        # 自相矛盾 - 轻度惩罚
        if player_data.get("contradictions"):
            contradiction_count = DataValidator.safe_get_int(player_data.get("contradiction_count", 1), 1)
            penalty = -15 - min(20, contradiction_count * 10)
            speech_score += penalty
            speech_weight += 0.5
        
        # 逻辑发言 - 正向加分
        if player_data.get("logical_speech"):
            speech_score += 35
            speech_weight += 0.8
        
        # 有益分析 - 正向加分
        if player_data.get("helpful_analysis"):
            speech_score += 25
            speech_weight += 0.7
        
        # 发言过短 - 轻度惩罚
        if player_data.get("short_speech"):
            speech_score -= 12
            speech_weight += 0.3
        
        # 归一化发言评分
        if speech_weight > 0:
            speech_score = speech_score / speech_weight
        else:
            speech_score = 0.0
        
        # B. 投票行为评分 (-100 to +100)
        vote_score = 0.0
        vote_weight = 0.0
        
        vote_history = DataValidator.safe_get_list(player_data.get("vote_history"))
        
        if len(vote_history) >= 2:
            # 计算投票准确度 - 使用贝叶斯平滑
            wolf_votes = sum(1 for v in vote_history if isinstance(v, dict) and v.get("target_was_wolf"))
            good_votes = sum(1 for v in vote_history if isinstance(v, dict) and v.get("target_was_good"))
            total_votes = len(vote_history)
            
            valid_result_count = wolf_votes + good_votes
            
            if valid_result_count >= 2:
                # 贝叶斯平滑
                prior_wolf = 1.0
                prior_good = 2.0
                
                smoothed_wolf_rate = (wolf_votes + prior_wolf) / (valid_result_count + prior_wolf + prior_good)
                smoothed_good_rate = (good_votes + prior_good) / (valid_result_count + prior_wolf + prior_good)
                
                net_accuracy = smoothed_wolf_rate - smoothed_good_rate
                
                # 使用S型函数(tanh)使评分更平滑
                vote_score = math.tanh(net_accuracy * 1.5) * 85
                vote_weight = 1.0 + (valid_result_count / 10.0)
                
                logger.debug(f"[TRUST SCORE] {player_name} vote accuracy: wolf={wolf_votes}/{valid_result_count}, "
                           f"good={good_votes}/{valid_result_count}, net={net_accuracy:.2f}, score={vote_score:.1f}")
            else:
                if player_data.get("accurate_votes"):
                    vote_score += 35
                    vote_weight += 0.6
                
                if player_data.get("wolf_protecting_votes"):
                    vote_score -= 45
                    vote_weight += 0.7
        else:
            if player_data.get("accurate_votes"):
                vote_score += 30
                vote_weight += 0.5
            
            if player_data.get("wolf_protecting_votes"):
                vote_score -= 40
                vote_weight += 0.6
        
        # 归一化投票评分
        if vote_weight > 0:
            vote_score = vote_score / vote_weight
        else:
            vote_score = 0.0
        
        # C. 死亡关联评分 (-100 to +100)
        death_score = 0.0
        death_weight = 0.0
        
        # 反对已死好人
        if player_data.get("opposed_to_dead_good"):
            opposed_players = DataValidator.safe_get_list(player_data.get("opposed_players"))
            verified_good_opposition = False
            
            for opposed in opposed_players:
                if opposed in seer_checks:
                    result = seer_checks[opposed]
                    if isinstance(result, str) and "wolf" not in result.lower():
                        verified_good_opposition = True
                        break
            
            if verified_good_opposition:
                death_score -= 55
                death_weight += 1.0
            else:
                death_score -= 25
                death_weight += 0.4
        
        # 被投出
        if player_data.get("voted_out"):
            death_score -= 35
            death_weight += 0.6
        
        # 保护了已死的狼人
        if player_data.get("protected_dead_wolf"):
            death_score -= 65
            death_weight += 1.1
        
        # 被已死的好人信任
        if player_data.get("trusted_by_dead_good"):
            death_score += 35
            death_weight += 0.7
        
        # 归一化死亡关联评分
        if death_weight > 0:
            death_score = death_score / death_weight
        else:
            death_score = 0.0
        
        # D. 角色行为评分 (-100 to +100)
        role_score = 0.0
        role_weight = 0.0
        
        if player_data.get("sheriff_elected"):
            role_score += 25
            role_weight += 0.5
        
        if player_data.get("sheriff_candidate"):
            role_score += 12
            role_weight += 0.3
        
        if player_data.get("over_acting"):
            role_score -= 20
            role_weight += 0.4
        
        # 归一化角色行为评分
        if role_weight > 0:
            role_score = role_score / role_weight
        else:
            role_score = 0.0
        
        # 2. 时间衰减因子
        if current_day <= 1:
            time_decay = 0.65
        elif current_day == 2:
            time_decay = 0.75
        elif current_day == 3:
            time_decay = 0.85
        elif current_day == 4:
            time_decay = 0.92
        else:
            time_decay = 1.0
        
        # 3. 综合评分（加权平均）
        category_weights = {
            'speech': 0.30,
            'vote': 0.40,
            'death': 0.20,
            'role': 0.10
        }
        
        weighted_sum = (
            speech_score * category_weights['speech'] +
            vote_score * category_weights['vote'] +
            death_score * category_weights['death'] +
            role_score * category_weights['role']
        )
        
        # 应用时间衰减
        decision_tree_score = weighted_sum * time_decay
        
        # 转换到 0 到 100 范围（从 -100~100 映射到 0~100）
        # 公式: (score + 100) / 2
        normalized_score = (decision_tree_score + 100.0) / 2.0
        final_score = max(0.0, min(100.0, normalized_score))
        
        logger.debug(f"[TRUST SCORE] {player_name} breakdown: "
                    f"Speech={speech_score:.1f}, Vote={vote_score:.1f}, "
                    f"Death={death_score:.1f}, Role={role_score:.1f}, "
                    f"Time_decay={time_decay:.2f}, Raw={decision_tree_score:.1f}, Final={final_score:.1f}")
        
        return int(final_score)


class VotingPatternAnalyzer(BaseAnalyzer):
    """投票模式分析器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
    
    def _get_default_result(self) -> str:
        """获取默认投票模式"""
        return "unknown"
    
    def _do_analyze(self, player_name: str, context: Dict) -> str:
        """执行投票模式分析(内部方法)"""
        return self._analyze_voting_pattern(player_name, context)
    
    @safe_execute(default_return="unknown")
    def analyze(self, player_name: str, context: Dict) -> str:
        """
        分析玩家的投票模式
        
        Returns:
            pattern type: 'protect_wolf', 'accurate', 'swing', 'charge', 'abstain', 'unknown'
        """
        return self._analyze_voting_pattern(player_name, context)
    
    def _analyze_voting_pattern(self, player_name: str, context: Dict) -> str:
        """
        内部方法: 分析玩家的投票模式
        
        Args:
            player_name: 玩家名称
            context: 游戏上下文
            
        Returns:
            投票模式类型
        """
        # 边界检查
        if not DataValidator.validate_player_name(player_name):
            logger.warning(f"Invalid player_name: {player_name}")
            return "unknown"
        
        if not isinstance(context, dict):
            logger.warning(f"Invalid context type: {type(context)}")
            return "unknown"
        
        # 安全获取player_data
        player_data_dict = DataValidator.safe_get_dict(context.get("player_data"))
        player_data = DataValidator.safe_get_dict(player_data_dict.get(player_name))
        
        vote_history = DataValidator.safe_get_list(player_data.get("vote_history"))
        voting_results = DataValidator.safe_get_dict(context.get("voting_results"))

        if len(vote_history) < 2:
            return "unknown"

        # Initialize pattern scores
        pattern_score = {
            "protect_wolf": 0.0,
            "charge": 0.0,
            "swing": 0.0,
            "accurate": 0.0,
            "abstain": 0.0,
        }

        # Count vote types
        total_votes = len(vote_history)
        vote_good_count = 0
        vote_wolf_count = 0
        abstain_count = 0
        first_vote_count = 0
        
        for vote in vote_history:
            if not isinstance(vote, dict):
                continue
                
            # Check actual voting results first
            vote_round = vote.get("round", 0)
            target = vote.get("target")
            
            counted = False
            if vote_round in voting_results and isinstance(voting_results[vote_round], dict):
                voted_out = voting_results[vote_round].get("voted_out")
                if target == voted_out:
                    if voting_results[vote_round].get("was_wolf"):
                        vote_wolf_count += 1
                        counted = True
                    elif voting_results[vote_round].get("was_good"):
                        vote_good_count += 1
                        counted = True
            
            # Fallback to vote_history data
            if not counted:
                if vote.get("target_was_good"):
                    vote_good_count += 1
                elif vote.get("target_was_wolf"):
                    vote_wolf_count += 1
            
            if vote.get("is_abstain"):
                abstain_count += 1
            
            if vote.get("is_first"):
                first_vote_count += 1

        # Calculate pattern scores
        if total_votes > 0:
            # Protect wolf pattern: consistently votes good players
            if vote_good_count >= 2 and vote_good_count / total_votes >= 0.6:
                pattern_score["protect_wolf"] = vote_good_count / total_votes
            
            # Accurate pattern: consistently votes wolves
            if vote_wolf_count >= 2 and vote_wolf_count / total_votes >= 0.6:
                pattern_score["accurate"] = vote_wolf_count / total_votes
            
            # Charge pattern: often first to vote
            if first_vote_count >= 2 and first_vote_count / total_votes >= 0.5:
                pattern_score["charge"] = first_vote_count / total_votes
            
            # Abstain pattern: frequently abstains
            if abstain_count >= 2 and abstain_count / total_votes >= 0.4:
                pattern_score["abstain"] = abstain_count / total_votes
            
            # Swing pattern: no clear pattern, mixed voting
            if max(pattern_score.values()) < 0.5:
                pattern_score["swing"] = 0.5

        # Return dominant pattern
        if max(pattern_score.values()) > 0:
            dominant_pattern = max(pattern_score.items(), key=lambda x: x[1])[0]
            logger.debug(f"[VOTING PATTERN] {player_name}: {dominant_pattern} (score: {pattern_score[dominant_pattern]:.2f})")
            return dominant_pattern
        
        return "unknown"


class GamePhaseAnalyzer(BaseAnalyzer):
    """游戏阶段分析器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
    
    def _get_default_result(self) -> str:
        """获取默认游戏阶段"""
        return "early"
    
    def _do_analyze(self, context: Dict) -> str:
        """执行游戏阶段分析(内部方法)"""
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        current_day = DataValidator.safe_get_int(game_state.get("current_day", 1), 1)
        
        if current_day <= self.config.EARLY_GAME_MAX_DAY:
            return "early"
        elif current_day <= self.config.MID_GAME_MAX_DAY:
            return "mid"
        else:
            return "late"
    
    @safe_execute(default_return="early")
    def analyze(self, context: Dict) -> str:
        """
        分析当前游戏阶段
        
        Returns:
            "early" (Day 1-2), "mid" (Day 3-5), "late" (Day 6+)
        """
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        current_day = DataValidator.safe_get_int(game_state.get("current_day", 1), 1)
        
        if current_day <= self.config.EARLY_GAME_MAX_DAY:
            return "early"
        elif current_day <= self.config.MID_GAME_MAX_DAY:
            return "mid"
        else:
            return "late"
    
    def is_endgame(self, context: Dict) -> bool:
        """判断是否残局"""
        game_state = DataValidator.safe_get_dict(context.get("game_state"))
        alive_count = DataValidator.safe_get_int(game_state.get("alive_count", 12), 12)
        return alive_count <= self.config.ENDGAME_ALIVE_THRESHOLD


class SpeechPositionAnalyzer(BaseAnalyzer):
    """发言位置分析器"""
    
    def __init__(self, config: VillagerConfig):
        super().__init__(config)
    
    def _get_default_result(self) -> str:
        """获取默认发言位置"""
        return "middle"
    
    def _do_analyze(self, my_name: str) -> str:
        """执行发言位置分析(内部方法)"""
        if not DataValidator.validate_player_name(my_name):
            logger.warning(f"Invalid my_name: {my_name}")
            return "middle"
        
        # Extract player number from name (e.g., "No.5" -> 5)
        import re
        match = re.search(r"(\d+)", my_name)
        if not match:
            return "middle"
        
        try:
            player_num = int(match.group(1))
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse player number from {my_name}")
            return "middle"
        
        if player_num <= 4:
            return "early"
        elif player_num <= 8:
            return "middle"
        else:
            return "late"
    
    @safe_execute(default_return="middle")
    def analyze(self, my_name: str) -> str:
        """
        确定发言位置
        
        Returns:
            'early' (1-4), 'middle' (5-8), 'late' (9-12)
        """
        if not DataValidator.validate_player_name(my_name):
            logger.warning(f"Invalid my_name: {my_name}")
            return "middle"
        
        # Extract player number from name (e.g., "No.5" -> 5)
        import re
        match = re.search(r"(\d+)", my_name)
        if not match:
            return "middle"
        
        try:
            player_num = int(match.group(1))
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse player number from {my_name}")
            return "middle"
        
        if player_num <= 4:
            return "early"
        elif player_num <= 8:
            return "middle"
        else:
            return "late"
