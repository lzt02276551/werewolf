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
    DESC_PROMPT, VOTE_PROMPT, SKILL_PROMPT, GAME_RULE_PROMPT,
    SHERIFF_ELECTION_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_VOTE_PROMPT, 
    SHERIFF_SPEECH_ORDER_PROMPT, SHERIFF_TRANSFER_PROMPT, SHERIFF_PK_PROMPT, 
    LAST_WORDS_PROMPT
)
from typing import Dict, List, Tuple, Optional
import os

# 导入预言家特有模块
from .config import SeerConfig
from .memory_dao import SeerMemoryDAO
from .analyzers import CheckPriorityCalculator
from .decision_makers import (
    CheckDecisionMaker, IdentityRevealDecisionMaker
)
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

    def __init__(self, model_name):
        """
        初始化预言家代理
        
        Args:
            model_name: LLM模型名称
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_SEER, model_name=model_name)
        
        # 初始化预言家配置
        self.config = SeerConfig()
        
        # 初始化DAO
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
        - IdentityRevealDecisionMaker: 身份公开决策
        """
        try:
            self.check_decision_maker = CheckDecisionMaker(self.config)
            self.check_priority_calculator = CheckPriorityCalculator(self.config)
            self.check_reason_generator = CheckReasonGenerator(self.config)
            self.identity_reveal_maker = IdentityRevealDecisionMaker(self.config)
            
            logger.info("✓ Seer-specific components initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize seer-specific components: {e}")
            # 设置为None以支持降级
            self.check_decision_maker = None
            self.check_priority_calculator = None
            self.check_reason_generator = None
            self.identity_reveal_maker = None
    
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
        """
        if req.message:
            self.memory_dao.append_history(req.message)
        
        my_name = self.memory_dao.get_my_name()
        message = str(req.message or "")
        
        # 检查是否是遗言阶段
        if "last words" in message.lower() or "遗言" in message:
            return self._generate_last_words()
        
        # 正常讨论阶段 - 使用父类的LLM生成方法
        checked_players = self.memory_dao.get_checked_players()
        context = self._build_context()
        
        prompt = format_prompt(DESC_PROMPT, {
            "name": my_name,
            "checked_players": checked_players,
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[SEER DISCUSS] Generated speech (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
        """
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        context = self._build_context()
        
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "name": my_name,
            "checked_players": checked_players,
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[SEER LAST WORDS] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    
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
        """
        处理警长竞选发言（使用父类的LLM生成方法）
        
        Args:
            req: 竞选发言请求
            
        Returns:
            AgentResp: 竞选发言内容
        """
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        context = self._build_context()
        
        prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
            "name": my_name,
            "checked_players": checked_players,
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[SEER SHERIFF SPEECH] Generated (length: {len(result)})")
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
        """
        处理警长PK发言（使用父类的LLM生成方法）
        
        Args:
            req: PK发言请求
            
        Returns:
            AgentResp: PK发言内容
        """
        my_name = self.memory_dao.get_my_name()
        checked_players = self.memory_dao.get_checked_players()
        context = self._build_context()
        
        # 识别对手
        opponent = "Unknown"
        game_state = self.memory_dao.get_game_state()
        if game_state.get('fake_seer_name'):
            opponent = game_state['fake_seer_name']
        
        prompt = format_prompt(SHERIFF_PK_PROMPT, {
            "name": my_name,
            "opponent": opponent,
            "checked_players": checked_players,
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[SEER SHERIFF PK] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
