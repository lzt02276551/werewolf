# -*- coding: utf-8 -*-
"""
预言家代理人 - 重构版
使用模块化架构，应用面向对象设计原则
"""

from agent_build_sdk.model.roles import ROLE_SEER
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq, 
    STATUS_START, STATUS_NIGHT, STATUS_SKILL, STATUS_SKILL_RESULT, 
    STATUS_NIGHT_INFO, STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE, 
    STATUS_VOTE_RESULT, STATUS_RESULT, 
    STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH, STATUS_SHERIFF_VOTE, 
    STATUS_SHERIFF, STATUS_SHERIFF_SPEECH_ORDER, STATUS_SHERIFF_PK,
    STATUS_HUNTER, STATUS_HUNTER_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.sdk.agent import format_prompt
from .prompt import (
    DESC_PROMPT, VOTE_PROMPT, SKILL_PROMPT, GAME_RULE_PROMPT,
    SHERIFF_ELECTION_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_VOTE_PROMPT, 
    SHERIFF_SPEECH_ORDER_PROMPT, SHERIFF_TRANSFER_PROMPT, SHERIFF_PK_PROMPT, 
    LAST_WORDS_PROMPT
)
from typing import Dict, List, Tuple, Optional
import os

# 导入重构后的模块
from .config import SeerConfig
from .memory_dao import SeerMemoryDAO
from .detectors import (
    InjectionDetector, FalseQuotationDetector, StatusContradictionDetector,
    SpeechQualityAnalyzer, MessageParser
)
from .analyzers import (
    TrustScoreManager, WolfProbabilityEstimator, VotingPatternAnalyzer,
    GamePhaseAnalyzer, CheckPriorityCalculator
)
from .decision_makers import (
    VoteDecisionMaker, CheckDecisionMaker, SheriffElectionDecisionMaker,
    SheriffVoteDecisionMaker, BadgeTransferDecisionMaker, SpeechOrderDecisionMaker,
    IdentityRevealDecisionMaker
)
from .ml_integration import MLAgent, MLDataCollector, MLTrainer
from .utils import (
    SpeechTruncator, PlayerExtractor, CheckReasonGenerator,
    LastWordsDetector, AnalysisFormatter, VotingAnalysisFormatter
)


