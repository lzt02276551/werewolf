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
from werewolf.guard.prompt import (
    DESC_PROMPT, 
    LAST_WORDS_PROMPT,
    VOTE_PROMPT,
    SKILL_PROMPT,
    SHERIFF_ELECTION_PROMPT,
    SHERIFF_SPEECH_PROMPT,
    SHERIFF_VOTE_PROMPT,
    SHERIFF_PK_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT
)
from werewolf.guard.decision_makers import GuardDecisionMaker
from typing import List, Optional, Dict, Any

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

    def __init__(self, model_name: str = None):
        """
        初始化守卫代理
        
        Args:
            model_name: LLM模型名称（可选）
                       如果不提供，将从环境变量 MODEL_NAME 读取
                       如果环境变量也没有，默认使用 "deepseek-chat"
        """
        # 如果没有提供model_name，从环境变量读取
        if model_name is None:
            import os
            model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
            logger.info(f"Using model from environment: {model_name}")
        
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
        - RoleEstimator: 角色估计器
        - WolfKillPredictor: 狼人击杀预测器
        - GuardPriorityCalculator: 守卫优先级计算器
        - TrustManager: 信任分数管理器（守卫特有实现）
        
        所有组件必须成功初始化，否则抛出异常
        """
        try:
            from .analyzers import RoleEstimator, WolfKillPredictor, GuardPriorityCalculator
            from .trust_manager import TrustScoreManager
            
            # 初始化守卫特有的信任管理器（覆盖父类的）
            self.trust_manager = TrustScoreManager(self.memory)
            logger.info("✓ Guard-specific trust manager initialized")
            
            # 初始化决策器
            self.guard_decision_maker = GuardDecisionMaker(self.config)
            
            # 初始化分析器
            self.role_estimator = RoleEstimator(self.config)
            self.wolf_kill_predictor = WolfKillPredictor(self.config)
            self.guard_priority_calculator = GuardPriorityCalculator(self.config)
            
            # 设置依赖（必须成功）
            if not hasattr(self, 'trust_manager') or not self.trust_manager:
                raise RuntimeError("Trust manager initialization failed - required for guard functionality")
            
            self.guard_decision_maker.set_dependencies(self.memory, self.trust_manager)
            self.guard_decision_maker.set_analyzers(
                self.role_estimator,
                self.wolf_kill_predictor,
                self.guard_priority_calculator
            )
            logger.info("✓ Guard decision maker with analyzers initialized")
            
            logger.info("✓ Guard-specific components initialized")
            
        except ImportError as e:
            logger.error(f"✗ Failed to import guard-specific components: {e}")
            raise RuntimeError(f"Guard component import failed: {e}") from e
        except Exception as e:
            logger.error(f"✗ Failed to initialize guard-specific components: {e}")
            raise RuntimeError(f"Guard component initialization failed: {e}") from e
    
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
        
        # 处理讨论阶段的消息（包含注入检测、虚假引用检测等）
        if req.status == STATUS_DISCUSS and req.name:
            # 检查是否是遗言阶段（使用统一的遗言检测方法）
            if self._is_last_words_phase(req):
                my_name = self.memory.load_variable("name")
                if req.name == my_name:
                    self.memory.set_variable("giving_last_words", True)
                    logger.info("[LAST WORDS] Guard is being eliminated, preparing final words")
            
            # 使用基类的消息处理方法（包含注入检测、虚假引用检测、消息解析、发言质量评估）
            self._process_player_message(req.message, req.name)
        
        # 其他事件：尝试调用父类处理
        if hasattr(super(), 'perceive'):
            try:
                return super().perceive(req)
            except Exception as e:
                logger.debug(f"Parent perceive failed: {e}")
        
        # 默认响应
        return AgentResp(success=True, result="", errMsg=None)
    
    def _is_last_words_phase(self, req: AgentReq) -> bool:
        """
        统一的遗言阶段检测方法
        
        遗言阶段的特征：
        1. 消息中包含 "last words", "final words", "遗言" 等关键词
        2. 消息中包含 "leaves their last words" 等短语
        3. 玩家名称后跟 "Last Words:" 或 "遗言："
        
        Args:
            req: 游戏事件请求
            
        Returns:
            是否是遗言阶段
        """
        if not req or not req.message:
            return False
        
        message_lower = req.message.lower()
        
        # 关键词检测
        last_words_keywords = [
            "last words", "final words", "遗言",
            "leaves their last words", "leaves his last words", "leaves her last words",
            "'s last words", "最后的话"
        ]
        
        return any(keyword in message_lower for keyword in last_words_keywords)
    
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
        night_number = current_night + 1
        self.memory.set_variable("current_night", night_number)
        self.memory.set_variable("last_guarded", target)
        
        # 更新守护玩家列表（去重）
        guarded_players = self.memory.load_variable("guarded_players") or []
        if target and target not in guarded_players:
            guarded_players.append(target)
            self.memory.set_variable("guarded_players", guarded_players)
        
        # 更新详细守护历史（按夜晚记录）
        guard_history = self.memory.load_variable("guard_history") or {}
        guard_history[night_number] = target if target else "Empty guard"
        self.memory.set_variable("guard_history", guard_history)
        
        logger.info(f"[GUARD SKILL] Night {night_number}: Guarding {target if target else 'Empty guard'}")
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
        
        # 验证决策器已初始化
        if not self.guard_decision_maker:
            raise RuntimeError("Guard decision maker not initialized - cannot make guard decision")
        
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name")
            current_night = self.memory.load_variable("current_night") or 0
            last_guarded = self.memory.load_variable("last_guarded")
            alive_players = self.memory.load_variable("alive_players") or []
            dead_players = self.memory.load_variable("dead_players") or []
            trust_scores = self.memory.load_variable("trust_scores") or {}
            speech_history = self.memory.load_variable("speech_history") or {}
            voting_history = self.memory.load_variable("voting_history") or {}
            sheriff = self.memory.load_variable("sheriff")
            
            context = {
                'my_name': my_name,
                'night_count': current_night + 1,  # 下一个夜晚
                'last_guarded': last_guarded,
                'alive_players': set(alive_players),
                'dead_players': set(dead_players),
                'trust_scores': trust_scores,
                'speech_history': speech_history,
                'voting_history': voting_history,
                'sheriff': sheriff,
                # 传递分析器引用
                'role_checker': self.role_estimator if hasattr(self, 'role_estimator') else None,
                'wolf_predictor': self.wolf_kill_predictor if hasattr(self, 'wolf_kill_predictor') else None,
            }
            
            target, reason, confidence = self.guard_decision_maker.decide(
                candidates, 
                context
            )
            
            # 如果置信度较高，直接返回
            if confidence >= 80:
                logger.info(f"[GUARD DECISION] High confidence ({confidence}): {target} - {reason}")
                return target
            
            # 如果置信度中等，使用LLM确认
            if confidence >= 60:
                logger.info(f"[GUARD DECISION] Medium confidence ({confidence}), using LLM to confirm")
                return self._llm_guard_decision(candidates, target, reason, confidence, context)
            
            # 置信度低，完全使用LLM
            logger.info(f"[GUARD DECISION] Low confidence ({confidence}), using full LLM decision")
            return self._llm_guard_decision(candidates, target, reason, confidence, context)
            
        except Exception as e:
            logger.error(f"Error in guard decision: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Guard decision failed: {e}") from e
    
    def _llm_guard_decision(
        self, 
        candidates: List[str], 
        algo_target: str, 
        algo_reason: str, 
        algo_confidence: int,
        context: Dict[str, Any]
    ) -> str:
        """
        使用LLM进行守护决策（结合算法建议）
        
        Args:
            candidates: 候选人列表
            algo_target: 算法推荐目标
            algo_reason: 算法推荐原因
            algo_confidence: 算法置信度
            context: 决策上下文
            
        Returns:
            守护目标
        """
        try:
            my_name = context.get('my_name', '')
            night_count = context.get('night_count', 0)
            last_guarded = context.get('last_guarded', '')
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                alive_players = context.get('alive_players', set())
                trust_summary = self.trust_manager.get_summary(alive_players, top_n=8)
            
            # 构建算法建议
            algorithm_suggestion = f"""Algorithm Recommendation:
