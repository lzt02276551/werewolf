# -*- coding: utf-8 -*-
"""
Wolf King Agent - 狼王代理人（重构版 - 继承BaseWolfAgent）

继承BaseWolfAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统（检测好人注入）
- 队友智商评估
- 威胁等级分析
- 卖队友战术
- ML增强
- 击杀决策
- 投票决策

狼王特有功能：
- 开枪技能
"""

from typing import Dict, List, Optional, Any
from agent_build_sdk.model.roles import ROLE_WOLF_KING
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_HUNTER, STATUS_HUNTER_RESULT,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_DAY, STATUS_DISCUSS,
    STATUS_VOTE, STATUS_VOTE_RESULT, STATUS_SKILL,
    STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_PK, STATUS_SHERIFF_VOTE, STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_wolf_agent import BaseWolfAgent
from werewolf.wolf_king.config import WolfKingConfig
from werewolf.wolf_king.prompt import (
    DESC_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_PK_PROMPT
)


class WolfKingAgent(BaseWolfAgent):
    """
    Wolf King Agent - 狼王代理人（重构版 - 继承BaseWolfAgent）
    
    继承BaseWolfAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统（检测好人注入）
    - 队友智商评估
    - 威胁等级分析
    - 卖队友战术
    - ML增强
    - 击杀决策
    - 投票决策
    
    狼王特有功能：
    - 开枪技能
    """
    
    def __init__(self, model_name: str, analysis_model_name: str = None):
        """
        初始化Wolf King Agent
        
        Args:
            model_name: LLM模型名称（用于生成发言）
            analysis_model_name: 分析模型名称（用于分析消息）
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_WOLF_KING, model_name, analysis_model_name)
        
        # 重新设置狼王配置（覆盖父类的BaseWolfConfig）
        self.config = WolfKingConfig()
        
        logger.info("✓ WolfKingAgent initialized with BaseWolfAgent")
    
    def _init_memory_variables(self):
        """
        初始化狼王特有的内存变量
        
        继承父类的内存变量，并添加狼王特有的：
        - 开枪状态
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加狼王特有变量
        self.memory.set_variable("can_shoot", True)
        
        logger.info("✓ Wolf King-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化狼王特有组件
        
        狼王当前没有特有组件，开枪决策使用父类的威胁评估
        """
        pass
    
    # ==================== 狼王特有方法 ====================
    
    def _make_shoot_decision(self, candidates: List[str]) -> str:
        """
        开枪决策（狼王特有）
        
        策略：优先射杀威胁最高的好人玩家
        
        Args:
            candidates: 候选人列表
            
        Returns:
            目标玩家名称，如果不开枪则返回空字符串
        """
        # 检查是否可以开枪
        if not self.memory.load_variable("can_shoot"):
            logger.info("[WOLF KING] Cannot shoot (ability already used)")
            return ""
        
        if not candidates:
            logger.warning("[WOLF KING] No shoot candidates provided")
            return ""
        
        teammates = self.memory.load_variable("teammates") or []
        # 过滤掉队友
        non_teammates = [c for c in candidates if c not in teammates]
        
        if not non_teammates:
            logger.info("[WOLF KING] No valid shoot targets (all teammates)")
            return ""
        
        # 根据配置的优先级策略选择目标
        target = self._select_shoot_target_by_priority(non_teammates)
        
        if target:
            threat_levels = self.memory.load_variable("threat_levels") or {}
            identified_roles = self.memory.load_variable("identified_roles") or {}
            threat = threat_levels.get(target, self.DEFAULT_THREAT_LEVEL)
            role = identified_roles.get(target, "unknown")
            logger.info(f"[WOLF KING SHOOT] Selected target: {target} (threat: {threat}, role: {role})")
        
        return target
    
    def _select_shoot_target_by_priority(self, candidates: List[str]) -> str:
        """
        根据优先级策略选择开枪目标
        
        Args:
            candidates: 候选人列表（已过滤队友）
            
        Returns:
            目标玩家名称
        """
        if not candidates:
            return ""
        
        priority = self.config.shoot_priority
        
        if priority == self.config.SHOOT_PRIORITY_HIGH_THREAT:
            return self._select_highest_threat_target(candidates)
        elif priority == self.config.SHOOT_PRIORITY_GOD_ROLE:
            return self._select_god_role_target(candidates)
        elif priority == self.config.SHOOT_PRIORITY_RANDOM:
            return candidates[0]
        else:
            logger.warning(f"Unknown shoot priority: {priority}, using high_threat")
            return self._select_highest_threat_target(candidates)
    
    def _select_highest_threat_target(self, candidates: List[str]) -> str:
        """选择威胁最高的目标"""
        threat_levels = self.memory.load_variable("threat_levels") or {}
        identified_roles = self.memory.load_variable("identified_roles") or {}
        
        scores = {}
        for candidate in candidates:
            base_threat = threat_levels.get(candidate, self.DEFAULT_THREAT_LEVEL)
            role = identified_roles.get(candidate, "unknown")
            
            # 角色加成
            role_bonus = self._get_role_threat_bonus_for_shoot(role)
            final_score = min(100, base_threat + role_bonus)
            scores[candidate] = final_score
        
        target = max(scores.items(), key=lambda x: x[1])[0]
        logger.debug(f"[SHOOT] Highest threat target: {target} (score: {scores[target]:.1f})")
        return target
    
    def _select_god_role_target(self, candidates: List[str]) -> str:
        """优先选择神职角色目标"""
        identified_roles = self.memory.load_variable("identified_roles") or {}
        
        # 神职角色优先级
        god_roles_priority = ["seer", "likely_seer", "witch", "guard"]
        
        for role in god_roles_priority:
            for candidate in candidates:
                if identified_roles.get(candidate) == role:
                    logger.debug(f"[SHOOT] God role target: {candidate} ({role})")
                    return candidate
        
        # 如果没有找到神职，选择威胁最高的
        logger.debug("[SHOOT] No god role found, selecting highest threat")
        return self._select_highest_threat_target(candidates)
    
    def _get_role_threat_bonus_for_shoot(self, role: str) -> int:
        """获取角色威胁加成（开枪专用）"""
        role_bonuses = {
            "seer": 40,
            "likely_seer": 35,
            "witch": 35,
            "guard": 30,
            "strong_villager": 20,
            "hunter": 0,  # 猎人不射（会反击）
        }
        return role_bonuses.get(role, 0)
    
    # ==================== 覆盖父类方法以添加狼王特性 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """
        感知阶段（覆盖以添加开枪处理）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF KING PERCEIVE] Status: {status}")
        
        try:
            if status == STATUS_SKILL:
                return self._handle_kill(req)
            
            return AgentResp(action="", content="")
            
        except Exception as e:
            logger.error(f"[PERCEIVE] Error: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        交互阶段（覆盖以添加开枪处理）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF KING INTERACT] Status: {status}")
        
        try:
            # 狼王特有：处理开枪
            if status == STATUS_HUNTER or status == STATUS_HUNTER_RESULT:
                return self._handle_shoot(req)
            
            # 其他状态的处理
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
            logger.error(f"[WOLF KING INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    def _handle_shoot(self, req: AgentReq) -> AgentResp:
        """处理开枪（狼王特有）"""
        candidates = req.choices
        
        # 检查是否可以开枪
        if not self.memory.load_variable("can_shoot"):
            logger.info("[WOLF KING] Cannot shoot (ability already used)")
            return AgentResp(action="skill", content="Do Not Shoot")
        
        if not candidates:
            logger.warning("[WOLF KING] No shoot candidates provided")
            return AgentResp(action="skill", content="Do Not Shoot")
        
        # 决定是否开枪
        target = self._make_shoot_decision(candidates)
        
        if not target:
            logger.info("[WOLF KING] Decided not to shoot")
            return AgentResp(action="skill", content="Do Not Shoot")
        
        # 验证目标
        target = self._validate_player_name(target, candidates)
        
        # 标记已使用技能
        self.memory.set_variable("can_shoot", False)
        
        logger.info(f"[WOLF KING SHOOT] Final target: {target}")
        return AgentResp(action="skill", content=target)
    
    # ==================== 从WolfAgent复制的方法 ====================
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """处理游戏开始"""
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        teammates = self._extract_teammates(req.history)
        self.memory.set_variable("teammates", teammates)
        
        logger.info(f"[WOLF KING] Game started, I am {my_name}, teammates: {teammates}")
        return AgentResp(action="", content="")
    
    def _handle_wolf_speech(self, req: AgentReq) -> AgentResp:
        """处理狼人内部发言"""
        from werewolf.wolf.prompt import WOLF_SPEECH_PROMPT
        
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        prompt = format_prompt(
            WOLF_SPEECH_PROMPT,
            history="\n".join(req.history[-20:]),
            name=my_name,
            teammates=", ".join(teammates)
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段"""
        my_name = self.memory.load_variable("name") or ""
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        teammates = self.memory.load_variable("teammates") or []
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            teammates=", ".join(teammates),
            shoot_info=shoot_info
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票"""
        candidates = req.choices
        if not candidates:
            return AgentResp(action="vote", content="No.1")
        
        target = self._make_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        return AgentResp(action="", content="")
    
    def _handle_kill(self, req: AgentReq) -> AgentResp:
        """处理击杀"""
        candidates = req.choices
        if not candidates:
            return AgentResp(action="skill", content="No.1")
        
        target = self._make_kill_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        return AgentResp(action="skill", content=target)
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举"""
        return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            shoot_info=shoot_info
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票"""
        candidates = req.choices
        if not candidates:
            return AgentResp(action="vote", content="No.1")
        
        teammates = self.memory.load_variable("teammates") or []
        teammate_candidates = [c for c in candidates if c in teammates]
        
        if teammate_candidates:
            target = teammate_candidates[0]
        else:
            threat_levels = self.memory.load_variable("threat_levels") or {}
            scores = {c: threat_levels.get(c, self.DEFAULT_THREAT_LEVEL) for c in candidates}
            target = min(scores.items(), key=lambda x: x[1])[0]
        
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            shoot_info=shoot_info
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果"""
        history_text = "\n".join(req.history)
        result = "win" if "Wolf faction wins" in history_text else "lose"
        self.memory.set_variable("game_result", result)
        
        logger.info(f"[WOLF KING] Game ended: {result}")
        return AgentResp(action="", content="")
