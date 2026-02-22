# -*- coding: utf-8 -*-
"""
猎人代理人决策器模块
实现各种决策器，使用策略模式
"""

from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.common.utils import DataValidator
from .config import HunterConfig
from .performance import monitor_performance
from .optimizer import DecisionOptimizer
from .validators import IntegrityChecker

if TYPE_CHECKING:
    from .analyzers import WolfProbabilityCalculator, ThreatLevelAnalyzer, MemoryDAO
else:
    # 运行时导入
    WolfProbabilityCalculator = None
    ThreatLevelAnalyzer = None
    MemoryDAO = None


# ==================== 开枪决策器 ====================

class ShootDecisionMaker(BaseDecisionMaker):
    """开枪决策器"""
    
    def __init__(
        self,
        config: HunterConfig,
        wolf_prob_calculator: WolfProbabilityCalculator,
        threat_analyzer: ThreatLevelAnalyzer,
        memory_dao
    ):
        super().__init__(config)
        self.wolf_prob_calculator = wolf_prob_calculator
        self.threat_analyzer = threat_analyzer
        self.memory_dao = memory_dao
        self.validator = DataValidator()
        
        # 添加决策优化器
        self.optimizer = DecisionOptimizer()
        logger.info("✓ ShootDecisionMaker initialized with optimizer")
    
    @monitor_performance
    def decide(
        self, 
        candidates: List[str], 
        my_name: str, 
        game_phase: str = "mid",
        current_day: int = 1,
        alive_count: int = 12
    ) -> Tuple[str, str, Dict[str, float]]:
        """
        决定开枪目标
        
        Args:
            candidates: 候选人列表
            my_name: 自己的名称
            game_phase: 游戏阶段
            current_day: 当前天数
            alive_count: 存活人数
        
        Returns:
            (目标, 理由, 所有候选人分数)
        """
        # 验证输入
        if not isinstance(candidates, list):
            raise ValueError(f"Invalid candidates type: {type(candidates)}, expected list")
        
        if not candidates:
            return ("Do Not Shoot", "No candidates provided", {})
        
        # 过滤有效候选人
        dead_players = self.memory_dao.get_dead_players()
        if not isinstance(dead_players, set):
            dead_players = set(dead_players) if dead_players else set()
        
        valid_candidates = [
            c for c in candidates 
            if c != my_name and c not in dead_players and self.validator.validate_player_name(c)
        ]
        
        if not valid_candidates:
            return ("Do Not Shoot", "No valid targets after filtering", {})
        
        # 特殊情况处理
        special_target, special_reason = self._handle_special_situations(valid_candidates)
        if special_target:
            logger.info(f"[SHOOT SPECIAL] {special_target}: {special_reason}")
            return (special_target, special_reason, {special_target: 200.0})
        
        # 计算每个候选人的开枪分数
        shoot_scores = {}
        confidence_scores = {}
        
        for candidate in valid_candidates:
            # 计算狼人概率
            wolf_prob = self.wolf_prob_calculator.calculate(candidate, game_phase)
            
            # 计算威胁等级
            threat_level = self.threat_analyzer.analyze(candidate, current_day, alive_count)
            
            # 计算置信度
            confidence = self._calculate_shoot_confidence(candidate)
            
            # 计算风险惩罚
            risk_penalty = self._calculate_shoot_risk_penalty(candidate)
            
            # 综合评分
            base_score = wolf_prob * 70 + threat_level * 20
            final_score = base_score * confidence - risk_penalty
            
            shoot_scores[candidate] = final_score
            confidence_scores[candidate] = confidence
            
            logger.debug(
                f"[SHOOT EVAL] {candidate}: Wolf={wolf_prob:.2f}, Threat={threat_level:.2f}, "
                f"Conf={confidence:.2f}, Risk=-{risk_penalty:.1f}, Score={final_score:.1f}"
            )
        
        # 选择最高分
        if not shoot_scores:
            return ("Do Not Shoot", "No valid scores calculated", {})
        
        sorted_candidates = sorted(shoot_scores.items(), key=lambda x: x[1], reverse=True)
        target = sorted_candidates[0][0]
        score = sorted_candidates[0][1]
        confidence = confidence_scores[target]
        
        # 使用优化器获取动态阈值
        min_confidence = self.optimizer.get_threshold('shoot_min_confidence')
        min_score = self.optimizer.get_threshold('shoot_min_score')
        
        # 如果优化器未初始化，使用配置默认值
        if min_confidence == 0.0:
            min_confidence = self.config.shoot_confidence_threshold
        if min_score == 0.0:
            min_score = self.config.vote_score_threshold
        
        # 获取优化器建议
        should_shoot, recommendation = self.optimizer.get_recommendation('shoot', score, confidence)
        
        if not should_shoot:
            logger.info(f"[SHOOT OPTIMIZER] Recommendation: Do Not Shoot - {recommendation}")
            return ("Do Not Shoot", recommendation, shoot_scores)
        
        # 验证决策完整性
        valid, error = IntegrityChecker.check_decision_integrity(target, valid_candidates, shoot_scores)
        if not valid:
            logger.error(f"[SHOOT INTEGRITY] Decision integrity check failed: {error}")
            return ("Do Not Shoot", f"Integrity check failed: {error}", shoot_scores)
        
        # 生成理由
        reason = self._generate_shoot_reason(target, score, confidence)
        
        logger.info(f"[SHOOT OPTIMIZER] Recommendation: Shoot {target} - {recommendation}")
        self.log_decision(target, reason)
        return (target, reason, shoot_scores)
    
    def _handle_special_situations(self, candidates: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        处理特殊情况（与SKILL_PROMPT中的决策树一致）
        
        特殊情况包括：
        A) 预言家查杀的狼人还活着 → 优先射击（95%狼概率）
        B) 假预言家 vs 真预言家 → 射击假预言家（80%狼概率）
        C) 错误投票淘汰（被冤枉） → 射击投票领袖
        D) 狼王嫌疑 → 评估是否射击（狼王会反击）
        E) 多个高概率目标 → 比较威胁等级
        F) 所有候选人低概率 → 考虑放弃射击
        
        Args:
            candidates: 候选人列表
            
        Returns:
            (特殊目标, 特殊原因) 或 (None, None)
        """
        # A) 预言家查杀的狼人
        seer_checks = self.memory_dao.get("seer_checks") or {}
        for player, result in seer_checks.items():
            if player in candidates:
                # 检查是否被预言家验证为狼人
                is_wolf = False
                if isinstance(result, dict):
                    is_wolf = result.get("is_wolf", False)
                elif isinstance(result, str):
                    is_wolf = "wolf" in result.lower()
                
                if is_wolf:
                    return (player, f"Seer identified {player} as wolf (95% confidence)")
        
        # C) 错误投票淘汰 - 射击投票领袖
        # 获取最近的投票记录，找出谁推动了对我的投票
        voting_history = self.memory_dao.get_voting_history()
        my_name = self.memory_dao.get_my_name()
        
        # 分析投票领袖（谁最积极地推动投票）
        if voting_history and my_name:
            vote_leaders = self._identify_vote_leaders(voting_history, my_name, candidates)
            if vote_leaders:
                leader = vote_leaders[0]
                return (leader, f"Vote leader who pushed for my elimination (likely wolf)")
        
        return (None, None)
    
    def _identify_vote_leaders(
        self, 
        voting_history: Dict[str, List[str]], 
        target: str, 
        candidates: List[str]
    ) -> List[str]:
        """
        识别投票领袖（增强类型安全 + 修复空列表bug）
        
        投票领袖定义：
        - 多次投票给目标玩家的玩家
        - 按投票次数排序
        
        Args:
            voting_history: 投票历史
            target: 被投票的目标
            candidates: 候选人列表
            
        Returns:
            投票领袖列表（按积极程度排序）
        """
        # 类型验证
        if not isinstance(voting_history, dict):
            logger.warning(f"voting_history is not dict: {type(voting_history)}")
            return []
        
        if not isinstance(target, str) or not target:
            logger.warning(f"Invalid target: {target}")
            return []
        
        if not isinstance(candidates, list):
            logger.warning(f"candidates is not list: {type(candidates)}")
            return []
        
        vote_counts = {}
        
        for voter, votes in voting_history.items():
            # 类型安全检查
            if not isinstance(voter, str) or voter not in candidates:
                continue
            
            if not isinstance(votes, list):
                logger.debug(f"Skipping {voter}: votes is not list ({type(votes)})")
                continue
            
            # 统计投票给目标的次数（带类型检查）
            try:
                target_votes = sum(1 for v in votes if isinstance(v, str) and v == target)
                if target_votes > 0:
                    vote_counts[voter] = target_votes
            except (TypeError, ValueError) as e:
                logger.debug(f"Error counting votes for {voter}: {e}")
                continue
        
        # 如果没有找到投票领袖，返回空列表（修复bug）
        if not vote_counts:
            logger.debug(f"[VOTE LEADERS] No vote leaders found for target {target}")
            return []
        
        # 按投票次数排序（带异常处理）
        try:
            sorted_leaders = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
            leaders = [leader for leader, _ in sorted_leaders]
            logger.debug(f"[VOTE LEADERS] Found {len(leaders)} leaders: {leaders}")
            return leaders
        except (TypeError, ValueError) as e:
            logger.error(f"Error sorting vote leaders: {e}")
            return []
    
    def _calculate_shoot_confidence(self, player: str) -> float:
        """
        计算开枪置信度（0.0-1.0）- 企业级五星算法
        
        置信度评估维度：
        1. 投票数据样本量（最多+0.3）
        2. 发言数据样本量（最多+0.15）
        3. 强证据存在（+0.2）
        4. 游戏阶段调整
        
        Args:
            player: 玩家名称
            
        Returns:
            置信度（0.0-1.0）
        """
        confidence = 0.5  # 基础置信度
        
        # 1. 投票数据样本量（带类型检查和验证）
        voting_results = self.memory_dao.get_voting_results()
        if not isinstance(voting_results, dict):
            logger.warning(f"voting_results is not dict: {type(voting_results)}")
            voting_results = {}
        
        if player in voting_results:
            results = voting_results[player]
            if isinstance(results, list):
                # 验证每个结果的格式
                valid_results = []
                for r in results:
                    try:
                        if self.validator.validate_voting_record(r):
                            valid_results.append(r)
                    except (TypeError, AttributeError) as e:
                        logger.debug(f"Invalid voting record: {e}")
                        continue
                
                sample_count = len(valid_results)
                # 样本越多，置信度越高（最多+0.3）
                confidence += min(0.3, sample_count * 0.06)
        
        # 2. 发言数据样本量（带类型检查）
        speech_history = self.memory_dao.get_speech_history()
        if not isinstance(speech_history, dict):
            logger.warning(f"speech_history is not dict: {type(speech_history)}")
            speech_history = {}
        
        if player in speech_history:
            speeches = speech_history[player]
            if isinstance(speeches, list):
                speech_count = len(speeches)
                # 发言越多，置信度越高（最多+0.15）
                confidence += min(0.15, speech_count * 0.03)
        
        # 3. 强证据（注入攻击或虚假引用）
        injection_attempts = self.memory_dao.get_injection_attempts()
        false_quotations = self.memory_dao.get_false_quotations()
        
        # 类型安全检查
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not a list: {type(injection_attempts)}")
            injection_attempts = []
        
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not a list: {type(false_quotations)}")
            false_quotations = []
        
        # 检查是否有强证据（带异常处理）
        has_injection = False
        has_false_quote = False
        
        try:
            has_injection = any(
                isinstance(att, dict) and att.get("player") == player 
                for att in injection_attempts
            )
        except (TypeError, AttributeError) as e:
            logger.debug(f"Error checking injection attempts: {e}")
        
        try:
            has_false_quote = any(
                isinstance(fq, dict) and fq.get("accuser") == player 
                for fq in false_quotations
            )
        except (TypeError, AttributeError) as e:
            logger.debug(f"Error checking false quotations: {e}")
        
        if has_injection or has_false_quote:
            confidence += 0.2
        
        # 确保置信度在有效范围内
        return min(1.0, max(0.0, confidence))
    
    def _calculate_shoot_risk_penalty(self, player: str) -> float:
        """
        计算开枪风险惩罚（0-50）- 企业级五星算法
        
        风险评估维度：
        1. 角色声称（预言家/女巫/守卫）
        2. 信任分数（高信任=高风险）
        3. 行为验证（声称+行为匹配）
        
        Args:
            player: 玩家名称
            
        Returns:
            风险惩罚（0-50）
        """
        penalty = 0.0
        
        # 1. 获取发言历史（带类型检查）
        speech_history = self.memory_dao.get_speech_history()
        if not isinstance(speech_history, dict):
            logger.warning(f"speech_history is not dict: {type(speech_history)}")
            speech_history = {}
        
        if player in speech_history:
            speeches = speech_history[player]
            if not isinstance(speeches, list):
                logger.warning(f"speeches for {player} is not list: {type(speeches)}")
                speeches = []
            
            # 合并所有发言（安全处理）
            combined_speech = " ".join(
                str(s).lower() for s in speeches if isinstance(s, str)
            )
            
            # 2. 预言家声称检测
            if "checked" in combined_speech or "verified" in combined_speech:
                if "seer" in combined_speech or "i am" in combined_speech:
                    # 明确声称预言家
                    penalty += 30
                else:
                    # 暗示预言家
                    penalty += 20
            
            # 3. 女巫声称检测
            if "saved" in combined_speech or "poison" in combined_speech:
                if "witch" in combined_speech or "i am" in combined_speech:
                    # 明确声称女巫
                    penalty += 25
                else:
                    # 暗示女巫
                    penalty += 15
            
            # 4. 守卫声称检测
            if "protected" in combined_speech or "guard" in combined_speech:
                # 守卫声称
                penalty += 15
        
        # 5. 信任分数风险（高信任=高风险）
        trust_scores = self.memory_dao.get_trust_scores()
        if not isinstance(trust_scores, dict):
            logger.warning(f"trust_scores is not dict: {type(trust_scores)}")
            trust_scores = {}
        
        trust_score = trust_scores.get(player, 50)
        if not isinstance(trust_score, (int, float)):
            logger.warning(f"Invalid trust_score for {player}: {type(trust_score)}, using 50")
            trust_score = 50
        
        if trust_score >= 80:
            penalty += 20
        elif trust_score >= 70:
            penalty += 12
        
        # 确保惩罚在有效范围内
        return min(50, max(0, penalty))
    
    def _generate_shoot_reason(self, target: str, score: float, confidence: float) -> str:
        """生成开枪理由"""
        wolf_prob = self.wolf_prob_calculator.calculate(target)
        trust_scores = self.memory_dao.get_trust_scores()
        trust_score = trust_scores.get(target, 50)
        
        reasons = []
        
        if score >= 80:
            reasons.append(f"极高狼人概率 (score: {score:.0f})")
        elif score >= 60:
            reasons.append(f"高狼人概率(score: {score:.0f})")
        else:
            reasons.append(f"最高狼人概率(score: {score:.0f})")
        
        reasons.append(f"wolf={wolf_prob:.0%}")
        reasons.append(f"trust={trust_score:.0f}")
        reasons.append(f"conf={confidence:.0%}")
        
        injection_attempts = self.memory_dao.get_injection_attempts()
        false_quotations = self.memory_dao.get_false_quotations()
        
        # 类型安全检查
        if not isinstance(injection_attempts, list):
            logger.warning(f"injection_attempts is not a list: {type(injection_attempts)}")
            injection_attempts = []
        
        if not isinstance(false_quotations, list):
            logger.warning(f"false_quotations is not a list: {type(false_quotations)}")
            false_quotations = []
        
        if any(isinstance(att, dict) and att.get("player") == target for att in injection_attempts):
            reasons.append("注入攻击")
        
        if any(isinstance(fq, dict) and fq.get("accuser") == target for fq in false_quotations):
            reasons.append("虚假引用")
        
        sheriff = self.memory_dao.get_sheriff()
        if sheriff == target:
            reasons.append("Sheriff(高威胁)")
        
        return ", ".join(reasons)




