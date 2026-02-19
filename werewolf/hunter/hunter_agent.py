# -*- coding: utf-8 -*-
"""
猎人代理人（重构版）
"""

from agent_build_sdk.model.roles import ROLE_HUNTER
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_VOTE_RESULT,
    STATUS_SKILL, STATUS_SKILL_RESULT, STATUS_NIGHT_INFO,
    STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE, STATUS_RESULT,
    STATUS_NIGHT, STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_VOTE, STATUS_SHERIFF, STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_SHERIFF_PK, STATUS_HUNTER, STATUS_HUNTER_RESULT,
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.hunter.prompt import (
    DESC_PROMPT, VOTE_PROMPT, SKILL_PROMPT, GAME_RULE_PROMPT,
    SHERIFF_ELECTION_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_VOTE_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT, SHERIFF_TRANSFER_PROMPT,
    SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT,
)
from typing import Dict, List, Tuple, Optional
import sys
import os

# 导入重构后的组件
from werewolf.common.utils import CacheManager
from .config import HunterConfig
from .analyzers import (
    TrustScoreAnalyzer, VotingPatternAnalyzer, SpeechQualityAnalyzer,
    ThreatLevelAnalyzer, WolfProbabilityCalculator, MemoryDAO
)
from .decision_makers import (
    VoteDecisionMaker, ShootDecisionMaker,
    SheriffElectionDecisionMaker, SheriffVoteDecisionMaker
)
from .detectors import DetectorManager
from .game_state import GameStateManager

