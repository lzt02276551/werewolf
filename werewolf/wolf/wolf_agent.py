# -*- coding: utf-8 -*-
"""
Wolf Agent - 狼人代理人（重构版 - 继承BaseWolfAgent）

继承BaseWolfAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统（检测好人注入）
- 队友智商评估
- 威胁等级分析
- 卖队友战术
- ML增强

狼人特有功能：
- 夜晚击杀决策
- 狼人内部发言
"""

from typing import Dict, List, Optional, Any
from agent_build_sdk.model.roles import ROLE_WOLF
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_VOTE_RESULT,
    STATUS_SKILL, STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE,
    STATUS_RESULT, STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_PK, STATUS_SHERIFF_VOTE, STATUS_SHERIFF_SPEECH_ORDER
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_wolf_agent import BaseWolfAgent
from werewolf.wolf.config import WolfConfig
from werewolf.wolf.prompt import (
    DESC_PROMPT, WOLF_SPEECH_PROMPT, SHERIFF_SPEECH_PROMPT,
    SHERIFF_PK_PROMPT
)


class WolfAgent(BaseWolfAgent):
    """
    Wolf Agent - 狼人代理人（重构版 - 继承BaseWolfAgent）
    
    继承BaseWolfAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统（检测好人注入）
    - 队友智商评估
    - 威胁等级分析
    - 卖队友战术
    - ML增强
    
    狼人特有功能：
    - 夜晚击杀决策
    - 狼人内部发言
    """

    def __init__(self, model_name: str, analysis_model_name: str = None):
        """
        初始化Wolf Agent
        
        Args:
            model_name: LLM模型名称（用于生成发言）
            analysis_model_name: 分析模型名称（用于分析消息）
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_WOLF, model_name, analysis_model_name)
        
        # 重新设置狼人配置（覆盖父类的BaseWolfConfig）
        self.config = WolfConfig()
        
        logger.info("✓ WolfAgent initialized with BaseWolfAgent")
    
    def _init_specific_components(self):
        """
        初始化狼人特有组件
        
        狼人当前没有特有组件，所有功能都在基类中
        """
        pass
    
    # ==================== 主要处理方法 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """
        感知阶段（狼人击杀）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF PERCEIVE] Status: {status}")
        
        try:
            if status == STATUS_SKILL:
                return self._handle_kill(req)
            
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
        logger.info(f"[WOLF INTERACT] Status: {status}")
        
        try:
            # 根据状态分发处理
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
            logger.error(f"[INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    # ==================== 状态处理方法 ====================
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """处理游戏开始"""
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        # 提取队友（使用父类方法）
        teammates = self._extract_teammates(req.history)
        self.memory.set_variable("teammates", teammates)
        
        logger.info(f"[WOLF] Game started, I am {my_name}, teammates: {teammates}")
        return AgentResp(action="", content="")
    
    def _handle_wolf_speech(self, req: AgentReq) -> AgentResp:
        """处理狼人内部发言"""
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
        
        logger.debug(f"[WOLF_SPEECH] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段（使用父类的消息处理）"""
        # 处理其他玩家的发言（使用父类方法）
        my_name = self.memory.load_variable("name") or ""
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        # 生成发言
        teammates = self.memory.load_variable("teammates") or []
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            teammates=", ".join(teammates)
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[DISCUSSION] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票（使用父类的投票决策）"""
        candidates = req.choices
        if not candidates:
            logger.warning("[VOTE] No candidates provided")
            return AgentResp(action="vote", content="No.1")
        
        # 使用父类的投票决策（自动包含卖队友逻辑）
        target = self._make_vote_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        return AgentResp(action="vote", content=target)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        logger.debug("[VOTE_RESULT] Processing vote result")
        return AgentResp(action="", content="")
    
    def _handle_kill(self, req: AgentReq) -> AgentResp:
        """处理击杀（使用父类的击杀决策）"""
        candidates = req.choices
        if not candidates:
            logger.warning("[KILL] No candidates provided")
            return AgentResp(action="skill", content="No.1")
        
        # 使用父类的击杀决策
        target = self._make_kill_decision(candidates)
        target = self._validate_player_name(target, candidates)
        
        logger.info(f"[KILL] Final target: {target}")
        return AgentResp(action="skill", content=target)
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举 - 简单策略：不竞选"""
        logger.info("[SHERIFF_ELECTION] Choosing not to run")
        return AgentResp(action="sheriff_election", content="Do Not Run")
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        my_name = self.memory.load_variable("name") or ""
        
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[SHERIFF_SPEECH] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票 - 优先投队友"""
        candidates = req.choices
        if not candidates:
            logger.warning("[SHERIFF_VOTE] No candidates provided")
            return AgentResp(action="vote", content="No.1")
        
        teammates = self.memory.load_variable("teammates") or []
        
        # 优先投队友
        teammate_candidates = [c for c in candidates if c in teammates]
        if teammate_candidates:
            target = teammate_candidates[0]
            logger.info(f"[SHERIFF_VOTE] Voting for teammate: {target}")
        else:
            # 否则投威胁最低的
            threat_levels = self.memory.load_variable("threat_levels") or {}
            scores = {c: threat_levels.get(c, self.DEFAULT_THREAT_LEVEL) for c in candidates}
            target = min(scores.items(), key=lambda x: x[1])[0]
            logger.info(f"[SHERIFF_VOTE] Voting for lowest threat: {target}")
        
        target = self._validate_player_name(target, candidates)
        return AgentResp(action="vote", content=target)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        logger.info("[SHERIFF_SPEECH_ORDER] Choosing Clockwise")
        return AgentResp(action="speech_order", content="Clockwise")
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        my_name = self.memory.load_variable("name") or ""
        
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name
        )
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[SHERIFF_PK] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果"""
        history_text = "\n".join(req.history)
        result = "win" if "Wolf faction wins" in history_text else "lose"
        self.memory.set_variable("game_result", result)
        
        logger.info(f"[WOLF] Game ended: {result}")
        return AgentResp(action="", content="")
