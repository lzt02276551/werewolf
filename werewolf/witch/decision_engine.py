# -*- coding: utf-8 -*-
"""
Witch决策引擎

提供解药和毒药使用决策逻辑，遵循企业级代码标准
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from werewolf.witch.config import WitchConfig
from werewolf.witch.base_components import WitchMemoryDAO


class WitchDecisionEngine(BaseDecisionMaker):
    """
    女巫决策引擎
    
    职责:
    1. 决定是否使用解药以及救谁
    2. 决定是否使用毒药以及毒谁
    3. 基于信任分数、角色价值、游戏阶段等因素综合决策
    
    Attributes:
        config: 女巫配置对象
        memory_dao: 内存数据访问对象
    """
    
    def __init__(self, config: WitchConfig, memory_dao: WitchMemoryDAO):
        """
        初始化决策引擎
        
        Args:
            config: 女巫配置对象
            memory_dao: 内存数据访问对象
        """
        super().__init__(config)
        self.config = config
        self.memory_dao = memory_dao
    
    def decide(self, *args, **kwargs) -> Dict[str, Any]:
        """
        通用决策接口（未使用）
        
        Returns:
            决策结果
        """
        return self._get_default_result()
    
    # ==================== 解药决策 ====================
    
    def decide_antidote(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        决定是否使用解药（简化版 - 符合女巫规则）
        
        策略：
        1. 首夜：除非明显自刀（信任<15），否则救
        2. 后续：评估玩家价值，避免救自刀
        
        Args:
            victim: 被杀的玩家
            context: 决策上下文
                
        Returns:
            (should_use, reason, score) 元组
        """
        try:
            # 基础验证
            if not self._validate_antidote_input(victim, context):
                return False, "Invalid input", 0.0
            
            if not self.memory_dao.get_has_antidote():
                return False, "Antidote already used", 0.0
            
            if not victim:
                return False, "No victim", 0.0
            
            # 计算分数并决策
            score = self._calculate_antidote_score(victim, context)
            should_use = score >= self.config.ANTIDOTE_SCORE_THRESHOLD
            reason = self._generate_antidote_reason(victim, score, context)
            
            logger.info(
                f"[ANTIDOTE] {victim}: {score:.1f}/100 - "
                f"{'SAVE' if should_use else 'SKIP'}"
            )
            
            return should_use, reason, score
            
        except Exception as e:
            logger.error(f"Error in decide_antidote: {e}")
            return False, f"Decision error: {e}", 0.0
    
    def _validate_and_check_antidote(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> Optional[Tuple[bool, str, float]]:
        """验证输入并检查解药状态"""
        if not self._validate_antidote_input(victim, context):
            return False, "Invalid input", 0.0
        
        if not self.memory_dao.get_has_antidote():
            return False, "Antidote already used", 0.0
        
        if not victim:
            return False, "No victim", 0.0
        
        return None
    
    def _check_first_night_strategy(
        self,
        context: Dict[str, Any]
    ) -> Optional[Tuple[bool, str, float]]:
        """检查首夜必救策略"""
        current_night = context.get("current_night", 0)
        if current_night == 1 and self.config.ANTIDOTE_FIRST_NIGHT_ALWAYS:
            return True, "First night always save strategy", 100.0
        return None
    
    def _calculate_and_decide_antidote(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """计算分数并做出决策"""
        score = self._calculate_antidote_score(victim, context)
        should_use = score >= self.config.ANTIDOTE_SCORE_THRESHOLD
        reason = self._generate_antidote_reason(victim, score, context)
        
        logger.info(
            f"[ANTIDOTE] {victim}: {score:.1f}/100 - "
            f"{'SAVE' if should_use else 'SKIP'}"
        )
        
        return should_use, reason, score
    
    def _validate_antidote_input(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        验证解药决策输入
        
        Args:
            victim: 被杀的玩家
            context: 决策上下文
            
        Returns:
            输入是否有效
        """
        if not isinstance(victim, str) or not victim:
            return False
        
        if not isinstance(context, dict):
            return False
        
        return True
    
    def _calculate_antidote_score(
        self,
        victim: str,
        context: Dict[str, Any]
    ) -> float:
        """
        计算解药使用分数（企业级五星标准 - 符合女巫规则）
        
        策略：有人倒下基本都救，但要避免明显的自刀
        
        评分维度（简化为4类）：
        1. 基础信任度（0-100）- 主要用于识别自刀
        2. 角色价值（预言家+30，守卫+25，其他神职+20）
        3. 首夜策略（首夜+40，除非极低信任<15）
        4. 自刀风险（信任<20时-40）
        
        Args:
            victim: 被杀的玩家
            context: 决策上下文
            
        Returns:
            解药分数(0-100)
        """
        trust_scores = context.get("trust_scores", {})
        player_data = context.get("player_data", {})
        seer_checks = context.get("seer_checks", {})
        current_night = context.get("current_night", 0)
        
        # 基础分数：信任度
        trust = trust_scores.get(victim, 50)
        score = trust
        
        victim_data = player_data.get(victim, {})
        
        # ========== 1. 角色价值加成（简化）==========
        
        # 预言家（最高价值）
        if victim_data.get("claimed_seer", False):
            score += 30
            logger.debug(f"[ANTIDOTE] {victim} claimed Seer, +30")
        
        # 守卫（次高价值）
        elif victim_data.get("claimed_guard", False):
            score += 25
            logger.debug(f"[ANTIDOTE] {victim} claimed Guard, +25")
        
        # 其他神职（猎人等）
        elif victim_data.get("claimed_hunter", False):
            score += 20
            logger.debug(f"[ANTIDOTE] {victim} claimed Hunter, +20")
        
        # ========== 2. 预言家验证加成 ==========
        
        if victim in seer_checks:
            result = str(seer_checks[victim]).lower()
            if "good" in result or "villager" in result:
                score += 25
                logger.debug(f"[ANTIDOTE] {victim} verified GOOD by Seer, +25")
        
        # ========== 3. 首夜策略（重要）==========
        
        if current_night == 1:
            # 首夜策略：使用配置的最低信任阈值
            min_trust = self.config.ANTIDOTE_FIRST_NIGHT_MIN_TRUST
            if trust >= min_trust:
                score += 40  # 首夜大幅加成
                logger.debug(f"[ANTIDOTE] First night bonus, +40 (trust {trust:.1f} >= {min_trust})")
            else:
                logger.debug(f"[ANTIDOTE] First night but trust too low ({trust:.1f} < {min_trust}), no bonus")
        
        # ========== 4. 自刀风险惩罚（关键）==========
        
        # 极低信任（很可能是自刀）
        if trust < self.config.TRUST_VERY_LOW:
            penalty = 40
            score -= penalty
            logger.debug(f"[ANTIDOTE] {victim} very low trust ({trust:.1f}), -{penalty} (likely self-knife)")
        
        # 限制在0-100范围内
        final_score = max(0, min(100, score))
        
        logger.info(
            f"[ANTIDOTE SCORE] {victim}: trust={trust:.1f}, final={final_score:.1f}"
        )
        
        return final_score
    
    def _generate_antidote_reason(
        self,
        victim: str,
        score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        生成解药使用理由
        
        Args:
            victim: 被杀的玩家
            score: 决策分数
            context: 决策上下文
            
        Returns:
            决策理由
        """
        trust_scores = context.get("trust_scores", {})
        trust = trust_scores.get(victim, 50)
        
        if score >= 80:
            return f"High value target (trust: {trust:.1f}, score: {score:.1f})"
        elif score >= 50:
            return f"Moderate value target (trust: {trust:.1f}, score: {score:.1f})"
        else:
            return f"Low value target (trust: {trust:.1f}, score: {score:.1f})"
    
    # ==================== 毒药决策 ====================
    
    def decide_poison(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], str, float]:
        """
        决定是否使用毒药以及毒谁
        
        Args:
            candidates: 候选人列表
            context: 决策上下文
                
        Returns:
            (target, reason, score) 元组
        """
        try:
            # 基础验证
            validation_result = self._validate_and_check_poison(candidates, context)
            if validation_result:
                return validation_result
            
            # 计算分数并选择目标
            return self._calculate_and_decide_poison(candidates, context)
            
        except Exception as e:
            logger.error(f"Error in decide_poison: {e}")
            return None, f"Decision error: {e}", 0.0
    
    def _validate_and_check_poison(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Optional[Tuple[None, str, float]]:
        """验证输入并检查毒药状态"""
        if not self._validate_poison_input(candidates, context):
            return None, "Invalid input", 0.0
        
        if not self.memory_dao.get_has_poison():
            return None, "Poison already used", 0.0
        
        if not candidates:
            return None, "No candidates", 0.0
        
        return None
    
    def _calculate_and_decide_poison(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], str, float]:
        """计算分数并做出决策"""
        # 计算每个候选人的分数
        scores = {
            candidate: self._calculate_poison_score(candidate, context)
            for candidate in candidates
        }
        
        if not scores:
            return None, "No valid scores", 0.0
        
        # 选择分数最高的
        target, score = max(scores.items(), key=lambda x: x[1])
        
        # 判断是否达到阈值
        if score < self.config.POISON_SCORE_THRESHOLD:
            return (
                None,
                f"Best score {score:.1f} below threshold "
                f"{self.config.POISON_SCORE_THRESHOLD}",
                score
            )
        
        reason = self._generate_poison_reason(target, score, context)
        logger.info(f"[POISON] {target}: {score:.1f}/100 - POISON")
        
        return target, reason, score
    
    def _validate_poison_input(
        self,
        candidates: List[str],
        context: Dict[str, Any]
    ) -> bool:
        """
        验证毒药决策输入
        
        Args:
            candidates: 候选人列表
            context: 决策上下文
            
        Returns:
            输入是否有效
        """
        if not isinstance(candidates, list):
            return False
        
        if not isinstance(context, dict):
            return False
        
        return True
    
    def _calculate_poison_score(
        self,
        target: str,
        context: Dict[str, Any]
    ) -> float:
        """
        计算毒药使用分数（企业级五星决策树算法 - 优化版）
        
        评分维度（8大类，权重优化）：
        1. 基础分数：100 - 信任度（信任度越低，分数越高）
        2. 预言家确认狼人：直接100分（必毒，最高优先级）
        3. 注入攻击：+45分（严重恶意行为）
        4. 虚假引用：+35分（欺骗行为）
        5. 前后矛盾：+30分（逻辑漏洞）
        6. 狼人保护行为：+25分（阵营暴露）
        7. 猎人声称：-50分（避免毒猎人，猎人被毒不能开枪）
        8. 狼王嫌疑：+35分（优先毒狼王，狼王被毒不能开枪）
        9. 预言家验证好人：-60分（避免毒好人）
        10. 残局调整：分数*0.9（更谨慎）
        
        Args:
            target: 目标玩家
            context: 决策上下文
            
        Returns:
            毒药分数(0-100)
        """
        trust_scores = context.get("trust_scores", {})
        seer_checks = context.get("seer_checks", {})
        player_data = context.get("player_data", {})
        
        trust = trust_scores.get(target, 50)
        
        # ========== 基础分数：100 - 信任度 ==========
        score = 100 - trust
        
        # 获取玩家数据
        target_data = player_data.get(target, {})
        
        # ========== 1. 预言家确认（最强证据，最高优先级）==========
        
        if target in seer_checks:
            result = str(seer_checks[target]).lower()
            if "wolf" in result or "werewolf" in result:
                score = 100  # 确认狼人，必毒
                logger.debug(f"[POISON] {target} confirmed WOLF by Seer, score=100 (MUST POISON)")
                return 100  # 直接返回，不需要其他计算
        
        # ========== 2. 行为异常检测（权重优化）==========
        
        # 注入攻击（最严重的恶意行为）
        injection_count = target_data.get("injection_attempts", 0)
        if injection_count > 0:
            bonus = min(injection_count * 22, 45)  # 每次+22，最多+45
            score += bonus
            logger.debug(f"[POISON] {target} injection attacks ({injection_count}), +{bonus}")
        
        # 虚假引用（欺骗行为）
        false_quote_count = target_data.get("false_quotes", 0)
        if false_quote_count > 0:
            bonus = min(false_quote_count * 17, 35)  # 每次+17，最多+35
            score += bonus
            logger.debug(f"[POISON] {target} false quotes ({false_quote_count}), +{bonus}")
        
        # 前后矛盾（逻辑漏洞）
        contradiction_count = target_data.get("contradictions", 0)
        if contradiction_count > 0:
            bonus = min(contradiction_count * 15, 30)  # 每次+15，最多+30
            score += bonus
            logger.debug(f"[POISON] {target} contradictions ({contradiction_count}), +{bonus}")
        
        # 狼人保护行为（阵营暴露）
        wolf_protect_count = target_data.get("protect_suspicious_count", 0)
        if wolf_protect_count > 0:
            bonus = min(wolf_protect_count * 12, 25)  # 每次+12，最多+25
            score += bonus
            logger.debug(f"[POISON] {target} protects wolves ({wolf_protect_count}), +{bonus}")
        
        # ========== 3. 投票行为分析 ==========
        
        # 投票好人次数（狼人特征）
        vote_good_count = target_data.get("vote_good_count", 0)
        if vote_good_count >= 2:  # 至少2次投票好人
            bonus = min(vote_good_count * 8, 20)  # 每次+8，最多+20
            score += bonus
            logger.debug(f"[POISON] {target} voted good players ({vote_good_count} times), +{bonus}")
        
        # ========== 4. 角色声称处理（风险控制）==========
        
        # 猎人声称：避免毒猎人（猎人被毒不能开枪）
        if target_data.get("claimed_hunter", False):
            penalty = 50
            score -= penalty
            logger.debug(f"[POISON] {target} claimed Hunter, -{penalty} (avoid poisoning hunter)")
        
        # 狼王嫌疑：优先毒狼王（狼王被毒不能开枪）
        if target_data.get("suspected_wolf_king", False):
            bonus = 35
            score += bonus
            logger.debug(f"[POISON] {target} suspected Wolf King, +{bonus} (priority target)")
        
        # ========== 5. 预言家验证好人：大幅降低分数 ==========
        
        if target in seer_checks:
            result = str(seer_checks[target]).lower()
            if "good" in result or "villager" in result:
                penalty = 60  # 验证好人，大幅降低分数
                score -= penalty
                logger.debug(f"[POISON] {target} verified GOOD by Seer, -{penalty} (avoid poisoning good)")
        
        # ========== 6. 游戏阶段调整 ==========
        
        alive_players = context.get("alive_players", 12)
        
        # 残局（≤6人存活）：提高毒药使用标准
        if alive_players <= 6:
            # 残局必须更谨慎，降低所有分数10%
            score *= 0.9
            logger.debug(f"[POISON] {target} endgame adjustment, score *= 0.9")
        
        # ========== 7. 限制在0-100范围内 ==========
        final_score = max(0, min(100, score))
        
        logger.info(
            f"[POISON SCORE] {target}: trust={trust:.1f}, "
            f"base={100-trust:.1f}, adjustments={final_score-(100-trust):.1f}, final={final_score:.1f}"
        )
        
        return final_score
    
    def _generate_poison_reason(
        self,
        target: str,
        score: float,
        context: Dict[str, Any]
    ) -> str:
        """
        生成毒药使用理由
        
        Args:
            target: 目标玩家
            score: 决策分数
            context: 决策上下文
            
        Returns:
            决策理由
        """
        trust_scores = context.get("trust_scores", {})
        seer_checks = context.get("seer_checks", {})
        
        trust = trust_scores.get(target, 50)
        
        reasons = []
        
        # 预言家确认
        if target in seer_checks and "wolf" in str(seer_checks[target]).lower():
            reasons.append("Seer confirmed wolf")
        
        # 信任度评估
        if trust < self.config.TRUST_VERY_LOW:
            reasons.append(f"very low trust ({trust:.1f})")
        elif trust < self.config.TRUST_LOW:
            reasons.append(f"low trust ({trust:.1f})")
        
        if reasons:
            return ", ".join(reasons) + f" (score: {score:.1f})"
        else:
            return f"Most suspicious (trust: {trust:.1f}, score: {score:.1f})"
