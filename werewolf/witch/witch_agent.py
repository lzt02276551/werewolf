# -*- coding: utf-8 -*-
"""
女巫代理人（企业级重构版）

遵循SOLID原则和设计模式最佳实践
从2444行精简到约600行，提高可维护性和可测试性
"""

from agent_build_sdk.model.roles import ROLE_WITCH
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_VOTE_RESULT,
    STATUS_SKILL, STATUS_SKILL_RESULT, STATUS_NIGHT_INFO,
    STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE, STATUS_RESULT,
    STATUS_NIGHT, STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_VOTE, STATUS_SHERIFF, STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_SHERIFF_PK, STATUS_HUNTER, STATUS_HUNTER_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.witch.prompt import (
    DESC_PROMPT, VOTE_PROMPT, SKILL_PROMPT, GAME_RULE_PROMPT,
    CLEAN_USER_PROMPT, SHERIFF_ELECTION_PROMPT, SHERIFF_SPEECH_PROMPT,
    SHERIFF_VOTE_PROMPT, SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT, SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT
)
from typing import Dict, List, Tuple, Optional, Any
import sys
import os
import re

# 导入重构后的组件
from werewolf.witch.config import WitchConfig
from werewolf.witch.base_components import WitchMemoryDAO, DataValidator
from werewolf.witch.decision_engine import WitchDecisionEngine