Target: {algo_target if algo_target else "Empty guard"}
Reason: {algo_reason}
Confidence: {algo_confidence}%

The algorithm has analyzed trust scores, role estimations, and wolf kill predictions.
You should review this recommendation and confirm or adjust based on game context."""
            
            # 构建历史记录
            speech_history = context.get('speech_history', {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SKILL_PROMPT, {
                "history": history_str,
                "name": my_name,
                "last_guarded": last_guarded if last_guarded else "None",
                "night_count": night_count,
                "trust_summary": trust_summary,
                "algorithm_suggestion": algorithm_suggestion,
                "choices": ", ".join(candidates)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            target = result.strip()
            
            # 验证结果
            if target and target in candidates:
                logger.info(f"[GUARD LLM DECISION] Confirmed: {target}")
                return target
            elif not target or target.lower() == "empty" or target.lower() == "none":
                logger.info(f"[GUARD LLM DECISION] Empty guard")
                return ""
            else:
                # LLM返回无效结果，使用算法推荐
                logger.warning(f"[GUARD LLM DECISION] Invalid result '{target}', using algorithm: {algo_target}")
                return algo_target
                
        except Exception as e:
            logger.error(f"[GUARD LLM DECISION] Error: {e}, using algorithm recommendation")
            return algo_target
    
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
        elif req.status == "sheriff_election":
            return self._interact_sheriff_election(req)
        elif req.status == "sheriff_speech":
            return self._interact_sheriff_speech(req)
        elif req.status == "sheriff_vote":
            return self._interact_sheriff_vote(req)
        elif req.status == "sheriff_pk":
            return self._interact_sheriff_pk(req)
        elif req.status == "sheriff_speech_order":
            return self._interact_sheriff_speech_order(req)
        elif req.status == "sheriff_transfer":
            return self._interact_sheriff_transfer(req)
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
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD DISCUSS] Generated speech (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD DISCUSS] Error generating speech: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to generate guard discussion speech: {e}") from e
    
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
        
        遗言是守卫最后的贡献，必须包含：
        1. 完整的守护历史
        2. 信任分数分析
        3. 狼人嫌疑人
        4. 投票建议
        
        Returns:
            AgentResp: 遗言内容
        """
        try:
            # 获取基本信息
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取守卫历史并格式化
            guard_history = self.memory.load_variable("guard_history") or {}
            guarded_players = self.memory.load_variable("guarded_players") or []
            
            # 详细格式化守护历史（按夜晚顺序）
            guard_history_detail = self._format_guard_history_detailed(guard_history)
            
            # 守护摘要
            guard_summary = self._format_guard_summary(guarded_players, guard_history)
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt（确保所有参数都存在）
            prompt = format_prompt(LAST_WORDS_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "guard_history_summary": guard_summary,
                "guard_history_detail": guard_history_detail
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD LAST WORDS] Generated (length: {len(result)})")
            logger.info(f"[GUARD LAST WORDS] Guard history: {guard_history_detail}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD LAST WORDS] Error generating: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to generate guard last words: {e}") from e
    
    def _format_guard_history_detailed(self, guard_history: Dict[int, str]) -> str:
        """
        详细格式化守护历史
        
        Args:
            guard_history: 守护历史字典 {night: target}
            
        Returns:
            格式化的守护历史字符串
        """
        if not guard_history:
            return "No guard history recorded"
        
        history_lines = []
        for night in sorted(guard_history.keys()):
            target = guard_history[night]
            if target and target != "Empty guard":
                history_lines.append(f"- Night {night}: Guarded {target}")
            else:
                history_lines.append(f"- Night {night}: Empty guard (strategic choice)")
        
        return "\n".join(history_lines) if history_lines else "No guard history recorded"
    
    def _format_guard_summary(self, guarded_players: List[str], guard_history: Dict[int, str]) -> str:
        """
        格式化守护摘要
        
        Args:
            guarded_players: 被守护过的玩家列表
            guard_history: 守护历史字典
            
        Returns:
            守护摘要字符串
        """
        if not guarded_players and not guard_history:
            return "No guards performed"
        
        total_nights = len(guard_history) if guard_history else 0
        unique_players = len(guarded_players) if guarded_players else 0
        empty_guards = sum(1 for target in guard_history.values() if not target or target == "Empty guard") if guard_history else 0
        
        summary_parts = []
        if total_nights > 0:
            summary_parts.append(f"Total {total_nights} nights")
        if unique_players > 0:
            summary_parts.append(f"guarded {unique_players} different players")
        if empty_guards > 0:
            summary_parts.append(f"{empty_guards} empty guards")
        
        return ", ".join(summary_parts) if summary_parts else "No guards performed"
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法 + LLM确认）
        
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
        algo_target = self._make_vote_decision(choices)
        
        # 如果有增强决策引擎，获取详细信息
        algo_confidence = 70
        algo_reason = "Trust-based decision"
        
        if hasattr(self, 'enhanced_decision_engine') and self.enhanced_decision_engine:
            try:
                context = self._build_context()
                current_day = context.get('current_day', self.memory.load_variable("day_count") or 1)
                alive_players = context.get('alive_players', self.memory.load_variable("alive_players") or [])
                total_players = len(self.memory.load_variable("all_players") or [])
                
                # 添加缺失的上下文字段
                context['current_day'] = current_day
                context['alive_players'] = alive_players
                context['total_players'] = total_players
                
                # 判断游戏阶段
                if current_day <= 2:
                    game_phase = 'early'
                elif len(alive_players) <= 5:
                    game_phase = 'endgame'
                else:
                    game_phase = 'midgame'
                
                _, confidence, all_scores = self.enhanced_decision_engine.decide_vote(
                    choices, context, game_phase
                )
                algo_confidence = int(confidence * 100)
                algo_reason = f"Enhanced decision (phase: {game_phase})"
            except Exception as e:
                logger.warning(f"[GUARD VOTE] Failed to get enhanced decision details: {e}")
        
        # 如果置信度高，直接返回
        if algo_confidence >= 80:
            logger.info(f"[GUARD VOTE] High confidence ({algo_confidence}): {algo_target}")
            return AgentResp(success=True, result=algo_target, errMsg=None)
        
        # 置信度中等或低，使用LLM确认
        try:
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建算法建议
            algorithm_suggestion = f"""Algorithm Recommendation:
Target: {algo_target}
Reason: {algo_reason}
Confidence: {algo_confidence}%

The algorithm has calculated comprehensive wolf probability and vote scores.
You should review this recommendation and confirm or adjust based on game context."""
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(VOTE_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "algorithm_suggestion": algorithm_suggestion,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            target = result.strip()
            
            # 验证结果
            if target and target in choices:
                logger.info(f"[GUARD VOTE] LLM confirmed: {target}")
                return AgentResp(success=True, result=target, errMsg=None)
            else:
                # LLM返回无效结果，使用算法推荐
                logger.warning(f"[GUARD VOTE] Invalid LLM result '{target}', using algorithm: {algo_target}")
                return AgentResp(success=True, result=algo_target, errMsg=None)
                
        except Exception as e:
            logger.error(f"[GUARD VOTE] LLM decision failed: {e}, using algorithm")
            return AgentResp(success=True, result=algo_target, errMsg=None)
    
    # ==================== 警长相关方法 ====================
    
    def _interact_sheriff_election(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举决策
        
        Args:
            req: 选举请求
            
        Returns:
            AgentResp: 是否参选
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            current_day = self.memory.load_variable("day_count") or 1
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_ELECTION_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            result = self._llm_generate(prompt, temperature=0.3)
            
            # 解析结果
            decision = "Run for sheriff" if "run" in result.lower() else "Don't run"
            
            logger.info(f"[GUARD SHERIFF ELECTION] Decision: {decision}")
            return AgentResp(success=True, result=decision, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF ELECTION] Error: {e}")
            return AgentResp(success=True, result="Don't run", errMsg=None)
    
    def _interact_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选演讲
        
        注意：警长选举发生在死亡公告之前，不能引用当晚的死亡信息
        
        Args:
            req: 演讲请求
            
        Returns:
            AgentResp: 演讲内容
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录（只包含之前的信息，不包含当晚死亡）
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 添加时序约束提醒
            timing_reminder = "⚠️ CRITICAL: Sheriff election happens BEFORE death announcements. Do NOT mention who died last night."
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            # 在prompt前添加时序约束
            prompt = f"{timing_reminder}\n\n{prompt}"
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD SHERIFF SPEECH] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF SPEECH] Error: {e}")
            return AgentResp(success=True, result="I am running for sheriff to help the good team.", errMsg=None)
    
    def _interact_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举投票
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        try:
            my_name = self.memory.load_variable("name")
            
            # 获取候选人列表并过滤掉自己
            if req.message:
                choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
            else:
                choices = []
            
            if not choices:
                logger.warning("[GUARD SHERIFF VOTE] No valid choices available")
                return AgentResp(success=True, result="", errMsg=None)
            
            # 构建上下文
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_VOTE_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            target = self._validate_player_name(result.strip(), choices)
            
            logger.info(f"[GUARD SHERIFF VOTE] Target: {target}")
            return AgentResp(success=True, result=target, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF VOTE] Error: {e}")
            return AgentResp(success=True, result=choices[0] if choices else "", errMsg=None)
    
    def _interact_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK演讲
        
        Args:
            req: PK请求
            
        Returns:
            AgentResp: PK演讲内容
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_PK_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[GUARD SHERIFF PK] Generated (length: {len(result)})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF PK] Error: {e}")
            return AgentResp(success=True, result="I am the better choice for sheriff.", errMsg=None)
    
    def _interact_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """
        处理警长发言顺序选择
        
        Args:
            req: 顺序请求
            
        Returns:
            AgentResp: 发言顺序
        """
        try:
            # 构建上下文
            my_name = self.memory.load_variable("name") or "Unknown"
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_SPEECH_ORDER_PROMPT, {
                "name": my_name,
                "trust_summary": trust_summary
            })
            
            result = self._llm_generate(prompt, temperature=0.3)
            
            # 解析结果
            order = "Clockwise" if "clockwise" in result.lower() and "counter" not in result.lower() else "Counter-clockwise"
            
            logger.info(f"[GUARD SHERIFF ORDER] Order: {order}")
            return AgentResp(success=True, result=order, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF ORDER] Error: {e}")
            return AgentResp(success=True, result="Clockwise", errMsg=None)
    
    def _interact_sheriff_transfer(self, req: AgentReq) -> AgentResp:
        """
        处理警徽转移
        
        Args:
            req: 转移请求
            
        Returns:
            AgentResp: 转移目标
        """
        try:
            my_name = self.memory.load_variable("name")
            
            # 获取候选人列表并过滤掉自己
            if req.message:
                choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
            else:
                choices = []
            
            if not choices:
                logger.warning("[GUARD SHERIFF TRANSFER] No valid choices available")
                return AgentResp(success=True, result="tear", errMsg=None)
            
            # 构建上下文
            alive_players = self.memory.load_variable("alive_players") or []
            
            # 获取信任分数摘要
            trust_summary = ""
            if hasattr(self, 'trust_manager') and self.trust_manager:
                trust_summary = self.trust_manager.get_summary(set(alive_players), top_n=8)
            
            # 构建历史记录
            speech_history = self.memory.load_variable("speech_history") or {}
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt
            prompt = format_prompt(SHERIFF_TRANSFER_PROMPT, {
                "history": history_str,
                "name": my_name,
                "trust_summary": trust_summary,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            
            # 解析结果
            if "tear" in result.lower():
                target = "tear"
            else:
                target = self._validate_player_name(result.strip(), choices)
            
            logger.info(f"[GUARD SHERIFF TRANSFER] Target: {target}")
            return AgentResp(success=True, result=target, errMsg=None)
            
        except Exception as e:
            logger.error(f"[GUARD SHERIFF TRANSFER] Error: {e}")
            import traceback
            traceback.print_exc()
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Failed to make sheriff transfer decision: {e}") from e
