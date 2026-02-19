# -*- coding: utf-8 -*-
"""
Wolf Agent - 狼人代理人（企业级重构版）

职责:
1. 继承BaseAgent，实现Wolf特定逻辑
2. 管理Wolf状态和记忆
3. 协调各组件完成决策
4. 提供夜晚击杀和白天投票决策

依赖:
- werewolf.core.base_agent.BaseAgent
- werewolf.wolf.config.WolfConfig
- werewolf.wolf.base_components.WolfMemoryDAO
- werewolf.wolf.decision_engine.WolfDecisionEngine
"""

from typing import Dict, List, Tuple, Optional, Any
import sys
import os
import re

from agent_build_sdk.model.roles import ROLE_WOLF
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_VOTE_RESULT,
    STATUS_SKILL, STATUS_SKILL_RESULT, STATUS_NIGHT_INFO,
    STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE, STATUS_RESULT,
    STATUS_NIGHT, STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_PK, STATUS_SHERIFF_VOTE, STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_SHERIFF, STATUS_HUNTER, STATUS_HUNTER_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.sdk.agent import format_prompt

from werewolf.wolf.config import WolfConfig
from werewolf.wolf.base_components import WolfMemoryDAO, DataValidator
from werewolf.wolf.decision_engine import WolfDecisionEngine
from werewolf.wolf.prompt import (
    DESC_PROMPT, VOTE_PROMPT, KILL_PROMPT, WOLF_SPEECH_PROMPT,
    GAME_RULE_PROMPT, CLEAN_USER_PROMPT, SHERIFF_ELECTION_PROMPT,
    SHERIFF_SPEECH_PROMPT, SHERIFF_VOTE_PROMPT, SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT, SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT
)

