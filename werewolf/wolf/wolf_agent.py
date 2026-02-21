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

from typing import List, Optional

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
    SHERIFF_PK_PROMPT, LAST_WORDS_PROMPT, SHERIFF_TRANSFER_PROMPT,
    VOTE_PROMPT, KILL_PROMPT, SHERIFF_ELECTION_PROMPT,
    SHERIFF_VOTE_PROMPT, SHERIFF_SPEECH_ORDER_PROMPT
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

    def __init__(self, model_name: Optional[str] = None, analysis_model_name: Optional[str] = None):
        """
        初始化Wolf Agent
        
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
                
                try:
                    prompt = format_prompt(
                        DESC_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                except Exception as e:
                    logger.error(f"[DISCUSS] LLM生成失败，使用后备发言: {e}")
                    # 后备方案：生成简单的发言
                    result = "I'm analyzing the situation carefully. Based on the information so far, I believe we should focus on finding suspicious behaviors."
                
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
                
                # 使用提示词进行投票决策
                target = self._make_vote_with_prompt(choices, teammates, my_name)
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
                
                try:
                    prompt = format_prompt(
                        WOLF_SPEECH_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                except Exception as e:
                    logger.error(f"[WOLF_SPEECH] LLM生成失败，使用后备发言: {e}")
                    # 后备方案：生成简单的建议
                    result = "I suggest we target the most suspicious player. Let's coordinate our votes carefully."
                
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
                
                # 使用提示词进行击杀决策
                target = self._make_kill_with_prompt(choices, teammates, my_name)
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
                
                try:
                    # 使用提示词进行警长竞选决策
                    prompt = format_prompt(
                        SHERIFF_ELECTION_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    # 解析结果
                    if "Run for Sheriff" in result or "竞选" in result:
                        result = "Run for Sheriff"
                    else:
                        result = "Do Not Run"
                except Exception as e:
                    logger.warning(f"[SHERIFF_ELECTION] LLM决策失败，使用后备方案: {e}")
                    # 后备方案：默认不竞选（保守策略）
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
                
                try:
                    prompt = format_prompt(
                        SHERIFF_SPEECH_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                except Exception as e:
                    logger.error(f"[SHERIFF_SPEECH] LLM生成失败，使用后备发言: {e}")
                    # 后备方案：生成简单的竞选发言
                    result = "I'm running for Sheriff because I believe I can help lead the village to victory. I will analyze carefully and make fair decisions."
                
                logger.info(f"[SHERIFF_SPEECH] Generated: {result[:50]}...")
                return AgentResp(success=True, result=result, errMsg=None)
            
            elif status == STATUS_SHERIFF_PK:
                # 警长PK发言
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                try:
                    prompt = format_prompt(
                        SHERIFF_PK_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
                except Exception as e:
                    logger.error(f"[SHERIFF_PK] LLM生成失败，使用后备发言: {e}")
                    # 后备方案：生成简单的PK发言
                    result = "I believe my analysis is more thorough and my judgment is sound. I ask for your trust and support."
                
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
                
                try:
                    # 使用提示词进行警长投票决策
                    prompt = format_prompt(
                        SHERIFF_VOTE_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates),
                        choices=", ".join(choices)
                    )
                    
                    result = self._llm_generate(prompt)
                    target = self._validate_player_name(result, choices)
                except Exception as e:
                    logger.warning(f"[SHERIFF_VOTE] LLM决策失败，使用后备方案: {e}")
                    # 后备方案：优先投队友
                    teammate_candidates = [c for c in choices if c in teammates]
                    if teammate_candidates:
                        target = teammate_candidates[0]
                    else:
                        target = choices[0]
                
                logger.info(f"[SHERIFF_VOTE] Voting for: {target}")
                return AgentResp(success=True, result=target, errMsg=None)
            
            elif status == STATUS_SHERIFF_SPEECH_ORDER:
                # 警长发言顺序
                try:
                    teammates = self.memory.load_variable("teammates")
                except KeyError:
                    teammates = []
                
                my_name = self.memory.load_variable("name") or ""
                
                try:
                    # 使用提示词进行发言顺序决策
                    prompt = format_prompt(
                        SHERIFF_SPEECH_ORDER_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates)
                    )
                    
                    result = self._llm_generate(prompt)
                    # 解析结果
                    if "Counter-clockwise" in result or "逆时针" in result or "小号" in result:
                        result = "Counter-clockwise"
                    else:
                        result = "Clockwise"
                except Exception as e:
                    logger.warning(f"[SHERIFF_SPEECH_ORDER] LLM决策失败，使用后备方案: {e}")
                    # 后备方案：默认顺时针
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
                              if name != my_name]
                else:
                    choices = []
                
                if not choices:
                    logger.warning("[SHERIFF_TRANSFER] No valid choices")
                    return AgentResp(success=True, result="No.1", errMsg=None)
                
                try:
                    # 使用提示词进行警徽转移决策
                    prompt = format_prompt(
                        SHERIFF_TRANSFER_PROMPT,
                        history="\n".join(self.memory.load_history()),
                        name=my_name,
                        teammates=", ".join(teammates),
                        choices=", ".join(choices)
                    )
                    
                    result = self._llm_generate(prompt)
                    
                    # 解析结果
                    if "Destroy" in result or "撕毁" in result:
                        target = "Destroy"
                    else:
                        target = self._validate_player_name(result, choices)
                except Exception as e:
                    logger.warning(f"[SHERIFF_TRANSFER] LLM决策失败，使用后备方案: {e}")
                    # 后备方案：转给第一个非队友
                    non_teammates = [c for c in choices if c not in teammates]
                    if non_teammates:
                        target = non_teammates[0]
                    else:
                        target = choices[0]
                
                logger.info(f"[SHERIFF_TRANSFER] Decision: {target}")
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
    
    def _make_kill_with_prompt(self, choices: List[str], teammates: List[str], my_name: str) -> str:
        """
        使用提示词进行击杀决策（带后备方案）
        
        Args:
            choices: 候选人列表
            teammates: 队友列表
            my_name: 自己的名称
            
        Returns:
            目标玩家名称
        """
        try:
            # 获取威胁等级和角色识别信息
            threat_levels = self.memory.load_variable("threat_levels") or {}
            identified_roles = self.memory.load_variable("identified_roles") or {}
            
            # 构建候选人排名信息
            ranked_info = []
            for candidate in choices:
                threat = threat_levels.get(candidate, 50)
                role = identified_roles.get(candidate, "unknown")
                ranked_info.append(f"{candidate}: Threat={threat}, Role={role}")
            
            ranked_candidates = "\n".join(ranked_info) if ranked_info else "No threat analysis available"
            
            prompt = format_prompt(
                KILL_PROMPT,
                history="\n".join(self.memory.load_history()),
                name=my_name,
                teammates=", ".join(teammates),
                choices=", ".join(choices),
                ranked_candidates=ranked_candidates
            )
            
            result = self._llm_generate(prompt)
            return result.strip()
        except Exception as e:
            logger.warning(f"[KILL] LLM决策失败，使用后备方案: {e}")
            # 使用基类的决策方法作为后备
            return self._make_kill_decision(choices)
    
    def _make_vote_with_prompt(self, choices: List[str], teammates: List[str], my_name: str) -> str:
        """
        使用提示词进行投票决策（带后备方案）
        
        Args:
            choices: 候选人列表
            teammates: 队友列表
            my_name: 自己的名称
            
        Returns:
            投票目标名称
        """
        try:
            # 获取威胁等级和可突破值信息
            threat_levels = self.memory.load_variable("threat_levels") or {}
            breakthrough_values = self.memory.load_variable("breakthrough_values") or {}
            
            # 构建候选人排名信息
            ranked_info = []
            for candidate in choices:
                threat = threat_levels.get(candidate, 50)
                breakthrough = breakthrough_values.get(candidate, 50)
                is_teammate = "TEAMMATE" if candidate in teammates else "NON-TEAMMATE"
                ranked_info.append(f"{candidate}: Threat={threat}, Breakthrough={breakthrough}, Status={is_teammate}")
            
            ranked_candidates = "\n".join(ranked_info) if ranked_info else "No analysis available"
            
            prompt = format_prompt(
                VOTE_PROMPT,
                history="\n".join(self.memory.load_history()),
                name=my_name,
                teammates=", ".join(teammates),
                choices=", ".join(choices),
                ranked_candidates=ranked_candidates
            )
            
            result = self._llm_generate(prompt)
            return result.strip()
        except Exception as e:
            logger.warning(f"[VOTE] LLM决策失败，使用后备方案: {e}")
            # 使用基类的决策方法作为后备
            return self._make_vote_decision(choices)

