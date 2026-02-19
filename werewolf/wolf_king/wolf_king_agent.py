# -*- coding: utf-8 -*-
"""
Wolf King Agent - 狼王代理人（企业级重构版）

职责:
1. 继承Wolf Agent的所有功能
2. 添加狼王特有的开枪技能
3. 管理开枪状态和决策

依赖:
- werewolf.wolf.wolf_agent.WolfAgent (继承基础功能)
- werewolf.wolf_king.config.WolfKingConfig
"""

from typing import Dict, List, Optional, Any
import re

from agent_build_sdk.model.roles import ROLE_WOLF_KING
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_HUNTER, STATUS_HUNTER_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt

# 导入Wolf Agent作为基类
from werewolf.wolf.wolf_agent import WolfAgent
from werewolf.wolf_king.config import WolfKingConfig
from werewolf.wolf_king.prompt import (
    DESC_PROMPT, SHOOT_SKILL_PROMPT, SHERIFF_SPEECH_PROMPT,
    SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT
)


class WolfKingAgent(WolfAgent):
    """
    Wolf King Agent - 狼王代理人
    
    继承WolfAgent的所有功能，添加开枪技能
    
    狼王特性:
    - 被投票出局时可以开枪带走一名玩家
    - 被毒死不能开枪
    - 拥有Wolf的所有能力（击杀、投票、发言等）
    
    Attributes:
        config: 狼王配置对象
        can_shoot: 是否可以开枪
    """
    
    def __init__(self, model_name: str, analysis_model_name: str = None):
        """
        初始化Wolf King Agent（双模型架构）
        
        Args:
            model_name: LLM模型名称（用于生成发言）
            analysis_model_name: 分析模型名称（用于分析消息），如果为None则从环境变量读取DETECTION_MODEL_NAME
        """
        # 注意：由于SDK限制，需要先设置role再调用super().__init__
        self._role = ROLE_WOLF_KING
        
        # 调用父类初始化（会初始化为ROLE_WOLF，并支持双模型）
        super().__init__(model_name, analysis_model_name)
        
        # 覆盖为狼王角色
        self.role = ROLE_WOLF_KING
        
        # 使用狼王配置替换狼人配置
        self.config = WolfKingConfig()
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Invalid WolfKing config: {e}")
            raise
        
        # 初始化狼王特有状态
        self._initialize_wolf_king_state()
        
        logger.info("✓ WolfKingAgent initialized successfully (Dual Model Architecture)")
        logger.info(f"  - Analysis model: {self.analysis_model_name}")
        logger.info(f"  - Generation model: {self.generation_model_name}")
    
    def _initialize_wolf_king_state(self) -> None:
        """
        初始化狼王特有状态
        
        设置开枪能力标志
        """
        self.memory.set_variable("can_shoot", True)
        logger.debug("Wolf King shooting ability initialized")
    
    # ==================== 狼王特有决策方法 ====================
    
    def _make_shoot_decision(self, candidates: List[str]) -> str:
        """
        开枪决策（狼王特有）
        
        策略：优先射杀威胁最高的好人玩家
        使用威胁评估和角色识别进行决策
        
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
        
        teammates = self.memory_dao.get_teammates()
        # 过滤掉队友
        non_teammates = [c for c in candidates if c not in teammates]
        
        if not non_teammates:
            logger.info("[WOLF KING] No valid shoot targets (all teammates)")
            return ""
        
        # 根据配置的优先级策略选择目标（使用威胁评估和角色识别）
        target = self._select_shoot_target_by_priority(non_teammates)
        
        if target:
            # 记录威胁等级和角色信息
            threat_levels = self.memory_dao.get_threat_levels()
            identified_roles = self.memory_dao.get_identified_roles()
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
            return candidates[0]  # 简单选第一个
        else:
            logger.warning(f"Unknown shoot priority: {priority}, using high_threat")
            return self._select_highest_threat_target(candidates)
    
    def _select_highest_threat_target(self, candidates: List[str]) -> str:
        """
        选择威胁最高的目标
        
        Args:
            candidates: 候选人列表
            
        Returns:
            威胁最高的玩家名称
        """
        threat_levels = self.memory_dao.get_threat_levels()
        identified_roles = self.memory_dao.get_identified_roles()
        
        # 计算每个候选人的威胁分数
        scores = {}
        for candidate in candidates:
            base_threat = threat_levels.get(candidate, self.DEFAULT_THREAT_LEVEL)
            role = identified_roles.get(candidate, "unknown")
            
            # 角色加成
            role_bonus = self._get_role_threat_bonus_for_shoot(role)
            final_score = min(100, base_threat + role_bonus)
            scores[candidate] = final_score
        
        # 选择分数最高的
        target = max(scores.items(), key=lambda x: x[1])[0]
        score = scores[target]
        
        logger.debug(f"[SHOOT] Highest threat target: {target} (score: {score:.1f})")
        return target
    
    def _select_god_role_target(self, candidates: List[str]) -> str:
        """
        优先选择神职角色目标
        
        Args:
            candidates: 候选人列表
            
        Returns:
            神职角色玩家名称，如果没有则返回威胁最高的
        """
        identified_roles = self.memory_dao.get_identified_roles()
        
        # 神职角色优先级
        god_roles_priority = ["seer", "likely_seer", "witch", "guard"]
        
        # 查找神职角色
        for role in god_roles_priority:
            for candidate in candidates:
                if identified_roles.get(candidate) == role:
                    logger.debug(f"[SHOOT] God role target: {candidate} ({role})")
                    return candidate
        
        # 如果没有找到神职，选择威胁最高的
        logger.debug("[SHOOT] No god role found, selecting highest threat")
        return self._select_highest_threat_target(candidates)
    
    def _get_role_threat_bonus_for_shoot(self, role: str) -> int:
        """
        获取角色威胁加成（开枪专用）
        
        开枪时的威胁评估可能与击杀不同
        
        Args:
            role: 角色类型
            
        Returns:
            威胁加成分数
        """
        # 开枪时优先考虑神职角色
        role_bonuses = {
            "seer": 40,  # 预言家最高优先级
            "likely_seer": 35,
            "witch": 35,  # 女巫高优先级
            "guard": 30,  # 守卫高优先级
            "strong_villager": 20,
            "hunter": 0,  # 猎人不射（会反击）
        }
        return role_bonuses.get(role, 0)
    
    # ==================== 覆盖父类方法以添加狼王特性 ====================
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段（覆盖以添加开枪状态信息）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        # 处理其他玩家的发言（继承自父类）
        my_name = self.memory_dao.get_my_name()
        for msg in req.history:
            if msg.startswith("No.") and ":" in msg:
                parts = msg.split(":", 1)
                if len(parts) == 2:
                    player_name = parts[0].strip()
                    message = parts[1].strip()
                    if player_name != my_name:
                        self._process_player_message(message, player_name)
        
        # 生成发言（使用狼王专用提示词）
        teammates = self.memory_dao.get_teammates()
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            DESC_PROMPT,
            history="\n".join(req.history[-30:]),
            name=my_name,
            teammates=", ".join(teammates),
            shoot_info=shoot_info
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[WOLF KING DISCUSSION] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
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
            
            # 其他状态调用父类处理
            return super().interact(req)
            
        except Exception as e:
            logger.error(f"[WOLF KING INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(action="", content="")
    
    def _handle_shoot(self, req: AgentReq) -> AgentResp:
        """
        处理开枪（狼王特有）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
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
    
    # ==================== 覆盖发言方法以使用狼王提示词 ====================
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选发言（使用狼王提示词）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            SHERIFF_SPEECH_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name(),
            shoot_info=shoot_info
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[WOLF KING SHERIFF_SPEECH] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK发言（使用狼王提示词）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(
            SHERIFF_PK_PROMPT,
            history="\n".join(req.history[-30:]),
            name=self.memory_dao.get_my_name(),
            shoot_info=shoot_info
        )
        
        speech = self.llm_call(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        logger.debug(f"[WOLF KING SHERIFF_PK] Generated speech length: {len(speech)}")
        return AgentResp(action="speak", content=speech)
