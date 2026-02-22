# -*- coding: utf-8 -*-
"""
守卫代理人（重构版 - 继承BaseGoodAgent）

继承BaseGoodAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统
- ML增强
- 信任分析
- 投票决策

守卫特有功能：
- 守护技能
- 守护目标选择
- 守护历史管理
"""

from agent_build_sdk.model.roles import ROLE_GUARD
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_SKILL, STATUS_DISCUSS, STATUS_VOTE
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_good_agent import BaseGoodAgent
from werewolf.guard.prompt import (
    DESC_PROMPT, 
    LAST_WORDS_PROMPT,
    VOTE_PROMPT,
    SKILL_PROMPT,
    SHERIFF_ELECTION_PROMPT,
    SHERIFF_SPEECH_PROMPT,
    SHERIFF_VOTE_PROMPT,
    SHERIFF_PK_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT
)
from werewolf.guard.decision_makers import GuardDecisionMaker
from typing import List, Optional, Dict, Any

# 导入守卫特有模块
from werewolf.guard.config import GuardConfig


class GuardAgent(BaseGoodAgent):
    """
    守卫代理人（重构版 - 继承BaseGoodAgent）
    
    继承BaseGoodAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统
    - ML增强
    - 信任分析
    - 投票决策
    
    守卫特有功能：
    - 守护技能
    - 守护目标选择
    - 守护历史管理
    """

    def __init__(self, model_name: str = None):
        """
        初始化守卫代理
        
        Args:
            model_name: LLM模型名称（可选）
                       如果不提供，将从环境变量 MODEL_NAME 读取
                       如果环境变量也没有，默认使用 "deepseek-chat"
        """
        # 如果没有提供model_name，从环境变量读取
        if model_name is None:
            import os
            model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
            logger.info(f"Using model from environment: {model_name}")
        
        # 先设置守卫配置（在调用父类初始化之前）
        # 这样父类初始化时就能使用GuardConfig
        self.config = GuardConfig()
        
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_GUARD, model_name=model_name)
        
        logger.info("✓ GuardAgent initialized with BaseGoodAgent")
    
    def _init_memory_variables(self):
        """
        初始化守卫特有的内存变量
        
        继承父类的内存变量，并添加守卫特有的：
        - 守护历史
        - 守护策略
        - 角色估计器状态
        - 守护统计（新增）
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加守卫特有变量
        # 守护历史
        self.memory.set_variable("guarded_players", [])
        self.memory.set_variable("last_guarded", "")  # 兼容模板：初始化为空字符串
        self.memory.set_variable("guard_history", {})
        
        # 游戏进度
        self.memory.set_variable("current_night", 0)
        self.memory.set_variable("day_count", 0)  # 添加day_count初始化
        
        # 守护策略
        role_specific = getattr(self.config, 'role_specific', {})
        self.memory.set_variable("first_night_strategy", 
                                role_specific.get('first_night_strategy', 'empty_guard'))
        self.memory.set_variable("protect_same_twice", 
                                role_specific.get('protect_same_twice', False))
        
        # 角色估计器状态（初始化为空列表，避免KeyError）
        self.memory.set_variable("confirmed_seers", [])
        self.memory.set_variable("likely_seers", [])
        
        # 信任历史（避免KeyError）- 直接设置，不检查
        self.memory.set_variable("trust_history", {})
        
        # 守护统计（新增 - 用于ML训练和遗言生成）
        self.memory.set_variable("guard_stats", {})
        
        logger.info("✓ Guard-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化守卫特有组件
        
        守卫特有组件：
        - GuardDecisionMaker: 守护决策器
        - RoleEstimator: 角色估计器（带memory持久化）
        - WolfKillPredictor: 狼人击杀预测器
        - GuardPriorityCalculator: 守卫优先级计算器
        - TrustManager: 信任分数管理器（守卫特有实现）
        
        所有组件必须成功初始化，否则抛出异常
        """
        try:
            from .analyzers import RoleEstimator, WolfKillPredictor, GuardPriorityCalculator
            from .trust_manager import TrustScoreManager
            
            # 确保memory已经初始化了必要的变量
            if "trust_scores" not in self.memory.memories:
                self.memory.set_variable("trust_scores", {})
            if "trust_history" not in self.memory.memories:
                self.memory.set_variable("trust_history", {})
            
            # 初始化守卫特有的信任管理器（覆盖父类的）
            self.trust_manager = TrustScoreManager(self.memory)
            logger.info("✓ Guard-specific trust manager initialized")
            
            # 初始化决策器
            self.guard_decision_maker = GuardDecisionMaker(self.config)
            
            # 初始化分析器（RoleEstimator需要memory支持持久化）
            self.role_estimator = RoleEstimator(self.config, memory=self.memory)
            self.wolf_kill_predictor = WolfKillPredictor(self.config)
            self.guard_priority_calculator = GuardPriorityCalculator(self.config)
            
            # 设置依赖（必须成功）
            if not self.trust_manager:
                raise RuntimeError("Trust manager initialization failed - required for guard functionality")
            
            self.guard_decision_maker.set_dependencies(self.memory, self.trust_manager)
            self.guard_decision_maker.set_analyzers(
                self.role_estimator,
                self.wolf_kill_predictor,
                self.guard_priority_calculator
            )
            logger.info("✓ Guard decision maker with analyzers initialized")
            
            logger.info("✓ Guard-specific components initialized")
            
        except ImportError as e:
            logger.error(f"✗ Failed to import guard-specific components: {e}")
            raise RuntimeError(f"Guard component import failed: {e}") from e
        except Exception as e:
            logger.error(f"✗ Failed to initialize guard-specific components: {e}")
            raise RuntimeError(f"Guard component initialization failed: {e}") from e
    
    # ==================== 守卫特有方法 ====================
    
    def perceive(self, req: AgentReq):
        """
        处理游戏事件（完全兼容平民模板 + 守卫特有处理）
        
        实现与平民模板相同的perceive逻辑，确保100%兼容游戏交互引擎
        
        Args:
            req: 游戏事件请求
        """
        from agent_build_sdk.model.werewolf_model import (
            STATUS_START, STATUS_NIGHT, STATUS_NIGHT_INFO, STATUS_DISCUSS,
            STATUS_VOTE, STATUS_VOTE_RESULT, STATUS_SHERIFF_ELECTION,
            STATUS_SHERIFF_SPEECH, STATUS_SHERIFF_VOTE, STATUS_SHERIFF,
            STATUS_SHERIFF_SPEECH_ORDER, STATUS_SHERIFF_PK, STATUS_RESULT,
            STATUS_HUNTER, STATUS_HUNTER_RESULT, STATUS_SKILL
        )
        
        # ==================== 守卫特有事件（优先处理）====================
        
        # 守护技能（守卫特有）
        if req.status == STATUS_SKILL:
            return self._handle_guard_skill(req)
        
        # 守护技能结果（守卫特有）
        if req.status == "STATUS_SKILL_RESULT":
            self._handle_skill_result(req)
            return
        
        # ==================== 标准游戏事件（与平民模板完全一致）===================="
        
        # 游戏开始（与平民模板一致）
        if req.status == STATUS_START:
            self.memory.clear()
            self.memory.set_variable("name", req.name)
            
            # 处理游戏开始（使用标准化处理器）
            from game_utils import GameStartHandler
            GameStartHandler.handle_game_start(req, self.memory, "Guard")
            
            self._init_memory_variables()
            
            # 初始化游戏状态（与平民模板一致）
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
            
            self.memory.append_history("Host: Hello, your assigned role is [Guard], you are " + req.name)
            logger.info(f"[GUARD START] Initialized as {req.name}")
            return
        
        # 夜晚阶段（与平民模板一致）
        elif req.status == STATUS_NIGHT:
            self.memory.append_history(
                "Host: Now entering night phase, close your eyes when it's dark"
            )
            game_state = self.memory.load_variable("game_state")
            game_state["current_round"] = game_state.get("current_round", 0) + 1
            self.memory.set_variable("game_state", game_state)
        
        # 夜晚信息（与平民模板一致 + 守卫特有的平安夜检测）
        elif req.status == STATUS_NIGHT_INFO:
            self.memory.append_history(
                f"Host: It's dawn! Last night's information is: {req.message}"
            )
            
            # 守卫特有：检测平安夜
            self._handle_night_info(req)
            
            # 更新游戏状态（与平民模板一致）
            game_state = self.memory.load_variable("game_state")
            game_state["current_day"] = game_state.get("current_day", 0) + 1
            
            # 解析夜晚死亡信息（与平民模板一致）
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
        
        # 讨论阶段（与平民模板一致）
        elif req.status == STATUS_DISCUSS:
            if req.name:
                # 检查是否是遗言阶段（与平民模板一致）
                my_name = self.memory.load_variable("name")
                is_last_words = (
                    ("final" in req.message.lower() or "last words" in req.message.lower() or "遗言" in req.message) or
                    (req.name == my_name and any(keyword in req.message.lower() for keyword in ["eliminated", "voted out", "speak", "words", "final"]))
                )
                
                if is_last_words and req.name == my_name:
                    self.memory.set_variable("giving_last_words", True)
                    logger.info("[LAST WORDS] Guard is being eliminated, preparing final words")
                
                # 使用基类的消息处理方法（包含注入检测、虚假引用检测、消息解析、发言质量评估）
                self._process_player_message(req.message, req.name)
                
                self.memory.append_history(req.name + ": " + req.message)
            else:
                self.memory.append_history(
                    "Host: Now entering day {}.".format(str(req.round))
                )
                self.memory.append_history(
                    "Host: Each player describes their information."
                )
            self.memory.append_history("---------------------------------------------")
        
        # 投票阶段（与平民模板一致）
        elif req.status == STATUS_VOTE:
            # 跟踪投票历史（与平民模板一致）
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
        
        # 投票结果（与平民模板一致）
        elif req.status == STATUS_VOTE_RESULT:
            out_player = req.name if req.name else req.message
            if out_player:
                self.memory.append_history(
                    "Host: The voting result is: {}.".format(out_player)
                )
                
                # 更新游戏状态（与平民模板一致）
                game_state = self.memory.load_variable("game_state")
                game_state["alive_count"] = game_state.get("alive_count", 12) - 1
                seer_checks = self.memory.load_variable("seer_checks")
                voting_results = self.memory.load_variable("voting_results")
                
                player_data = self.memory.load_variable("player_data")
                
                # 判断被投出的玩家是狼人还是好人（与平民模板一致）
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
                
                # 记录投票结果（与平民模板一致）
                current_day = game_state.get("current_day", 0)
                if current_day not in voting_results:
                    voting_results[current_day] = {}
                voting_results[current_day]["voted_out"] = out_player
                voting_results[current_day]["was_wolf"] = was_wolf
                voting_results[current_day]["was_good"] = not was_wolf
                self.memory.set_variable("voting_results", voting_results)
                
                # 更新投票历史结果（与平民模板一致）
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
                
                # 标记玩家被投出（与平民模板一致）
                if out_player not in player_data:
                    player_data[out_player] = {}
                player_data[out_player]["voted_out"] = True
                player_data[out_player]["alive"] = False
                
                # 更新存活/死亡玩家列表（与平民模板一致）
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
        
        # 警长选举（与平民模板一致）
        elif req.status == STATUS_SHERIFF_ELECTION:
            self.memory.append_history(
                "Host: Players running for sheriff: " + req.message
            )
            game_state = self.memory.load_variable("game_state")
            game_state["sheriff_election"] = True
            game_state["sheriff_candidates"] = req.message.split(",")
            self.memory.set_variable("game_state", game_state)
        
        # 警长演讲（与平民模板一致）
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
        
        # 警长投票（与平民模板一致）
        elif req.status == STATUS_SHERIFF_VOTE:
            self.memory.append_history(
                "Sheriff voting: " + req.name + " voted for " + req.message
            )
        
        # 警长结果（与平民模板一致）
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
        
        # 游戏结果（与平民模板一致）
        elif req.status == STATUS_RESULT:
            self.memory.append_history(req.message)
            
            # 游戏结束，收集数据并触发增量学习（与平民模板一致）
            logger.info("[GAME END] Collecting game data and triggering incremental learning")
            self._collect_game_data(req.message)
            
            from game_utils import GameEndTrigger
            GameEndTrigger.trigger_game_end(req, self.memory, "Guard")
        
        # 猎人技能（与平民模板一致）
        elif req.status == STATUS_HUNTER:
            self.memory.append_history(
                "Hunter/Wolf King is: "
                + req.name
                + ", they are activating their skill, choosing to shoot"
            )
        
        # 猎人结果（与平民模板一致）
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
        
        # 警长发言顺序（与平民模板一致）
        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            if "Counter-clockwise" in req.message or "小号" in req.message:
                self.memory.append_history(
                    "Host: Sheriff speech order is smaller numbers first"
                )
            else:
                self.memory.append_history(
                    "Host: Sheriff speech order is larger numbers first"
                )
        
        # 警长PK（与平民模板一致）
        elif req.status == STATUS_SHERIFF_PK:
            self.memory.append_history(f"Sheriff PK speech: {req.name}: {req.message}")
        
        # 未知状态（与平民模板一致）
        else:
            raise NotImplementedError
    
    def _handle_skill_result(self, req: AgentReq):
        """
        处理技能结果（守护结果）
        
        Args:
            req: 技能结果请求
        """
        if req.message:
            self.memory.append_history(f"Host: {req.message}")
            
            # 记录守护是否成功
            if "Guard guarded" in req.message or "successfully" in req.message.lower():
                self.memory.set_variable("last_guard_success", True)
                logger.info("[GUARD RESULT] Guard was successful")
            elif "Protection failed" in req.message or "failed" in req.message.lower():
                self.memory.set_variable("last_guard_success", False)
                logger.info("[GUARD RESULT] Guard failed")
    
    def _handle_night_info(self, req: AgentReq):
        """
        处理夜晚信息（检测平安夜并更新统计）
        
        Args:
            req: 夜晚信息请求
        """
        if req.message:
            self.memory.append_history(f"Host: Daybreak! Last night's information: {req.message}")
            
            # 检测平安夜（没有人死亡）
            message_lower = req.message.lower()
            is_peaceful = (
                "peaceful" in message_lower or 
                "no one died" in message_lower or 
                "平安夜" in req.message or
                "无人死亡" in req.message
            )
            
            if is_peaceful:
                current_night = self.memory.load_variable("current_night") or 0
                self._update_peaceful_night_status(current_night)
                logger.info(f"[NIGHT INFO] Peaceful night detected for night {current_night}")
    
    def _is_last_words_phase(self, req: AgentReq) -> bool:
        """
        统一的遗言阶段检测方法
        
        遗言阶段的特征：
        1. 消息中包含 "last words", "final words", "遗言" 等关键词
        2. 消息中包含 "leaves their last words" 等短语
        3. 玩家名称后跟 "Last Words:" 或 "遗言："
        
        Args:
            req: 游戏事件请求
            
        Returns:
            是否是遗言阶段
        """
        if not req or not req.message:
            return False
        
        message_lower = req.message.lower()
        
        # 关键词检测
        last_words_keywords = [
            "last words", "final words", "遗言",
            "leaves their last words", "leaves his last words", "leaves her last words",
            "'s last words", "最后的话"
        ]
        
        return any(keyword in message_lower for keyword in last_words_keywords)
    
    def _handle_guard_skill(self, req: AgentReq) -> AgentResp:
        """
        处理守护技能（兼容模板接口）
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 守护目标（包含skillTargetPlayer字段以兼容模板）
        """
        target = self._make_guard_decision(req.message.split(",") if req.message else [])
        
        # 更新守护历史（统一管理，避免数据不一致）
        current_night = self.memory.load_variable("current_night") or 0
        night_number = current_night + 1
        self.memory.set_variable("current_night", night_number)
        self.memory.set_variable("last_guarded", target)
        
        # 更新详细守护历史（按夜晚记录）- 主要数据源
        guard_history = self.memory.load_variable("guard_history") or {}
        guard_history[night_number] = target if target else "Empty guard"
        self.memory.set_variable("guard_history", guard_history)
        
        # 从guard_history派生guarded_players列表（保证一致性）
        guarded_players = list(set([
            v for v in guard_history.values() 
            if v and v != "Empty guard"
        ]))
        self.memory.set_variable("guarded_players", guarded_players)
        
        # 更新守护成功率统计（用于ML训练）
        self._update_guard_stats(night_number, target)
        
        logger.info(f"[GUARD SKILL] Night {night_number}: Guarding {target if target else 'Empty guard'}")
        
        # 兼容模板接口：返回skillTargetPlayer字段
        return AgentResp(success=True, result=target, skillTargetPlayer=target, errMsg=None)
    
    def _make_guard_decision(self, candidates: List[str]) -> str:
        """
        守护决策
        
        Args:
            candidates: 候选玩家列表
            
        Returns:
            守护目标
        """
        if not candidates:
            return ""
        
        # 验证决策器已初始化
        if not self.guard_decision_maker:
            raise RuntimeError("Guard decision maker not initialized - cannot make guard decision")
        
        try:
            # 安全地加载变量（使用try-except避免KeyError）
            def safe_load(var_name, default=None):
                try:
                    return self.memory.load_variable(var_name)
                except KeyError:
                    return default
            
            # 构建上下文
            my_name = safe_load("name", "Unknown")
            current_night = safe_load("current_night", 0) or 0
            last_guarded = safe_load("last_guarded")
            alive_players = safe_load("alive_players", [])
            dead_players = safe_load("dead_players", [])
            trust_scores = safe_load("trust_scores", {})
            speech_history = safe_load("speech_history", {})
            voting_history = safe_load("voting_history", {})
            sheriff = safe_load("sheriff")
            
            context = {
                'my_name': my_name,
                'night_count': current_night + 1,  # 下一个夜晚
                'last_guarded': last_guarded,
                'alive_players': set(alive_players),
                'dead_players': set(dead_players),
                'trust_scores': trust_scores,
                'speech_history': speech_history,
                'voting_history': voting_history,
                'sheriff': sheriff,
                # 传递分析器引用
                'role_checker': self.role_estimator if hasattr(self, 'role_estimator') else None,
                'wolf_predictor': self.wolf_kill_predictor if hasattr(self, 'wolf_kill_predictor') else None,
            }
            
            target, reason, confidence = self.guard_decision_maker.decide(
                candidates, 
                context
            )
            
            # 如果置信度较高，直接返回
            if confidence >= 80:
                logger.info(f"[GUARD DECISION] High confidence ({confidence}): {target} - {reason}")
                return target
            
            # 如果置信度中等，使用LLM确认
            if confidence >= 60:
                logger.info(f"[GUARD DECISION] Medium confidence ({confidence}), using LLM to confirm")
                return self._llm_guard_decision(candidates, target, reason, confidence, context)
            
            # 置信度低，完全使用LLM
            logger.info(f"[GUARD DECISION] Low confidence ({confidence}), using full LLM decision")
            return self._llm_guard_decision(candidates, target, reason, confidence, context)
            
        except Exception as e:
            logger.error(f"Error in guard decision: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Guard decision failed: {e}") from e
    
    def _llm_guard_decision(
        self, 
        candidates: List[str], 
        algo_target: str, 
        algo_reason: str, 
        algo_confidence: int,
        context: Dict[str, Any]
    ) -> str:
        """
        使用LLM进行守护决策（结合算法建议 + 优化降级逻辑 + 超时控制）
        
        降级策略：
        1. LLM有效 → 使用LLM结果
        2. LLM无效 + 算法有效 → 使用算法推荐
        3. 都无效 + 中后期 → 守护最高信任玩家
        4. 都无效 + 前期 → 空守护
        
        Args:
            candidates: 候选人列表
            algo_target: 算法推荐目标
            algo_reason: 算法推荐原因
            algo_confidence: 算法置信度
            context: 决策上下文
            
        Returns:
            守护目标
            
        Raises:
            RuntimeError: 当LLM和算法都失败时
        """
        try:
            my_name = context.get('my_name', '')
            night_count = context.get('night_count', 0)
            last_guarded = context.get('last_guarded', '')
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager is not None:
                alive_players = context.get('alive_players', set())
                trust_summary = self.trust_manager.get_summary(alive_players, top_n=8)
            
            # 构建算法建议
            algorithm_suggestion = f"""Algorithm Recommendation:
Target: {algo_target if algo_target else "Empty guard"}
Reason: {algo_reason}
Confidence: {algo_confidence}%

The algorithm has analyzed trust scores, role estimations, and wolf kill predictions.
You should review this recommendation and confirm or adjust based on game context."""
            
            # 构建历史记录
            speech_history = context.get('speech_history', {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SKILL_PROMPT, {
                "history": history_str,
                "name": my_name,
                "last_guarded": last_guarded if last_guarded else "None",
                "night_count": night_count,
                "trust_summary": trust_summary,
                "algorithm_suggestion": algorithm_suggestion,
                "choices": ", ".join(candidates)
            })
            
            # 调用LLM（添加超时控制）
            import time
            start_time = time.time()
            timeout = 90  # 90秒超时
            
            result = self._llm_generate(prompt, temperature=0.2)
            
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"[GUARD LLM DECISION] LLM call took {elapsed:.1f}s (timeout: {timeout}s)")
            
            target = result.strip()
            
            # 验证结果
            if target and target in candidates:
                logger.info(f"[GUARD LLM DECISION] Confirmed: {target}")
                return target
            elif not target or target.lower() == "empty" or target.lower() == "none":
                logger.info(f"[GUARD LLM DECISION] Empty guard")
                return ""
            else:
                # LLM返回无效结果，验证算法推荐
                if algo_target and algo_target in candidates:
                    logger.warning(f"[GUARD LLM DECISION] Invalid result '{target}', using valid algorithm: {algo_target}")
                    return algo_target
                else:
                    # 算法推荐也无效，使用智能降级
                    return self._fallback_guard_decision(candidates, night_count, context)
                
        except Exception as e:
            logger.error(f"[GUARD LLM DECISION] Error: {e}, using fallback")
            # 验证算法推荐是否有效
            if algo_target and algo_target in candidates:
                return algo_target
            else:
                return self._fallback_guard_decision(candidates, night_count, context)
    
    def _fallback_guard_decision(
        self, 
        candidates: List[str], 
        night_count: int, 
        context: Dict[str, Any]
    ) -> str:
        """
        智能降级守护决策
        
        策略：
        - 前期（夜晚1-2）：空守护（安全策略）
        - 中后期（夜晚3+）：守护最高信任玩家（保护好人）
        
        Args:
            candidates: 候选人列表
            night_count: 夜晚编号
            context: 决策上下文
            
        Returns:
            守护目标
        """
        if not candidates:
            logger.warning("[GUARD FALLBACK] No candidates, empty guard")
            return ""
        
        # 前期：空守护
        if night_count <= 2:
            logger.info(f"[GUARD FALLBACK] Early game (night {night_count}), empty guard for safety")
            return ""
        
        # 中后期：守护最高信任玩家
        trust_scores = context.get('trust_scores', {})
        if not trust_scores:
            logger.warning("[GUARD FALLBACK] No trust scores, using first candidate")
            return candidates[0]
        
        # 找出最高信任的候选人
        max_trust = -1
        best_target = candidates[0]
        
        for candidate in candidates:
            trust = trust_scores.get(candidate, 50)
            if trust > max_trust:
                max_trust = trust
                best_target = candidate
        
        logger.info(f"[GUARD FALLBACK] Mid/late game (night {night_count}), guarding highest trust: {best_target} (trust: {max_trust:.1f})")
        return best_target
    
    # ==================== 交互方法（使用父类方法）====================
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        处理交互请求（完全兼容模板代理人）
        
        Args:
            req: 交互请求
            
        Returns:
            AgentResp: 交互响应
        """
        logger.info(f"GuardAgent interact: {req}")
        
        # 导入所有需要的状态常量（与模板一致）
        from agent_build_sdk.model.werewolf_model import (
            STATUS_DISCUSS, STATUS_VOTE, STATUS_SKILL,
            STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH, STATUS_SHERIFF_VOTE,
            STATUS_SHERIFF_PK, STATUS_SHERIFF_SPEECH_ORDER, STATUS_SHERIFF
        )
        
        if req.status == STATUS_DISCUSS:
            return self._interact_discuss(req)
        elif req.status == STATUS_VOTE:
            return self._interact_vote(req)
        elif req.status == STATUS_SKILL:
            return self._handle_guard_skill(req)
        elif req.status == STATUS_SHERIFF_ELECTION:
            return self._interact_sheriff_election(req)
        elif req.status == STATUS_SHERIFF_SPEECH:
            return self._interact_sheriff_speech(req)
        elif req.status == STATUS_SHERIFF_VOTE:
            return self._interact_sheriff_vote(req)
        elif req.status == STATUS_SHERIFF_PK:
            return self._interact_sheriff_pk(req)
        elif req.status == STATUS_SHERIFF_SPEECH_ORDER:
            return self._interact_sheriff_speech_order(req)
        elif req.status == STATUS_SHERIFF:
            return self._interact_sheriff_transfer(req)
        else:
            # 未知状态，返回默认响应（与模板一致）
            logger.warning(f"[GUARD INTERACT] Unknown status: {req.status}, returning default response")
            return AgentResp(success=True, result="", errMsg=None)
    
    def _interact_discuss(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段的发言（完全兼容模板代理人）
        
        Args:
            req: 讨论请求
            
        Returns:
            AgentResp: 发言内容
        """
        # 添加消息到历史（与模板一致）
        if req.message:
            self.memory.append_history(req.message)
        
        # 检查是否是遗言阶段（与模板一致）
        giving_last_words = self.memory.load_variable("giving_last_words")
        
        if giving_last_words:
            return self._generate_last_words()
        
        # 构建prompt参数
        try:
            # 获取基本信息（使用安全的加载方法）
            my_name = self.memory.load_variable("name") if "name" in self.memory.memories else "Unknown"
            alive_players = self.memory.load_variable("alive_players") if "alive_players" in self.memory.memories else []
            dead_players = self.memory.load_variable("dead_players") if "dead_players" in self.memory.memories else []
            current_day = self.memory.load_variable("day_count") if "day_count" in self.memory.memories else 1
            
            # 获取守卫信息
            guarded_players = self.memory.load_variable("guarded_players") if "guarded_players" in self.memory.memories else []
            guard_info = f"Guarded history: {', '.join(guarded_players) if guarded_players else 'None yet'}"
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager is not None:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 获取注入攻击嫌疑人
            injection_suspects = self.memory.load_variable("injection_suspects") if "injection_suspects" in self.memory.memories else {}
            injection_str = ", ".join([f"{p}({t})" for p, t in injection_suspects.items()]) if injection_suspects else "None"
            
            # 获取虚假引用
            false_quotations = self.memory.load_variable("false_quotations") if "false_quotations" in self.memory.memories else []
            false_quote_str = ", ".join([f"{fq.get('accuser', '?')}" for fq in false_quotations if isinstance(fq, dict)]) if false_quotations else "None"
            
            # 获取状态矛盾
            status_contradictions = self.memory.load_variable("player_status_claims") if "player_status_claims" in self.memory.memories else {}
            status_str = ", ".join([p for p, v in status_contradictions.items() if v]) if status_contradictions else "None"
            
            # 确定游戏阶段
            if current_day <= 3:
                game_phase = "Early Game"
                phase_strategy = "Stay hidden, analyze from villager perspective"
            elif current_day <= 6:
                game_phase = "Mid Game"
                phase_strategy = "Consider hinting at guard ability if situation is clear"
            else:
                game_phase = "Late Game"
                phase_strategy = "Expose identity and share guard history to lead good team"
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") if "speech_history" in self.memory.memories else {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(DESC_PROMPT, {
                "history": history_str,
                "name": my_name,
                "guard_info": guard_info,
                "game_phase": game_phase,
                "current_day": current_day,
                "alive_count": len(alive_players),
                "trust_summary": trust_summary,
                "injection_suspects": injection_str,
                "false_quotations": false_quote_str,
                "status_contradictions": status_str,
                "phase_strategy": phase_strategy
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            
            # 长度控制（与模板一致）
            original_length = len(result)
            if original_length > self.config.MAX_SPEECH_LENGTH:
                truncated = result[:self.config.MAX_SPEECH_LENGTH]
                last_period = max(
                    truncated.rfind('。'), 
                    truncated.rfind('.'), 
                    truncated.rfind('！'), 
                    truncated.rfind('!')
                )
                if last_period > self.config.MIN_SPEECH_LENGTH:
                    result = truncated[:last_period + 1]
                else:
                    result = truncated
                logger.info(f"Speech truncated from {original_length} to {len(result)} chars")
            elif original_length < self.config.MIN_SPEECH_LENGTH:
                logger.warning(f"Speech too short: {original_length} chars")
            
            logger.info(f"GuardAgent interact result: {result}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD DISCUSS] Error generating speech: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to generate guard discussion speech: {e}") from e
    
    def _format_history(self, speech_history: dict, max_entries: int = 10) -> str:
        """
        格式化发言历史
        
        Args:
            speech_history: 发言历史字典
            max_entries: 最大条目数
            
        Returns:
            格式化的历史字符串
        """
        if not speech_history or not isinstance(speech_history, dict):
            return "No speech history available."
        
        entries = []
        for player, speeches in speech_history.items():
            if isinstance(speeches, list) and speeches:
                # 只取最近的发言
                recent = speeches[-2:] if len(speeches) > 2 else speeches
                for speech in recent:
                    if speech and isinstance(speech, str):
                        entries.append(f"{player}: {speech[:100]}...")
        
        # 限制条目数
        if len(entries) > max_entries:
            entries = entries[-max_entries:]
        
        return "\n".join(entries) if entries else "No recent speeches."
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        遗言是守卫最后的贡献，必须包含：
        1. 完整的守护历史
        2. 信任分数分析
        3. 狼人嫌疑人
        4. 投票建议
        
        Returns:
            AgentResp: 遗言内容
        """
        try:
            # 获取基本信息
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取守卫历史并格式化
            guard_history = self.memory.load_variable("guard_history") or {}
            guarded_players = self.memory.load_variable("guarded_players") or []
            
            # 详细格式化守护历史（按夜晚顺序）
            guard_history_detail = self._format_guard_history_detailed(guard_history)
            
            # 守护摘要
            guard_summary = self._format_guard_summary(guarded_players, guard_history)
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt（确保所有参数都存在）
            prompt = format_prompt(LAST_WORDS_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "guard_history_summary": guard_summary,
                "guard_history_detail": guard_history_detail
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            
            # 长度控制（与模板一致）
            if len(result) > self.config.MAX_SPEECH_LENGTH:
                result = result[:self.config.MAX_SPEECH_LENGTH]
            
            # 清除遗言标志（与模板一致）
            self.memory.set_variable("giving_last_words", False)
            
            logger.info(f"GuardAgent last words result: {result}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD LAST WORDS] Error generating: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to generate guard last words: {e}") from e
    
    def _format_guard_history_detailed(self, guard_history: Dict[int, str]) -> str:
        """
        详细格式化守护历史（优化版 - 突出关键夜晚）
        
        Args:
            guard_history: 守护历史字典 {night: target}
            
        Returns:
            格式化的守护历史字符串
        """
        if not guard_history:
            return "No guard history recorded (game just started)"
        
        history_lines = []
        guard_stats = self.memory.load_variable("guard_stats") or {}
        
        for night in sorted(guard_history.keys()):
            target = guard_history[night]
            stats = guard_stats.get(night, {})
            was_peaceful = stats.get('was_peaceful', False)
            
            if target and target != "Empty guard":
                # 标记成功守护（平安夜）
                marker = " ⭐ (Peaceful night - successful guard!)" if was_peaceful else ""
                history_lines.append(f"- Night {night}: Guarded {target}{marker}")
            else:
                history_lines.append(f"- Night {night}: Empty guard (strategic choice)")
        
        return "\n".join(history_lines) if history_lines else "No guard history recorded"
    
    def _format_guard_summary(self, guarded_players: List[str], guard_history: Dict[int, str]) -> str:
        """
        格式化守护摘要
        
        Args:
            guarded_players: 被守护过的玩家列表
            guard_history: 守护历史字典
            
        Returns:
            守护摘要字符串
        """
        if not guarded_players and not guard_history:
            return "No guards performed"
        
        total_nights = len(guard_history) if guard_history else 0
        unique_players = len(guarded_players) if guarded_players else 0
        empty_guards = sum(1 for target in guard_history.values() if not target or target == "Empty guard") if guard_history else 0
        
        summary_parts = []
        if total_nights > 0:
            summary_parts.append(f"Total {total_nights} nights")
        if unique_players > 0:
            summary_parts.append(f"guarded {unique_players} different players")
        if empty_guards > 0:
            summary_parts.append(f"{empty_guards} empty guards")
        
        return ", ".join(summary_parts) if summary_parts else "No guards performed"
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（完全兼容模板代理人）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        # 添加投票提示到历史（与模板一致）
        self.memory.append_history(
            "Host: It's time to vote. Everyone, please point to the person you think might be a werewolf."
        )
        
        my_name = self.memory.load_variable("name")
        
        # 获取候选人列表并过滤掉自己（与模板一致）
        choices = [
            name
            for name in req.message.split(",")
            if name != my_name
        ]
        
        if not choices:
            logger.warning("[GUARD VOTE] No valid choices available")
            return AgentResp(success=True, result="", errMsg=None)
        
        # 保存choices到内存（与模板一致）
        self.memory.set_variable("choices", choices)
        
        # 使用父类的投票决策方法（自动融合ML，与模板一致）
        target = self._make_vote_decision(choices)
        
        # 混合模式：使用LLM验证或调整（与模板一致）
        if self.config.DECISION_MODE == "hybrid":
            # 添加决策树推荐（与模板一致）
            dt_hint = f"\n[DECISION TREE RECOMMENDATION: Vote {target}]"
            
            prompt = format_prompt(
                VOTE_PROMPT,
                {
                    "name": my_name,
                    "choices": choices,
                    "history": "\n".join(self.memory.load_history()) + dt_hint,
                },
            )
            logger.info("prompt:" + prompt)
            result = self._llm_generate(prompt, temperature=0.2)
            
            # 验证LLM输出（使用基类的增强验证方法，与模板一致）
            result = self._validate_player_name(result, choices)
        else:
            # 纯代码模式（与模板一致）
            result = target
        
        logger.info(f"interact result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    # ==================== 警长相关方法 ====================
    
    def _interact_sheriff_election(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举决策（完全兼容模板代理人）
        
        Args:
            req: 选举请求
            
        Returns:
            AgentResp: 是否参选
        """
        # 构建上下文（与模板一致）
        context = self._build_context()
        
        # 使用决策树决定是否竞选（与模板一致）
        # 守卫没有特定的选举决策器，使用基类的
        should_run = False  # 守卫默认不竞选（保持低调）
        dt_reason = "Guard should stay hidden in early game"
        
        logger.info(f"[DECISION TREE SHERIFF] Should run: {should_run}, Reason: {dt_reason}")
        
        # 混合模式（与模板一致）
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
            result = self._llm_generate(prompt, temperature=0.3)
        else:
            result = "Run for Sheriff" if should_run else "Do Not Run"
        
        logger.info(f"GuardAgent sheriff election result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选演讲
        
        注意：警长选举发生在死亡公告之前，不能引用当晚的死亡信息
        
        Args:
            req: 演讲请求
            
        Returns:
            AgentResp: 演讲内容
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录（只包含之前的信息，不包含当晚死亡）
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 添加时序约束提醒
            timing_reminder = "⚠️ CRITICAL: Sheriff election happens BEFORE death announcements. Do NOT mention who died last night."
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            # 在prompt前添加时序约束
            prompt = f"{timing_reminder}\n\n{prompt}"
            
            result = self._llm_generate(prompt, temperature=0.7)
            
            # 长度控制（与模板一致）
            if len(result) > self.config.MAX_SPEECH_LENGTH:
                result = result[:self.config.MAX_SPEECH_LENGTH]
            
            logger.info(f"GuardAgent sheriff speech result: {result}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF SPEECH] Error: {e}")
            return AgentResp(success=True, result="I am running for sheriff to help the good team.", errMsg=None)
    
    def _interact_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举投票（完全兼容模板代理人）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        # 获取候选人列表（与模板一致）
        choices = [name for name in req.message.split(",")]
        
        # 构建上下文（与模板一致）
        context = self._build_context()
        
        # 使用决策树决定警长投票（与模板一致）
        # 守卫使用基类的sheriff_vote_decision_maker
        target = choices[0] if choices else ""  # 默认投第一个
        dt_reason = "Default vote"
        
        if hasattr(self, 'sheriff_vote_decision_maker') and self.sheriff_vote_decision_maker:
            try:
                target, dt_reason = self.sheriff_vote_decision_maker.decide(choices, context)
            except Exception as e:
                logger.warning(f"Sheriff vote decision failed: {e}")
        
        logger.info(f"[DECISION TREE SHERIFF VOTE] Target: {target}, Reason: {dt_reason}")
        
        # 混合模式（与模板一致）
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
            result = self._llm_generate(prompt, temperature=0.2)
            
            if result not in choices:
                logger.warning(f"LLM output '{result}' not in choices, using decision tree result: {target}")
                result = target
        else:
            result = target
        
        logger.info(f"GuardAgent sheriff vote result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK演讲
        
        Args:
            req: PK请求
            
        Returns:
            AgentResp: PK演讲内容
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_PK_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            
            # 长度控制（与模板一致）
            if len(result) > self.config.MAX_SPEECH_LENGTH:
                result = result[:self.config.MAX_SPEECH_LENGTH]
            
            logger.info(f"GuardAgent sheriff pk result: {result}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF PK] Error: {e}")
            return AgentResp(success=True, result="I am the better choice for sheriff.", errMsg=None)
    
    def _interact_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """
        处理警长发言顺序选择（完全兼容模板代理人）
        
        Args:
            req: 顺序请求
            
        Returns:
            AgentResp: 发言顺序
        """
        # 构建上下文（与模板一致）
        context = self._build_context()
        
        # 使用决策树决定发言顺序（与模板一致）
        # 守卫没有特定的发言顺序决策器，使用简单逻辑
        order = "Clockwise"  # 默认顺时针
        dt_reason = "Default speech order"
        
        logger.info(f"[DECISION TREE SPEECH ORDER] Order: {order}, Reason: {dt_reason}")
        
        # 混合模式（与模板一致）
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
            result = self._llm_generate(prompt, temperature=0.3)
            
            if "clockwise" not in result.lower() and "counter" not in result.lower():
                logger.warning(f"LLM output '{result}' not valid, using decision tree result: {order}")
                result = order
        else:
            result = order
        
        logger.info(f"GuardAgent sheriff speech order result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_transfer(self, req: AgentReq) -> AgentResp:
        """
        处理警徽转移
        
        Args:
            req: 转移请求
            
        Returns:
            AgentResp: 转移目标
        """
        try:
            my_name = self.memory.load_variable("name")
            
            # 获取候选人列表并过滤掉自己
            if req.message:
                choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
            else:
                choices = []
            
            if not choices:
                logger.warning("[GUARD SHERIFF TRANSFER] No valid choices available")
                return AgentResp(success=True, result="tear", errMsg=None)
            
            # 构建上下文
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_TRANSFER_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            
            # 解析结果
            if "tear" in result.lower():
                target = "tear"
            else:
                target = self._validate_player_name(result.strip(), choices)
            
            logger.info(f"[GUARD SHERIFF TRANSFER] Target: {target}")
            return AgentResp(success=True, result=target, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF TRANSFER] Error: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to make sheriff transfer decision: {e}") from e
    
    # ==================== 优化方法 ====================
    
    def _update_guard_stats(self, night: int, target: str):
        """
        更新守护统计（用于ML训练和遗言生成）
        
        Args:
            night: 夜晚编号
            target: 守护目标
        """
        guard_stats = self.memory.load_variable("guard_stats") or {}
        guard_stats[night] = {
            'target': target,
            'timestamp': night,
            'was_peaceful': False  # 将在下一个白天更新
        }
        self.memory.set_variable("guard_stats", guard_stats)
    
    def _update_peaceful_night_status(self, night: int):
        """
        更新平安夜状态（在白天阶段调用）
        
        Args:
            night: 夜晚编号
        """
        guard_stats = self.memory.load_variable("guard_stats") or {}
        if night in guard_stats:
            guard_stats[night]['was_peaceful'] = True
            self.memory.set_variable("guard_stats", guard_stats)
            logger.info(f"[GUARD STATS] Night {night} marked as peaceful - successful guard!")
    
    def _calculate_guard_success_rate(self) -> float:
        """
        计算守护成功率
        
        Returns:
            成功率 (0.0-1.0)
        """
        guard_stats = self.memory.load_variable("guard_stats") or {}
        if not guard_stats:
            return 0.0
        
        # 只统计非空守护
        non_empty_guards = [
            stats for stats in guard_stats.values()
            if stats.get('target') and stats.get('target') != "Empty guard"
        ]
        
        if not non_empty_guards:
            return 0.0
        
        successful_guards = sum(
            1 for stats in non_empty_guards
            if stats.get('was_peaceful', False)
        )
        
        return successful_guards / len(non_empty_guards)
