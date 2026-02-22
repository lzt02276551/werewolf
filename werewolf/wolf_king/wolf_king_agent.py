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
    STATUS_SHERIFF,
    STATUS_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_wolf_agent import BaseWolfAgent
from werewolf.wolf_king.config import WolfKingConfig
from werewolf.wolf_king.prompt import (
    DESC_PROMPT, SHERIFF_SPEECH_PROMPT, SHERIFF_PK_PROMPT,
    WOLF_SPEECH_PROMPT, SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT, LAST_WORDS_PROMPT,
    VOTE_PROMPT, KILL_PROMPT, SHOOT_SKILL_PROMPT,
    SHERIFF_ELECTION_PROMPT, SHERIFF_VOTE_PROMPT
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
    
    def __init__(self, model_name: str = None, analysis_model_name: str = None):
        """
        初始化Wolf King Agent
        
        Args:
            model_name: LLM模型名称（可选）
                       如果不提供，将从环境变量 MODEL_NAME 读取
                       如果环境变量也没有，默认使用 "deepseek-chat"
            analysis_model_name: 分析模型名称（可选，已废弃，使用环境变量 DETECTION_MODEL_NAME）
        """
        # 如果没有提供model_name，从环境变量读取
        if model_name is None:
            import os
            model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
            logger.info(f"Using model from environment: {model_name}")
        
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
        
        # 根据配置的优先级策略选择目标（算法建议）
        algorithm_target = self._select_shoot_target_by_priority(non_teammates)
        
        # 使用狼王专用开枪提示词进行确认
        my_name = self.memory.load_variable("name") or ""
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHOOT_SKILL_PROMPT, {
            "history": "\n".join(history[-20:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "algorithm_suggestion": algorithm_target,
            "choices": ", ".join(candidates)
        })
        
        # 使用较低温度确保决策稳定
        llm_target = self._llm_generate(prompt, temperature=0.2)
        llm_target = llm_target.strip()
        
        # 验证LLM输出
        if "Do Not Shoot" in llm_target or "do not shoot" in llm_target.lower():
            logger.info("[WOLF KING] LLM decided not to shoot")
            return ""
        
        # 验证玩家名称
        final_target = self._validate_player_name(llm_target, candidates)
        if final_target not in non_teammates:
            # 如果LLM输出无效，使用算法建议
            final_target = algorithm_target
        
        if final_target:
            threat_levels = self.memory.load_variable("threat_levels") or {}
            identified_roles = self.memory.load_variable("identified_roles") or {}
            threat = threat_levels.get(final_target, self.DEFAULT_THREAT_LEVEL)
            role = identified_roles.get(final_target, "unknown")
            logger.info(f"[WOLF KING SHOOT] Algorithm: {algorithm_target}, LLM: {llm_target}, Final: {final_target} (threat: {threat}, role: {role})")
        
        return final_target
    
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
        感知阶段（狼王不需要特殊处理）
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        # 狼王的所有逻辑都在interact阶段处理
        return AgentResp(success=True, result=None, errMsg=None)
    
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
            # 狼王特有：处理开枪和击杀
            if status == STATUS_SKILL:
                return self._handle_skill(req)
            
            # 狼王特有：处理开枪（被淘汰时）
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
                STATUS_SHERIFF: self._handle_sheriff_general,
                STATUS_RESULT: self._handle_result,
            }
            
            handler = handler_map.get(status)
            if handler:
                return handler(req)
            else:
                logger.warning(f"[INTERACT] Unknown status: {status}")
                return AgentResp(success=True, result=None, errMsg=None)
            
        except Exception as e:
            logger.error(f"[WOLF KING INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(success=True, result=None, errMsg=None)
    
    def _handle_shoot(self, req: AgentReq) -> AgentResp:
        """处理开枪（狼王特有）"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 从req.message中解析候选人
        if req.message:
            candidates = [name.strip() for name in req.message.split(",") 
                         if name.strip() and name.strip() != my_name and name.strip() not in teammates]
        else:
            candidates = []
        
        # 检查是否可以开枪
        if not self.memory.load_variable("can_shoot"):
            logger.info("[WOLF KING] Cannot shoot (ability already used)")
            return AgentResp(success=True, result="Do Not Shoot", skillTargetPlayer="Do Not Shoot", errMsg=None)
        
        if not candidates:
            logger.warning("[WOLF KING] No shoot candidates provided")
            return AgentResp(success=True, result="Do Not Shoot", skillTargetPlayer="Do Not Shoot", errMsg=None)
        
        # 决定是否开枪
        target = self._make_shoot_decision(candidates)
        
        if not target:
            logger.info("[WOLF KING] Decided not to shoot")
            return AgentResp(success=True, result="Do Not Shoot", skillTargetPlayer="Do Not Shoot", errMsg=None)
        
        # 验证目标
        target = self._validate_player_name(target, candidates)
        
        # 标记已使用技能
        self.memory.set_variable("can_shoot", False)
        
        logger.info(f"[WOLF KING SHOOT] Final target: {target}")
        return AgentResp(success=True, result=target, skillTargetPlayer=target, errMsg=None)
    
    def _handle_skill(self, req: AgentReq) -> AgentResp:
        """
        处理技能（STATUS_SKILL）
        
        根据req.name和req.message判断是击杀还是开枪：
        - 如果name包含"shoot"或message包含"last words"/"遗言"，则是开枪
        - 否则是击杀
        
        这与模板的处理方式一致
        """
        message = req.message or ""
        name = req.name or ""
        
        # 判断是否是开枪技能
        is_shoot = (
            "shoot" in name.lower() or 
            "last words" in message.lower() or 
            "遗言" in message or
            "请发表最后的遗言" in message or
            "please give your final words" in message.lower()
        )
        
        if is_shoot:
            # 开枪技能
            return self._handle_shoot_skill(req)
        else:
            # 击杀技能
            return self._handle_kill(req)
    
    def _handle_shoot_skill(self, req: AgentReq) -> AgentResp:
        """
        处理开枪技能（STATUS_SKILL中的开枪）
        
        与模板一致的处理方式
        """
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 检查是否可以开枪
        can_shoot = self.memory.load_variable("can_shoot")
        if not can_shoot:
            logger.info("[WOLF KING] Cannot shoot (ability already used)")
            return AgentResp(success=True, result="don't shoot", skillTargetPlayer=None, errMsg=None)
        
        # 从message中解析候选人（移除"请发表最后的遗言"等文本）
        message = req.message or ""
        message = message.replace("please give your final words", "").replace("请发表最后的遗言", "")
        
        candidates = [name.strip() for name in message.split(",")
                     if name.strip() and name.strip() != my_name and name.strip() not in teammates]
        
        if not candidates:
            logger.warning("[WOLF KING] No shoot candidates provided")
            return AgentResp(success=True, result="don't shoot", skillTargetPlayer=None, errMsg=None)
        
        # 决定是否开枪
        target = self._make_shoot_decision(candidates)
        
        if not target:
            logger.info("[WOLF KING] Decided not to shoot")
            return AgentResp(success=True, result="don't shoot", skillTargetPlayer=None, errMsg=None)
        
        # 验证目标
        target = self._validate_player_name(target, candidates)
        
        # 标记已使用技能
        self.memory.set_variable("can_shoot", False)
        
        logger.info(f"[WOLF KING SHOOT SKILL] Final target: {target}")
        
        # 返回格式与模板一致
        return AgentResp(
            success=True, 
            result=target, 
            skillTargetPlayer=None if target in ["don't shoot", "不开枪"] else target, 
            errMsg=None
        )
    
    # ==================== 从WolfAgent复制的方法 ====================
    
    def _handle_start(self, req: AgentReq) -> AgentResp:
        """处理游戏开始"""
        my_name = req.name
        self.memory.set_variable("name", my_name)
        
        # 从message中提取队友信息
        if req.message:
            teammates = [name.strip() for name in req.message.split(",") if name.strip()]
            self.memory.set_variable("teammates", teammates)
            logger.info(f"[WOLF KING] Game started, I am {my_name}, teammates: {teammates}")
        else:
            logger.info(f"[WOLF KING] Game started, I am {my_name}, no teammates info yet")
        
        return AgentResp(success=True, result=None, errMsg=None)
    
    def _handle_wolf_speech(self, req: AgentReq) -> AgentResp:
        """处理狼人内部发言"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(WOLF_SPEECH_PROMPT, {
            "history": "\n".join(history[-20:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates)
        })
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(success=True, result=speech, errMsg=None)
    
    def _handle_discussion(self, req: AgentReq) -> AgentResp:
        """处理讨论阶段"""
        my_name = self.memory.load_variable("name") or ""
        
        # 处理当前消息
        if req.message and req.name and req.name != my_name:
            self._process_player_message(req.message, req.name)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        teammates = self.memory.load_variable("teammates") or []
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(DESC_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "shoot_info": shoot_info
        })
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(success=True, result=speech, errMsg=None)
    
    def _handle_vote(self, req: AgentReq) -> AgentResp:
        """处理投票"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 从req.message中解析候选人
        if req.message:
            candidates = [name.strip() for name in req.message.split(",") 
                         if name.strip() and name.strip() != my_name]
        else:
            candidates = []
        
        if not candidates:
            logger.warning("[WOLF KING VOTE] No valid candidates")
            return AgentResp(success=True, result="No.1", errMsg=None)
        
        # 使用基类的决策逻辑获取算法建议
        target = self._make_vote_decision(candidates)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        # 使用狼王专用投票提示词进行确认
        prompt = format_prompt(VOTE_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "algorithm_suggestion": target,
            "choices": ", ".join(candidates)
        })
        
        # 使用较低温度确保决策稳定
        llm_target = self._llm_generate(prompt, temperature=0.2)
        llm_target = llm_target.strip()
        
        # 验证LLM输出，如果无效则使用算法建议
        final_target = self._validate_player_name(llm_target, candidates)
        if final_target not in candidates:
            final_target = target
        
        logger.info(f"[WOLF KING VOTE] Algorithm: {target}, LLM: {llm_target}, Final: {final_target}")
        return AgentResp(success=True, result=final_target, errMsg=None)
    
    def _handle_vote_result(self, req: AgentReq) -> AgentResp:
        """处理投票结果"""
        return AgentResp(success=True, result=None, errMsg=None)
    
    def _handle_kill(self, req: AgentReq) -> AgentResp:
        """处理击杀"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 从req.message中解析候选人
        if req.message:
            candidates = [name.strip() for name in req.message.split(",") 
                         if name.strip() and name.strip() != my_name and name.strip() not in teammates]
        else:
            candidates = []
        
        if not candidates:
            logger.warning("[WOLF KING KILL] No valid candidates")
            return AgentResp(success=True, result="No.1", skillTargetPlayer="No.1", errMsg=None)
        
        # 使用基类的决策逻辑获取算法建议
        target = self._make_kill_decision(candidates)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        # 使用狼王专用击杀提示词进行确认
        prompt = format_prompt(KILL_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "algorithm_suggestion": target,
            "choices": ", ".join(candidates)
        })
        
        # 使用较低温度确保决策稳定
        llm_target = self._llm_generate(prompt, temperature=0.2)
        llm_target = llm_target.strip()
        
        # 验证LLM输出，如果无效则使用算法建议
        final_target = self._validate_player_name(llm_target, candidates)
        if final_target not in candidates:
            final_target = target
        
        logger.info(f"[WOLF KING KILL] Algorithm: {target}, LLM: {llm_target}, Final: {final_target}")
        return AgentResp(success=True, result=final_target, skillTargetPlayer=final_target, errMsg=None)
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """处理警长选举"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHERIFF_ELECTION_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "shoot_info": shoot_info
        })
        
        decision = self._llm_generate(prompt, temperature=0.3)
        decision = decision.strip()
        
        # 验证输出
        if "Run for Sheriff" in decision or "run" in decision.lower():
            result = "Run for Sheriff"
            logger.info("[WOLF KING] Decided to run for Sheriff")
        else:
            result = "Do Not Run"
            logger.info("[WOLF KING] Decided not to run for Sheriff")
        
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """处理警长竞选发言"""
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "shoot_info": shoot_info
        })
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(success=True, result=speech, errMsg=None)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """处理警长投票"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        
        # 从req.message中解析候选人
        if req.message:
            candidates = [name.strip() for name in req.message.split(",") 
                         if name.strip() and name.strip() != my_name]
        else:
            candidates = []
        
        if not candidates:
            logger.warning("[WOLF KING] No sheriff vote candidates")
            return AgentResp(success=True, result="No.1", errMsg=None)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        # 使用狼王专用警长投票提示词
        prompt = format_prompt(SHERIFF_VOTE_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "choices": ", ".join(candidates)
        })
        
        target = self._llm_generate(prompt, temperature=0.3)
        target = target.strip()
        
        # 验证输出
        target = self._validate_player_name(target, candidates)
        
        logger.info(f"[WOLF KING] Sheriff vote: {target}")
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _handle_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """处理警长发言顺序选择"""
        my_name = self.memory.load_variable("name") or ""
        teammates = self.memory.load_variable("teammates") or []
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHERIFF_SPEECH_ORDER_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates)
        })
        
        order = self._llm_generate(prompt, temperature=0.3)
        order = order.strip()
        
        # 验证输出
        if "Counter-clockwise" in order or "counter" in order.lower():
            result = "Counter-clockwise"
        else:
            result = "Clockwise"
        
        logger.info(f"[WOLF KING] Speech order: {result}")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """处理警长PK发言"""
        my_name = self.memory.load_variable("name") or ""
        teammates = self.memory.load_variable("teammates") or []
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHERIFF_PK_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "shoot_info": shoot_info
        })
        
        speech = self._llm_generate(prompt)
        speech = self._truncate_output(speech, self.config.MAX_SPEECH_LENGTH)
        
        return AgentResp(success=True, result=speech, errMsg=None)
    
    def _handle_result(self, req: AgentReq) -> AgentResp:
        """处理游戏结果"""
        # 优先从req.message中判断
        message = req.message or ""
        
        # 如果message中没有结果信息，再从历史记录中查找
        if "Wolf faction wins" not in message and "Good faction wins" not in message:
            history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
            history_text = "\n".join(history)
            combined_text = history_text + " " + message
        else:
            combined_text = message
        
        result = "win" if "Wolf faction wins" in combined_text else "lose"
        self.memory.set_variable("game_result", result)
        
        logger.info(f"[WOLF KING] Game ended: {result}")
        return AgentResp(success=True, result=None, errMsg=None)
    
    def _handle_sheriff_general(self, req: AgentReq) -> AgentResp:
        """
        处理警长相关的通用状态
        
        根据消息内容判断具体是什么操作：
        - 警长转移
        - 遗言
        - 其他警长相关操作
        """
        # 检查req.message来判断是否是警长转移
        message = (req.message or "").lower()
        
        # 如果message包含候选人列表（逗号分隔），则是警长转移
        if "," in req.message:
            return self._handle_sheriff_transfer(req)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        history_text = "\n".join(history[-5:]).lower() if history else ""
        
        # 判断是否是警长转移
        if "transfer" in history_text or "badge" in history_text or "警徽" in history_text:
            return self._handle_sheriff_transfer(req)
        
        # 判断是否是遗言
        if "last words" in history_text or "遗言" in history_text or "final" in history_text:
            return self._handle_last_words(req)
        
        # 默认返回成功
        logger.info("[WOLF KING] Sheriff general status, no specific action")
        return AgentResp(success=True, result=None, errMsg=None)
    
    def _handle_sheriff_transfer(self, req: AgentReq) -> AgentResp:
        """处理警长转移（狼王被淘汰时）"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        # 从req.message中解析候选人
        if req.message:
            candidates = [name.strip() for name in req.message.split(",") 
                         if name.strip() and name.strip() != my_name]
        else:
            candidates = []
        
        if not candidates:
            logger.warning("[WOLF KING] No sheriff transfer candidates")
            return AgentResp(success=True, result="Destroy", errMsg=None)
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(SHERIFF_TRANSFER_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "shoot_info": shoot_info,
            "choices": ", ".join(candidates)
        })
        
        target = self._llm_generate(prompt, temperature=0.3)
        target = target.strip()
        
        # 验证输出
        if "Destroy" in target or "destroy" in target.lower():
            result = "Destroy"
            logger.info("[WOLF KING] Destroying sheriff badge")
        else:
            # 验证玩家名称
            result = self._validate_player_name(target, candidates)
            logger.info(f"[WOLF KING] Transferring sheriff badge to: {result}")
        
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _handle_last_words(self, req: AgentReq) -> AgentResp:
        """处理遗言（狼王被淘汰后的最后发言）"""
        teammates = self.memory.load_variable("teammates") or []
        my_name = self.memory.load_variable("name") or ""
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        # 从内存获取历史记录
        history = self.memory.load_history() if hasattr(self.memory, 'load_history') else []
        
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "history": "\n".join(history[-30:]) if history else "",
            "name": my_name,
            "teammates": ", ".join(teammates),
            "shoot_info": shoot_info
        })
        
        speech = self._llm_generate(prompt)
        # 遗言长度控制：600-1000字符
        max_length = 1000
        if len(speech) > max_length:
            speech = speech[:max_length - 3] + "..."
        
        logger.info(f"[WOLF KING] Last words length: {len(speech)}")
        return AgentResp(success=True, result=speech, errMsg=None)