# ML增强（可选）
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class WolfAgent(BasicRoleAgent):
    """
    Wolf Agent - 狼人代理人
    
    继承BasicRoleAgent（SDK要求），实现Wolf特定逻辑
    
    注意: 由于SDK限制，暂时继承BasicRoleAgent而非BaseAgent
    未来版本将迁移到BaseAgent
    
    Attributes:
        config: Wolf配置对象
        memory_dao: 内存数据访问对象
        decision_engine: 决策引擎
        ml_agent: ML增强代理（可选）
        ml_enabled: ML是否启用
    """
    
    # 常量定义
    DEFAULT_INTELLIGENCE_SCORE = 50
    DEFAULT_THREAT_LEVEL = 50
    DEFAULT_BREAKTHROUGH_VALUE = 50
    
    SPEECH_QUALITY_EXCELLENT = 70
    SPEECH_QUALITY_POOR = 30
    SPEECH_LENGTH_MIN = 50
    SPEECH_LENGTH_OPTIMAL_MIN = 100
    SPEECH_LENGTH_OPTIMAL_MAX = 300
    
    INTELLIGENCE_DELTA_POSITIVE = 5
    INTELLIGENCE_DELTA_NEGATIVE = -5
    THREAT_DELTA_POSITIVE = 5
    THREAT_DELTA_NEGATIVE = -5
    BREAKTHROUGH_DELTA_POSITIVE = 5
    BREAKTHROUGH_DELTA_NEGATIVE = -5
    
    def __init__(self, model_name: str, analysis_model_name: str = None):
        """
        初始化Wolf Agent
        
        Args:
            model_name: LLM模型名称（用于生成发言）
            analysis_model_name: 分析模型名称（用于分析消息），如果为None则从环境变量读取DETECTION_MODEL_NAME
        """
        super().__init__(ROLE_WOLF, model_name=model_name)
        
        # 双模型架构：分析模型和生成模型
        # 优先级：参数 > 环境变量DETECTION_MODEL_NAME > 主模型
        self.analysis_model_name = (
            analysis_model_name or 
            os.getenv('DETECTION_MODEL_NAME') or 
            model_name
        )
        self.generation_model_name = model_name
        
        # 初始化配置
        self.config = WolfConfig()
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Invalid Wolf config: {e}")
            raise
        
        # 初始化内存变量
        self._initialize_memory_variables()
        
        # 初始化组件
        self.memory_dao = WolfMemoryDAO(self.memory)
        self.decision_engine = WolfDecisionEngine(self.config, self.memory_dao)
        
        # 初始化分析客户端（用于消息分析）
        self._initialize_analysis_client()
        
        # 初始化ML增强（可选）
        self._initialize_ml_enhancement()
        
        logger.info("✓ WolfAgent initialized successfully")
        logger.info(f"  - Analysis model: {self.analysis_model_name}")
        logger.info(f"  - Generation model: {self.generation_model_name}")
    
    def _initialize_analysis_client(self) -> None:
        """
        初始化分析客户端
        
        创建独立的LLM客户端用于消息分析
        """
        self.analysis_client = None
        
        # 如果分析模型与生成模型相同，不需要独立客户端
        if self.analysis_model_name == self.generation_model_name:
            logger.info("Analysis model same as generation model, using shared client")
            return
        
        try:
            from openai import OpenAI
            
            # 获取检测模型的API配置
            detection_api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            detection_base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if detection_api_key and detection_base_url:
                self.analysis_client = OpenAI(
                    api_key=detection_api_key,
                    base_url=detection_base_url
                )
                logger.info(f"✓ Analysis LLM client initialized (Model: {self.analysis_model_name})")
            else:
                logger.warning("Detection API not configured, using shared client")
        except Exception as e:
            logger.warning(f"Failed to initialize analysis client: {e}, using shared client")
    
    def _initialize_memory_variables(self) -> None:
        """
        初始化内存变量
        
        设置所有需要的内存变量初始值
        """
        memory_vars = {
            "teammates": [],
            "teammate_intelligence": {},
            "threat_levels": {},
            "voting_history": {},
            "voting_results": {},
            "breakthrough_values": {},
            "speech_quality": {},
            "identified_roles": {},
            "wolves_eliminated": 0,
            "good_players_eliminated": 0,
            "current_night": 0,
            "current_day": 0,
            "witch_antidote_used": False,
            "witch_poison_used": False,
            "injection_attempts": {},
            "intelligence_history": {},
            "threat_history": {},
            "breakthrough_history": {},
            "game_data_collected": [],
            "game_result": None,
        }
        
        for key, value in memory_vars.items():
            self.memory.set_variable(key, value)
        
        logger.debug("Memory variables initialized")
    
    def _initialize_ml_enhancement(self) -> None:
        """
        初始化ML增强功能
        
        如果ML可用且配置启用，则初始化ML代理
        """
        self.ml_agent = None
        self.ml_enabled = False
        
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled (not available)")
            return
        
        if not self.config.enable_ml:
            logger.info("ML enhancement disabled (config)")
            return
        
        try:
            from game_utils import MLConfig
            model_dir = MLConfig.get_model_dir()
            
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            
            if self.ml_enabled:
                logger.info("✓ ML enhancement enabled")
            else:
                logger.info("ML enhancement disabled (ML agent not enabled)")
        except Exception as e:
            logger.error(f"✗ ML initialization failed: {e}")
            self.ml_enabled = False

    
    # ==================== 消息处理方法 ====================
    
    def _process_player_message(self, message: str, player_name: str) -> None:
        """
        处理玩家发言
        
        分析发言质量，评估队友智商或好人威胁/可突破值
        
        Args:
            message: 发言内容
            player_name: 玩家名称
        """
        if not message or not player_name:
            logger.warning("Empty message or player_name in _process_player_message")
            return
        
        if not DataValidator.validate_player_name(player_name):
            logger.warning(f"Invalid player name: {player_name}")
            return
        
        teammates = self.memory_dao.get_teammates()
        
        # 分析发言质量
        quality = self._analyze_speech_quality(message)
        speech_quality = self.memory_dao.get_speech_quality()
        speech_quality[player_name] = quality
        self.memory.set_variable("speech_quality", speech_quality)
        
        # 根据是否是队友进行不同的评估
        if player_name in teammates:
            self._evaluate_teammate_intelligence(player_name, message, quality)
        else:
            self._evaluate_good_player(player_name, message, quality)
    
    def _analyze_speech_quality(self, message: str) -> int:
        """
        分析发言质量 - 使用LLM分析模型
        
        使用专门的分析模型评估发言质量，替代硬编码规则
        
        Args:
            message: 发言内容
            
        Returns:
            质量分数 (0-100)
        """
        # 如果启用ML，优先使用ML分析
        if self.ml_enabled and self.ml_agent:
            try:
                # 构建简化的玩家数据用于ML分析
                player_data = {
                    'speech_lengths': [len(message)],
                    'trust_score': 50,  # 默认值
                    'vote_accuracy': 0.5,
                    'contradiction_count': 0,
                    'injection_attempts': 0,
                    'false_quotation_count': 0,
                    'voting_speed_avg': 5.0,
                    'speech_similarity_avg': 0.5,
                    'night_survival_rate': 0.5,
                    'sheriff_votes_received': 0,
                    'aggressive_score': 0.5,
                    'defensive_score': 0.5,
                    'logic_keyword_count': 0,
                    'emotion_keyword_count': 0
                }
                
                # ML预测（狼人概率越高，质量越可疑）
                wolf_prob = self.ml_agent.predict_wolf_probability(player_data)
                # 转换为质量分数：好人发言质量高，狼人发言质量低
                ml_quality = int((1 - wolf_prob) * 100)
                
                logger.debug(f"ML speech quality: {ml_quality} (wolf_prob: {wolf_prob:.3f})")
                return ml_quality
            except Exception as e:
                logger.debug(f"ML analysis failed, fallback to LLM: {e}")
        
        # 使用LLM分析模型进行深度分析
        try:
            analysis_prompt = f"""Analyze the quality of this speech in a Werewolf game.
Consider: logic, coherence, persuasiveness, and strategic value.

Speech: {message}

Rate the quality from 0-100 (0=very poor, 100=excellent).
Return ONLY a number between 0 and 100."""

            # 使用分析客户端（如果可用）或主客户端
            if self.analysis_client:
                response = self.analysis_client.chat.completions.create(
                    model=self.analysis_model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.3
                )
                response_text = response.choices[0].message.content
            else:
                # 使用主客户端
                response_text = self.llm_call(analysis_prompt)
            
            # 提取数字
            import re
            numbers = re.findall(r'\d+', response_text)
            if numbers:
                quality = int(numbers[0])
                quality = max(0, min(100, quality))
                logger.debug(f"LLM speech quality: {quality}")
                return quality
        except Exception as e:
            logger.debug(f"LLM analysis failed, fallback to heuristic: {e}")
        
        # 后备方案：简化的启发式评估
        quality = self.DEFAULT_INTELLIGENCE_SCORE
        
        # 长度评分
        length = len(message)
        if self.SPEECH_LENGTH_OPTIMAL_MIN <= length <= self.SPEECH_LENGTH_OPTIMAL_MAX:
            quality += 10
        elif length < self.SPEECH_LENGTH_MIN:
            quality -= 10
        
        # 限制在0-100范围内
        return max(0, min(100, quality))
    
    def _evaluate_teammate_intelligence(
        self, 
        teammate: str, 
        message: str, 
        quality: int
    ) -> None:
        """
        评估队友智商
        
        根据发言质量调整队友智商评分
        
        Args:
            teammate: 队友名称
            message: 发言内容
            quality: 发言质量分数
        """
        intelligence = self.memory_dao.get_teammate_intelligence()
        
        # 初始化智商分数
        if teammate not in intelligence:
            intelligence[teammate] = self.DEFAULT_INTELLIGENCE_SCORE
        
        # 根据发言质量调整智商
        if quality >= self.SPEECH_QUALITY_EXCELLENT:
            delta = self.INTELLIGENCE_DELTA_POSITIVE
        elif quality < self.SPEECH_QUALITY_POOR:
            delta = self.INTELLIGENCE_DELTA_NEGATIVE
        else:
            delta = 0
        
        if delta != 0:
            current = intelligence[teammate]
            new_score = max(0, min(100, current + delta))
            intelligence[teammate] = new_score
            self.memory_dao.set_teammate_intelligence(intelligence)
            
            logger.debug(
                f"[TEAMMATE] {teammate} intelligence: {current} -> {new_score} "
                f"(quality: {quality})"
            )
    
    def _evaluate_good_player(
        self, 
        player: str, 
        message: str, 
        quality: int
    ) -> None:
        """
        评估好人玩家
        
        根据发言质量调整威胁等级和可突破值
        
        Args:
            player: 玩家名称
            message: 发言内容
            quality: 发言质量分数
        """
        threat_levels = self.memory_dao.get_threat_levels()
        breakthrough_values = self.memory_dao.get_breakthrough_values()
        
        # 初始化分数
        if player not in threat_levels:
            threat_levels[player] = self.DEFAULT_THREAT_LEVEL
        if player not in breakthrough_values:
            breakthrough_values[player] = self.DEFAULT_BREAKTHROUGH_VALUE
        
        # 根据发言质量调整
        if quality >= self.SPEECH_QUALITY_EXCELLENT:
            # 高质量发言：威胁增加，可突破值降低
            threat_levels[player] = min(100, threat_levels[player] + self.THREAT_DELTA_POSITIVE)
            breakthrough_values[player] = max(0, breakthrough_values[player] + self.BREAKTHROUGH_DELTA_NEGATIVE)
        elif quality < self.SPEECH_QUALITY_POOR:
            # 低质量发言：威胁降低，可突破值增加
            threat_levels[player] = max(0, threat_levels[player] + self.THREAT_DELTA_NEGATIVE)
            breakthrough_values[player] = min(100, breakthrough_values[player] + self.BREAKTHROUGH_DELTA_POSITIVE)
        
        self.memory_dao.set_threat_levels(threat_levels)
        self.memory_dao.set_breakthrough_values(breakthrough_values)
    
    # ==================== 决策方法 ====================
    
    def _make_kill_decision(self, candidates: List[str]) -> str:
        """
        击杀决策 - 集成ML预测
        
        使用决策引擎和ML模型共同选择击杀目标
        
        Args:
            candidates: 候选人列表
            
        Returns:
            目标玩家名称
        """
        if not candidates:
            logger.warning("[KILL] No candidates provided")
            return ""
        
        context = self._build_decision_context()
        
        # 如果启用ML，增强决策上下文
        if self.ml_enabled and self.ml_agent:
            context['ml_predictions'] = self._get_ml_predictions_for_candidates(candidates)
        
        target, reason, confidence = self.decision_engine.decide_kill_target(candidates, context)
        
        # 如果决策引擎没有返回目标，使用后备策略
        if not target and candidates:
            teammates = self.memory_dao.get_teammates()
            non_teammates = [c for c in candidates if c not in teammates]
            target = non_teammates[0] if non_teammates else candidates[0]
            reason = "Fallback selection (no valid decision)"
            logger.warning(f"[KILL] Using fallback target: {target}")
        
        logger.info(f"[KILL] Target: {target}, Reason: {reason}, Confidence: {confidence:.2f}")
        return target if target else (candidates[0] if candidates else "")
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """
        投票决策 - 集成ML预测
        
        使用决策引擎和ML模型共同选择投票目标
        
        Args:
            candidates: 候选人列表
            
        Returns:
            目标玩家名称
        """
        if not candidates:
            logger.warning("[VOTE] No candidates provided")
            return ""
        
        context = self._build_decision_context()
        
        # 如果启用ML，增强决策上下文
        if self.ml_enabled and self.ml_agent:
            context['ml_predictions'] = self._get_ml_predictions_for_candidates(candidates)
        
        target, reason, confidence = self.decision_engine.decide_vote_target(candidates, context)
        
        # 如果决策引擎没有返回目标，使用后备策略
        if not target and candidates:
            target = candidates[0]
            reason = "Fallback selection (no valid decision)"
            logger.warning(f"[VOTE] Using fallback target: {target}")
        
        logger.info(f"[VOTE] Target: {target}, Reason: {reason}, Confidence: {confidence:.2f}")
        return target if target else (candidates[0] if candidates else "")
    
    def _get_ml_predictions_for_candidates(self, candidates: List[str]) -> Dict[str, float]:
        """
        获取候选人的ML预测结果
        
        Args:
            candidates: 候选人列表
            
        Returns:
            {player_name: wolf_probability}
        """
        predictions = {}
        
        for candidate in candidates:
            # 从内存中获取玩家数据
            player_data = self._build_player_data_for_ml(candidate)
            
            try:
                wolf_prob = self.ml_agent.predict_wolf_probability(player_data)
                predictions[candidate] = wolf_prob
                logger.debug(f"ML prediction for {candidate}: {wolf_prob:.3f}")
            except Exception as e:
                logger.debug(f"ML prediction failed for {candidate}: {e}")
                predictions[candidate] = 0.5  # 默认值
        
        return predictions
    
    def _build_player_data_for_ml(self, player_name: str) -> Dict:
        """
        为ML预测构建玩家数据
        
        Args:
            player_name: 玩家名称
            
        Returns:
            玩家数据字典
        """
        # 从内存中提取玩家相关数据
        threat_levels = self.memory_dao.get_threat_levels()
        breakthrough_values = self.memory_dao.get_breakthrough_values()
        speech_quality = self.memory_dao.get_speech_quality()
        voting_history = self.memory_dao.get_voting_history()
        
        return {
            'trust_score': 100 - threat_levels.get(player_name, 50),  # 威胁越高，信任越低
            'speech_lengths': [100],  # 简化
            'vote_accuracy': 0.5,  # 简化
            'contradiction_count': 0,
            'injection_attempts': 0,
            'false_quotation_count': 0,
            'voting_speed_avg': 5.0,
            'speech_similarity_avg': 0.5,
            'night_survival_rate': 0.5,
            'sheriff_votes_received': 0,
            'aggressive_score': threat_levels.get(player_name, 50) / 100.0,
            'defensive_score': breakthrough_values.get(player_name, 50) / 100.0,
            'logic_keyword_count': speech_quality.get(player_name, 50) // 10,
            'emotion_keyword_count': 5
        }
    
    def _build_decision_context(self) -> Dict[str, Any]:
        """
        构建决策上下文
        
        收集所有决策所需的信息
        
        Returns:
            决策上下文字典
        """
        return {
            "teammates": self.memory_dao.get_teammates(),
            "teammate_intelligence": self.memory_dao.get_teammate_intelligence(),
            "threat_levels": self.memory_dao.get_threat_levels(),
            "breakthrough_values": self.memory_dao.get_breakthrough_values(),
            "identified_roles": self.memory_dao.get_identified_roles(),
            "voting_history": self.memory_dao.get_voting_history(),
            "speech_quality": self.memory_dao.get_speech_quality(),
        }
    
    # ==================== 工具方法 ====================
    
    def _truncate_output(self, text: str, max_length: int) -> str:
        """
        截断输出文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _validate_player_name(self, output: str, valid_choices: List[str]) -> str:
        """
        验证并提取玩家名称
        
        从LLM输出中提取有效的玩家名称
        
        Args:
            output: LLM输出
            valid_choices: 有效选项列表
            
        Returns:
            有效的玩家名称
        """
        if not valid_choices:
            logger.error("No valid choices provided")
            return "No.1"
        
        cleaned = output.strip()
        
        # 尝试在输出中找到有效选项
        for choice in valid_choices:
            if choice in cleaned:
                return choice
        
        # 如果没找到，使用第一个选项作为后备
        logger.warning(f"Invalid player name in output: {output}, using fallback: {valid_choices[0]}")
        return valid_choices[0]
    
    def _extract_teammates(self, history: List[str]) -> List[str]:
        """
        从历史消息中提取队友信息
        
        Args:
            history: 历史消息列表
            
        Returns:
            队友名称列表
        """
        teammates = []
        
        # 只检查前20条消息（游戏开始时的信息）
        for msg in history[:20]:
            if "Your teammates are" in msg or "你的队友是" in msg:
                # 提取队友编号
                matches = re.findall(r'No\.(\d+)', msg)
                teammates = [f"No.{m}" for m in matches]
                logger.info(f"Extracted teammates: {teammates}")
                break
        
        return teammates

    
    # ==================== 主要处理方法 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """
        感知阶段（狼人击杀）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF PERCEIVE] Status: {status}")
        
        try:
            if status == STATUS_SKILL:
                return self._handle_kill(req)
            
            return AgentResp(action="", content="")
            
        except Exception as e:
            logger.error(f"[PERCEIVE] Error: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        交互阶段
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF INTERACT] Status: {status}")
        
        try:
            # 根据状态分发处理
            handler_map = {
                STATUS_START: self._handle_start,
                STATUS_WOLF_SPEECH: self._handle_wolf_speech,
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
            
            handler = handler_map.get(status)
            if handler:
                return handler(req)
            else:
                logger.warning(f"[INTERACT] Unknown status: {status}")
                return AgentResp(action="", content="")
                
        except Exception as e:
            logger.error(f"[INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    # ==================== 状态处理方法 ====================
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """
        处理游戏开始
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        # 提取队友
        teammates = self._extract_teammates(req.history)
        self.memory_dao.set_teammates(teammates)
        
        logger.info(f"[WOLF] Game started, I am {my_name}, teammates: {teammates}")
        return AgentResp(action="", content="")
    
    def _handle_wolf_speech(self, req: AgentReq) -> AgentResp:
        """
        处理狼人内部发言
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        teammates = self.memory_dao.get_teammates()
        
        prompt = format_prompt(
            WOLF_SPEECH_PROMPT,
            history="\n".join(req.history[-20:]),
            name=self.memory_dao.get_my_name(),
            teammates=", ".join(teammates)
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[WOLF_SPEECH] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        # 处理其他玩家的发言
        my_name = self.memory_dao.get_my_name()
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        # 生成发言
        teammates = self.memory_dao.get_teammates()
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            teammates=", ".join(teammates)
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[DISCUSSION] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        candidates = req.choices
        if not candidates:
            logger.warning("[VOTE] No candidates provided")
            return AgentResp(action="vote", content="No.1")
        
        target = self._make_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """
        处理投票结果
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        # 可以在这里分析投票结果，更新玩家评估
        logger.debug("[VOTE_RESULT] Processing vote result")
        return AgentResp(action="", content="")
    
    def _handle_kill(self, req: AgentReq) -> AgentResp:
        """
        处理击杀
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        candidates = req.choices
        if not candidates:
            logger.warning("[KILL] No candidates provided")
            return AgentResp(action="skill", content="No.1")
        
        target = self._make_kill_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        logger.info(f"[KILL] Final target: {target}")
        return AgentResp(action="skill", content=target)
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举
        
        简单策略：不竞选警长
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        logger.info("[SHERIFF_ELECTION] Choosing not to run")
        return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选发言
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name()
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[SHERIFF_SPEECH] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """
        处理警长投票
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        candidates = req.choices
        if not candidates:
            logger.warning("[SHERIFF_VOTE] No candidates provided")
            return AgentResp(action="vote", content="No.1")
        
        teammates = self.memory_dao.get_teammates()
        
        # 优先投队友
        teammate_candidates = [c for c in candidates if c in teammates]
        if teammate_candidates:
            target = teammate_candidates[0]
            logger.info(f"[SHERIFF_VOTE] Voting for teammate: {target}")
        else:
            # 否则投威胁最低的
            threat_levels = self.memory_dao.get_threat_levels()
            scores = {c: threat_levels.get(c, self.DEFAULT_THREAT_LEVEL) for c in candidates}
            target = min(scores.items(), key=lambda x: x[1])[0]
            logger.info(f"[SHERIFF_VOTE] Voting for lowest threat: {target}")
        
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """
        处理警长发言顺序选择
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        logger.info("[SHERIFF_SPEECH_ORDER] Choosing Clockwise")
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK发言
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name()
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[SHERIFF_PK] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """
        处理游戏结果
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        history_text = "\n".join(req.history)
        result = "win" if "Wolf faction wins" in history_text else "lose"
        self.memory.set_variable("game_result", result)
        
        logger.info(f"[WOLF] Game ended: {result}")
        return AgentResp(action="", content="")
