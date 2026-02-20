# -*- coding: utf-8 -*-
"""
猎人代理人（重构版 - 继承BaseGoodAgent）

继承BaseGoodAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统
- ML增强
- 信任分析
- 投票决策

猎人特有功能：
- 开枪技能
- 开枪目标选择
- 复仇模式
"""

from agent_build_sdk.model.roles import ROLE_HUNTER
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_SKILL, STATUS_DISCUSS, STATUS_VOTE, STATUS_RESULT
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_good_agent import BaseGoodAgent
from werewolf.hunter.prompt import DESC_PROMPT, LAST_WORDS_PROMPT
from werewolf.hunter.decision_makers import ShootDecisionMaker
from werewolf.hunter.analyzers import (
    ThreatLevelAnalyzer, WolfProbabilityCalculator,
    TrustScoreAnalyzer, VotingPatternAnalyzer, SpeechQualityAnalyzer
)
from typing import List, Optional

# 导入猎人特有模块
from werewolf.hunter.config import HunterConfig
from werewolf.common.utils import CacheManager


class HunterAgent(BaseGoodAgent):
    """
    猎人代理人（重构版 - 继承BaseGoodAgent）
    
    继承BaseGoodAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统
    - ML增强
    - 信任分析
    - 投票决策
    
    猎人特有功能：
    - 开枪技能
    - 开枪目标选择
    - 复仇模式
    """

    def __init__(self, model_name: str):
        """
        初始化猎人代理
        
        Args:
            model_name: LLM模型名称
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_HUNTER, model_name=model_name)
        
        # 重新设置猎人配置（覆盖父类的BaseGoodConfig）
        self.config = HunterConfig()
        
        logger.info("✓ HunterAgent initialized with BaseGoodAgent")
    
    def _init_memory_variables(self):
        """
        初始化猎人特有的内存变量
        
        继承父类的内存变量，并添加猎人特有的：
        - 开枪状态
        - 开枪历史
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加猎人特有变量
        self.memory.set_variable("can_shoot", True)
        self.memory.set_variable("shot_used", False)
        self.memory.set_variable("shoot_target", None)
        self.memory.set_variable("shoot_history", [])
        
        logger.info("✓ Hunter-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化猎人特有组件
        
        猎人特有组件：
        - ShootDecisionMaker: 开枪决策器
        - ThreatLevelAnalyzer: 威胁等级分析器
        - WolfProbabilityCalculator: 狼人概率计算器
        """
        try:
            # 创建猎人特有的分析器
            from werewolf.hunter.analyzers import MemoryDAO
            
            self.hunter_memory_dao = MemoryDAO(self.memory)
            self.cache_manager = CacheManager()
            
            # 创建猎人特有的分析器（复用父类的基础分析器）
            self.hunter_trust_analyzer = TrustScoreAnalyzer(self.config, self.hunter_memory_dao)
            self.hunter_voting_analyzer = VotingPatternAnalyzer(self.config, self.hunter_memory_dao)
            self.hunter_speech_analyzer = SpeechQualityAnalyzer(self.config, self.hunter_memory_dao)
            
            # 创建猎人特有的高级分析器
            self.threat_analyzer = ThreatLevelAnalyzer(
                self.config, self.hunter_memory_dao, self.cache_manager
            )
            self.wolf_prob_calculator = WolfProbabilityCalculator(
                self.config,
                self.hunter_trust_analyzer,
                self.hunter_voting_analyzer,
                self.hunter_speech_analyzer,
                self.hunter_memory_dao
            )
            
            # 创建开枪决策器
            self.shoot_decision_maker = ShootDecisionMaker(
                self.config,
                self.wolf_prob_calculator,
                self.threat_analyzer,
                self.hunter_memory_dao
            )
            
            logger.info("✓ Hunter-specific components initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize hunter-specific components: {e}")
            self.shoot_decision_maker = None
            self.threat_analyzer = None
            self.wolf_prob_calculator = None
    
    # ==================== 猎人特有方法 ====================
    
    def perceive(self, req: AgentReq) -> AgentResp:
        """
        处理游戏事件（重写父类方法以添加猎人特有处理）
        
        Args:
            req: 游戏事件请求
            
        Returns:
            AgentResp: 响应
        """
        # 猎人特有事件：技能使用（开枪）
        if req.status == STATUS_SKILL:
            return self._handle_shoot_skill(req)
        else:
            # 其他事件使用父类处理
            return super().perceive(req)
    
    def _handle_shoot_skill(self, req: AgentReq) -> AgentResp:
        """
        处理开枪技能
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 开枪目标
        """
        # 检查是否可以开枪
        can_shoot = self.memory.load_variable("can_shoot")
        if not can_shoot:
            logger.info("[HUNTER] Cannot shoot (already used or poisoned)")
            return AgentResp(success=True, result="Do Not Shoot", errMsg=None)
        
        # 获取候选人列表
        candidates = req.choices if hasattr(req, 'choices') else []
        if not candidates and req.message:
            candidates = [c.strip() for c in req.message.split(",") if c.strip()]
        
        # 决定是否开枪
        target = self._make_shoot_decision(candidates)
        
        if target == "Do Not Shoot":
            logger.info("[HUNTER] Decided not to shoot")
            return AgentResp(success=True, result="Do Not Shoot", errMsg=None)
        
        # 验证目标
        target = self._validate_player_name(target, candidates)
        
        # 标记已使用技能
        self.memory.set_variable("can_shoot", False)
        self.memory.set_variable("shot_used", True)
        self.memory.set_variable("shoot_target", target)
        
        # 记录开枪历史
        shoot_history = self.memory.load_variable("shoot_history") or []
        shoot_history.append(target)
        self.memory.set_variable("shoot_history", shoot_history)
        
        logger.info(f"[HUNTER] Shooting: {target}")
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _make_shoot_decision(self, candidates: List[str]) -> str:
        """
        开枪决策
        
        Args:
            candidates: 候选玩家列表
            
        Returns:
            开枪目标（或 "Do Not Shoot"）
        """
        if not candidates:
            return "Do Not Shoot"
        
        try:
            # 使用决策器
            if self.shoot_decision_maker:
                my_name = self.memory.load_variable("name") or ""
                game_state = self.memory.load_variable("game_state") or {}
                current_day = game_state.get("current_day", 1)
                alive_players = self.memory.load_variable("alive_players") or []
                alive_count = len(alive_players)
                
                # 评估游戏阶段
                if current_day <= 2:
                    game_phase = "early"
                elif current_day >= 6:
                    game_phase = "late"
                else:
                    game_phase = "mid"
                
                target, reason, scores = self.shoot_decision_maker.decide(
                    candidates, 
                    my_name,
                    game_phase,
                    current_day,
                    alive_count
                )
                logger.info(f"[SHOOT DECISION] Target: {target}, Reason: {reason}")
                return target
            
            # 降级：不开枪
            return "Do Not Shoot"
            
        except Exception as e:
            logger.error(f"Error in shoot decision: {e}")
            return "Do Not Shoot"
    
    # ==================== 交互方法（使用父类方法）====================
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        处理交互请求（使用父类方法简化）
        
        Args:
            req: 交互请求
            
        Returns:
            AgentResp: 交互响应
        """
        logger.info(f"[HUNTER INTERACT] Status: {req.status}")
        
        if req.status == STATUS_DISCUSS:
            return self._interact_discuss(req)
        elif req.status == STATUS_VOTE:
            return self._interact_vote(req)
        elif req.status == STATUS_RESULT:
            return self._handle_game_result(req)
        else:
            # 其他状态使用父类的默认处理
            return super().interact(req)
    
    def _interact_discuss(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段的发言（使用父类的LLM生成方法）
        
        Args:
            req: 讨论请求
            
        Returns:
            AgentResp: 发言内容
        """
        # 处理其他玩家的发言
        if hasattr(req, 'history') and req.history:
            for msg in req.history:
                if msg.startswith("No.") and ":" in msg:
                    parts = msg.split(":", 1)
                    if len(parts) == 2:
                        player_name = parts[0].strip()
                        message = parts[1].strip()
                        my_name = self.memory.load_variable("name")
                        if player_name != my_name:
                            self._process_player_message(message, player_name)
        
        # 检查是否是遗言阶段
        message = str(req.message or "")
        if "last words" in message.lower() or "遗言" in message:
            return self._generate_last_words()
        
        # 使用父类的LLM生成方法
        context = self._build_context()
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(DESC_PROMPT, {
            "history": "\n".join(req.history) if hasattr(req, 'history') else "",
            "name": self.memory.load_variable("name"),
            "shoot_info": shoot_info
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[HUNTER DISCUSS] Generated speech (length: {len(result)})")
        return AgentResp(action="speak", content=result)
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
        """
        context = self._build_context()
        can_shoot = self.memory.load_variable("can_shoot")
        shoot_info = "can shoot" if can_shoot else "already shot"
        
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "history": context,
            "shoot_info": shoot_info
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[HUNTER LAST WORDS] Generated (length: {len(result)})")
        return AgentResp(action="speak", content=result)
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        my_name = self.memory.load_variable("name")
        
        # 获取候选人列表
        if hasattr(req, 'choices'):
            choices = req.choices
        elif req.message:
            choices = [c.strip() for c in req.message.split(",") if c.strip()]
        else:
            choices = []
        
        # 过滤掉自己
        choices = [name for name in choices if name != my_name]
        
        # 使用父类的投票决策方法（自动融合ML）
        target = self._make_vote_decision(choices)
        
        logger.info(f"[HUNTER VOTE] Target: {target}")
        return AgentResp(action="vote", content=target)
    
    def _handle_game_result(self, req: AgentReq) -> AgentResp:
        """
        处理游戏结果（触发ML训练）
        
        Args:
            req: 游戏结果请求
            
        Returns:
            AgentResp: 空响应
        """
        # 记录游戏结果
        result_message = req.message if hasattr(req, 'message') else ""
        result = "win" if "Good faction wins" in result_message else "lose"
        self.memory.set_variable("game_result", result)
        logger.info(f"[HUNTER] Game ended: {result}")
        
        # 使用父类的游戏结束处理（自动收集数据和训练ML）
        self._handle_game_end(req)
        
        return AgentResp(action="", content="")
