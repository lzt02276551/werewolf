# -*- coding: utf-8 -*-
"""
平民代理人主文件（重构版）
应用面向对象设计原则，模块化架构
"""

from .prompt import (
    DESC_PROMPT,
    VOTE_PROMPT,
    GAME_RULE_PROMPT,
    SHERIFF_ELECTION_PROMPT,
    SHERIFF_SPEECH_PROMPT,
    SHERIFF_VOTE_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT,
    SHERIFF_PK_PROMPT,
    LAST_WORDS_PROMPT,
)
from agent_build_sdk.model.roles import ROLE_VILLAGER
from agent_build_sdk.model.werewolf_model import (
    AgentResp,
    AgentReq,
    STATUS_START,
    STATUS_VOTE_RESULT,
    STATUS_NIGHT_INFO,
    STATUS_DISCUSS,
    STATUS_VOTE,
    STATUS_RESULT,
    STATUS_NIGHT,
    STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF,
    STATUS_SHERIFF_VOTE,
    STATUS_SHERIFF_ELECTION,
    STATUS_SHERIFF_PK,
    STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_HUNTER,
    STATUS_HUNTER_RESULT,
)
from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.sdk.agent import format_prompt

# 导入重构后的模块
from werewolf.common.utils import DataValidator, CacheManager
from .config import VillagerConfig
from .detectors import InjectionDetector, FalseQuoteDetector, MessageParser, SpeechQualityEvaluator
from .analyzers import (
    TrustScoreManager, TrustScoreCalculator, VotingPatternAnalyzer,
    GamePhaseAnalyzer, SpeechPositionAnalyzer
)
from .decision_makers import (
    VoteDecisionMaker, SheriffElectionDecisionMaker, SheriffVoteDecisionMaker,
    BadgeTransferDecisionMaker, SpeechOrderDecisionMaker, LastWordsGenerator
)

