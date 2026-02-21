# -*- coding: utf-8 -*-
"""
女巫代理人（重构版 - 继承BaseGoodAgent）

继承BaseGoodAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统
- ML增强
- 信任分析
- 投票决策

女巫特有功能：
- 解药使用决策
- 毒药使用决策
- 药品状态管理
"""

from agent_build_sdk.model.roles import ROLE_WITCH
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_SKILL, STATUS_DISCUSS, STATUS_VOTE
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_good_agent import BaseGoodAgent
from werewolf.witch.prompt import DESC_PROMPT, LAST_WORDS_PROMPT
from typing import Dict, List, Tuple, Optional
import re

# 导入女巫特有模块
from werewolf.witch.config import WitchConfig
from werewolf.witch.base_components import WitchMemoryDAO
from werewolf.witch.decision_engine import WitchDecisionEngine


class WitchAgent(BaseGoodAgent):
    """
    女巫代理人（重构版 - 继承BaseGoodAgent）
    
    继承BaseGoodAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统
    - ML增强
    - 信任分析
    - 投票决策
    
    女巫特有功能：
    - 解药使用决策
    - 毒药使用决策
    - 药品状态管理
    """

    def __init__(self, model_name: str, analysis_model_name: Optional[str] = None):
        """
        初始化女巫代理
        
        Args:
            model_name: LLM模型名称
            analysis_model_name: 分析模型名称（可选，用于向后兼容）
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_WITCH, model_name=model_name)
        
        # 重新设置女巫配置（覆盖父类的BaseGoodConfig）
        self.config = WitchConfig()
        
        # 初始化DAO
        self.memory_dao = WitchMemoryDAO(self.memory)
        
        # 初始化决策引擎
        self.decision_engine = WitchDecisionEngine(self.config, self.memory_dao)
        
        logger.info("✓ WitchAgent initialized with BaseGoodAgent")
    
    def _init_memory_variables(self):
        """
        初始化女巫特有的内存变量
        
        继承父类的内存变量，并添加女巫特有的：
        - 药品状态（解药、毒药）
        - 药品使用历史
        - 首夜策略
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加女巫特有变量
        # 药品状态
        self.memory.set_variable("has_poison", True)
        self.memory.set_variable("has_antidote", True)
        
        # 药品使用历史
        self.memory.set_variable("saved_players", [])
        self.memory.set_variable("poisoned_players", [])
        self.memory.set_variable("killed_history", [])
        
        # 游戏进度
        self.memory.set_variable("current_night", 0)
        self.memory.set_variable("current_day", 0)
        
        # 其他信息
        self.memory.set_variable("wolves_eliminated", 0)
        self.memory.set_variable("good_players_lost", 0)
        self.memory.set_variable("first_night_strategy", 
                                getattr(self.config, 'DEFAULT_FIRST_NIGHT_STRATEGY', 'always_save'))
        
        logger.info("✓ Witch-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化女巫特有组件
        
        女巫特有组件：
        - WitchDecisionEngine: 药品使用决策引擎
        """
        # 决策引擎已在 __init__ 中初始化
        logger.info("✓ Witch-specific components initialized")
    
    # ==================== 女巫特有方法 ====================
    
    def perceive(self, req: AgentReq):
        """
        处理游戏事件（重写父类方法以添加女巫特有处理）
        
        Args:
            req: 游戏事件请求
        """
        # 女巫特有事件：技能使用（解药/毒药）
        if req.status == STATUS_SKILL:
            return self._handle_skill(req)
        else:
            # 其他事件使用父类处理
            return super().perceive(req)
    
    def _handle_skill(self, req: AgentReq) -> AgentResp:
        """
        处理技能使用（解药/毒药决策）
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 技能使用响应
        """
        action, target = self._make_skill_decision(req)
        
        logger.info(f"[WITCH SKILL] Action: {action}, Target: {target}")
        return AgentResp(success=True, result=f"{action}:{target}", errMsg=None)
    
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
            
            # 从请求中提取被杀玩家
            victim = self._extract_killed_player(req)
            
            # 检查是否是自己被杀
            my_name = self.memory_dao.get_my_name()
            if victim == my_name:
                logger.info(f"[SKILL] Night {current_night}: Witch was killed, checking self-save strategy")
                # 根据配置决定是否自救
                if self._should_self_save(current_night):
                    if self.memory_dao.get_has_antidote():
                        self.memory_dao.set_has_antidote(False)
                        self.memory_dao.add_saved_player(victim)
                        logger.info(f"[SKILL] Night {current_night}: SELF-SAVE")
                        return "antidote", victim
            
            # 解药决策（救其他人）
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
    
    def _extract_killed_player(self, req: AgentReq) -> Optional[str]:
        """
        从请求中提取被杀玩家
        
        Args:
            req: 请求对象
            
        Returns:
            被杀玩家名称，未找到返回None
        """
        try:
            # 优先从message中提取
            if req.message:
                msg = str(req.message)
                if "was killed" in msg or "died" in msg or "被杀" in msg:
                    match = re.search(r'No\.(\d+)', msg)
                    if match:
                        victim = f"No.{match.group(1)}"
                        logger.info(f"[EXTRACT] Found victim from message: {victim}")
                        return victim
            
            # 从历史中提取
            if req.history:
                for msg in reversed(req.history[-10:]):
                    if "was killed" in msg or "died" in msg or "被杀" in msg:
                        match = re.search(r'No\.(\d+)', msg)
                        if match:
                            victim = f"No.{match.group(1)}"
                            logger.info(f"[EXTRACT] Found victim from history: {victim}")
                            return victim
            
            logger.warning("[EXTRACT] No victim found in message or history")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting killed player: {e}")
            return None
    
    def _should_self_save(self, current_night: int) -> bool:
        """
        决定是否自救
        
        Args:
            current_night: 当前夜晚数
            
        Returns:
            是否应该自救
        """
        # 第一夜通常自救
        if current_night == 1:
            return True
        
        # 后期根据局势判断
        # 可以添加更复杂的逻辑，例如：
        # - 如果好人阵营处于劣势，优先自救
        # - 如果已经确定多个狼人，可以不自救
        wolves_eliminated = self.memory_dao.get_wolves_eliminated()
        good_players_lost = self.memory_dao.get_good_players_lost()
        
        # 简单策略：如果好人损失较多，自救
        if good_players_lost > wolves_eliminated + 1:
            return True
        
        return False
    
    # ==================== 交互方法（使用父类方法）====================
    
    def interact(self, req: AgentReq) -> AgentResp:
            """
            处理交互请求（使用父类方法简化）

            Args:
                req: 交互请求

            Returns:
                AgentResp: 交互响应
            """
            logger.info(f"[WITCH INTERACT] Status: {req.status}")

            if req.status == STATUS_SKILL:
                return self._handle_skill(req)
            elif req.status == STATUS_DISCUSS:
                return self._interact_discuss(req)
            elif req.status == STATUS_VOTE:
                return self._interact_vote(req)
            else:
                # 未知状态，返回默认响应
                logger.warning(f"[WITCH INTERACT] Unknown status: {req.status}, returning default response")
                return AgentResp(success=True, result="", errMsg=None)

    
    def _interact_discuss(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段的发言（使用父类的LLM生成方法）
        
        Args:
            req: 讨论请求
            
        Returns:
            AgentResp: 发言内容
        """
        # 检查是否是遗言阶段
        message = str(req.message or "")
        if "last words" in message.lower() or "遗言" in message:
            return self._generate_last_words()
        
        # 使用父类的LLM生成方法
        context = self._build_context()
        prompt = format_prompt(DESC_PROMPT, {
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH DISCUSS] Generated speech (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
        """
        context = self._build_context()
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "history": context
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH LAST WORDS] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]
        
        # 使用父类的投票决策方法（自动融合ML）
        target = self._make_vote_decision(choices)
        
        logger.info(f"[WITCH VOTE] Target: {target}")
        return AgentResp(success=True, result=target, errMsg=None)
