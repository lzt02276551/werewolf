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

from agent_build_sdk.model.roles import ROLE_WOLF
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_START, STATUS_WOLF_SPEECH, STATUS_VOTE_RESULT,
    STATUS_SKILL, STATUS_SKILL_RESULT, STATUS_NIGHT_INFO,
    STATUS_DAY, STATUS_DISCUSS, STATUS_VOTE, STATUS_NIGHT,
    STATUS_RESULT, STATUS_SHERIFF_ELECTION, STATUS_SHERIFF_SPEECH,
    STATUS_SHERIFF_PK, STATUS_SHERIFF_VOTE, STATUS_SHERIFF_SPEECH_ORDER,
    STATUS_SHERIFF, STATUS_HUNTER, STATUS_HUNTER_RESULT
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
        感知阶段 - 接收游戏信息并更新记忆
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF PERCEIVE] Status: {status}")
        
        try:
            if status == STATUS_START:
                # 游戏开始 - 初始化记忆
                self.memory.clear()
                self.memory.set_variable("name", req.name)
                self.memory.set_variable("teammates", [])
                self.memory.append_history(f"主持人: 你好，你的角色是【狼人】，你是 {req.name}")
                
                if req.message:
                    # 接收队友信息
                    teammates = req.message.split(",")
                    self.memory.set_variable("teammates", teammates)
                    self.memory.append_history(f"主持人: 你的狼队友是: {req.message}")
                    logger.info(f"[WOLF] Teammates: {teammates}")
            
            elif status == STATUS_NIGHT:
                # 夜晚开始
                self.memory.append_history("主持人: 天黑请闭眼")
            
            elif status == STATUS_WOLF_SPEECH:
                # 狼人内部交流
                if req.name:
                    self.memory.append_history(f"狼人 {req.name} 说: {req.message}")
                else:
                    self.memory.append_history("主持人: 狼人请睁眼，确认彼此身份，并选择击杀目标")
            
            elif status == STATUS_SKILL_RESULT:
                # 击杀结果
                self.memory.append_history(f"主持人: 狼人，你们今晚选择击杀的目标是: {req.name}")
            
            elif status == STATUS_NIGHT_INFO:
                # 夜间信息公布
                self.memory.append_history(f"主持人: 天亮了！昨晚的信息是: {req.message}")
            
            elif status == STATUS_DISCUSS:
                # 讨论阶段
                if req.name:
                    # 其他玩家发言
                    self.memory.append_history(req.name + ': ' + req.message)
                else:
                    # 主持人发言
                    self.memory.append_history(f'主持人: 现在进入第{req.round}天')
                    self.memory.append_history('主持人: 各位玩家依次描述自己的信息')
                self.memory.append_history("---------------------------------------------")
            
            elif status == STATUS_VOTE:
                # 投票信息
                self.memory.append_history(f'第{req.round}天. 投票信息: {req.name} 投给了 {req.message}')
            
            elif status == STATUS_VOTE_RESULT:
                # 投票结果
                if req.name:
                    self.memory.append_history(f'主持人: 投票结果是: {req.name} 出局')
                else:
                    self.memory.append_history('主持人: 无人出局')
            
            elif status == STATUS_SHERIFF_ELECTION:
                # 警长竞选
                self.memory.append_history(f"主持人: 竞选警长的玩家有: {req.message}")
            
            elif status == STATUS_SHERIFF_SPEECH:
                # 警长竞选发言
                self.memory.append_history(f"{req.name} (警长竞选发言): {req.message}")
            
            elif status == STATUS_SHERIFF_VOTE:
                # 警长投票
                self.memory.append_history(f"警长投票: {req.name} 投给了 {req.message}")
            
            elif status == STATUS_SHERIFF:
                # 警长结果/转移
                if req.name:
                    self.memory.append_history(f"主持人: 警徽归属: {req.name}")
                    self.memory.set_variable("sheriff", req.name)
                if req.message:
                    self.memory.append_history(req.message)
            
            elif status == STATUS_HUNTER:
                # 猎人/狼王技能
                self.memory.append_history(f"猎人/狼王是: {req.name}，正在发动技能，选择开枪")
            
            elif status == STATUS_HUNTER_RESULT:
                # 猎人/狼王技能结果
                if req.message:
                    self.memory.append_history(f"猎人/狼王是: {req.name}，开枪带走了 {req.message}")
                else:
                    self.memory.append_history(f"猎人/狼王是: {req.name}，没有带走任何人")
            
            elif status == STATUS_SHERIFF_SPEECH_ORDER:
                # 警长发言顺序
                if "Counter-clockwise" in req.message or "小号" in req.message:
                    self.memory.append_history("主持人: 警长选择发言顺序为小号优先")
                else:
                    self.memory.append_history("主持人: 警长选择发言顺序为大号优先")
            
            elif status == STATUS_SHERIFF_PK:
                # 警长PK发言
                self.memory.append_history(f"警长PK发言: {req.name}: {req.message}")
            
            elif status == STATUS_RESULT:
                # 游戏结果
                self.memory.append_history(req.message)
            
            # 对于需要交互的状态，不在这里处理
            return AgentResp(success=True, result=None, errMsg=None)
            
        except Exception as e:
            logger.error(f"[PERCEIVE] Error: {e}", exc_info=True)
            return AgentResp(success=False, result=None, errMsg=str(e))
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        交互阶段 - 需要Agent做出决策和行动
        
        Args:
            req: Agent请求对象
            
        Returns:
            Agent响应对象
        """
        status = req.status
        logger.info(f"[WOLF INTERACT] Status: {status}")
        
        try:
            # 根据状态分发处理
            if status == STATUS_DISCUSS:
                # 讨论发言
                if req.message:
                    self.memory.append_history(req.message)
                
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                prompt = format_prompt(
                    DESC_PROMPT,
                    history="\n".join(self.memory.load_history()),
                    name=my_name,
                    teammates=", ".join(teammates)
                )
                
                result = self._llm_generate(prompt)
                result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                logger.info(f"[DISCUSS] Generated speech: {result[:50]}...")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_VOTE:
                # 投票
                self.memory.append_history('主持人: 现在进入投票环节，请大家指认你认为可能是狼人的玩家')
                
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                # 从req.message中解析候选人
                if req.message:
                    choices = [name for name in req.message.split(",")
                              if name != my_name and name not in teammates]
                else:
                    choices = req.choices or []
                
                if not choices:
                    logger.warning("[VOTE] No valid choices")
                    return AgentResp(success=True, result="No.1", errMsg=None)
                
                # 使用父类的投票决策
                target = self._make_vote_decision(choices)
                target = self._validate_player_name(target, choices)
                
                logger.info(f"[VOTE] Voting for: {target}")
                return AgentResp(success=True, result=target, errMsg=None)
            
            elif status == STATUS_WOLF_SPEECH:
                # 狼人内部交流
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                prompt = format_prompt(
                    WOLF_SPEECH_PROMPT,
                    history="\n".join(self.memory.load_history()),
                    name=my_name,
                    teammates=", ".join(teammates)
                )
                
                result = self._llm_generate(prompt)
                result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                logger.info(f"[WOLF_SPEECH] Generated: {result[:50]}...")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SKILL:
                # 击杀技能
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                # 从req.message中解析候选人
                if req.message:
                    choices = [name for name in req.message.split(",")
                              if name != my_name and name not in teammates]
                else:
                    choices = req.choices or []
                
                if not choices:
                    logger.warning("[KILL] No valid choices")
                    return AgentResp(success=True, result="No.1", skillTargetPlayer="No.1", errMsg=None)
                
                # 使用父类的击杀决策
                target = self._make_kill_decision(choices)
                target = self._validate_player_name(target, choices)
                
                logger.info(f"[KILL] Target: {target}")
                return AgentResp(success=True, result=target, skillTargetPlayer=target, errMsg=None)
            
            elif status == STATUS_SHERIFF_ELECTION:
                # 警长竞选
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                # 简单策略：不竞选
                result = "Do Not Run"
                logger.info(f"[SHERIFF_ELECTION] Decision: {result}")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SHERIFF_SPEECH:
                # 警长竞选发言
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                prompt = format_prompt(
                    SHERIFF_SPEECH_PROMPT,
                    history="\n".join(self.memory.load_history()),
                    name=my_name,
                    teammates=", ".join(teammates)
                )
                
                result = self._llm_generate(prompt)
                result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                logger.info(f"[SHERIFF_SPEECH] Generated: {result[:50]}...")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SHERIFF_PK:
                # 警长PK发言
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                prompt = format_prompt(
                    SHERIFF_PK_PROMPT,
                    history="\n".join(self.memory.load_history()),
                    name=my_name,
                    teammates=", ".join(teammates)
                )
                
                result = self._llm_generate(prompt)
                result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                logger.info(f"[SHERIFF_PK] Generated: {result[:50]}...")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SHERIFF_VOTE:
                # 警长投票
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                # 从req.message中解析候选人
                if req.message:
                    choices = [name for name in req.message.split(",")]
                else:
                    choices = req.choices or []
                
                if not choices:
                    logger.warning("[SHERIFF_VOTE] No valid choices")
                    return AgentResp(success=True, result="No.1", errMsg=None)
                
                # 优先投队友
                teammate_candidates = [c for c in choices if c in teammates]
                if teammate_candidates:
                    target = teammate_candidates[0]
                    logger.info(f"[SHERIFF_VOTE] Voting for teammate: {target}")
                else:
                    # 否则投第一个
                    target = choices[0]
                    logger.info(f"[SHERIFF_VOTE] Voting for: {target}")
                
                return AgentResp(success=True, result=target, errMsg=None)
            
            elif status == STATUS_SHERIFF_SPEECH_ORDER:
                # 警长发言顺序
                result = "Clockwise"
                logger.info(f"[SHERIFF_SPEECH_ORDER] Choosing: {result}")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SHERIFF:
                # 警长转移警徽
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                # 从req.message中解析候选人
                if req.message:
                    choices = [name for name in req.message.split(",")
                              if name != my_name and name not in teammates]
                else:
                    choices = []
                
                if not choices:
                    logger.warning("[SHERIFF_TRANSFER] No valid choices")
                    return AgentResp(success=True, result="No.1", errMsg=None)
                
                # 简单策略：转给第一个非队友
                target = choices[0]
                logger.info(f"[SHERIFF_TRANSFER] Transferring to: {target}")
                return AgentResp(success=True, result=target, errMsg=None)
            
            # 默认返回
            return AgentResp(success=True, result=None, errMsg=None)
            
        except Exception as e:
            logger.error(f"[INTERACT] Error in status {status}: {e}", exc_info=True)
            return AgentResp(success=False, result=None, errMsg=str(e))
    
    # ==================== 辅助方法（继承自BaseWolfAgent） ====================
    # _llm_generate() - LLM生成
    # _truncate_output() - 输出截断
    # _make_vote_decision() - 投票决策
    # _make_kill_decision() - 击杀决策
    # _validate_player_name() - 验证玩家名称
    # _extract_teammates() - 提取队友信息
    # _process_player_message() - 处理玩家消息（LLM检测）