# ML Enhancement Integration
import sys
import os
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class VillagerAgent(BasicRoleAgent):
    """平民角色代理（重构版）- 模块化架构"""

    def __init__(self, model_name):
        super().__init__(ROLE_VILLAGER, model_name=model_name)
        
        # 配置
        self.config = VillagerConfig()
        
        # 初始化内存变量
        self._init_memory_variables()
        
        # 初始化检测专用LLM客户端（在ML之前，因为ML不依赖它）
        self.detection_client = self._init_detection_client()
        
        # ML增强
        self.ml_agent = None
        self.ml_enabled = False
        self._init_ml_enhancement()
        
        # 初始化所有组件（依赖注入）
        self._init_components()
    
    def _init_memory_variables(self):
        """初始化内存变量"""
        self.memory.set_variable("player_data", {})
        self.memory.set_variable("game_state", {})
        self.memory.set_variable("seer_checks", {})
        self.memory.set_variable("voting_results", {})
        self.memory.set_variable("all_players", [])
        self.memory.set_variable("alive_players", [])
        self.memory.set_variable("dead_players", [])
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
        self.memory.set_variable("giving_last_words", False)
        self.memory.set_variable("sheriff", None)
    
    def _init_ml_enhancement(self):
        """初始化ML增强系统"""
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled - module not available")
            return
        
        try:
            model_dir = os.getenv('ML_MODEL_DIR', './ml_models')
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            
            if self.ml_enabled:
                logger.info("✓ ML enhancement enabled for Villager")
                
                # 初始化增量学习系统
                try:
                    from incremental_learning import IncrementalLearningSystem
                    from game_end_handler import set_learning_system
                    
                    retrain_interval = int(os.getenv('ML_RETRAIN_INTERVAL', '5'))
                    learning_system = IncrementalLearningSystem(self.ml_agent, retrain_interval)
                    set_learning_system(learning_system)
                    
                    logger.info(f"✓ Incremental learning enabled (retrain every {retrain_interval} games)")
                except Exception as e:
                    logger.warning(f"⚠ Incremental learning not available: {e}")
            else:
                logger.info("⚠ ML enhancement initialized but not enabled")
        except Exception as e:
            logger.error(f"✗ Failed to initialize ML enhancement: {e}")
            self.ml_agent = None
            self.ml_enabled = False
    
    def _init_detection_client(self):
        """初始化消息检测专用的LLM客户端（DeepSeek Reasoner）"""
        detection_model = os.getenv('DETECTION_MODEL_NAME')
        
        if not detection_model:
            logger.info("未配置DETECTION_MODEL_NAME，消息检测将使用主模型")
            if hasattr(self, 'client') and self.client:
                return self.client
            else:
                logger.warning("主模型客户端未初始化，检测器将使用规则模式")
                return None
        
        try:
            from openai import OpenAI
            
            # 优先使用检测专用配置，否则回退到主模型配置
            api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if not api_key:
                logger.warning("未配置DETECTION_API_KEY，消息检测将使用主模型")
                return getattr(self, 'client', None)
            
            # 创建检测专用客户端
            detection_client = OpenAI(api_key=api_key, base_url=base_url)
            
            logger.info(f"✓ 消息检测专用LLM已配置: {detection_model} (DeepSeek Reasoner)")
            logger.info(f"  - API Base: {base_url}")
            logger.info(f"  - 用途: 消息注入检测、虚假引用检测、消息解析、发言质量评估")
            
            return detection_client
            
        except Exception as e:
            logger.error(f"初始化检测专用LLM失败: {e}，将使用主模型")
            return getattr(self, 'client', None)
    
    def _init_components(self):
        """初始化所有组件（依赖注入模式）"""
        # 缓存管理器
        self.cache_manager = CacheManager()
        
        # 检测器
        self.injection_detector = InjectionDetector(self.config, self.detection_client)
        self.false_quote_detector = FalseQuoteDetector(self.config, self.detection_client)
        self.message_parser = MessageParser(self.config, self.detection_client)
        self.speech_quality_evaluator = SpeechQualityEvaluator(self.config, self.detection_client)
        
        # 分析器
        self.trust_score_manager = TrustScoreManager(self.config)
        self.trust_score_calculator = TrustScoreCalculator(self.config)
        self.voting_pattern_analyzer = VotingPatternAnalyzer(self.config)
        self.game_phase_analyzer = GamePhaseAnalyzer(self.config)
        self.speech_position_analyzer = SpeechPositionAnalyzer(self.config)
        
        # 决策器
        self.vote_decision_maker = VoteDecisionMaker(
            self.config, self.trust_score_calculator, self.voting_pattern_analyzer
        )
        self.sheriff_election_decision_maker = SheriffElectionDecisionMaker(self.config)
        self.sheriff_vote_decision_maker = SheriffVoteDecisionMaker(
            self.config, self.trust_score_calculator
        )
        self.badge_transfer_decision_maker = BadgeTransferDecisionMaker(
            self.config, self.trust_score_calculator
        )
        self.speech_order_decision_maker = SpeechOrderDecisionMaker(
            self.config, self.trust_score_calculator
        )
        self.last_words_generator = LastWordsGenerator(
            self.config, self.trust_score_calculator, self.voting_pattern_analyzer
        )

    # ==================== 辅助方法 ====================
    
    def _collect_game_data(self, result_message: str):
        """收集游戏数据用于增量学习"""
        try:
            from game_end_handler import get_game_end_handler
            handler = get_game_end_handler()
            
            if not handler:
                return
            
            # 收集所有玩家的数据
            player_data_dict = self.memory.load_variable("player_data")
            context = self._build_context()
            
            for player_name, data in player_data_dict.items():
                if not isinstance(data, dict):
                    continue
                
                # 构建ML特征数据
                from game_utils import MLDataBuilder
                ml_features = MLDataBuilder.build_player_data_for_ml(player_name, context)
                
                # 判断角色（从预言家验证或游戏结果推断）
                role = self._infer_player_role(player_name, result_message, context)
                
                # 更新handler的玩家统计
                handler.update_player_stats(player_name, {
                    'role': role,
                    **ml_features
                })
            
            logger.info(f"✓ Collected data for {len(player_data_dict)} players")
            
        except Exception as e:
            logger.error(f"Failed to collect game data: {e}")
    
    def _infer_player_role(self, player_name: str, result_message: str, context: Dict) -> str:
        """推断玩家角色"""
        # 1. 从预言家验证中获取
        seer_checks = context.get("seer_checks", {})
        if player_name in seer_checks:
            result = seer_checks[player_name]
            if isinstance(result, str):
                if "wolf" in result.lower():
                    return "wolf"
                else:
                    return "good"
        
        # 2. 从游戏结果推断（如果有明确信息）
        # 这里可以根据result_message进一步推断
        # 暂时返回unknown，让GameEndHandler处理
        
        return "unknown"
    
    def _build_context(self) -> dict:
        """构建决策上下文"""
        return {
            "player_data": self.memory.load_variable("player_data"),
            "game_state": self.memory.load_variable("game_state"),
            "seer_checks": self.memory.load_variable("seer_checks"),
            "voting_results": self.memory.load_variable("voting_results"),
            "trust_scores": self.memory.load_variable("trust_scores") if hasattr(self.memory, "trust_scores") else {},
            "voting_history": self.memory.load_variable("voting_history") if hasattr(self.memory, "voting_history") else {},
            "speech_history": self.memory.load_variable("speech_history") if hasattr(self.memory, "speech_history") else {},
            "my_name": self.memory.load_variable("name"),
        }
    
    def _get_alive_players_from_system(self):
        """从系统信息中获取存活玩家列表"""
        history = self.memory.load_history()
        if not isinstance(history, list):
            return set()
        
        all_players = set()
        dead_players = set()
        
        import re
        for line in history:
            if not isinstance(line, str):
                continue
            
            # 提取所有玩家编号
            players = re.findall(r"No\.\d+", line)
            for player in players:
                all_players.add(player)
            
            # 只从Host公告中提取死亡信息
            if line.startswith("Host:"):
                death_keywords = [
                    "eliminated", "voted out", "died", "killed", "was eliminated",
                    "出局", "死亡", "被淘汰",
                ]
                
                if any(keyword in line.lower() for keyword in death_keywords):
                    dead_match = re.search(r"(No\.\d+)", line)
                    if dead_match:
                        dead_players.add(dead_match.group(1))
        
        alive_players = all_players - dead_players
        logger.info(f"[SYSTEM INFO] All: {len(all_players)}, Dead: {len(dead_players)}, Alive: {len(alive_players)}")
        
        return alive_players
    
    def _get_current_day(self):
        """从系统信息中获取当前天数"""
        history = self.memory.load_history()
        if not isinstance(history, list):
            return 1
        
        current_day = 0
        
        import re
        for line in history:
            if not isinstance(line, str):
                continue
            match = re.search(r"day\s+(\d+)", line.lower())
            if match:
                try:
                    day = int(match.group(1))
                    if day > current_day:
                        current_day = day
                except (ValueError, TypeError):
                    continue
        
        if current_day == 0:
            game_state = self.memory.load_variable("game_state")
            if isinstance(game_state, dict):
                current_day = DataValidator.safe_get_int(game_state.get("current_day", 1), 1)
            else:
                current_day = 1
        
        return current_day

    # ==================== 感知方法 ====================
    
    def perceive(self, req=AgentReq):
        """处理游戏事件，更新内部状态"""
        if req.status == STATUS_START:
            self.memory.clear()
            self.memory.set_variable("name", req.name)
            
            # 处理游戏开始
            from game_utils import GameStartHandler
            GameStartHandler.handle_game_start(req, self.memory, "Villager")
            
            self._init_memory_variables()
            
            # 初始化游戏状态
            self.memory.set_variable("game_state", {
                "current_day": 0,
                "current_round": 0,
                "wolves_dead": 0,
                "goods_dead": 0,
                "total_players": 12,
                "alive_count": 12,
                "sheriff": None,
                "sheriff_election": False,
                "sheriff_candidates": [],
            })
            
            alive_players = [req.name]
            self.memory.set_variable("alive_players", alive_players)
            
            self.memory.append_history(GAME_RULE_PROMPT)
            self.memory.append_history(
                "Host: Hello, your assigned role is [Villager], you are " + req.name
            )
        
        elif req.status == STATUS_NIGHT:
            self.memory.append_history(
                "Host: Now entering night phase, close your eyes when it's dark"
            )
            game_state = self.memory.load_variable("game_state")
            game_state["current_round"] = game_state.get("current_round", 0) + 1
            self.memory.set_variable("game_state", game_state)
        
        elif req.status == STATUS_NIGHT_INFO:
            self.memory.append_history(
                f"Host: It's dawn! Last night's information is: {req.message}"
            )
            
            # 更新游戏状态
            game_state = self.memory.load_variable("game_state")
            game_state["current_day"] = game_state.get("current_day", 0) + 1
            
            # 解析夜晚死亡信息
            import re
            dead_match = re.search(r"(No\.\d+)", req.message)
            if dead_match and ("died" in req.message.lower() or "killed" in req.message.lower()):
                dead_player = dead_match.group(1)
                game_state["goods_dead"] = game_state.get("goods_dead", 0) + 1
                game_state["alive_count"] = game_state.get("alive_count", 12) - 1
                
                # 标记玩家被夜晚杀死
                player_data = self.memory.load_variable("player_data")
                if dead_player not in player_data:
                    player_data[dead_player] = {}
                player_data[dead_player]["killed_at_night"] = True
                player_data[dead_player]["alive"] = False
                self.memory.set_variable("player_data", player_data)
                
                # 更新存活/死亡玩家列表
                alive_players = self.memory.load_variable("alive_players")
                dead_players = self.memory.load_variable("dead_players")
                if dead_player in alive_players:
                    alive_players.remove(dead_player)
                if dead_player not in dead_players:
                    dead_players.append(dead_player)
                self.memory.set_variable("alive_players", alive_players)
                self.memory.set_variable("dead_players", dead_players)
                
            self.memory.set_variable("game_state", game_state)
        
        elif req.status == STATUS_DISCUSS:
            if req.name:
                # 检查是否是遗言阶段
                my_name = self.memory.load_variable("name")
                is_last_words = (
                    ("final" in req.message.lower() or "last words" in req.message.lower() or "遗言" in req.message) or
                    (req.name == my_name and any(keyword in req.message.lower() for keyword in ["eliminated", "voted out", "speak", "words", "final"]))
                )
                
                if is_last_words and req.name == my_name:
                    self.memory.set_variable("giving_last_words", True)
                    logger.info("[LAST WORDS] Villager is being eliminated, preparing final words")
                
                # 注入攻击检测
                injection_type, subtype, confidence, penalty = self.injection_detector.detect(req.message, req.name)
                
                # 检查是否是他人的遗言阶段
                is_others_last_words = False
                if injection_type not in ["MALICIOUS", "POTENTIAL_FALSE_QUOTE"]:
                    is_others_last_words = (
                        "leaves their last words" in req.message.lower() or
                        "last words:" in req.message.lower() or
                        "'s last words" in req.message.lower() or
                        "遗言：" in req.message or
                        "的遗言" in req.message
                    )
                    
                    if is_others_last_words:
                        logger.info(f"[LAST WORDS PHASE] {req.name} is giving their last words (legitimate game phase)")
                        injection_type, subtype, confidence, penalty = ("CLEAN", "LAST_WORDS", 1.0, 0)

                player_data = self.memory.load_variable("player_data")
                if req.name not in player_data:
                    player_data[req.name] = {}

                if injection_type == "MALICIOUS":
                    player_data[req.name]["malicious_injection"] = True
                    player_data[req.name]["injection_subtype"] = subtype
                    player_data[req.name]["injection_confidence"] = confidence
                    player_data[req.name]["trust_penalty"] = penalty
                    logger.info(f"[INJECTION DETECTED] {req.name}: {subtype} (confidence: {confidence:.2f}, penalty: {penalty})")
                    
                elif injection_type == "BENIGN":
                    player_data[req.name]["benign_injection"] = True
                    player_data[req.name]["analytical_behavior"] = True
                    logger.info(f"[BENIGN BEHAVIOR] {req.name}: {subtype} (confidence: {confidence:.2f}, bonus: {penalty})")
                
                elif injection_type == "POTENTIAL_FALSE_QUOTE":
                    # 验证虚假引用
                    history = self.memory.load_history()
                    is_false, false_confidence, details = self.false_quote_detector.detect(
                        req.name, req.message, history
                    )
                    if is_false and false_confidence > 0.6:
                        player_data[req.name]["false_quotes"] = True
                        player_data[req.name]["false_quote_details"] = details
                        player_data[req.name]["trust_penalty"] = player_data[req.name].get("trust_penalty", 0) - 20
                        logger.info(f"[FALSE QUOTE DETECTED] {req.name}: {details}")

                # 解析消息
                parsed_info = self.message_parser.detect(req.message, req.name)
                
                # 处理角色声称
                if parsed_info.get("claimed_role"):
                    player_data[req.name]["claimed_role"] = parsed_info["claimed_role"]
                    logger.info(f"{req.name} claimed role: {parsed_info['claimed_role']}")
                
                # 处理预言家验证信息
                if parsed_info.get("seer_check"):
                    seer_check = parsed_info["seer_check"]
                    checked_player = seer_check.get("player")
                    result = seer_check.get("result")
                    if checked_player and result:
                        seer_checks = self.memory.load_variable("seer_checks")
                        seer_checks[checked_player] = result
                        self.memory.set_variable("seer_checks", seer_checks)
                        logger.info(f"Seer check recorded: {checked_player} = {result}")
                
                # 处理支持/怀疑关系
                for supported_player in parsed_info.get("support_players", []):
                    if supported_player not in player_data:
                        player_data[supported_player] = {}
                    if "supported_by" not in player_data[supported_player]:
                        player_data[supported_player]["supported_by"] = []
                    if req.name not in player_data[supported_player]["supported_by"]:
                        player_data[supported_player]["supported_by"].append(req.name)
                
                for suspected_player in parsed_info.get("suspect_players", []):
                    if suspected_player not in player_data:
                        player_data[suspected_player] = {}
                    if "suspected_by" not in player_data[suspected_player]:
                        player_data[suspected_player]["suspected_by"] = []
                    if req.name not in player_data[suspected_player]["suspected_by"]:
                        player_data[suspected_player]["suspected_by"].append(req.name)
                
                # 处理投票意向
                if parsed_info.get("vote_intention"):
                    player_data[req.name]["vote_intention"] = parsed_info["vote_intention"]
                    logger.info(f"{req.name} vote intention: {parsed_info['vote_intention']}")
                
                # 评估发言质量
                quality = self.speech_quality_evaluator.detect(req.message, {})
                player_data[req.name]["speech_quality"] = quality
                if quality >= 60:
                    player_data[req.name]["logical_speech"] = True
                elif quality < 30:
                    player_data[req.name]["short_speech"] = True

                self.memory.set_variable("player_data", player_data)
                self.memory.append_history(req.name + ": " + req.message)
            else:
                self.memory.append_history(
                    "Host: Now entering day {}.".format(str(req.round))
                )
                self.memory.append_history(
                    "Host: Each player describes their information."
                )
            self.memory.append_history("---------------------------------------------")
        
        elif req.status == STATUS_VOTE:
            # 跟踪投票历史
            voter = req.name
            target = req.message
            
            if voter and target:
                player_data = self.memory.load_variable("player_data")
                if voter not in player_data:
                    player_data[voter] = {}
                if "vote_history" not in player_data[voter]:
                    player_data[voter]["vote_history"] = []
                
                game_state = self.memory.load_variable("game_state")
                current_day = game_state.get("current_day", 0)
                
                player_data[voter]["vote_history"].append({
                    "round": current_day,
                    "target": target,
                    "target_was_good": None,
                    "target_was_wolf": None,
                    "is_abstain": False,
                    "is_first": len(player_data[voter]["vote_history"]) == 0,
                })
                self.memory.set_variable("player_data", player_data)
            
            self.memory.append_history(
                f"Day {req.round} voting phase, {req.name} voted for {req.message}"
            )

        elif req.status == STATUS_VOTE_RESULT:
            out_player = req.name if req.name else req.message
            if out_player:
                self.memory.append_history(
                    "Host: The voting result is: {}.".format(out_player)
                )
                
                # 更新游戏状态
                game_state = self.memory.load_variable("game_state")
                game_state["alive_count"] = game_state.get("alive_count", 12) - 1
                seer_checks = self.memory.load_variable("seer_checks")
                voting_results = self.memory.load_variable("voting_results")
                
                player_data = self.memory.load_variable("player_data")
                
                # 判断被投出的玩家是狼人还是好人
                was_wolf = False
                if out_player in seer_checks:
                    result = seer_checks[out_player]
                    if "wolf" in result.lower():
                        was_wolf = True
                        game_state["wolves_dead"] = game_state.get("wolves_dead", 0) + 1
                    else:
                        game_state["goods_dead"] = game_state.get("goods_dead", 0) + 1
                else:
                    game_state["goods_dead"] = game_state.get("goods_dead", 0) + 1
                
                # 记录投票结果
                current_day = game_state.get("current_day", 0)
                if current_day not in voting_results:
                    voting_results[current_day] = {}
                voting_results[current_day]["voted_out"] = out_player
                voting_results[current_day]["was_wolf"] = was_wolf
                voting_results[current_day]["was_good"] = not was_wolf
                self.memory.set_variable("voting_results", voting_results)
                
                # 更新投票历史结果
                for player, data in player_data.items():
                    if not isinstance(data, dict):
                        continue
                    
                    if "vote_history" in data and isinstance(data["vote_history"], list):
                        vote_updated = False
                        for vote in data["vote_history"]:
                            if not isinstance(vote, dict):
                                continue
                            
                            if vote.get("round") == current_day and vote.get("target") == out_player:
                                vote["target_was_wolf"] = was_wolf
                                vote["target_was_good"] = not was_wolf
                                
                                if not vote_updated:
                                    if was_wolf:
                                        data["accurate_votes"] = data.get("accurate_votes", 0) + 1
                                    else:
                                        data["wolf_protecting_votes"] = data.get("wolf_protecting_votes", 0) + 1
                                    vote_updated = True
                
                # 标记玩家被投出
                if out_player not in player_data:
                    player_data[out_player] = {}
                player_data[out_player]["voted_out"] = True
                player_data[out_player]["alive"] = False
                
                # 更新存活/死亡玩家列表
                alive_players = self.memory.load_variable("alive_players")
                dead_players = self.memory.load_variable("dead_players")
                if out_player in alive_players:
                    alive_players.remove(out_player)
                if out_player not in dead_players:
                    dead_players.append(out_player)
                self.memory.set_variable("alive_players", alive_players)
                self.memory.set_variable("dead_players", dead_players)
                
                self.memory.set_variable("player_data", player_data)
                self.memory.set_variable("game_state", game_state)
            else:
                self.memory.append_history("Host: No one is eliminated.")
        
        elif req.status == STATUS_SHERIFF_ELECTION:
            self.memory.append_history(
                "Host: Players running for sheriff: " + req.message
            )
            game_state = self.memory.load_variable("game_state")
            game_state["sheriff_election"] = True
            game_state["sheriff_candidates"] = req.message.split(",")
            self.memory.set_variable("game_state", game_state)
        
        elif req.status == STATUS_SHERIFF_SPEECH:
            self.memory.append_history(
                req.name + " (sheriff campaign speech): " + req.message
            )
            
            player_data = self.memory.load_variable("player_data")
            if req.name not in player_data:
                player_data[req.name] = {}
            
            parsed_info = self.message_parser.detect(req.message, req.name)
            
            if parsed_info.get("claimed_role"):
                claimed_role = parsed_info["claimed_role"]
                player_data[req.name][f"claimed_{claimed_role}"] = True
                logger.info(f"{req.name} claimed {claimed_role} in sheriff speech")
            
            player_data[req.name]["sheriff_candidate"] = True
            self.memory.set_variable("player_data", player_data)
        
        elif req.status == STATUS_SHERIFF_VOTE:
            self.memory.append_history(
                "Sheriff voting: " + req.name + " voted for " + req.message
            )
        
        elif req.status == STATUS_SHERIFF:
            if req.name:
                self.memory.append_history("Host: Sheriff badge goes to: " + req.name)
                self.memory.set_variable("sheriff", req.name)
                game_state = self.memory.load_variable("game_state")
                game_state["sheriff"] = req.name
                self.memory.set_variable("game_state", game_state)

                player_data = self.memory.load_variable("player_data")
                if req.name not in player_data:
                    player_data[req.name] = {}
                player_data[req.name]["sheriff_elected"] = True
                self.memory.set_variable("player_data", player_data)
            if req.message:
                self.memory.append_history(req.message)
        
        elif req.status == STATUS_RESULT:
            self.memory.append_history(req.message)
            
            # 游戏结束，收集数据并触发增量学习
            logger.info("[GAME END] Collecting game data and triggering incremental learning")
            self._collect_game_data(req.message)
            
            from game_utils import GameEndTrigger
            GameEndTrigger.trigger_game_end(req, self.memory, "Villager")
        
        elif req.status == STATUS_HUNTER:
            self.memory.append_history(
                "Hunter/Wolf King is: "
                + req.name
                + ", they are activating their skill, choosing to shoot"
            )
        
        elif req.status == STATUS_HUNTER_RESULT:
            if req.message:
                self.memory.append_history(
                    "Hunter/Wolf King is: "
                    + req.name
                    + ", they shot and took "
                    + req.message
                )
                game_state = self.memory.load_variable("game_state")
                game_state["alive_count"] = game_state.get("alive_count", 12) - 1
                self.memory.set_variable("game_state", game_state)
            else:
                self.memory.append_history(
                    "Hunter/Wolf King is: " + req.name + ", they didn't take anyone"
                )
        
        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            if "Counter-clockwise" in req.message or "小号" in req.message:
                self.memory.append_history(
                    "Host: Sheriff speech order is smaller numbers first"
                )
            else:
                self.memory.append_history(
                    "Host: Sheriff speech order is larger numbers first"
                )
        
        elif req.status == STATUS_SHERIFF_PK:
            self.memory.append_history(f"Sheriff PK speech: {req.name}: {req.message}")
        
        else:
            raise NotImplementedError

    # ==================== 交互方法 ====================
    
    def interact(self, req=AgentReq) -> AgentResp:
        """处理游戏交互，做出决策"""
        logger.info("VillagerAgent interact: {}".format(req))

        # 构建决策上下文
        context = self._build_context()

        if req.status == STATUS_DISCUSS:
            if req.message:
                self.memory.append_history(req.message)

            # 检查是否是遗言阶段
            giving_last_words = self.memory.load_variable("giving_last_words")
            
            if giving_last_words:
                # 遗言阶段：生成最后的发言
                logger.info("[LAST WORDS] Generating villager's final words")
                
                # 生成遗言提示
                hints = self.last_words_generator.decide(context)
                
                # 检查是否是警长
                game_state = context.get("game_state", {})
                is_sheriff = game_state.get("sheriff") == context.get("my_name")
                
                if is_sheriff:
                    hints += "\n[YOU ARE SHERIFF: Include badge transfer recommendation in last words]"
                
                prompt = format_prompt(
                    LAST_WORDS_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "history": "\n".join(self.memory.load_history()) + hints,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                # 清除标志
                self.memory.set_variable("giving_last_words", False)
                
                logger.info("VillagerAgent last words result: {}".format(result))
                return AgentResp(success=True, result=result, errMsg=None)

            # 确定发言位置
            speech_position = self.speech_position_analyzer.analyze(
                self.memory.load_variable("name")
            )
            
            # 评估游戏阶段
            game_phase = self.game_phase_analyzer.analyze(context)
            
            # 检查是否残局
            is_endgame = self.game_phase_analyzer.is_endgame(context)
            
            # 更新游戏状态
            game_state = self.memory.load_variable("game_state")
            game_state["game_phase"] = game_phase
            game_state["is_endgame"] = is_endgame
            game_state["current_day"] = self._get_current_day()
            self.memory.set_variable("game_state", game_state)
            
            # 添加位置、阶段和残局上下文到提示
            position_hint = ""
            if speech_position == "early":
                position_hint = "\n[POSITION: Early speaker (1-4). Use observational speech strategy.]"
            elif speech_position == "middle":
                position_hint = "\n[POSITION: Middle speaker (5-8). Use analytical speech strategy.]"
            else:
                position_hint = "\n[POSITION: Late speaker (9-12). Use summary speech strategy.]"
            
            # 添加游戏阶段指导
            if game_phase == "early":
                position_hint += "\n[GAME PHASE: Early (Day 1-2). Focus on speech logic, avoid hasty conclusions.]"
            elif game_phase == "mid":
                position_hint += "\n[GAME PHASE: Mid (Day 3-5). Weight voting patterns, verify神职 claims.]"
            else:
                position_hint += "\n[GAME PHASE: Late (Day 6+). Complete behavior chain analysis.]"
            
            if is_endgame:
                position_hint += "\n[ENDGAME: ≤6 players alive. Every vote is critical.]"
            
            # 添加注入检测警告
            injection_warnings = ""
            player_data = self.memory.load_variable("player_data")
            for player, data in player_data.items():
                if data.get("malicious_injection"):
                    subtype = data.get("injection_subtype", "UNKNOWN")
                    injection_warnings += f"\n[INJECTION WARNING] {player}: {subtype} detected - strong wolf signal"
                if data.get("false_quotes"):
                    injection_warnings += f"\n[FALSE QUOTE WARNING] {player}: False quotation detected - wolf signal"
            
            if injection_warnings:
                position_hint += injection_warnings

            prompt = format_prompt(
                DESC_PROMPT,
                {
                    "name": self.memory.load_variable("name"),
                    "history": "\n".join(self.memory.load_history()) + position_hint,
                },
            )
            logger.info("prompt:" + prompt)
            result = self.llm_caller(prompt)
            
            # 长度控制
            original_length = len(result)
            if original_length > self.config.MAX_SPEECH_LENGTH:
                truncated = result[:self.config.MAX_SPEECH_LENGTH]
                last_period = max(truncated.rfind('。'), truncated.rfind('.'), truncated.rfind('！'), truncated.rfind('!'))
                if last_period > self.config.MIN_SPEECH_LENGTH:
                    result = truncated[:last_period + 1]
                else:
                    result = truncated
                logger.info(f"Speech truncated from {original_length} to {len(result)} chars")
            elif original_length < self.config.MIN_SPEECH_LENGTH:
                logger.warning(f"Speech too short: {original_length} chars")
            
            logger.info("VillagerAgent interact result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_VOTE:
            self.memory.append_history(
                "Host: It's time to vote. Everyone, please point to the person you think might be a werewolf."
            )
            choices = [
                name
                for name in req.message.split(",")
                if name != self.memory.load_variable("name")
            ]
            self.memory.set_variable("choices", choices)

            # 使用决策树决定投票目标
            my_name = self.memory.load_variable("name")
            target, reason, vote_scores = self.vote_decision_maker.decide(choices, my_name, context)
            
            # 记录决策树结果
            logger.info(f"[DECISION TREE VOTE] Target: {target}, Reason: {reason}")
            for player, score in sorted(vote_scores.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {player}: {score:.1f}")
            
            # ML增强：融合ML预测
            if self.ml_enabled and self.ml_agent:
                ml_scores = {}
                for candidate in choices:
                    from game_utils import MLDataBuilder
                    player_ml_data = MLDataBuilder.build_player_data_for_ml(candidate, context)
                    wolf_prob = self.ml_agent.predict_wolf_probability(player_ml_data)
                    ml_scores[candidate] = wolf_prob * 100  # 转换为0-100分数
                
                # 融合决策树和ML分数
                fusion_ratio = float(os.getenv('ML_FUSION_RATIO', '0.4'))  # ML权重40%
                final_scores = {}
                for candidate in choices:
                    dt_score = vote_scores.get(candidate, 0)
                    ml_score = ml_scores.get(candidate, 50)
                    final_scores[candidate] = dt_score * (1 - fusion_ratio) + ml_score * fusion_ratio
                
                # 选择最高分
                if final_scores:
                    ml_target = max(final_scores.items(), key=lambda x: x[1])[0]
                    logger.info(f"[ML FUSION] ML target: {ml_target}, Fusion scores: {final_scores}")
                    
                    # 如果ML和决策树差异较大，记录警告
                    if ml_target != target:
                        logger.info(f"[ML FUSION] ML suggests {ml_target} (prob={ml_scores[ml_target]:.2f}), "
                                  f"DT suggests {target} (score={vote_scores[target]:.1f})")
                    
                    # 使用融合后的目标
                    target = ml_target
            
            # 混合模式：使用LLM验证或调整
            if self.config.DECISION_MODE == "hybrid":
                # 添加决策树推荐
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: Vote {target} - {reason}]"
                dt_hint += f"\n[Vote Scores: {', '.join([f'{p}:{s:.0f}' for p, s in sorted(vote_scores.items(), key=lambda x: x[1], reverse=True)[:3]])}]"

                prompt = format_prompt(
                    VOTE_PROMPT,
                    {
                        "name": my_name,
                        "choices": choices,
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                # 验证LLM输出
                if result not in choices:
                    logger.warning(f"LLM output '{result}' not in choices, using decision tree result: {target}")
                    result = target
            else:
                # 纯代码模式
                result = target
            
            logger.info("interact result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF_ELECTION:
            # 使用决策树决定是否竞选
            should_run, dt_reason = self.sheriff_election_decision_maker.decide(context)
            logger.info(f"[DECISION TREE SHERIFF] Should run: {should_run}, Reason: {dt_reason}")

            # 混合模式
            if self.config.DECISION_MODE == "hybrid":
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: {'Run for Sheriff' if should_run else 'Do Not Run'} - {dt_reason}]"
                
                prompt = format_prompt(
                    SHERIFF_ELECTION_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
            else:
                result = "Run for Sheriff" if should_run else "Do Not Run"
            
            logger.info("VillagerAgent sheriff election result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF_SPEECH:
            prompt = format_prompt(
                SHERIFF_SPEECH_PROMPT,
                {
                    "name": self.memory.load_variable("name"),
                    "history": "\n".join(self.memory.load_history()),
                },
            )
            logger.info("prompt:" + prompt)
            result = self.llm_caller(prompt)
            if len(result) > self.config.MAX_SPEECH_LENGTH:
                result = result[:self.config.MAX_SPEECH_LENGTH]
            logger.info("VillagerAgent sheriff speech result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF_PK:
            prompt = format_prompt(
                SHERIFF_PK_PROMPT,
                {
                    "name": self.memory.load_variable("name"),
                    "history": "\n".join(self.memory.load_history()),
                },
            )
            logger.info("prompt:" + prompt)
            result = self.llm_caller(prompt)
            if len(result) > self.config.MAX_SPEECH_LENGTH:
                result = result[:self.config.MAX_SPEECH_LENGTH]
            logger.info("VillagerAgent sheriff pk result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF_VOTE:
            choices = [name for name in req.message.split(",")]
            
            # 使用决策树决定警长投票
            target, dt_reason = self.sheriff_vote_decision_maker.decide(choices, context)
            logger.info(f"[DECISION TREE SHERIFF VOTE] Target: {target}, Reason: {dt_reason}")

            # 混合模式
            if self.config.DECISION_MODE == "hybrid":
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: Vote {target} - {dt_reason}]"
                
                prompt = format_prompt(
                    SHERIFF_VOTE_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "choices": choices,
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                if result not in choices:
                    logger.warning(f"LLM output '{result}' not in choices, using decision tree result: {target}")
                    result = target
            else:
                result = target
            
            logger.info("VillagerAgent sheriff vote result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            # 使用决策树决定发言顺序
            order, dt_reason = self.speech_order_decision_maker.decide(context)
            logger.info(f"[DECISION TREE SPEECH ORDER] Order: {order}, Reason: {dt_reason}")
            
            # 混合模式
            if self.config.DECISION_MODE == "hybrid":
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: {order} - {dt_reason}]"
                
                prompt = format_prompt(
                    SHERIFF_SPEECH_ORDER_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                if "clockwise" not in result.lower() and "counter" not in result.lower():
                    logger.warning(f"LLM output '{result}' not valid, using decision tree result: {order}")
                    result = order
            else:
                result = order
            
            logger.info("VillagerAgent sheriff speech order result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)

        elif req.status == STATUS_SHERIFF:
            # 警徽转移
            choices = [
                name
                for name in req.message.split(",")
                if name != self.memory.load_variable("name")
            ]
            
            # 使用决策树决定警徽转移
            target, dt_reason = self.badge_transfer_decision_maker.decide(choices, context)
            logger.info(f"[DECISION TREE BADGE TRANSFER] Target: {target}, Reason: {dt_reason}")

            # 混合模式
            if self.config.DECISION_MODE == "hybrid":
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: Transfer to {target} - {dt_reason}]"
                
                prompt = format_prompt(
                    SHERIFF_TRANSFER_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "choices": choices,
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                if result not in choices and result != "Destroy Badge":
                    logger.warning(f"LLM output '{result}' not valid, using decision tree result: {target}")
                    result = target
            else:
                result = target
            
            logger.info("VillagerAgent sheriff transfer result: {}".format(result))
            return AgentResp(success=True, result=result, errMsg=None)
        
        else:
            raise NotImplementedError
