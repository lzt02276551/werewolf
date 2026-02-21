# -*- coding: utf-8 -*-
"""
守卫代理人（重构版 - 继承BaseGoodAgent）

继承BaseGoodAgent获得所有共享功能：
- 双模型架构（分析+生成）
- LLM检测系统
- ML增强
- 信任分析
- 投票决策

守卫特有功能：
- 守护技能
- 守护目标选择
- 守护历史管理
"""

from agent_build_sdk.model.roles import ROLE_GUARD
from agent_build_sdk.model.werewolf_model import (
    AgentResp, AgentReq,
    STATUS_SKILL, STATUS_DISCUSS, STATUS_VOTE
)
from agent_build_sdk.utils.logger import logger
from agent_build_sdk.sdk.agent import format_prompt
from werewolf.core.base_good_agent import BaseGoodAgent
from werewolf.guard.prompt import DESC_PROMPT, LAST_WORDS_PROMPT
from werewolf.guard.decision_makers import GuardDecisionMaker
from typing import List, Optional

# 导入守卫特有模块
from werewolf.guard.config import GuardConfig


class GuardAgent(BaseGoodAgent):
    """
    守卫代理人（重构版 - 继承BaseGoodAgent）
    
    继承BaseGoodAgent获得所有共享功能：
    - 双模型架构（分析+生成）
    - LLM检测系统
    - ML增强
    - 信任分析
    - 投票决策
    
    守卫特有功能：
    - 守护技能
    - 守护目标选择
    - 守护历史管理
    """

    def __init__(self, model_name: str):
        """
        初始化守卫代理
        
        Args:
            model_name: LLM模型名称
        """
        # 调用父类初始化（自动初始化所有共享组件）
        super().__init__(ROLE_GUARD, model_name=model_name)
        
        # 重新设置守卫配置（覆盖父类的BaseGoodConfig）
        self.config = GuardConfig()
        
        logger.info("✓ GuardAgent initialized with BaseGoodAgent")
    
    def _init_memory_variables(self):
        """
        初始化守卫特有的内存变量
        
        继承父类的内存变量，并添加守卫特有的：
        - 守护历史
        - 守护策略
        """
        # 调用父类方法初始化共享变量
        super()._init_memory_variables()
        
        # 添加守卫特有变量
        # 守护历史
        self.memory.set_variable("guarded_players", [])
        self.memory.set_variable("last_guarded", None)
        self.memory.set_variable("guard_history", {})
        
        # 游戏进度
        self.memory.set_variable("current_night", 0)
        
        # 守护策略
        role_specific = getattr(self.config, 'role_specific', {})
        self.memory.set_variable("first_night_strategy", 
                                role_specific.get('first_night_strategy', 'empty_guard'))
        self.memory.set_variable("protect_same_twice", 
                                role_specific.get('protect_same_twice', False))
        
        logger.info("✓ Guard-specific memory variables initialized")
    
    def _init_specific_components(self):
        """
        初始化守卫特有组件
        
        守卫特有组件：
        - GuardDecisionMaker: 守护决策器
        """
        try:
            self.guard_decision_maker = GuardDecisionMaker(self.config)
            
            # 设置依赖（如果trust_manager已初始化）
            if hasattr(self, 'trust_manager') and self.trust_manager:
                self.guard_decision_maker.set_dependencies(self.memory, self.trust_manager)
                logger.info("✓ Guard decision maker dependencies set")
            else:
                logger.warning("⚠ Trust manager not available, guard decision maker will use fallback logic")
            
            logger.info("✓ Guard-specific components initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize guard-specific components: {e}")
            self.guard_decision_maker = None
    
    # ==================== 守卫特有方法 ====================
    
    def perceive(self, req: AgentReq):
        """
        处理游戏事件（重写父类方法以添加守卫特有处理）
        
        Args:
            req: 游戏事件请求
        """
        # 守卫特有事件：技能使用（守护）
        if req.status == STATUS_SKILL:
            return self._handle_guard_skill(req)
        else:
            # 其他事件使用父类处理
            return super().perceive(req)
    
    def _handle_guard_skill(self, req: AgentReq) -> AgentResp:
        """
        处理守护技能
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 守护目标
        """
        target = self._make_guard_decision(req.message.split(",") if req.message else [])
        
        # 更新守护历史
        current_night = self.memory.load_variable("current_night") or 0
        self.memory.set_variable("current_night", current_night + 1)
        self.memory.set_variable("last_guarded", target)
        
        guarded_players = self.memory.load_variable("guarded_players") or []
        if target and target not in guarded_players:
            guarded_players.append(target)
            self.memory.set_variable("guarded_players", guarded_players)
        
        logger.info(f"[GUARD SKILL] Night {current_night + 1}: Guarding {target}")
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _make_guard_decision(self, candidates: List[str]) -> str:
        """
        守护决策
        
        Args:
            candidates: 候选玩家列表
            
        Returns:
            守护目标
        """
        if not candidates:
            return ""
        
        try:
            # 使用决策器
            if self.guard_decision_maker:
                # 构建上下文
                my_name = self.memory.load_variable("name")
                current_night = self.memory.load_variable("current_night") or 0
                last_guarded = self.memory.load_variable("last_guarded")
                
                context = {
                    'my_name': my_name,
                    'night_count': current_night + 1,  # 下一个夜晚
                    'last_guarded': last_guarded,
                    'alive_players': set(self.memory.load_variable("alive_players") or []),
                    'dead_players': set(self.memory.load_variable("dead_players") or []),
                    'trust_scores': self.memory.load_variable("trust_scores") or {},
                    'speech_history': self.memory.load_variable("speech_history") or {},
                    'voting_history': self.memory.load_variable("voting_history") or {},
                }
                
                target, reason, confidence = self.guard_decision_maker.decide(
                    candidates, 
                    context
                )
                logger.info(f"[GUARD DECISION] Target: {target}, Reason: {reason}, Confidence: {confidence}")
                return target
            
            # 降级：选择第一个候选人
            return candidates[0]
            
        except Exception as e:
            logger.error(f"Error in guard decision: {e}")
            return candidates[0] if candidates else ""
    
    # ==================== 交互方法（使用父类方法）====================
    
    def interact(self, req: AgentReq) -> AgentResp:
        """
        处理交互请求（使用父类方法简化）
        
        Args:
            req: 交互请求
            
        Returns:
            AgentResp: 交互响应
        """
        logger.info(f"[GUARD INTERACT] Status: {req.status}")
        
        if req.status == STATUS_DISCUSS:
            return self._interact_discuss(req)
        elif req.status == STATUS_VOTE:
            return self._interact_vote(req)
        else:
            # 未知状态，返回默认响应
            logger.warning(f"[GUARD INTERACT] Unknown status: {req.status}, returning default response")
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
        
        # 构建prompt参数
        try:
            # 获取基本信息
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            dead_players = self.memory.load_variable("dead_players") or []
            current_day = self.memory.load_variable("day_count") or 1
            
            # 获取守卫信息
            guarded_players = self.memory.load_variable("guarded_players") or []
            guard_info = f"Guarded history: {', '.join(guarded_players) if guarded_players else 'None yet'}"
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 获取注入攻击嫌疑人
            injection_suspects = self.memory.load_variable("injection_suspects") or {}
            injection_str = ", ".join([f"{p}({t})" for p, t in injection_suspects.items()]) if injection_suspects else "None"
            
            # 获取虚假引用
            false_quotations = self.memory.load_variable("false_quotations") or []
            false_quote_str = ", ".join([f"{fq.get('accuser', '?')}" for fq in false_quotations if isinstance(fq, dict)]) if false_quotations else "None"
            
            # 获取状态矛盾
            status_contradictions = self.memory.load_variable("player_status_claims") or {}
            status_str = ", ".join([p for p, v in status_contradictions.items() if v]) if status_contradictions else "None"
            
            # 确定游戏阶段
            if current_day <= 3:
                game_phase = "Early Game"
                phase_strategy = "Stay hidden, analyze from villager perspective"
            elif current_day <= 6:
                game_phase = "Mid Game"
                phase_strategy = "Consider hinting at guard ability if situation is clear"
            else:
                game_phase = "Late Game"
                phase_strategy = "Expose identity and share guard history to lead good team"
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(DESC_PROMPT, {
                "history": history_str,
                "name": my_name,
                "guard_info": guard_info,
                "game_phase": game_phase,
                "current_day": current_day,
                "alive_count": len(alive_players),
                "trust_summary": trust_summary,
                "injection_suspects": injection_str,
                "false_quotations": false_quote_str,
                "status_contradictions": status_str,
                "phase_strategy": phase_strategy
            })
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD DISCUSS] Generated speech (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD DISCUSS] Error generating speech: {e}")
            # 降级：返回简单发言
            return AgentResp(success=True, result="I'm analyzing the situation carefully.", errMsg=None)
    
    def _format_history(self, speech_history: dict, max_entries: int = 10) -> str:
        """
        格式化发言历史
        
        Args:
            speech_history: 发言历史字典
            max_entries: 最大条目数
            
        Returns:
            格式化的历史字符串
        """
        if not speech_history or not isinstance(speech_history, dict):
            return "No speech history available."
        
        entries = []
        for player, speeches in speech_history.items():
            if isinstance(speeches, list) and speeches:
                # 只取最近的发言
                recent = speeches[-2:] if len(speeches) > 2 else speeches
                for speech in recent:
                    if speech and isinstance(speech, str):
                        entries.append(f"{player}: {speech[:100]}...")
        
        # 限制条目数
        if len(entries) > max_entries:
            entries = entries[-max_entries:]
        
        return "\n".join(entries) if entries else "No recent speeches."
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
        """
        try:
            # 获取基本信息
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取守卫历史
            guard_history = self.memory.load_variable("guard_history") or {}
            guarded_players = self.memory.load_variable("guarded_players") or []
            
            # 格式化守卫历史
            guard_history_detail = []
            for night, target in guard_history.items():
                if target:
                    guard_history_detail.append(f"Night {night}: Guarded {target}")
                else:
                    guard_history_detail.append(f"Night {night}: Empty guard")
            
            guard_history_str = "\n".join(guard_history_detail) if guard_history_detail else "No guard history recorded"
            guard_summary = f"Guarded {len(guarded_players)} different players" if guarded_players else "No successful guards"
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(LAST_WORDS_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "guard_history_summary": guard_summary,
                "guard_history_detail": guard_history_str
            })
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD LAST WORDS] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD LAST WORDS] Error generating: {e}")
            # 降级：返回简单遗言
            return AgentResp(success=True, result="I am the Guard. Trust the good players and vote out the wolves.", errMsg=None)
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        my_name = self.memory.load_variable("name")
        
        # 获取候选人列表并过滤掉自己
        if req.message:
            choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
        else:
            choices = []
        
        if not choices:
            logger.warning("[GUARD VOTE] No valid choices available")
            return AgentResp(success=True, result="", errMsg=None)
        
        # 使用父类的投票决策方法（自动融合ML）
        target = self._make_vote_decision(choices)
        
        logger.info(f"[GUARD VOTE] Target: {target}")
        return AgentResp(success=True, result=target, errMsg=None)