class SeerAgent(BasicRoleAgent):
    """
    预言家代理人 - 重构版
    
    使用模块化架构，集成：
    - 检测器：注入攻击、虚假引用、状态矛盾等
    - 分析器：信任分数、狼人概率、投票模式等
    - 决策器：投票、检查、警长选举等
    - ML集成：模型训练、预测、数据收集
    """

    def __init__(self, model_name):
        super().__init__(ROLE_SEER, model_name=model_name)
        
        # 初始化配置
        self.config = SeerConfig()
        
        # 初始化DAO
        self.memory_dao = SeerMemoryDAO(self.memory)
        
        # 初始化所有memory变量
        self._init_memory_variables()
        
        # 初始化检测专用LLM客户端（在super().__init__之后，self.client已经存在）
        self.detection_client, self.detection_model = self._init_detection_client()
        
        # 初始化所有组件
        self._init_components()
        
        logger.info("✓ SeerAgent initialized successfully with modular architecture")

    
    def _init_memory_variables(self):
        """初始化所有memory变量"""
        self.memory.set_variable("checked_players", {})
        self.memory.set_variable("player_data", {})
        self.memory.set_variable("game_state", {})
        self.memory.set_variable("trust_scores", {})
        self.memory.set_variable("trust_history", {})
        self.memory.set_variable("voting_history", {})
        self.memory.set_variable("voting_results", {})
        self.memory.set_variable("speech_history", {})
        self.memory.set_variable("injection_attempts", [])
        self.memory.set_variable("false_quotations", [])
        self.memory.set_variable("night_count", 0)
        self.memory.set_variable("day_count", 0)
        self.memory.set_variable("player_status_claims", {})
        self.memory.set_variable("injection_corrections", [])
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
        self.memory.set_variable("dead_players", set())
    
    def _init_detection_client(self) -> Tuple[Optional[any], Optional[str]]:
        """
        初始化消息检测专用的LLM客户端
        
        从环境变量读取检测模型配置，创建独立的分析LLM客户端
        
        Returns:
            (detection_client, detection_model) 元组
        """
        detection_model = os.getenv('DETECTION_MODEL_NAME')
        
        if not detection_model:
            logger.info("⚠ 未配置DETECTION_MODEL_NAME，预言家消息检测将使用规则模式")
            return None, None
        
        try:
            from openai import OpenAI
            
            # 优先使用检测专用配置，否则回退到主模型配置
            api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if not api_key or not base_url:
                logger.warning("⚠ 未配置检测模型API，预言家消息检测将使用规则模式")
                return None, None
            
            # 创建检测专用客户端
            detection_client = OpenAI(api_key=api_key, base_url=base_url)
            
            logger.info("✓ 预言家双模型架构已初始化")
            logger.info(f"  - 生成模型: {self.model_name} (用于发言生成)")
            logger.info(f"  - 分析模型: {detection_model} (用于消息分析)")
            logger.info(f"  - API地址: {base_url}")
            
            return detection_client, detection_model
            
        except Exception as e:
            logger.error(f"✗ 初始化检测专用LLM失败: {e}，将使用规则模式")
            return None, None

    
    def _init_components(self):
        """初始化所有组件"""
        # 检测器
        self.injection_detector = InjectionDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.false_quotation_detector = FalseQuotationDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.status_contradiction_detector = StatusContradictionDetector(
            self.config, self.detection_client, self.detection_model
        )
        self.speech_quality_analyzer = SpeechQualityAnalyzer(
            self.config, self.detection_client, self.detection_model
        )
        self.message_parser = MessageParser(
            self.config, self.detection_client, self.detection_model
        )
        
        # 分析器
        self.trust_score_manager = TrustScoreManager(self.config)
        self.wolf_prob_estimator = WolfProbabilityEstimator(self.config)
        self.voting_pattern_analyzer = VotingPatternAnalyzer(self.config)
        self.game_phase_analyzer = GamePhaseAnalyzer(self.config)
        self.check_priority_calculator = CheckPriorityCalculator(self.config)
        
        # 决策器
        self.vote_decision_maker = VoteDecisionMaker(
            self.config, self.wolf_prob_estimator, self.voting_pattern_analyzer
        )
        self.check_decision_maker = CheckDecisionMaker(self.config)
        self.sheriff_election_maker = SheriffElectionDecisionMaker(self.config)
        self.sheriff_vote_maker = SheriffVoteDecisionMaker(self.config)
        self.badge_transfer_maker = BadgeTransferDecisionMaker(self.config)
        self.speech_order_maker = SpeechOrderDecisionMaker(self.config)
        self.identity_reveal_maker = IdentityRevealDecisionMaker(self.config)
        
        # ML集成
        self.ml_agent = MLAgent(self.config, self.memory_dao)
        self.ml_data_collector = MLDataCollector(self.config, self.memory_dao)
        self.ml_trainer = MLTrainer(self.config, self.memory_dao, self.ml_agent)
        
        # 工具类
        self.speech_truncator = SpeechTruncator(self.config)
        self.player_extractor = PlayerExtractor()
        self.check_reason_generator = CheckReasonGenerator(self.config)
        self.last_words_detector = LastWordsDetector()
        self.analysis_formatter = AnalysisFormatter()
        self.voting_analysis_formatter = VotingAnalysisFormatter()
        
        logger.info("✓ All components initialized")

    
    def perceive(self, req=AgentReq):
        """处理游戏事件（重构版 - 使用模块化组件）"""
        if req.status == STATUS_START:
            self._handle_game_start(req)
        elif req.status == STATUS_NIGHT:
            self._handle_night(req)
        elif req.status == STATUS_SKILL_RESULT:
            self._handle_skill_result(req)
        elif req.status == STATUS_NIGHT_INFO:
            self._handle_night_info(req)
        elif req.status == STATUS_DISCUSS:
            self._handle_discuss(req)
        elif req.status == STATUS_VOTE:
            self._handle_vote(req)
        elif req.status == STATUS_VOTE_RESULT:
            self._handle_vote_result(req)
        elif req.status == STATUS_SHERIFF_ELECTION:
            self._handle_sheriff_election(req)
        elif req.status == STATUS_SHERIFF_SPEECH:
            self._handle_sheriff_speech(req)
        elif req.status == STATUS_SHERIFF_VOTE:
            self._handle_sheriff_vote(req)
        elif req.status == STATUS_SHERIFF:
            self._handle_sheriff(req)
        elif req.status == STATUS_HUNTER:
            self._handle_hunter(req)
        elif req.status == STATUS_HUNTER_RESULT:
            self._handle_hunter_result(req)
        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            self._handle_sheriff_speech_order(req)
        elif req.status == STATUS_SHERIFF_PK:
            self._handle_sheriff_pk(req)
        elif req.status == STATUS_RESULT:
            self._handle_game_end(req)
        else:
            raise NotImplementedError(f"Status {req.status} not implemented")

    
    def _handle_game_start(self, req):
        """处理游戏开始"""
        self.memory.clear()
        self.memory_dao.append_history(GAME_RULE_PROMPT)
        self.memory_dao.append_history(f"Host: Hello, your assigned role is [Seer], you are {req.name}")
        self.memory.set_variable("name", req.name)
        
        # 处理游戏开始（生成统一的game_id）
        from game_utils import GameStartHandler
        GameStartHandler.handle_game_start(req, self.memory, "Seer")
        
        logger.info(f"Game started: {req.name} as Seer")
    
    def _handle_night(self, req):
        """处理夜晚阶段"""
        self.memory_dao.append_history("Host: Night falls, everyone close your eyes")
        
        # 增加夜晚和白天计数
        night_count = self.memory_dao.get_night_count() + 1
        self.memory_dao.set_night_count(night_count)
        
        day_count = self.memory_dao.get_day_count() + 1
        self.memory_dao.set_day_count(day_count)
        
        logger.info(f"Night {night_count}, Day {day_count}")
    
    def _handle_skill_result(self, req):
        """处理技能结果（检查结果）"""
        self.memory_dao.append_history(req.message)
        
        # 解析检查结果
        target_player = req.name
        is_wolf = 'wolf' in req.message.lower() or 'werewolf' in req.message.lower()
        
        # 记录检查结果
        night_count = self.memory_dao.get_night_count()
        self.memory_dao.add_checked_player(target_player, is_wolf, night_count)
        
        # 更新信任分数
        trust_scores = self.memory_dao.get_trust_scores()
        trust_history = self.memory_dao.get_trust_history()
        
        if is_wolf:
            self.trust_score_manager.update(
                target_player, self.config.TRUST_WOLF_CHECK, 1.0, 1.0,
                trust_scores, trust_history
            )
        else:
            self.trust_score_manager.update(
                target_player, self.config.TRUST_GOOD_CHECK, 1.0, 1.0,
                trust_scores, trust_history
            )
        
        self.memory_dao.set_trust_scores(trust_scores)
        self.memory_dao.set_trust_history(trust_history)
        
        logger.info(f"Check result: {target_player} is {'WOLF' if is_wolf else 'GOOD'}")
    
    def _handle_night_info(self, req):
        """处理夜晚信息（死亡公告）"""
        self.memory_dao.append_history(f"Host: It's daybreak! Last night's information is: {req.message}")
        
        # 更新死亡玩家
        if "died" in req.message.lower() or "killed" in req.message.lower():
            for word in req.message.split():
                if word.startswith("No."):
                    self.memory_dao.add_dead_player(word)
                    
                    # 更新信任分数（夜晚被杀通常是好人）
                    trust_scores = self.memory_dao.get_trust_scores()
                    trust_history = self.memory_dao.get_trust_history()
                    
                    self.trust_score_manager.update(
                        word, self.config.TRUST_KILLED_AT_NIGHT, 0.8, 0.8,
                        trust_scores, trust_history
                    )
                    
                    self.memory_dao.set_trust_scores(trust_scores)
                    self.memory_dao.set_trust_history(trust_history)
                    
                    logger.info(f"Night kill victim {word}: trust +{self.config.TRUST_KILLED_AT_NIGHT}")

    
    def _handle_discuss(self, req):
        """处理讨论阶段（使用检测器和分析器）"""
        if req.name:
            # 初始化信任分数
            trust_scores = self.memory_dao.get_trust_scores()
            if req.name not in trust_scores:
                trust_scores[req.name] = 50
                self.memory_dao.set_trust_scores(trust_scores)
            
            # 检查是否是遗言阶段
            if self.last_words_detector.is_last_words_phase(req.message):
                logger.info(f"[LAST WORDS PHASE] {req.name} is giving their last words - skipping detection")
                self.memory_dao.append_history(req.name + ': ' + req.message)
                return
            
            # 使用检测器分析发言
            self._analyze_player_speech(req.name, req.message)
            
            # 记录发言历史
            speech_history = self.memory_dao.get_speech_history()
            if req.name not in speech_history:
                speech_history[req.name] = []
            speech_history[req.name].append(req.message)
            self.memory_dao.set_speech_history(speech_history)
            
            self.memory_dao.append_history(req.name + ': ' + req.message)
        else:
            self.memory_dao.append_history(f'Host: Now entering day {req.round}.')
            self.memory_dao.append_history('Host: Each player describe your information.')
    
    def _analyze_player_speech(self, player_name: str, message: str):
        """分析玩家发言（使用检测器）"""
        player_data = self.memory_dao.get_player_data()
        if player_name not in player_data:
            player_data[player_name] = {}
        
        trust_scores = self.memory_dao.get_trust_scores()
        trust_history = self.memory_dao.get_trust_history()
        
        # 1. 注入攻击检测
        injection_type = self.injection_detector.detect(message)
        
        if injection_type == 'SYSTEM_FAKE':
            player_data[player_name]['malicious_injection'] = True
            self.trust_score_manager.update(
                player_name, self.config.TRUST_INJECTION_ATTACK_SYSTEM, 0.95, 1.0,
                trust_scores, trust_history
            )
            self.memory_dao.add_injection_attempt({'player': player_name, 'type': 'system_fake'})
            logger.warning(f"[CRITICAL] Detected SYSTEM_FAKE injection from {player_name}")
            
        elif injection_type == 'STATUS_FAKE':
            player_data[player_name]['malicious_injection'] = True
            self.trust_score_manager.update(
                player_name, self.config.TRUST_INJECTION_ATTACK_STATUS, 0.85, 1.0,
                trust_scores, trust_history
            )
            self.memory_dao.add_injection_attempt({'player': player_name, 'type': 'status_fake'})
            logger.warning(f"[WARNING] Detected STATUS_FAKE injection from {player_name}")
        
        # 2. 状态矛盾检测
        dead_players = self.memory_dao.get_dead_players()
        if self.status_contradiction_detector.detect(player_name, message, dead_players):
            logger.warning(f"[STATUS CONTRADICTION] {player_name} claims to be dead but is still speaking")
        
        # 3. 虚假引用检测
        history = self.memory_dao.get_history()
        false_quote_result = self.false_quotation_detector.detect(player_name, message, history)
        is_false_quote = false_quote_result.get('detected', False)
        confidence = false_quote_result.get('confidence', 0.0)
        
        if is_false_quote and confidence > 0.7:
            player_data[player_name]['false_quotes'] = True
            self.trust_score_manager.update(
                player_name, self.config.TRUST_FALSE_QUOTATION, confidence, 0.9,
                trust_scores, trust_history
            )
            self.memory_dao.add_false_quotation({
                'player': player_name, 
                'message': message, 
                'confidence': confidence
            })
            logger.warning(f"[WARNING] Detected false quote from {player_name} (confidence: {confidence:.2f})")
        
        # 4. 发言质量分析
        if len(message) >= 100:
            is_logical = self.speech_quality_analyzer.is_logical(message)
            if is_logical:
                player_data[player_name]['logical_speech'] = True
                self.trust_score_manager.update(
                    player_name, self.config.TRUST_LOGICAL_SPEECH, 0.8, 0.7,
                    trust_scores, trust_history
                )
                logger.info(f"{player_name} has logical speech, trust +{self.config.TRUST_LOGICAL_SPEECH}")
        
        # 保存更新
        self.memory_dao.set_player_data(player_data)
        self.memory_dao.set_trust_scores(trust_scores)
        self.memory_dao.set_trust_history(trust_history)

    
    def _handle_vote(self, req):
        """处理投票"""
        voter = req.name
        target = req.message
        
        voting_history = self.memory_dao.get_voting_history()
        if voter not in voting_history:
            voting_history[voter] = []
        voting_history[voter].append(target)
        self.memory_dao.set_voting_history(voting_history)
        
        self.memory_dao.append_history(f'Day {req.round} voting phase, {voter} voted for {target}')
    
    def _handle_vote_result(self, req):
        """处理投票结果"""
        out_player = req.name if req.name else req.message
        if out_player:
            self.memory_dao.append_history(f'Host: Vote result is: {out_player}.')
            self.memory_dao.add_dead_player(out_player)
            
            # 更新信任分数
            trust_scores = self.memory_dao.get_trust_scores()
            trust_history = self.memory_dao.get_trust_history()
            
            self.trust_score_manager.update(
                out_player, self.config.TRUST_VOTED_OUT, 0.7, 0.8,
                trust_scores, trust_history
            )
            
            self.memory_dao.set_trust_scores(trust_scores)
            self.memory_dao.set_trust_history(trust_history)
            
            # 如果玩家已被验证，更新投票准确度
            checked_players = self.memory_dao.get_checked_players()
            if out_player in checked_players:
                was_wolf = checked_players[out_player]['is_wolf']
                self._update_voting_accuracy(out_player, was_wolf)
                logger.info(f"Verified player eliminated: {out_player} ({'wolf' if was_wolf else 'good'})")
        else:
            self.memory_dao.append_history('Host: No one is eliminated.')
    
    def _update_voting_accuracy(self, out_player: str, was_wolf: bool):
        """更新投票准确度"""
        voting_history = self.memory_dao.get_voting_history()
        voting_results = self.memory_dao.get_voting_results()
        trust_scores = self.memory_dao.get_trust_scores()
        trust_history = self.memory_dao.get_trust_history()
        
        for voter, votes in voting_history.items():
            if out_player in votes:
                if voter not in voting_results:
                    voting_results[voter] = []
                voting_results[voter].append((out_player, was_wolf))
                
                # 更新信任分数
                if was_wolf:
                    self.trust_score_manager.update(
                        voter, self.config.TRUST_ACCURATE_VOTING, 1.0, 1.0,
                        trust_scores, trust_history
                    )
                    logger.info(f"{voter} voted correctly (verified wolf), trust +{self.config.TRUST_ACCURATE_VOTING}")
                else:
                    self.trust_score_manager.update(
                        voter, self.config.TRUST_INACCURATE_VOTING, 1.0, 1.0,
                        trust_scores, trust_history
                    )
                    logger.info(f"{voter} voted incorrectly (verified good), trust {self.config.TRUST_INACCURATE_VOTING}")
        
        self.memory_dao.set_voting_results(voting_results)
        self.memory_dao.set_trust_scores(trust_scores)
        self.memory_dao.set_trust_history(trust_history)
    
    def _handle_sheriff_election(self, req):
        """处理警长选举"""
        self.memory_dao.append_history("Host: Players running for sheriff: " + req.message)
        
        game_state = self.memory_dao.get_game_state()
        game_state['sheriff_election'] = True
        self.memory_dao.set_game_state(game_state)
        
        # 更新候选人信任分数
        trust_scores = self.memory_dao.get_trust_scores()
        trust_history = self.memory_dao.get_trust_history()
        
        for candidate in req.message.split(","):
            candidate = candidate.strip()
            if candidate:
                self.trust_score_manager.update(
                    candidate, 5, 0.5, 0.5,
                    trust_scores, trust_history
                )
        
        self.memory_dao.set_trust_scores(trust_scores)
        self.memory_dao.set_trust_history(trust_history)
    
    def _handle_sheriff_speech(self, req):
        """处理警长竞选发言"""
        self.memory_dao.append_history(req.name + " (campaign speech): " + req.message)
        
        # 检测假预言家
        if req.name != self.memory_dao.get_my_name():
            parsed_info = self.message_parser.parse(req.message, req.name)
            
            if parsed_info.get("claimed_role") == "seer":
                game_state = self.memory_dao.get_game_state()
                game_state['fake_seer_present'] = True
                game_state['fake_seer_name'] = req.name
                self.memory_dao.set_game_state(game_state)
                logger.warning(f"FAKE SEER detected: {req.name}")
    
    def _handle_sheriff_vote(self, req):
        """处理警长投票"""
        self.memory_dao.append_history("Sheriff vote: " + req.name + " voted for " + req.message)
    
    def _handle_sheriff(self, req):
        """处理警长结果"""
        if req.name:
            self.memory_dao.append_history("Host: Sheriff badge belongs to: " + req.name)
            self.memory_dao.set_sheriff(req.name)
            
            # 更新信任分数
            trust_scores = self.memory_dao.get_trust_scores()
            trust_history = self.memory_dao.get_trust_history()
            
            self.trust_score_manager.update(
                req.name, self.config.TRUST_ELECTED_SHERIFF, 0.7, 0.7,
                trust_scores, trust_history
            )
            
            self.memory_dao.set_trust_scores(trust_scores)
            self.memory_dao.set_trust_history(trust_history)
            
            # 更新玩家数据
            player_data = self.memory_dao.get_player_data()
            if req.name not in player_data:
                player_data[req.name] = {}
            player_data[req.name]['is_sheriff'] = True
            self.memory_dao.set_player_data(player_data)
        
        if req.message:
            self.memory_dao.append_history(req.message)
    
    def _handle_hunter(self, req):
        """处理猎人/狼王技能"""
        self.memory_dao.append_history("Hunter/Wolf King is: " + req.name + ", activating skill, choosing to shoot")
    
    def _handle_hunter_result(self, req):
        """处理猎人/狼王技能结果"""
        if req.message:
            self.memory_dao.append_history("Hunter/Wolf King is: " + req.name + ", shot and took down " + req.message)
            self.memory_dao.add_dead_player(req.message)
        else:
            self.memory_dao.append_history("Hunter/Wolf King is: " + req.name + ", did not take down anyone")
    
    def _handle_sheriff_speech_order(self, req):
        """处理警长发言顺序"""
        if "Counter-clockwise" in req.message:
            self.memory_dao.append_history("Host: Sheriff speech order is lower numbers first")
        else:
            self.memory_dao.append_history("Host: Sheriff speech order is higher numbers first")
    
    def _handle_sheriff_pk(self, req):
        """处理警长PK发言"""
        self.memory_dao.append_history(f"Sheriff PK speech: {req.name}: {req.message}")
    
    def _handle_game_end(self, req):
        """处理游戏结束"""
        self.memory_dao.append_history(req.message)
        
        # 收集数据并进行增量学习
        logger.info("[GAME END] Collecting game data for ML training (Seer)")
        self.ml_data_collector.collect_game_data()
        self.ml_data_collector.save_to_file()
        self.ml_trainer.train()
        
        # 触发游戏结束处理
        from game_utils import GameEndTrigger
        GameEndTrigger.trigger_game_end(req, self.memory, "Seer")

    
    def interact(self, req=AgentReq) -> AgentResp:
        """处理交互请求（重构版 - 使用决策器）"""
        logger.info(f"seer interact: {req}")
        
        if req.status == STATUS_DISCUSS:
            return self._interact_discuss(req)
        elif req.status == STATUS_VOTE:
            return self._interact_vote(req)
        elif req.status == STATUS_SKILL:
            return self._interact_skill(req)
        elif req.status == STATUS_SHERIFF_ELECTION:
            return self._interact_sheriff_election(req)
        elif req.status == STATUS_SHERIFF_SPEECH:
            return self._interact_sheriff_speech(req)
        elif req.status == STATUS_SHERIFF_VOTE:
            return self._interact_sheriff_vote(req)
        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            return self._interact_sheriff_speech_order(req)
        elif req.status == STATUS_SHERIFF:
            return self._interact_badge_transfer(req)
        elif req.status == STATUS_SHERIFF_PK:
            return self._interact_sheriff_pk(req)
        else:
            raise NotImplementedError(f"Interact status {req.status} not implemented")

    
    def _interact_discuss(self, req) -> AgentResp:
        """处理讨论阶段的发言（使用LLM生成）"""
        if req.message:
            self.memory_dao.append_history(req.message)
        
        my_name = self.memory_dao.get_my_name()
        message = str(req.message or "")
        
        # 检查是否是遗言阶段
        if self.last_words_detector.is_last_words_phase(message):
            return self._generate_last_words()
        
        # 正常讨论阶段
        return self._generate_discussion_speech()
    
    def _generate_last_words(self) -> AgentResp:
        """生成遗言"""
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        trust_scores = self.memory_dao.get_trust_scores()
        player_data = self.memory_dao.get_player_data()
        
        # 构建摘要
        trust_summary = self.analysis_formatter.format_trust_summary(trust_scores)
        check_summary = self.analysis_formatter.format_check_results(checked_players)
        suspect_summary = self.analysis_formatter.format_suspect_analysis(
            trust_scores, player_data, checked_players, my_name
        )
        
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "name": my_name,
            "checked_players": checked_players,
            "history": "\n".join(self.memory_dao.get_history()) + trust_summary + check_summary + suspect_summary
        })
        
        result = self.llm_caller(prompt)
        result = self.speech_truncator.truncate(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"seer last words result (length: {len(result)}): {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _generate_discussion_speech(self) -> AgentResp:
        """生成讨论发言"""
        my_name = self.memory_dao.get_my_name()
        night_count = self.memory_dao.get_night_count()
        
        # 获取游戏阶段信息
        alive_players = self.player_extractor.get_alive_players(
            self.memory_dao.get_speech_history(),
            self.memory_dao.get_dead_players(),
            my_name
        )
        alive_count = len(alive_players)
        current_day = self.game_phase_analyzer.get_current_day(night_count)
        game_phase = self.game_phase_analyzer.get_phase(current_day, alive_count)
        phase_strategy = self.game_phase_analyzer.get_strategy(game_phase, alive_count)
        
        # 构建上下文
        checked_players = self.memory_dao.get_checked_players()
        
        prompt = format_prompt(DESC_PROMPT, {
            "name": my_name,
            "game_phase": game_phase.value,
            "current_day": current_day,
            "alive_count": alive_count,
            "phase_strategy": phase_strategy,
            "checked_players": checked_players,
            "history": "\n".join(self.memory_dao.get_history())
        })
        
        result = self.llm_caller(prompt)
        result = self.speech_truncator.truncate(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"seer interact result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_vote(self, req) -> AgentResp:
        """处理投票决策（使用决策器）"""
        self.memory_dao.append_history('Host: It\'s time to vote. Everyone, please point to the person you think is likely a werewolf.')
        
        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]
        
        # 构建决策上下文
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores(),
            'voting_results': self.memory_dao.get_voting_results(),
            'night_count': self.memory_dao.get_night_count()
        }
        
        # 使用决策器决定投票目标
        target, reason, vote_scores = self.vote_decision_maker.decide(choices, my_name, context)
        
        logger.info(f"[DECISION TREE VOTE] Target: {target}, Reason: {reason}")
        for player, score in sorted(vote_scores.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {player}: {score:.1f}")
        
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _interact_skill(self, req) -> AgentResp:
        """处理技能使用（检查决策）"""
        checked_players = self.memory_dao.get_checked_players()
        my_name = self.memory_dao.get_my_name()
        
        choices = [name for name in req.message.split(",")
                  if name != my_name and name not in checked_players]
        
        if not choices:
            logger.warning("No valid choices for skill, using first available")
            choices = [name for name in req.message.split(",") if name != my_name]
        
        # 构建上下文
        context = {
            'checked_players': checked_players,
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores(),
            'voting_history': self.memory_dao.get_voting_history(),
            'voting_results': self.memory_dao.get_voting_results(),
            'speech_history': self.memory_dao.get_speech_history(),
            'injection_attempts': self.memory_dao.get_injection_attempts(),
            'false_quotations': self.memory_dao.get_false_quotations(),
            'night_count': self.memory_dao.get_night_count()
        }
        
        # 计算每个候选人的检查优先级
        check_scores = {}
        for player in choices:
            score = self.check_priority_calculator.calculate(player, context)
            check_scores[player] = score
            logger.info(f"Check priority for {player}: {score:.1f}")
        
        # 选择最高优先级
        if check_scores:
            target = max(check_scores.items(), key=lambda x: x[1])[0]
        else:
            target = choices[0] if choices else "No.1"
        
        logger.info(f"seer skill result: {target}")
        return AgentResp(success=True, result=target, skillTargetPlayer=target, errMsg=None)
    
    def _interact_sheriff_election(self, req) -> AgentResp:
        """处理警长选举决策（使用决策器）"""
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores(),
            'night_count': self.memory_dao.get_night_count()
        }
        
        should_run, reason = self.sheriff_election_maker.decide(context)
        logger.info(f"[DECISION TREE SHERIFF] Should run: {should_run}, Reason: {reason}")
        
        result = "Run for Sheriff" if should_run else "Do Not Run"
        logger.info(f"seer agent sheriff election result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_speech(self, req) -> AgentResp:
        """处理警长竞选发言"""
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        
        prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
            "name": my_name,
            "checked_players": checked_players,
            "history": "\n".join(self.memory_dao.get_history())
        })
        
        result = self.llm_caller(prompt)
        result = self.speech_truncator.truncate(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"seer agent sheriff speech result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_vote(self, req) -> AgentResp:
        """处理警长投票决策（使用决策器）"""
        choices = [name for name in req.message.split(",")]
        
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores()
        }
        
        target, reason = self.sheriff_vote_maker.decide(choices, context)
        logger.info(f"[DECISION TREE SHERIFF VOTE] Target: {target}, Reason: {reason}")
        
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _interact_sheriff_speech_order(self, req) -> AgentResp:
        """处理发言顺序决策（使用决策器）"""
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores()
        }
        
        order, reason = self.speech_order_maker.decide(context)
        logger.info(f"[DECISION TREE SPEECH ORDER] Order: {order}, Reason: {reason}")
        
        return AgentResp(success=True, result=order, errMsg=None)
    
    def _interact_badge_transfer(self, req) -> AgentResp:
        """处理徽章转移决策（使用决策器）"""
        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]
        
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores()
        }
        
        target, reason = self.badge_transfer_maker.decide(choices, context)
        logger.info(f"[DECISION TREE BADGE TRANSFER] Target: {target}, Reason: {reason}")
        
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _interact_sheriff_pk(self, req) -> AgentResp:
        """处理警长PK发言"""
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        
        # 识别对手
        opponent = "Unknown"
        game_state = self.memory_dao.get_game_state()
        if game_state.get('fake_seer_name'):
            opponent = game_state['fake_seer_name']
        
        prompt = format_prompt(SHERIFF_PK_PROMPT, {
            "name": my_name,
            "opponent": opponent,
            "checked_players": checked_players,
            "history": "\n".join(self.memory_dao.get_history())
        })
        
        result = self.llm_caller(prompt)
        result = self.speech_truncator.truncate(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"seer agent sheriff pk result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
