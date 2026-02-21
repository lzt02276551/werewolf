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
        决定是否使用解药
        
        Args:
            victim: 被杀的玩家
            context: 决策上下文
                
        Returns:
            (should_use, reason, score) 元组
        """
        try:
            # 基础验证
            validation_result = self._validate_and_check_antidote(victim, context)
            if validation_result:
                return validation_result
            
            # 首夜策略检查
            first_night_result = self._check_first_night_strategy(context)
            if first_night_result:
                return first_night_result
            
            # 计算分数并决策
            return self._calculate_and_decide_antidote(victim, context)
            
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
        计算解药使用分数（决策树算法）
        
        评分维度：
        1. 基础信任度（0-100）
        2. 角色价值加成（预言家+30，守卫+25，强力平民+20）
        3. 威胁等级加成（警长+20，高质量发言+15）
        4. 自刀风险惩罚（低信任-30）
        5. 首夜特殊处理（首夜必救，除非极低信任<20）
        
        Args:
            victim: 被杀的玩家
            context: 决策上下文
            
        Returns:
            解药分数(0-100)
        """
        trust_scores = context.get("trust_scores", {})
        player_data = context.get("player_data", {})
        current_night = context.get("current_night", 0)
        
        # 基础分数：信任度
        trust = trust_scores.get(victim, 50)
        score = trust
        
        # 获取玩家数据
        victim_data = player_data.get(victim, {})
        
        # ========== 角色价值加成 ==========
        
        # 预言家声称（最高价值）
        if victim_data.get("claimed_seer", False):
            score += 30
            logger.debug(f"[ANTIDOTE] {victim} claimed Seer, +30")
        
        # 守卫声称
        if victim_data.get("claimed_guard", False):
            score += 25
            logger.debug(f"[ANTIDOTE] {victim} claimed Guard, +25")
        
        # 强力平民（高质量发言）
        if victim_data.get("logical_speech", False):
            score += 20
            logger.debug(f"[ANTIDOTE] {victim} strong villager (logical speech), +20")
        
        # 猎人声称（中等价值）
        if victim_data.get("claimed_hunter", False):
            score += 15
            logger.debug(f"[ANTIDOTE] {victim} claimed Hunter, +15")
        
        # ========== 威胁等级加成 ==========
        
        # 警长身份
        if victim_data.get("is_sheriff", False):
            score += 20
            logger.debug(f"[ANTIDOTE] {victim} is Sheriff, +20")
        
        # 高质量发言
        speech_quality = victim_data.get("speech_quality", 50)
        if speech_quality >= 70:
            score += 15
            logger.debug(f"[ANTIDOTE] {victim} high speech quality ({speech_quality}), +15")
        
        # 引领讨论
        if victim_data.get("leads_discussion", False):
            score += 10
            logger.debug(f"[ANTIDOTE] {victim} leads discussion, +10")
        
        # ========== 自刀风险惩罚 ==========
        
        # 低信任度（可能是自刀）
        if trust < self.config.TRUST_LOW:
            score -= 30
            logger.debug(f"[ANTIDOTE] {victim} low trust ({trust:.1f}), -30 (self-knife risk)")
        
        # 极低信任度（很可能是自刀）
        if trust < self.config.TRUST_VERY_LOW:
            score -= 20  # 额外惩罚
            logger.debug(f"[ANTIDOTE] {victim} very low trust ({trust:.1f}), -20 (high self-knife risk)")
        
        # ========== 首夜特殊处理 ==========
        
        # 首夜策略：除非极低信任，否则倾向于救
        if current_night == 1:
            if trust >= 20:  # 不是极低信任
                score += 30  # 首夜加成
                logger.debug(f"[ANTIDOTE] First night bonus, +30")
        
        # 限制在0-100范围内
        final_score = max(0, min(100, score))
        
        logger.info(
            f"[ANTIDOTE SCORE] {victim}: trust={trust:.1f}, "
            f"role_value={score-trust:.1f}, final={final_score:.1f}"
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
        计算毒药使用分数（决策树算法）
        
        评分维度：
        1. 基础分数：100 - 信任度（信任度越低，分数越高）
        2. 预言家确认狼人：直接100分（必毒）
        3. 注入攻击：+40分
        4. 虚假引用：+30分
        5. 前后矛盾：+25分
        6. 狼人保护行为：+20分
        7. 猎人声称：-50分（避免毒猎人，猎人被毒不能开枪）
        8. 狼王嫌疑：+30分（优先毒狼王，狼王被毒不能开枪）
        
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
        
        # 基础分数：100 - 信任度
        score = 100 - trust
        
        # 获取玩家数据
        target_data = player_data.get(target, {})
        
        # ========== 预言家确认（最强证据）==========
        
        if target in seer_checks:
            result = str(seer_checks[target]).lower()
            if "wolf" in result:
                score = 100  # 确认狼人，必毒
                logger.debug(f"[POISON] {target} confirmed wolf by Seer, score=100")
                return 100  # 直接返回，不需要其他计算
        
        # ========== 行为异常检测 ==========
        
        # 注入攻击
        injection_count = target_data.get("injection_attempts", 0)
        if injection_count > 0:
            bonus = min(injection_count * 20, 40)  # 最多+40
            score += bonus
            logger.debug(f"[POISON] {target} injection attacks ({injection_count}), +{bonus}")
        
        # 虚假引用
        false_quote_count = target_data.get("false_quotes", 0)
        if false_quote_count > 0:
            bonus = min(false_quote_count * 15, 30)  # 最多+30
            score += bonus
            logger.debug(f"[POISON] {target} false quotes ({false_quote_count}), +{bonus}")
        
        # 前后矛盾
        contradiction_count = target_data.get("contradictions", 0)
        if contradiction_count > 0:
            bonus = min(contradiction_count * 12, 25)  # 最多+25
            score += bonus
            logger.debug(f"[POISON] {target} contradictions ({contradiction_count}), +{bonus}")
        
        # 狼人保护行为
        wolf_protect_count = target_data.get("protect_suspicious_count", 0)
        if wolf_protect_count > 0:
            bonus = min(wolf_protect_count * 10, 20)  # 最多+20
            score += bonus
            logger.debug(f"[POISON] {target} protects wolves ({wolf_protect_count}), +{bonus}")
        
        # ========== 角色声称处理 ==========
        
        # 猎人声称：避免毒猎人（猎人被毒不能开枪）
        if target_data.get("claimed_hunter", False):
            score -= 50
            logger.debug(f"[POISON] {target} claimed Hunter, -50 (avoid poisoning hunter)")
        
        # 狼王嫌疑：优先毒狼王（狼王被毒不能开枪）
        if target_data.get("suspected_wolf_king", False):
            score += 30
            logger.debug(f"[POISON] {target} suspected Wolf King, +30 (priority target)")
        
        # 限制在0-100范围内
        final_score = max(0, min(100, score))
        
        logger.info(
            f"[POISON SCORE] {target}: trust={trust:.1f}, "
            f"base={100-trust:.1f}, bonus={final_score-(100-trust):.1f}, final={final_score:.1f}"
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
