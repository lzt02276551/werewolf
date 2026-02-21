# -*- coding: utf-8 -*-
"""
平民代理人主文件（重构版 - 继承 BaseGoodAgent）
使用继承机制减少代码重复，提高可维护性
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
from agent_build_sdk.sdk.agent import format_prompt

# 导入基类
from werewolf.core.base_good_agent import BaseGoodAgent
from werewolf.common.utils import DataValidator
from .config import VillagerConfig

# 导入平民特有的决策器
from .decision_makers import (
    BadgeTransferDecisionMaker, SpeechOrderDecisionMaker, LastWordsGenerator
)
from .analyzers import SpeechPositionAnalyzer

# ML Enhancement Integration
import sys
import os


class VillagerAgent(BaseGoodAgent):
    """
    平民角色代理（重构版 - 继承 BaseGoodAgent）
    
    继承 BaseGoodAgent 获得所有共享功能：
    - ML增强
    - 检测系统（注入检测、虚假引用检测、消息解析、发言质量评估）
    - 分析系统（信任分数管理、投票模式分析、游戏阶段分析）
    - 决策系统（投票决策、警长选举决策、警长投票决策）
    
    平民特有功能：
    - 无特殊技能（纯粹的推理和投票）
    """

    def __init__(self, model_name):
        """
        初始化平民代理
        
        Args:
            model_name: LLM模型名称
        """
        # 调用父类初始化（会自动初始化所有共享组件）
        super().__init__(ROLE_VILLAGER, model_name=model_name)
        
        # 使用平民特有配置覆盖基类配置
        self.config = VillagerConfig()
        
        logger.info("✓ VillagerAgent initialized (inherits from BaseGoodAgent)")
    
    def _init_specific_components(self):
        """
        初始化平民特有组件
        
        平民特有的决策器和分析器：
        - BadgeTransferDecisionMaker: 警长徽章转移决策
        - SpeechOrderDecisionMaker: 发言顺序决策
        - LastWordsGenerator: 遗言生成器
        - SpeechPositionAnalyzer: 发言位置分析器
        """
        try:
            self.badge_transfer_decision_maker = BadgeTransferDecisionMaker(
                self.config, self.trust_score_calculator
            )
            self.speech_order_decision_maker = SpeechOrderDecisionMaker(
                self.config, self.trust_score_calculator
            )
            self.last_words_generator = LastWordsGenerator(
                self.config, self.trust_score_calculator, self.voting_pattern_analyzer
            )
            self.speech_position_analyzer = SpeechPositionAnalyzer(self.config)
            
            logger.info("✓ Villager-specific components initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize villager-specific components: {e}")
            # 设置为 None 以支持降级
            self.badge_transfer_decision_maker = None
            self.speech_order_decision_maker = None
            self.last_words_generator = None
            self.speech_position_analyzer = None


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
        """推断玩家角色（继承自基类的 _build_context，这里保留用于游戏数据收集）"""
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
    
    # _build_context 方法已在 BaseGoodAgent 中实现，这里不需要重复
    
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

            # 使用基类的投票决策方法（包含决策树和ML融合）
            target = self._make_vote_decision(choices)
            
            # 混合模式：使用LLM验证或调整
            if self.config.DECISION_MODE == "hybrid":
                # 添加决策树推荐
                dt_hint = f"\n[DECISION TREE RECOMMENDATION: Vote {target}]"

                prompt = format_prompt(
                    VOTE_PROMPT,
                    {
                        "name": self.memory.load_variable("name"),
                        "choices": choices,
                        "history": "\n".join(self.memory.load_history()) + dt_hint,
                    },
                )
                logger.info("prompt:" + prompt)
                result = self.llm_caller(prompt)
                
                # 验证LLM输出
                result = self._validate_player_name(result, choices)
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
            # 未知状态，返回默认响应
            logger.warning(f"[VILLAGER INTERACT] Unknown status: {req.status}, returning default response")
            return AgentResp(success=True, result="", errMsg=None)
