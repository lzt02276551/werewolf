# -*- coding: utf-8 -*-
"""
守卫代理人（重构版）
从3400+行精简到约500行
"""

from agent_build_sdk.model.roles import ROLE_GUARD
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
from werewolf.guard.prompt import (
    DESC_PROMPT, VOTE_PROMPT, SKILL_PROMPT, GAME_RULE_PROMPT,
    SHERIFF_ELECTION_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_VOTE_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT, SHERIFF_TRANSFER_PROMPT,
    SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT
)
from typing import Dict, List, Tuple, Optional, Any
import sys
import os

# 导入重构后的组件
from .config import GuardConfig
from .trust_manager import TrustScoreManager
from .decision_makers import VoteDecisionMaker, GuardDecisionMaker
from .validators import DataValidator, MemoryValidator
from .detectors import InjectionDetector, FalseQuotationDetector, StatusContradictionDetector, SpeechQualityDetector
from .analyzers import WolfProbabilityAnalyzer, VotingPatternAnalyzer, RoleEstimator, WolfKillPredictor, GuardPriorityCalculator

# ML增强
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class GuardAgent(BasicRoleAgent):
    """守卫代理人（重构版）"""

    def __init__(self, model_name):
        super().__init__(ROLE_GUARD, model_name=model_name)
        
        self.config = GuardConfig()
        self._init_memory_variables()
        
        # 初始化检测专用LLM客户端
        self.detection_client, self.detection_model = self._init_detection_client()
        
        # 初始化组件
        self.trust_manager = TrustScoreManager(self.memory)
        self._init_components()
        self._init_ml_enhancement()
        
        logger.info("✓ GuardAgent initialized (Dual Model Architecture)")
        logger.info(f"  - Generation Model: {model_name}")
        logger.info(f"  - Analysis Model: {self.detection_model or '规则模式'}")
    
    def _init_detection_client(self) -> Tuple[Optional[any], Optional[str]]:
        """
        初始化消息检测专用的LLM客户端
        
        从环境变量读取检测模型配置，创建独立的分析LLM客户端
        
        Returns:
            (detection_client, detection_model) 元组
        """
        detection_model = os.getenv('DETECTION_MODEL_NAME')
        
        if not detection_model:
            logger.info("⚠ 未配置DETECTION_MODEL_NAME，守卫消息检测将使用规则模式")
            return None, None
        
        try:
            from openai import OpenAI
            
            # 优先使用检测专用配置，否则回退到主模型配置
            api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if not api_key or not base_url:
                logger.warning("⚠ 未配置检测模型API，守卫消息检测将使用规则模式")
                return None, None
            
            # 创建检测专用客户端
            detection_client = OpenAI(api_key=api_key, base_url=base_url)
            
            logger.info("✓ 守卫双模型架构已初始化")
            logger.info(f"  - 生成模型: {self.model_name} (用于发言生成)")
            logger.info(f"  - 分析模型: {detection_model} (用于消息分析)")
            logger.info(f"  - API地址: {base_url}")
            
            return detection_client, detection_model
            
        except Exception as e:
            logger.error(f"✗ 初始化检测专用LLM失败: {e}，将使用规则模式")
            return None, None
    
    def _init_memory_variables(self):
        """初始化内存变量"""
        self.memory.set_variable("last_guarded", "")
        self.memory.set_variable("trust_scores", {})
        self.memory.set_variable("alive_players", set())
        self.memory.set_variable("dead_players", set())
        self.memory.set_variable("key_events", [])
        self.memory.set_variable("injection_suspects", {})
        self.memory.set_variable("night_count", 0)
        self.memory.set_variable("day_count", 0)
        self.memory.set_variable("guard_history", [])
        self.memory.set_variable("voting_history", {})
        self.memory.set_variable("voting_results", {})
        self.memory.set_variable("speech_history", {})
        self.memory.set_variable("false_quotations", [])
        self.memory.set_variable("wolf_kill_pattern", [])
        self.memory.set_variable("player_status_claims", {})
        self.memory.set_variable("injection_corrections", [])
        self.memory.set_variable("trust_history", {})
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
    
    def _init_components(self):
        """初始化组件"""
        # 初始化检测器（传入检测专用LLM客户端）
        self.injection_detector = InjectionDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.false_quotation_detector = FalseQuotationDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.status_contradiction_detector = StatusContradictionDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.speech_quality_detector = SpeechQualityDetector(
            self.config, self.detection_client, self.detection_model
        )
        
        # 初始化分析器
        self.wolf_analyzer = WolfProbabilityAnalyzer(self.config, self.memory, self.trust_manager)
        self.voting_analyzer = VotingPatternAnalyzer(self.config, self.memory)
        self.role_estimator = RoleEstimator(self.config, self.memory, self.trust_manager)
        self.wolf_kill_predictor = WolfKillPredictor(self.config, self.memory, self.trust_manager, self.role_estimator)
        self.guard_priority_calculator = GuardPriorityCalculator(self.config, self.memory, self.trust_manager, self.role_estimator)
        
        # 初始化决策器
        self.vote_decision_maker = VoteDecisionMaker(self.config, self.memory, self.trust_manager)
        self.guard_decision_maker = GuardDecisionMaker(self.config, self.memory, self.trust_manager)
        
        # 注入分析器到决策器（依赖注入）
        self.vote_decision_maker.set_analyzers(self.wolf_analyzer, self.voting_analyzer)
        self.guard_decision_maker.set_analyzers(self.role_estimator, self.wolf_kill_predictor, self.guard_priority_calculator)
        
        logger.info("✓ Components initialized")
    
    def _init_ml_enhancement(self):
        """初始化ML增强"""
        self.ml_agent = None
        self.ml_enabled = False
        
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled")
            return
        
        try:
            from game_utils import MLConfig
            model_dir = MLConfig.get_model_dir()
            
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            
            if self.ml_enabled:
                logger.info("✓ ML enhancement enabled")
        except Exception as e:
            logger.error(f"✗ ML init failed: {e}")
    
    # ==================== 消息处理 ====================
    
    def _process_player_message(self, message: str, player_name: str):
        """处理玩家发言（企业级版本）"""
        try:
            # 记录发言历史
            speech_history = MemoryValidator.safe_load_dict(self.memory, "speech_history")
            if player_name not in speech_history:
                speech_history[player_name] = []
            speech_history[player_name].append(message)
            self.memory.set_variable("speech_history", speech_history)
            
            # 1. 注入攻击检测
            detected, injection_type, confidence = self.injection_detector.detect(message, player_name)
            if detected:
                injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
                injection_suspects[player_name] = injection_type
                self.memory.set_variable("injection_suspects", injection_suspects)
                
                if injection_type == "system_fake":
                    self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_INJECTION_SYSTEM_FAKE, 
                                                   "Type 1 injection: System fake", confidence)
                elif injection_type == "status_fake":
                    self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_INJECTION_STATUS_FAKE,
                                                   "Type 2 injection: Status fake", confidence)
                elif injection_type == "benign":
                    self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_INJECTION_BENIGN,
                                                   "Benign wolf analysis", confidence)
            
            # 2. 虚假引用检测
            detected, fq_detail = self.false_quotation_detector.detect(message, player_name, speech_history)
            if detected and fq_detail:
                false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
                false_quotations.append(fq_detail)
                self.memory.set_variable("false_quotations", false_quotations)
                
                self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_FALSE_QUOTATION,
                                               "False quotation detected", fq_detail.get("confidence", 0.8))
            
            # 3. 状态矛盾检测
            dead_players = MemoryValidator.safe_load_set(self.memory, "dead_players")
            detected, contradiction_type = self.status_contradiction_detector.detect(message, player_name, dead_players)
            if detected:
                player_status_claims = MemoryValidator.safe_load_dict(self.memory, "player_status_claims")
                player_status_claims[player_name] = contradiction_type
                self.memory.set_variable("player_status_claims", player_status_claims)
                
                self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_STATUS_CONTRADICTION,
                                               f"Status contradiction: {contradiction_type}", 0.9)
            
            # 4. 发言质量分析
            quality_result = self.speech_quality_detector.analyze(message)
            if quality_result["assessment"] == "high_quality":
                self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_GOOD_SPEECH,
                                               "High quality speech", 0.6)
            elif quality_result["assessment"] == "low_quality":
                self.trust_manager.update_score(player_name, self.config.TRUST_DELTA_SHORT_SPEECH,
                                               "Low quality speech", 0.6)
            
        except Exception as e:
            logger.error(f"[PROCESS MESSAGE] Error: {e}")
    
    # ==================== 决策方法 ====================
    
    def _make_guard_decision(self, candidates: List[str]) -> str:
        """守卫决策"""
        my_name = self.memory.load_variable("name")
        night_count = MemoryValidator.safe_load_int(self.memory, "night_count", 0)
        last_guarded = self.memory.load_variable("last_guarded") or ""
        
        target, reason = self.guard_decision_maker.decide(candidates, my_name, night_count, last_guarded)
        logger.info(f"[GUARD] {target if target else 'empty'}: {reason}")
        return target
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """投票决策"""
        my_name = self.memory.load_variable("name")
        target, reason = self.vote_decision_maker.decide(candidates, my_name)
        logger.info(f"[VOTE] {target}: {reason}")
        return target if target else (candidates[0] if candidates else "")
    
    # ==================== 工具方法 ====================
    
    def _truncate_output(self, text: str, max_length: int) -> str:
        """截断输出"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _validate_player_name(self, output: str, valid_choices: List[str]) -> str:
        """验证玩家名称"""
        cleaned = output.strip()
        for choice in valid_choices:
            if choice in cleaned:
                return choice
        logger.warning(f"Invalid player name: {output}, using fallback")
        return valid_choices[0] if valid_choices else "No.1"
    
    def _update_game_state(self, req: AgentReq):
        """更新游戏状态"""
        # 更新存活/死亡玩家
        dead_players = MemoryValidator.safe_load_set(self.memory, "dead_players")
        
        for msg in req.history[-10:]:
            if any(keyword in msg for keyword in ["died", "killed", "eliminated", "shot"]):
                import re
                player_matches = re.findall(r'No\.(\d+)', msg)
                for player_num in player_matches:
                    player_name = f"No.{player_num}"
                    dead_players.add(player_name)
        
        self.memory.set_variable("dead_players", dead_players)
    
    # ==================== 主要处理方法 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """感知阶段（守卫技能）"""
        status = req.status
        logger.info(f"[GUARD PERCEIVE] Status: {status}")
        
        if status == STATUS_SKILL:
            return self._handle_guard_skill(req)
        
        return AgentResp(action="", content="")
    
    def interact(self, req: AgentReq) -> AgentResp:
        """交互阶段"""
        status = req.status
        logger.info(f"[GUARD INTERACT] Status: {status}")
        
        # 更新游戏状态
        self._update_game_state(req)
        
        # 根据状态分发处理
        if status == STATUS_START:
            return self._handle_start(req)
        elif status == STATUS_DAY or status == STATUS_DISCUSS:
            return self._handle_discussion(req)
        elif status == STATUS_VOTE:
            return self._handle_vote(req)
        elif status == STATUS_VOTE_RESULT:
            return self._handle_vote_result(req)
        elif status == STATUS_SHERIFF_ELECTION:
            return self._handle_sheriff_election(req)
        elif status == STATUS_SHERIFF_SPEECH:
            return self._handle_sheriff_speech(req)
        elif status == STATUS_SHERIFF_VOTE:
            return self._handle_sheriff_vote(req)
        elif status == STATUS_SHERIFF_SPEECH_ORDER:
            return self._handle_sheriff_speech_order(req)
        elif status == STATUS_SHERIFF_PK:
            return self._handle_sheriff_pk(req)
        elif status == STATUS_RESULT:
            return self._handle_result(req)
        else:
            return AgentResp(action="", content="")
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """处理游戏开始"""
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        # 初始化所有玩家的信任分数
        import re
        all_players = set()
        for msg in req.history[:20]:
            player_matches = re.findall(r'No\.(\d+)', msg)
            for player_num in player_matches:
                all_players.add(f"No.{player_num}")
        
        self.trust_manager.initialize_players(list(all_players))
        logger.info(f"[GUARD] Game started, I am {my_name}")
        return AgentResp(action="", content="")
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段（双模型架构）"""
        # 处理其他玩家的发言
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    my_name = self.memory.load_variable("name")
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        # 模型1：分析模型 - 分析当前局势
        analysis_result = self._analyze_game_state(req)
        
        # 模型2：生成模型 - 基于分析结果生成发言
        speech = self._generate_speech(req, analysis_result)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _analyze_game_state(self, req: AgentReq) -> Dict[str, Any]:
        """模型1：分析游戏状态（分析模型）"""
        trust_summary = self.trust_manager.get_summary(top_n=8)
        injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
        false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
        
        # 构建分析提示词
        analysis_prompt = f"""Analyze the current game state as Guard:

History (last 30 messages):
{chr(10).join(req.history[-30:])}

Trust Scores: {trust_summary}
Injection Suspects: {list(injection_suspects.keys())}
False Quotations: {len(false_quotations)} detected

Task: Provide a structured analysis:
1. Most suspicious players (2-3) with evidence
2. Most trusted players (2-3) with reasons
3. Key events to mention
4. Recommended voting target

Keep analysis concise and factual."""
        
        # 调用分析模型（使用较低temperature以获得更客观的分析）
        analysis_text = self.llm_call(analysis_prompt)
        
        return {
            "analysis_text": analysis_text,
            "trust_summary": trust_summary,
            "injection_suspects": injection_suspects,
            "false_quotations": false_quotations
        }
    
    def _generate_speech(self, req: AgentReq, analysis: Dict[str, Any]) -> str:
        """模型2：生成发言（生成模型）"""
        # 构建生成提示词 - 使用字典方式传参
        prompt_vars = {
            "history": "\n".join(req.history[-30:]),
            "name": self.memory.load_variable("name"),
            "trust_summary": analysis["trust_summary"],
            "guard_info": "",
            "game_phase": "Day",
            "current_day": 1,
            "alive_count": 12,
            "injection_suspects": str(list(analysis["injection_suspects"].keys())),
            "false_quotations": str(len(analysis["false_quotations"])),
            "status_contradictions": "None",
            "phase_strategy": "Analyze and identify suspicious players"
        }
        
        prompt = format_prompt(DESC_PROMPT, prompt_vars)
        
        # 添加分析结果作为上下文
        enhanced_prompt = f"""{prompt}

[Internal Analysis for Reference]:
{analysis["analysis_text"]}

Based on the above analysis, generate your speech (900-1300 characters):"""
        
        # 调用生成模型
        speech = self.llm_call(enhanced_prompt)
        
        return speech
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票"""
        candidates = req.choices
        target = self._make_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        # 更新死亡玩家
        self._update_game_state(req)
        return AgentResp(action="", content="")
    
    def _handle_guard_skill(self, req: AgentReq) -> AgentResp:
        """处理守卫技能"""
        # 增加夜晚计数
        night_count = MemoryValidator.safe_load_int(self.memory, "night_count", 0)
        night_count += 1
        self.memory.set_variable("night_count", night_count)
        
        candidates = req.choices
        target = self._make_guard_decision(candidates)
        
        # 记录守卫历史
        guard_history = MemoryValidator.safe_load_list(self.memory, "guard_history")
        guard_history.append(target if target else "empty")
        self.memory.set_variable("guard_history", guard_history)
        self.memory.set_variable("last_guarded", target)
        
        logger.info(f"[GUARD] Night {night_count}: {target if target else 'empty guard'}")
        return AgentResp(action="skill", content=target if target else "")
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举"""
        # 简单策略：不竞选警长
        return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        prompt_vars = {
            "history": "\n".join(req.history[-30:]),
            "name": self.memory.load_variable("name"),
            "trust_summary": self.trust_manager.get_summary(top_n=8)
        }
        
        prompt = format_prompt(SHERIFF_SPEECH_PROMPT, prompt_vars)
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票"""
        candidates = req.choices
        # 简单策略：投给信任分数最高的
        if candidates:
            target = max(candidates, key=lambda p: self.trust_manager.get_score(p))
        else:
            target = candidates[0] if candidates else "No.1"
        
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        prompt_vars = {
            "history": "\n".join(req.history[-30:]),
            "name": self.memory.load_variable("name"),
            "trust_summary": self.trust_manager.get_summary(top_n=8)
        }
        
        prompt = format_prompt(SHERIFF_PK_PROMPT, prompt_vars)
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果（增量学习集成）"""
        result = "win" if "Good faction wins" in "\n".join(req.history) else "lose"
        self.memory.set_variable("game_result", result)
        logger.info(f"[GUARD] Game ended: {result}")
        
        # 收集游戏数据用于增量学习
        self._collect_game_data_for_learning(req, result)
        
        return AgentResp(action="", content="")
    
    def _collect_game_data_for_learning(self, req: AgentReq, result: str):
        """收集游戏数据用于增量学习"""
        try:
            from game_end_handler import get_game_end_handler
            from incremental_learning import IncrementalLearningSystem
            
            # 获取游戏结束处理器
            handler = get_game_end_handler()
            
            # 如果还没有学习系统，初始化它
            if handler.learning_system is None and self.ml_agent and self.ml_enabled:
                learning_system = IncrementalLearningSystem(self.ml_agent, retrain_interval=5)
                handler.learning_system = learning_system
                logger.info("✓ Incremental learning system initialized")
            
            # 收集所有玩家的特征数据
            my_name = self.memory.load_variable("name")
            trust_scores = self.trust_manager.get_all_scores()
            voting_results = MemoryValidator.safe_load_dict(self.memory, "voting_results")
            speech_history = MemoryValidator.safe_load_dict(self.memory, "speech_history")
            injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
            false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
            
            # 为每个玩家构建特征数据
            for player_name, trust_score in trust_scores.items():
                if player_name == my_name:
                    continue  # 跳过自己
                
                # 计算投票准确率
                vote_accuracy = 0.5
                if player_name in voting_results and voting_results[player_name]:
                    results = voting_results[player_name]
                    wolf_hits = sum(1 for r in results if isinstance(r, (tuple, list)) and len(r) >= 2 and r[1])
                    vote_accuracy = wolf_hits / len(results) if results else 0.5
                
                # 计算发言长度
                speech_lengths = [100]  # 默认值
                if player_name in speech_history and speech_history[player_name]:
                    speech_lengths = [len(s) for s in speech_history[player_name]]
                
                # 统计异常行为
                contradiction_count = 1 if player_name in injection_suspects else 0
                injection_attempts = 1 if player_name in injection_suspects and injection_suspects[player_name] in ["system_fake", "status_fake"] else 0
                false_quotation_count = sum(1 for fq in false_quotations if isinstance(fq, dict) and fq.get("accuser") == player_name)
                
                # 构建玩家数据
                player_stats = {
                    "trust_score": trust_score,
                    "vote_accuracy": vote_accuracy,
                    "contradiction_count": contradiction_count,
                    "injection_attempts": injection_attempts,
                    "false_quotation_count": false_quotation_count,
                    "speech_lengths": speech_lengths,
                    "voting_speed_avg": 5.0,  # 默认值
                    "vote_targets": [],
                    "mentions_others_count": len(speech_history.get(player_name, [])) * 3,
                    "mentioned_by_others_count": 2,
                    "aggressive_score": 0.5,
                    "defensive_score": 0.5,
                    "emotion_keyword_count": 5,
                    "logic_keyword_count": 3,
                    "night_survival_rate": 0.5,
                    "alliance_strength": 0.5,
                    "isolation_score": 0.5,
                    "speech_consistency_score": 0.7,
                    "avg_response_time": 5.0,
                    "role": "unknown"  # 实际角色需要从游戏结果中获取
                }
                
                # 更新处理器中的玩家统计
                handler.update_player_stats(player_name, player_stats)
            
            # 触发游戏结束处理
            result_message = "\n".join(req.history[-5:])
            handler.on_game_end(result_message)
            
            logger.info("✓ Game data collected for incremental learning")
            
        except Exception as e:
            logger.warning(f"Failed to collect game data for learning: {e}")
            # 不影响主流程，只记录警告