# ML增强
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class HunterAgent(BasicRoleAgent):
    """猎人代理人（重构版）"""

    def __init__(self, model_name):
        super().__init__(ROLE_HUNTER, model_name=model_name)
        
        self.config = HunterConfig()
        self._init_memory_variables()
        self.memory_dao = MemoryDAO(self.memory)
        self.cache_manager = CacheManager()
        self.game_state_manager = GameStateManager(self.config, self.memory_dao)
        
        self._init_analyzers()
        self._init_decision_makers()
        self._init_detection_system()
        self._init_ml_enhancement()
        
        logger.info("✓ HunterAgent initialized")
    
    def _init_memory_variables(self):
        """初始化内存变量"""
        self.memory.set_variable("can_shoot", True)
        self.memory.set_variable("trust_scores", {})
        self.memory.set_variable("voting_history", {})
        self.memory.set_variable("voting_results", {})
        self.memory.set_variable("speech_history", {})
        self.memory.set_variable("injection_attempts", [])
        self.memory.set_variable("false_quotations", [])
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
        self.memory.set_variable("dead_players", set())
    
    def _init_analyzers(self):
        """初始化分析器"""
        self.trust_analyzer = TrustScoreAnalyzer(self.config, self.memory_dao)
        self.voting_analyzer = VotingPatternAnalyzer(self.config, self.memory_dao)
        self.speech_analyzer = SpeechQualityAnalyzer(self.config, self.memory_dao)
        self.threat_analyzer = ThreatLevelAnalyzer(self.config, self.memory_dao, self.cache_manager)
        
        self.wolf_prob_calculator = WolfProbabilityCalculator(
            self.config, self.trust_analyzer, self.voting_analyzer,
            self.speech_analyzer, self.memory_dao
        )
        logger.info("✓ Analyzers initialized")
    
    def _init_decision_makers(self):
        """初始化决策器"""
        self.vote_decision_maker = VoteDecisionMaker(
            self.config, self.wolf_prob_calculator,
            self.threat_analyzer, self.memory_dao
        )
        self.shoot_decision_maker = ShootDecisionMaker(
            self.config, self.wolf_prob_calculator,
            self.threat_analyzer, self.memory_dao
        )
        self.sheriff_election_decision_maker = SheriffElectionDecisionMaker(
            self.config, self.memory_dao
        )
        self.sheriff_vote_decision_maker = SheriffVoteDecisionMaker(
            self.config, self.memory_dao
        )
        logger.info("✓ Decision makers initialized")
    
    def _init_detection_system(self):
        """初始化检测系统（双模型架构）"""
        detection_client = None
        detection_model = None
        
        try:
            # 从环境变量读取检测模型配置
            detection_api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            detection_base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            detection_model_name = os.getenv('DETECTION_MODEL_NAME')
            
            if detection_api_key and detection_base_url and detection_model_name:
                from openai import OpenAI
                detection_client = OpenAI(
                    api_key=detection_api_key,
                    base_url=detection_base_url
                )
                detection_model = detection_model_name
                
                logger.info("✓ 猎人双模型架构已初始化")
                logger.info(f"  - 生成模型: {self.model_name} (用于发言生成)")
                logger.info(f"  - 分析模型: {detection_model} (用于消息分析)")
                logger.info(f"  - API地址: {detection_base_url}")
            else:
                logger.info("⚠ 未配置DETECTION_MODEL_NAME，猎人检测将使用规则模式")
        except Exception as e:
            logger.warning(f"⚠ 猎人检测客户端初始化失败: {e}，使用规则模式")
        
        self.detector_manager = DetectorManager(
            self.config, self.memory_dao, detection_client, detection_model
        )
        logger.info("✓ 猎人检测系统已初始化")
    
    def _init_ml_enhancement(self):
        """初始化ML增强"""
        self.ml_agent = None
        self.ml_enabled = False
        self.ml_confidence = 0.0
        
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled")
            return
        
        try:
            from game_utils import MLConfig
            model_dir = MLConfig.get_model_dir()
            
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            self.ml_confidence = self._calculate_ml_confidence()
            
            if self.ml_enabled:
                logger.info(f"✓ ML enabled (confidence: {self.ml_confidence:.2%})")
        except Exception as e:
            logger.error(f"✗ ML init failed: {e}")
    
    def _calculate_ml_confidence(self) -> float:
        """计算ML置信度"""
        if not self.ml_agent or not self.ml_enabled:
            return 0.0
        
        try:
            from pathlib import Path
            import json
            import math
            
            history_file = Path('./ml_models/training_history.json')
            if not history_file.exists():
                return 0.40
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if not history:
                return 0.40
            
            last_train = history[-1]
            total_samples = last_train.get('total_samples', 0)
            training_sessions = len(history)
            
            sample_bonus = min(0.40, 0.15 * math.log10(total_samples + 1)) if total_samples > 0 else 0.0
            session_bonus = min(0.15, training_sessions * 0.015)
            quality_bonus = 0.05 if last_train.get('accuracy', 0) > 0.7 else 0.0
            
            confidence = 0.40 + sample_bonus + session_bonus + quality_bonus
            return min(0.85, max(0.40, confidence))
        except Exception as e:
            logger.warning(f"[ML] Confidence calculation failed: {e}")
            return 0.40
    
    # ==================== 消息处理 ====================
    
    def _process_player_message(self, message: str, player_name: str):
        """处理玩家发言"""
        my_name = self.memory_dao.get_my_name()
        
        # 执行所有检测
        detection_results = self.detector_manager.detect_all(message, player_name, my_name)
        
        if detection_results.get('any_detected'):
            severity = detection_results.get('max_severity', -30)
            details = detection_results.get('details', {})
            
            if details.get('injection', {}).get('detected'):
                self.trust_analyzer.update_trust_score(
                    player_name, severity,
                    f"注入攻击: {details['injection'].get('reason', '')}",
                    confidence=details['injection'].get('confidence', 0.9)
                )
            
            if details.get('false_quotation', {}).get('detected'):
                self.trust_analyzer.update_trust_score(
                    player_name, -15,
                    f"虚假引用: {details['false_quotation'].get('quoted_player', '')}",
                    confidence=details['false_quotation'].get('confidence', 0.8)
                )
            
            if details.get('status_contradiction', {}).get('detected'):
                self.trust_analyzer.update_trust_score(
                    player_name, -35, "状态矛盾",
                    confidence=details['status_contradiction'].get('confidence', 0.95)
                )
        
        # 分析发言质量
        speech_modifier = self.speech_analyzer.analyze(player_name, message)
        if abs(speech_modifier) > 0.05:
            delta = speech_modifier * 20
            self.trust_analyzer.update_trust_score(player_name, delta, "发言质量")
        
        # 记录发言历史
        speech_history = self.memory_dao.get_speech_history()
        if player_name not in speech_history:
            speech_history[player_name] = []
        speech_history[player_name].append(message)
        self.memory_dao.set_speech_history(speech_history)
    
    # ==================== 决策方法 ====================
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """投票决策"""
        my_name = self.memory_dao.get_my_name()
        game_phase = self.game_state_manager.assess_game_phase()
        target, reason, _ = self.vote_decision_maker.decide(candidates, my_name, game_phase)
        logger.info(f"[VOTE] {target}: {reason}")
        return target
    
    def _make_shoot_decision(self, candidates: List[str]) -> str:
        """开枪决策"""
        my_name = self.memory_dao.get_my_name()
        game_phase = self.game_state_manager.assess_game_phase()
        current_day = self.game_state_manager.get_current_day()
        alive_count = self.game_state_manager.count_alive_players()
        
        target, reason, _ = self.shoot_decision_maker.decide(
            candidates, my_name, game_phase, current_day, alive_count
        )
        logger.info(f"[SHOOT] {target}: {reason}")
        return target
    
    def _make_sheriff_election_decision(self) -> bool:
        """警长选举决策"""
        game_situation = self.game_state_manager.evaluate_game_situation()
        current_round = self.game_state_manager.get_current_day()
        should_run, reason = self.sheriff_election_decision_maker.decide(game_situation, current_round)
        logger.info(f"[SHERIFF ELECTION] {should_run}: {reason}")
        return should_run
    
    def _make_sheriff_vote_decision(self, candidates: List[str]) -> str:
        """警长投票决策"""
        target, reason = self.sheriff_vote_decision_maker.decide(candidates)
        logger.info(f"[SHERIFF VOTE] {target}: {reason}")
        return target
    
    # ==================== 工具方法 ====================
    
    def _truncate_output(self, text: str, max_length: int, add_ellipsis: bool = True) -> str:
        """截断输出"""
        if len(text) <= max_length:
            return text
        if add_ellipsis and max_length > 3:
            return text[:max_length - 3] + "..."
        return text[:max_length]
    
    def _validate_player_name(self, output: str, valid_choices: List[str]) -> str:
        """验证玩家名称"""
        cleaned = output.strip()
        for choice in valid_choices:
            if choice in cleaned:
                return choice
        logger.warning(f"Invalid player name: {output}, using fallback")
        return valid_choices[0] if valid_choices else "No.1"
    
    def _initialize_trust_score(self, player_name: str):
        """初始化信任分数"""
        trust_scores = self.memory_dao.get_trust_scores()
        if player_name not in trust_scores:
            trust_scores[player_name] = 50
            self.memory_dao.set_trust_scores(trust_scores)
    
    def _track_voting_accuracy(self, voter: str, target: str, was_wolf: bool):
        """跟踪投票准确度"""
        self.voting_analyzer.track_voting_accuracy(voter, target, was_wolf)
    
    def _track_voting_pattern(self, voter: str, target: str):
        """跟踪投票模式"""
        voting_history = self.memory.load_variable("voting_history") or {}
        if voter not in voting_history:
            voting_history[voter] = []
        voting_history[voter].append(target)
        self.memory.set_variable("voting_history", voting_history)

    # ==================== 主要处理方法 ====================

    def perceive(self, req: AgentReq) -> AgentResp:
        """
        感知阶段（猎人技能）

        Args:
            req: Agent请求对象

        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[HUNTER PERCEIVE] Status: {status}")

        try:
            if status == STATUS_SKILL:
                return self._handle_skill(req)

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
        logger.info(f"[HUNTER INTERACT] Status: {status}")

        try:
            # 更新游戏状态
            self.game_state_manager.update_dead_players()

            # 根据状态分发处理
            handler_map = {
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

            handler = handler_map.get(status)
            if handler:
                return handler(req)
            else:
                logger.warning(f"[INTERACT] Unknown status: {status}")
                return AgentResp(action="", content="")

        except Exception as e:
            logger.error(f"[INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(action="", content="")


    
    # ==================== 主要处理方法 ====================
    
    def handle(self, req: AgentReq) -> AgentResp:
        """处理游戏请求"""
        status = req.status
        logger.info(f"[HUNTER] Status: {status}")
        
        # 更新游戏状态
        self.game_state_manager.update_dead_players()
        
        # 根据状态分发处理
        if status == STATUS_START:
            return self._handle_start(req)
        elif status == STATUS_DAY or status == STATUS_DISCUSS:
            return self._handle_discussion(req)
        elif status == STATUS_VOTE:
            return self._handle_vote(req)
        elif status == STATUS_VOTE_RESULT:
            return self._handle_vote_result(req)
        elif status == STATUS_SKILL:
            return self._handle_skill(req)
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
        logger.info(f"[HUNTER] Game started, I am {my_name}")
        return AgentResp(action="", content="")
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段"""
        # 处理其他玩家的发言
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    if player_name != self.memory_dao.get_my_name():
                        self._process_player_message(message, player_name)
        
        # 生成发言
        game_phase = self.game_state_manager.assess_game_phase()
        shoot_info = "can shoot" if self.memory_dao.get_can_shoot() else "already shot"
        
        # 检查是否有注入攻击者需要曝光
        injection_attempts = self.memory_dao.get_injection_attempts()
        injection_suspects = list(set([att['player'] for att in injection_attempts]))
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history),
            name=self.memory_dao.get_my_name(),
            shoot_info=shoot_info,
            injection_suspects=", ".join(injection_suspects) if injection_suspects else "None"
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票"""
        candidates = req.choices
        target = self._make_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        # 从历史记录中提取投票结果
        for msg in req.history[-5:]:
            if "Vote result is:" in msg or "was eliminated" in msg:
                # 更新死亡玩家
                self.game_state_manager.update_dead_players()
                break
        
        return AgentResp(action="", content="")
    
    def _handle_skill(self, req: AgentReq) -> AgentResp:
        """处理技能使用（开枪）"""
        candidates = req.choices
        
        # 检查是否可以开枪
        if not self.memory_dao.get_can_shoot():
            logger.info("[HUNTER] Cannot shoot (already used or poisoned)")
            return AgentResp(action="skill", content="Do Not Shoot")
        
        # 决定是否开枪
        target = self._make_shoot_decision(candidates)
        
        if target == "Do Not Shoot":
            return AgentResp(action="skill", content="Do Not Shoot")
        
        # 验证目标
        target = self._validate_player_name(target, candidates)
        
        # 标记已使用技能
        self.memory_dao.set_can_shoot(False)
        
        logger.info(f"[HUNTER] Shooting: {target}")
        return AgentResp(action="skill", content=target)
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举"""
        should_run = self._make_sheriff_election_decision()
        
        if should_run:
            return AgentResp(action="sheriff_election", content="Run for Sheriff")
        else:
            return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        shoot_info = "can shoot" if self.memory_dao.get_can_shoot() else "already shot"
        
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history),
            name=self.memory_dao.get_my_name(),
            shoot_info=shoot_info
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票"""
        candidates = req.choices
        target = self._make_sheriff_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        # 简单策略：默认顺时针
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        shoot_info = "can shoot" if self.memory_dao.get_can_shoot() else "already shot"
        
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history),
            name=self.memory_dao.get_my_name(),
            shoot_info=shoot_info
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果"""
        # 记录游戏结果用于ML训练
        result = "win" if "Good faction wins" in "\n".join(req.history) else "lose"
        self.memory.set_variable("game_result", result)
        logger.info(f"[HUNTER] Game ended: {result}")
        
        # 触发游戏结束处理，收集特征数据并训练模型
        try:
            from werewolf.game_utils import GameEndTrigger
            GameEndTrigger.trigger_game_end(req, self.memory, "Hunter")
        except Exception as e:
            logger.error(f"[HUNTER] Failed to trigger game end: {e}")
        
        return AgentResp(action="", content="")
