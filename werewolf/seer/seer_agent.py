# -*- coding: utf-8 -*-
"""
预言家代理人 - 重构版（继承BaseGoodAgent）

继承BaseGoodAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统
- ML增强
- 信任分析
- 投票决策

预言家特有功能：
- 验人技能
- 验人结果管理
- 验人优先级计算
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
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_good_agent import BaseGoodAgent
from .prompt import (
    DESC_PROMPT, 
    SHERIFF_SPEECH_PROMPT, 
    SHERIFF_PK_PROMPT, 
    LAST_WORDS_PROMPT
)
from typing import Dict, List, Tuple, Optional
import os

# 导入预言家特有模块
from .config import SeerConfig
from .memory_dao import SeerMemoryDAO
from .analyzers import CheckPriorityCalculator
from .decision_makers import CheckDecisionMaker
from .utils import CheckReasonGenerator


class SeerAgent(BaseGoodAgent):
    """
    预言家代理（重构版 - 继承BaseGoodAgent）
    
    继承BaseGoodAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统
    - ML增强
    - 信任分析
    - 投票决策
    
    预言家特有功能：
    - 验人技能
    - 验人结果管理
    - 验人优先级计算
    """

    def __init__(self, model_name: str = None):
        """
        初始化预言家代理
        
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
        
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_SEER, model_name=model_name)
        
        # 覆盖配置为预言家特有配置
        # 注意：SeerConfig 继承自 BaseGoodConfig，所以所有父类组件仍然可以正常工作
        self.config = SeerConfig()
        
        # 重新初始化预言家特有组件（使用新配置）
        self._init_specific_components()
        
        # 初始化DAO（使用预言家的MemoryDAO）
        self.memory_dao = SeerMemoryDAO(self.memory)
        
        logger.info("✓ SeerAgent initialized with BaseGoodAgent")
    
    def _init_memory_variables(self):
        """
        初始化预言家特有的内存变量
        
        继承父类的内存变量，并添加预言家特有的：
        - checked_players: 验人记录
        - night_count: 夜晚计数
        - day_count: 白天计数
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加预言家特有变量
        self.memory.set_variable("checked_players", {})
        self.memory.set_variable("night_count", 0)
        self.memory.set_variable("day_count", 0)
        
        logger.info("✓ Seer-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化预言家特有组件
        
        预言家特有组件：
        - CheckDecisionMaker: 验人决策
        - CheckPriorityCalculator: 验人优先级计算
        - CheckReasonGenerator: 验人理由生成
        - BadgeTransferDecisionMaker: 警徽转移决策（从平民继承）
        - SpeechOrderDecisionMaker: 发言顺序决策（从平民继承）
        
        从父类继承的组件（已在BaseGoodAgent中初始化）：
        - sheriff_election_decision_maker: 警长选举决策
        - sheriff_vote_decision_maker: 警长投票决策
        """
        # 初始化预言家特有组件
        self.check_decision_maker = CheckDecisionMaker(self.config)
        self.check_priority_calculator = CheckPriorityCalculator(self.config)
        self.check_reason_generator = CheckReasonGenerator(self.config)
        
        # 初始化警徽转移和发言顺序决策器（从平民模块导入）
        from werewolf.villager.decision_makers import (
            BadgeTransferDecisionMaker,
            SpeechOrderDecisionMaker
        )
        
        self.badge_transfer_decision_maker = BadgeTransferDecisionMaker(
            self.config, self.trust_score_calculator
        )
        self.speech_order_decision_maker = SpeechOrderDecisionMaker(
            self.config, self.trust_score_calculator
        )
        
        logger.info("✓ Seer-specific components initialized")
    
    # ==================== 辅助方法 ====================
    
    def _is_last_words_phase(self, message: str) -> bool:
        """
        统一的遗言阶段检测方法
        
        Args:
            message: 消息内容
            
        Returns:
            是否是遗言阶段
        """
        if not message or not isinstance(message, str):
            return False
        
        message_lower = message.lower()
        last_words_keywords = [
            "last words", "final words", "遗言",
            "leaves their last words", "leaves his last words", "leaves her last words",
            "'s last words", "最后的话"
        ]
        
        return any(keyword in message_lower for keyword in last_words_keywords)
    
    def _build_context(self) -> str:
        """
        构建上下文字符串（用于prompt）
        
        Returns:
            格式化的上下文字符串
        """
        history = self.memory_dao.get_history()
        if not history:
            return "No history available."
        
        # 只取最近的10条记录
        recent_history = history[-10:] if len(history) > 10 else history
        return "\n".join(recent_history)
    
    def _format_checked_players(self) -> str:
        """
        格式化检查结果
        
        Returns:
            格式化的检查结果字符串
        """
        checked_players = self.memory_dao.get_checked_players()
        if not checked_players:
            return "No checks performed yet."
        
        lines = []
        for player, data in sorted(checked_players.items(), key=lambda x: x[1].get('night', 0)):
            is_wolf = data.get('is_wolf', False)
            night = data.get('night', 0)
            result = "WOLF" if is_wolf else "GOOD"
            lines.append(f"Night {night}: {player} → {result}")
        
        return "\n".join(lines)
    
    def _format_trust_summary(self, alive_players: List[str], my_name: str) -> str:
        """
        格式化信任分数摘要（统一格式）
        
        Args:
            alive_players: 存活玩家列表
            my_name: 自己的名字
            
        Returns:
            格式化的信任分数摘要
        """
        trust_scores = self.memory_dao.get_trust_scores()
        if not trust_scores or not alive_players:
            return "No trust data"
        
        sorted_players = sorted(
            [(p, trust_scores.get(p, 50)) for p in alive_players if p != my_name],
            key=lambda x: x[1],
            reverse=True
        )
        
        trust_lines = [f"{p}: {score:.0f}" for p, score in sorted_players[:8]]
        return "\n".join(trust_lines) if trust_lines else "No trust data"
    
    def _determine_game_phase(self, current_day: int, alive_count: int) -> tuple:
        """
        确定游戏阶段和策略
        
        Args:
            current_day: 当前天数
            alive_count: 存活人数
            
        Returns:
            (游戏阶段, 阶段策略)
        """
        checked_players = self.memory_dao.get_checked_players()
        has_wolf_check = any(data.get('is_wolf', False) for data in checked_players.values())
        
        if has_wolf_check:
            return ("Reveal Phase", "REVEAL immediately - you have wolf check, guide voting")
        
        game_state = self.memory_dao.get_game_state()
        fake_seer_appeared = game_state.get('fake_seer_name') is not None
        
        if fake_seer_appeared:
            return ("Counter-Claim Phase", "COUNTER-CLAIM immediately - fake seer appeared")
        
        if current_day <= self.config.EARLY_GAME_MAX_DAY:
            return ("Early Game", "Stay hidden, gather more checks, analyze behavior")
        elif current_day <= self.config.MID_GAME_MAX_DAY:
            return ("Mid Game", "Consider revealing if good faction needs leadership")
        elif alive_count <= self.config.ENDGAME_ALIVE_THRESHOLD or current_day >= 6:
            return ("Late Game", "Reveal identity and lead good faction to victory")
        else:
            return ("Mid Game", "Consider revealing if good faction needs leadership")
    
    def _get_current_day(self) -> int:
        """获取当前天数"""
        day_count = self.memory_dao.get_day_count()
        if day_count:
            return day_count
        game_state = self.memory_dao.get_game_state()
        return game_state.get('current_day', 1)
    
    def _get_alive_count(self) -> int:
        """
        获取存活人数
        
        Returns:
            存活人数
            
        Raises:
            ValueError: 如果无法获取存活人数
        """
        game_state = self.memory_dao.get_game_state()
        alive_count = game_state.get('alive_count')
        if alive_count:
            return alive_count
        
        # 从发言历史和死亡玩家计算
        speech_history = self.memory_dao.get_speech_history()
        dead_players = self.memory_dao.get_dead_players()
        
        if not speech_history:
            raise ValueError("无法获取存活人数：发言历史为空且game_state中没有alive_count")
        
        all_players = set(speech_history.keys())
        alive = all_players - dead_players
        
        if not alive:
            raise ValueError("无法获取存活人数：计算结果为0")
        
        return len(alive)
    
    def perceive(self, req=AgentReq):
        """
        处理游戏事件（重写父类方法以添加预言家特有处理）
        
        Args:
            req: 游戏事件请求
        """
        # 预言家特有事件：技能结果（验人结果）
        if req.status == STATUS_SKILL_RESULT:
            return self._handle_skill_result(req)
        else:
            # 其他事件使用父类处理
            return super().perceive(req)
    
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
        
        if is_wolf:
            new_score = self.trust_score_manager.analyze(
                target_player, self.config.TRUST_WOLF_CHECK, 1.0, 1.0,
                trust_scores
            )
        else:
            new_score = self.trust_score_manager.analyze(
                target_player, self.config.TRUST_GOOD_CHECK, 1.0, 1.0,
                trust_scores
            )
        
        self.memory_dao.set_trust_scores(trust_scores)
        
        logger.info(f"Check result: {target_player} is {'WOLF' if is_wolf else 'GOOD'}, trust score: {new_score}")
    

    
    

    
    
    
    
    
    
    
    
    
    
    
    

    
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
            # 未知状态，返回默认响应
            logger.warning(f"[SEER INTERACT] Unknown status: {req.status}, returning default response")
            return AgentResp(success=True, result="", errMsg=None)

    
    def _interact_discuss(self, req) -> AgentResp:
        """
        处理讨论阶段的发言（使用父类的LLM生成方法）
        
        Args:
            req: 讨论请求
            
        Returns:
            AgentResp: 发言内容
            
        Raises:
            RuntimeError: 如果发言生成失败
        """
        if req.message:
            self.memory_dao.append_history(req.message)
        
        my_name = self.memory_dao.get_my_name()
        message = str(req.message or "")
        
        # 检查是否是遗言阶段（使用统一方法）
        if self._is_last_words_phase(message):
            return self._generate_last_words()
        
        # 正常讨论阶段 - 使用父类的LLM生成方法
        try:
            # 获取基本信息
            current_day = self._get_current_day()
            alive_count = self._get_alive_count()
            
            # 格式化检查结果
            checked_players_str = self._format_checked_players()
            
            # 确定游戏阶段
            game_phase, phase_strategy = self._determine_game_phase(current_day, alive_count)
            
            # 构建历史记录
            context = self._build_context()
            
            # 格式化prompt
            prompt = format_prompt(DESC_PROMPT, {
                "name": my_name,
                "checked_players": checked_players_str,
                "history": context,
                "game_phase": game_phase,
                "current_day": current_day,
                "alive_count": alive_count,
                "phase_strategy": phase_strategy
            })
            
            result = self._llm_generate(prompt)
            
            if not result or len(result.strip()) == 0:
                raise RuntimeError("LLM生成的发言为空")
            
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[SEER DISCUSS] Generated speech (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[SEER DISCUSS] Error generating speech: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"预言家发言生成失败: {e}") from e
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
            
        Raises:
            RuntimeError: 如果遗言生成失败
        """
        try:
            my_name = self.memory_dao.get_my_name()
            
            # 格式化检查结果
            checked_players_str = self._format_checked_players()
            
            # 构建历史记录
            context = self._build_context()
            
            # 格式化prompt
            prompt = format_prompt(LAST_WORDS_PROMPT, {
                "name": my_name,
                "checked_players": checked_players_str,
                "history": context
            })
            
            result = self._llm_generate(prompt)
            
            if not result or len(result.strip()) == 0:
                raise RuntimeError("LLM生成的遗言为空")
            
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[SEER LAST WORDS] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[SEER LAST WORDS] Error generating: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"预言家遗言生成失败: {e}") from e
    
    
    def _interact_vote(self, req) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法）

        Args:
            req: 投票请求

        Returns:
            AgentResp: 投票目标
        """
        self.memory_dao.append_history('Host: It\'s time to vote. Everyone, please point to the person you think is likely a werewolf.')

        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]

        # 使用父类的投票决策方法（自动融合ML）
        target = self._make_vote_decision(choices)

        logger.info(f"[SEER VOTE] Target: {target}")
        return AgentResp(success=True, result=target, errMsg=None)

    
    def _interact_skill(self, req) -> AgentResp:
        """
        处理技能使用（检查决策）- 使用决策器
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 检查目标
        """
        checked_players = self.memory_dao.get_checked_players()
        my_name = self.memory_dao.get_my_name()
        
        # 解析候选人列表
        all_choices = [name.strip() for name in req.message.split(",") if name.strip()]
        choices = [name for name in all_choices if name != my_name]
        
        if not choices:
            logger.warning("No valid choices for skill, using first available")
            choices = all_choices
        
        if not choices:
            logger.error("No choices available for skill")
            return AgentResp(success=True, result="No.1", skillTargetPlayer="No.1", errMsg=None)
        
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
        
        # 使用决策器做出检查决策
        target, reason = self.check_decision_maker.decide(choices, context)
        
        logger.info(f"[SEER SKILL] Target: {target}, Reason: {reason}")
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
        
        should_run, reason = self.sheriff_election_decision_maker.decide(context)
        logger.info(f"[DECISION TREE SHERIFF] Should run: {should_run}, Reason: {reason}")
        
        result = "Run for Sheriff" if should_run else "Do Not Run"
        logger.info(f"seer agent sheriff election result: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_sheriff_speech(self, req) -> AgentResp:
        """
        处理警长竞选发言（使用父类的LLM生成方法）
        
        注意：警长选举发生在死亡公告之前，不能引用当晚的死亡信息
        
        Args:
            req: 竞选发言请求
            
        Returns:
            AgentResp: 竞选发言内容
        """
        try:
            my_name = self.memory_dao.get_my_name()
            
            # 格式化检查结果
            checked_players_str = self._format_checked_players()
            
            # 构建历史记录（只包含之前的信息，不包含当晚死亡）
            context = self._build_context()
            
            # 添加时序约束提醒
            timing_reminder = "⚠️ CRITICAL: Sheriff election happens BEFORE death announcements. Do NOT mention who died last night."
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
                "name": my_name,
                "checked_players": checked_players_str,
                "history": context
            })
            
            # 在prompt前添加时序约束
            prompt = f"{timing_reminder}\n\n{prompt}"
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[SEER SHERIFF SPEECH] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[SEER SHERIFF SPEECH] Error: {e}")
            import traceback
            traceback.print_exc()
            return AgentResp(success=True, result="I am the Seer running for sheriff to help the good team.", errMsg=None)
    
    def _interact_sheriff_vote(self, req) -> AgentResp:
        """处理警长投票决策（使用决策器）"""
        choices = [name for name in req.message.split(",")]
        
        context = {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores()
        }
        
        target, reason = self.sheriff_vote_decision_maker.decide(choices, context)
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
        
        order, reason = self.speech_order_decision_maker.decide(context)
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
        
        target, reason = self.badge_transfer_decision_maker.decide(choices, context)
        logger.info(f"[DECISION TREE BADGE TRANSFER] Target: {target}, Reason: {reason}")
        
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _interact_sheriff_pk(self, req) -> AgentResp:
        """
        处理警长PK发言（使用父类的LLM生成方法）
        
        Args:
            req: PK发言请求
            
        Returns:
            AgentResp: PK发言内容
        """
        try:
            my_name = self.memory_dao.get_my_name()
            
            # 格式化检查结果
            checked_players_str = self._format_checked_players()
            
            # 构建历史记录
            context = self._build_context()
            
            # 识别对手
            opponent = "Unknown"
            game_state = self.memory_dao.get_game_state()
            if game_state.get('fake_seer_name'):
                opponent = game_state['fake_seer_name']
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_PK_PROMPT, {
                "name": my_name,
                "opponent": opponent,
                "checked_players": checked_players_str,
                "history": context
            })
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[SEER SHERIFF PK] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[SEER SHERIFF PK] Error: {e}")
            import traceback
            traceback.print_exc()
            return AgentResp(success=True, result="I am the true Seer. Vote for me to lead the good faction.", errMsg=None)