# ML增强
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class WitchAgent(BasicRoleAgent):
    """
    女巫代理人（企业级重构版 - 双模型架构）
    
    职责:
    1. 管理女巫的药品状态（解药、毒药）
    2. 协调决策引擎完成技能使用决策
    3. 处理游戏各阶段的交互
    4. 维护玩家信任分数和游戏状态
    
    双模型架构:
    - 分析模型（analysis_llm）：用于分析玩家消息、检测注入攻击、评估可疑度
    - 生成模型（generation_llm）：用于生成发言、投票决策等
    
    Attributes:
        config: 女巫配置对象
        memory_dao: 内存数据访问对象
        decision_engine: 决策引擎
        message_analyzer: 消息分析器（使用分析模型）
        ml_agent: ML增强代理（可选）
        ml_enabled: 是否启用ML增强
    """

    def __init__(self, model_name: str, analysis_model_name: Optional[str] = None):
        """
        初始化女巫代理人（双模型架构）
        
        Args:
            model_name: 生成模型名称（用于发言生成），如果为None则从环境变量读取
            analysis_model_name: 分析模型名称（用于消息分析），如果为None则从环境变量读取
        """
        # 从环境变量读取生成模型配置
        generation_model = model_name or os.getenv('MODEL_NAME', 'deepseek-chat')
        super().__init__(ROLE_WITCH, model_name=generation_model)
        
        self.config = WitchConfig()
        self._init_memory_variables()
        
        # 初始化组件
        self.memory_dao = WitchMemoryDAO(self.memory)
        self.decision_engine = WitchDecisionEngine(self.config, self.memory_dao)
        
        # 初始化双模型架构
        self._init_dual_model_architecture(analysis_model_name)
        
        # 初始化ML增强
        self._init_ml_enhancement()
        
        logger.info("✓ WitchAgent initialized (Enterprise Edition - Dual Model Architecture)")
        logger.info(f"  - Generation Model: {generation_model}")
        logger.info(f"  - Analysis Model: {self.analysis_model_name}")
    
    def _init_dual_model_architecture(self, analysis_model_name: Optional[str] = None) -> None:
        """
        初始化双模型架构
        
        从环境变量读取检测模型配置，创建独立的分析LLM客户端
        
        Args:
            analysis_model_name: 分析模型名称（可选，优先级高于环境变量）
        """
        from werewolf.witch.analyzers import WitchMessageAnalyzer
        from openai import OpenAI
        
        # 从环境变量读取检测模型配置
        self.analysis_model_name = (
            analysis_model_name or 
            os.getenv('DETECTION_MODEL_NAME') or 
            self.model_name
        )
        
        # 创建独立的分析LLM客户端
        analysis_llm_client = None
        try:
            # 获取检测模型的API配置（优先使用DETECTION_*，否则使用主模型配置）
            detection_api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            detection_base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if detection_api_key and detection_base_url:
                # 创建独立的OpenAI客户端用于分析
                analysis_llm_client = OpenAI(
                    api_key=detection_api_key,
                    base_url=detection_base_url
                )
                logger.info(f"✓ Analysis LLM client initialized (Model: {self.analysis_model_name})")
            else:
                logger.info("⚠ Detection API not configured, using rule-based analysis")
        except Exception as e:
            logger.warning(f"Failed to initialize analysis LLM client: {e}, falling back to rule-based analysis")
        
        # 初始化消息分析器
        self.message_analyzer = WitchMessageAnalyzer(
            config=self.config,
            analysis_llm_client=analysis_llm_client,
            analysis_model_name=self.analysis_model_name
        )
    
    # ==================== 初始化方法 ====================
    
    def _init_memory_variables(self) -> None:
        """
        初始化内存变量
        
        设置女巫角色所需的所有内存变量初始值
        """
        # 药品状态
        self.memory.set_variable("has_poison", True)
        self.memory.set_variable("has_antidote", True)
        
        # 信任和玩家数据
        self.memory.set_variable("trust_scores", {})
        self.memory.set_variable("trust_history", {})
        self.memory.set_variable("player_data", {})
        
        # 药品使用历史
        self.memory.set_variable("saved_players", [])
        self.memory.set_variable("poisoned_players", [])
        self.memory.set_variable("killed_history", [])
        
        # 投票历史
        self.memory.set_variable("voting_history", {})
        self.memory.set_variable("voting_results", {})
        
        # 游戏进度
        self.memory.set_variable("current_night", 0)
        self.memory.set_variable("current_day", 0)
        
        # 其他信息
        self.memory.set_variable("seer_checks", {})
        self.memory.set_variable("wolves_eliminated", 0)
        self.memory.set_variable("good_players_lost", 0)
        self.memory.set_variable("first_night_strategy", 
                                self.config.DEFAULT_FIRST_NIGHT_STRATEGY)
        
        # 游戏数据收集
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
    
    def _init_ml_enhancement(self) -> None:
        """
        初始化ML增强功能
        
        尝试加载ML代理，如果失败则禁用ML功能
        """
        self.ml_agent = None
        self.ml_enabled = False
        
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled (module not available)")
            return
        
        try:
            from game_utils import MLConfig
            model_dir = MLConfig.get_model_dir()
            
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            
            if self.ml_enabled:
                logger.info("✓ ML enhancement enabled")
            else:
                logger.info("ML enhancement disabled (model not loaded)")
        except Exception as e:
            logger.error(f"✗ ML init failed: {e}")
            self.ml_enabled = False
    
    # ==================== 消息处理方法 ====================
    
    def _process_player_message(self, message: str, player_name: str) -> None:
        """
        处理玩家发言（使用分析模型）
        
        分析发言质量并更新玩家数据
        
        Args:
            message: 发言内容
            player_name: 玩家名称
        """
        if not message or not player_name:
            return
        
        try:
            # 使用分析模型进行消息分析
            analysis_result = self.message_analyzer.analyze_message(
                message=message,
                player_name=player_name,
                context=self._build_context()
            )
            
            # 更新玩家数据
            self._update_player_data_from_analysis(player_name, message, analysis_result)
            
            # 处理预言家声称
            if analysis_result['is_seer_claim']:
                self._handle_seer_claim(player_name, analysis_result)
            
            # 处理注入攻击
            if analysis_result['injection_detected']:
                self._handle_injection_attack(player_name)
            
            # 根据可疑度调整信任分数
            self._adjust_trust_by_suspicion(player_name, analysis_result['suspicion_level'])
            
            logger.debug(f"[WITCH] Processed message from {player_name}: {analysis_result['reasoning']}")
            
        except Exception as e:
            logger.error(f"Error processing player message: {e}")
    
    def _update_player_data_from_analysis(
        self,
        player_name: str,
        message: str,
        analysis_result: Dict[str, Any]
    ) -> None:
        """从分析结果更新玩家数据"""
        player_data = self.memory_dao.get_player_data()
        if player_name not in player_data:
            player_data[player_name] = {}
        
        player_data[player_name]["speech_quality"] = analysis_result['speech_quality']
        player_data[player_name]["last_speech"] = message[:200]
        player_data[player_name]["suspicion_level"] = analysis_result['suspicion_level']
        
        self.memory_dao.set_player_data(player_data)
    
    def _handle_seer_claim(self, player_name: str, analysis_result: Dict[str, Any]) -> None:
        """处理预言家声称"""
        player_data = self.memory_dao.get_player_data()
        player_data[player_name]["claimed_seer"] = True
        self.memory_dao.set_player_data(player_data)
        
        logger.info(f"[WITCH] {player_name} claimed to be Seer (detected by analysis model)")
        
        if analysis_result['seer_checks']:
            self._update_seer_checks(analysis_result['seer_checks'], player_name)
    
    def _handle_injection_attack(self, player_name: str) -> None:
        """处理注入攻击"""
        logger.warning(f"[WITCH] Injection attack detected from {player_name}")
        self._update_trust_score(player_name, -30, "injection attack detected by analysis model")
    
    def _adjust_trust_by_suspicion(self, player_name: str, suspicion_level: float) -> None:
        """根据可疑度调整信任分数"""
        if suspicion_level > 0.7:
            self._update_trust_score(player_name, -10, f"high suspicion level: {suspicion_level:.2f}")
        elif suspicion_level < 0.3:
            self._update_trust_score(player_name, +5, f"low suspicion level: {suspicion_level:.2f}")
    
    def _extract_seer_checks(self, message: str, seer_name: str) -> None:
        """
        从预言家发言中提取验证信息
        
        Args:
            message: 发言内容
            seer_name: 预言家名称
        """
        try:
            seer_checks = self.memory_dao.get_seer_checks()
            
            # 检测"好人"验证
            good_patterns = [
                r'No\.(\d+)\s+is\s+(?:a\s+)?(?:good|villager)',
                r'checked\s+No\.(\d+).*?(?:good|villager)',
                r'No\.(\d+).*?(?:is\s+)?(?:good|villager)',
                r'我查验.*?No\.(\d+).*?好人',
                r'No\.(\d+).*?是好人'
            ]
            
            for pattern in good_patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                for player_num in matches:
                    checked_player = f"No.{player_num}"
                    seer_checks[checked_player] = "good"
                    logger.info(f"[SEER_CHECK] {seer_name} checked {checked_player}: good")
            
            # 检测"狼人"验证
            wolf_patterns = [
                r'No\.(\d+)\s+is\s+(?:a\s+)?(?:wolf|werewolf)',
                r'checked\s+No\.(\d+).*?(?:wolf|werewolf)',
                r'No\.(\d+).*?(?:is\s+)?(?:wolf|werewolf)',
                r'我查验.*?No\.(\d+).*?狼',
                r'No\.(\d+).*?是狼'
            ]
            
            for pattern in wolf_patterns:
                matches = re.findall(pattern, message, re.IGNORECASE)
                for player_num in matches:
                    checked_player = f"No.{player_num}"
                    seer_checks[checked_player] = "wolf"
                    logger.info(f"[SEER_CHECK] {seer_name} checked {checked_player}: wolf")
            
            self.memory.set_variable("seer_checks", seer_checks)
            
        except Exception as e:
            logger.error(f"Error extracting seer checks: {e}")
    
    def _update_seer_checks(self, seer_checks: Dict[str, str], seer_name: str) -> None:
        """
        更新预言家验证信息
        
        Args:
            seer_checks: 验证信息字典 {player: 'good'/'wolf'}
            seer_name: 预言家名称
        """
        try:
            current_checks = self.memory_dao.get_seer_checks()
            
            for player, result in seer_checks.items():
                current_checks[player] = result
                logger.info(f"[SEER_CHECK] {seer_name} checked {player}: {result} (detected by analysis model)")
            
            self.memory.set_variable("seer_checks", current_checks)
            
        except Exception as e:
            logger.error(f"Error updating seer checks: {e}")
    
    def _analyze_speech_quality(self, message: str) -> int:
        """
        分析发言质量
        
        基于发言长度、关键词等因素评估质量
        
        Args:
            message: 发言内容
            
        Returns:
            质量分数(0-100)
        """
        quality = 50
        
        # 长度评分
        length = len(message)
        if 100 <= length <= 300:
            quality += 10
        elif length < 50:
            quality -= 10
        elif length > 500:
            quality -= 5  # 过长可能是废话
        
        # 关键词评分
        keywords = [
            "vote", "suspicious", "wolf", "analysis", "trust",
            "投票", "可疑", "狼人", "分析", "信任"
        ]
        keyword_count = sum(1 for kw in keywords if kw.lower() in message.lower())
        quality += min(keyword_count * 5, 20)  # 最多加20分
        
        # 限制在0-100范围内
        return max(0, min(100, quality))
    
    def _detect_seer_claim(self, message: str) -> bool:
        """
        检测预言家声称
        
        Args:
            message: 发言内容
            
        Returns:
            是否声称预言家
        """
        seer_keywords = [
            "I am Seer", "I am the Seer", "I checked",
            "我是预言家", "我验", "查验", "我查"
        ]
        return any(keyword in message for keyword in seer_keywords)
    
    def _update_trust_score(
        self,
        player: str,
        delta: float,
        reason: str = ""
    ) -> None:
        """
        更新信任分数
        
        Args:
            player: 玩家名称
            delta: 分数变化
            reason: 更新原因
        """
        try:
            trust_scores = self.memory_dao.get_trust_scores()
            
            if player not in trust_scores:
                trust_scores[player] = 50
            
            current = trust_scores[player]
            new_score = current + delta
            new_score = max(0, min(100, new_score))
            
            trust_scores[player] = new_score
            self.memory_dao.set_trust_scores(trust_scores)
            
            logger.debug(
                f"[TRUST] {player}: {current:.1f} -> {new_score:.1f} "
                f"({reason if reason else 'no reason'})"
            )
            
        except Exception as e:
            logger.error(f"Error updating trust score: {e}")
    
    # ==================== 决策方法 ====================
    
    def _make_skill_decision(self, req: AgentReq) -> Tuple[str, str]:
        """
        技能决策（解药/毒药）
        
        Args:
            req: 请求对象
            
        Returns:
            (action, target) 元组:
            - action: "antidote", "poison", 或 "none"
            - target: 目标玩家名称
        """
        try:
            # 增加夜晚计数
            self.memory_dao.increment_night()
            current_night = self.memory_dao.get_current_night()
            
            # 从历史中提取被杀玩家
            victim = self._extract_killed_player(req.history)
            
            # 解药决策
            antidote_action = self._decide_antidote_action(victim, current_night)
            if antidote_action:
                return antidote_action
            
            # 毒药决策
            poison_action = self._decide_poison_action(req, current_night)
            if poison_action:
                return poison_action
            
            logger.info(f"[SKILL] Night {current_night}: No action")
            return "none", ""
            
        except Exception as e:
            logger.error(f"Error in skill decision: {e}")
            return "none", ""
    
    def _decide_antidote_action(
        self,
        victim: Optional[str],
        current_night: int
    ) -> Optional[Tuple[str, str]]:
        """
        决定解药行动
        
        Args:
            victim: 被杀玩家
            current_night: 当前夜晚数
            
        Returns:
            (action, target)元组，或None表示不使用
        """
        if not victim or not self.memory_dao.get_has_antidote():
            return None
        
        context = self._build_context()
        should_save, reason, score = self.decision_engine.decide_antidote(
            victim, context
        )
        
        if should_save:
            self.memory_dao.set_has_antidote(False)
            self.memory_dao.add_saved_player(victim)
            logger.info(
                f"[SKILL] Night {current_night}: SAVE {victim} "
                f"({reason}, score: {score:.1f})"
            )
            return "antidote", victim
        
        return None
    
    def _decide_poison_action(
        self,
        req: AgentReq,
        current_night: int
    ) -> Optional[Tuple[str, str]]:
        """
        决定毒药行动
        
        Args:
            req: 请求对象
            current_night: 当前夜晚数
            
        Returns:
            (action, target)元组，或None表示不使用
        """
        if not self.memory_dao.get_has_poison():
            return None
        
        candidates = req.choices if hasattr(req, 'choices') and req.choices else []
        context = self._build_context()
        target, reason, score = self.decision_engine.decide_poison(
            candidates, context
        )
        
        if target:
            self.memory_dao.set_has_poison(False)
            self.memory_dao.add_poisoned_player(target)
            logger.info(
                f"[SKILL] Night {current_night}: POISON {target} "
                f"({reason}, score: {score:.1f})"
            )
            return "poison", target
        
        return None
    
    def _extract_killed_player(self, history: List[str]) -> Optional[str]:
        """
        从历史中提取被杀玩家
        
        Args:
            history: 历史消息列表
            
        Returns:
            被杀玩家名称，未找到返回None
        """
        try:
            for msg in reversed(history[-10:]):
                if "was killed" in msg or "died" in msg or "被杀" in msg:
                    match = re.search(r'No\.(\d+)', msg)
                    if match:
                        return f"No.{match.group(1)}"
            return None
        except Exception as e:
            logger.error(f"Error extracting killed player: {e}")
            return None
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """
        投票决策
        
        Args:
            candidates: 候选人列表
            
        Returns:
            目标玩家名称
        """
        try:
            if not candidates:
                return "No.1"
            
            trust_scores = self.memory_dao.get_trust_scores()
            
            # 选择信任分数最低的
            scores = {c: trust_scores.get(c, 50) for c in candidates}
            target = min(scores.items(), key=lambda x: x[1])[0]
            
            logger.info(f"[VOTE] {target} (trust: {scores[target]:.1f})")
            return target
            
        except Exception as e:
            logger.error(f"Error in vote decision: {e}")
            return candidates[0] if candidates else "No.1"
    
    def _build_context(self) -> Dict[str, Any]:
        """
        构建决策上下文
        
        Returns:
            上下文字典
        """
        return {
            "trust_scores": self.memory_dao.get_trust_scores(),
            "player_data": self.memory_dao.get_player_data(),
            "seer_checks": self.memory_dao.get_seer_checks(),
            "saved_players": self.memory_dao.get_saved_players(),
            "poisoned_players": self.memory_dao.get_poisoned_players(),
            "current_night": self.memory_dao.get_current_night(),
            "current_day": self.memory_dao.get_current_day(),
        }
    
    # ==================== 工具方法 ====================
    
    def _truncate_output(self, text: str, max_length: int) -> str:
        """
        截断输出
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _validate_player_name(
        self,
        output: str,
        valid_choices: List[str]
    ) -> str:
        """
        验证玩家名称
        
        Args:
            output: 输出文本
            valid_choices: 有效选项列表
            
        Returns:
            验证后的玩家名称
        """
        cleaned = output.strip()
        for choice in valid_choices:
            if choice in cleaned:
                return choice
        
        logger.warning(f"Invalid player name: {output}, using fallback")
        return valid_choices[0] if valid_choices else "No.1"
    
    # ==================== 主要处理方法 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """
        感知阶段（女巫技能）
        
        Args:
            req: 请求对象
            
        Returns:
            响应对象
        """
        status = req.status
        logger.info(f"[WITCH PERCEIVE] Status: {status}")
        
        if status == STATUS_SKILL:
            return self._handle_skill(req)
        
        return AgentResp(action="", content="")
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        交互阶段
        
        Args:
            req: 请求对象
            
        Returns:
            响应对象
        """
        status = req.status
        logger.info(f"[WITCH INTERACT] Status: {status}")
        
        # 根据状态分发处理
        handlers = {
            STATUS_START: self._handle_start,
            STATUS_DAY: self._handle_discussion,
            STATUS_DISCUSS: self._handle_discussion,
            STATUS_VOTE: self._handle_vote,
            STATUS_VOTE_RESULT: self._handle_vote_result,
            STATUS_SHERIFF_ELECTION: self._handle_sheriff_election,
            STATUS_SHERIFF_SPEECH: self._handle_sheriff_speech,
            STATUS_SHERIFF_VOTE: self._handle_sheriff_vote,
            STATUS_SHERIFF_SPEECH_ORDER: self._handle_sheriff_speech_order,
            STATUS_SHERIFF_PK: self._handle_sheriff_pk,
            STATUS_RESULT: self._handle_result,
        }
        
        handler = handlers.get(status)
        if handler:
            return handler(req)
        
        return AgentResp(action="", content="")
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """处理游戏开始"""
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        # 初始化所有玩家的信任分数
        all_players = set()
        for msg in req.history[:20]:
            player_matches = re.findall(r'No\.(\d+)', msg)
            for player_num in player_matches:
                all_players.add(f"No.{player_num}")
        
        trust_scores = self.memory_dao.get_trust_scores()
        for player in all_players:
            if player not in trust_scores:
                trust_scores[player] = 50
        self.memory_dao.set_trust_scores(trust_scores)
        
        logger.info(f"[WITCH] Game started, I am {my_name}")
        return AgentResp(action="", content="", success=True)
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段"""
        # 增加天数计数（只在STATUS_DAY时增加）
        if req.status == STATUS_DAY:
            current_day = self.memory_dao.get_current_day()
            self.memory.set_variable("current_day", current_day + 1)
            logger.info(f"[WITCH] Day {current_day + 1} started")
        
        # 处理其他玩家的发言
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    my_name = self.memory_dao.get_my_name()
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        # 生成发言
        has_poison = "has poison" if self.memory_dao.get_has_poison() else "no poison"
        has_antidote = "has antidote" if self.memory_dao.get_has_antidote() else "no antidote"
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name(),
            skill_info=f"{has_poison}, {has_antidote}"
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票"""
        candidates = req.choices
        
        # 使用LLM进行投票决策分析
        trust_scores = self.memory_dao.get_trust_scores()
        trust_info = "\n".join([
            f"{player}: {score:.1f}" 
            for player, score in sorted(trust_scores.items(), key=lambda x: x[1])
        ])
        
        prompt = format_prompt(
            VOTE_PROMPT,
            history="\n".join(req.history[-50:]),
            name=self.memory_dao.get_my_name(),
            choices=", ".join(candidates),
            trust_info=trust_info if trust_info else "No trust data yet"
        )
        
        # 调用LLM获取投票决策
        llm_output = self.llm_call(prompt)
        target = self._validate_player_name(llm_output, candidates)
        
        # 更新投票历史
        voting_history = self.memory_dao.get_dict("voting_history", {})
        current_day = self.memory_dao.get_current_day()
        voting_history[f"day_{current_day}"] = target
        self.memory.set_variable("voting_history", voting_history)
        
        logger.info(f"[VOTE] Day {current_day}: {target}")
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        return AgentResp(action="", content="", success=True)
    
    def _handle_skill(self, req: AgentReq) -> AgentResp:
        """处理技能使用"""
        action, target = self._make_skill_decision(req)
        
        if action == "antidote":
            return AgentResp(action="skill", content=f"antidote {target}")
        elif action == "poison":
            return AgentResp(action="skill", content=f"poison {target}")
        else:
            return AgentResp(action="skill", content="")
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举"""
        # 简单策略：不竞选警长
        return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name()
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票"""
        candidates = req.choices
        
        # 使用LLM进行警长投票决策
        trust_scores = self.memory_dao.get_trust_scores()
        trust_info = "\n".join([
            f"{player}: {score:.1f}" 
            for player, score in sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)
        ])
        
        prompt = format_prompt(
            SHERIFF_VOTE_PROMPT,
            history="\n".join(req.history[-50:]),
            name=self.memory_dao.get_my_name(),
            choices=", ".join(candidates),
            trust_info=trust_info if trust_info else "No trust data yet"
        )
        
        # 调用LLM获取投票决策
        llm_output = self.llm_call(prompt)
        target = self._validate_player_name(llm_output, candidates)
        
        logger.info(f"[SHERIFF_VOTE] {target}")
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name()
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果"""
        result = "win" if "Good faction wins" in "\n".join(req.history) else "lose"
        self.memory.set_variable("game_result", result)
        logger.info(f"[WITCH] Game ended: {result}")
        return AgentResp(action="", content="", success=True)
