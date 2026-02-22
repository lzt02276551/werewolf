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
from typing import Dict, List, Tuple, Optional, Any
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

    def __init__(self, model_name: str = None, analysis_model_name: Optional[str] = None):
        """
        初始化女巫代理
        
        Args:
            model_name: LLM模型名称（可选）
                       如果不提供，将从环境变量 MODEL_NAME 读取
                       如果环境变量也没有，默认使用 "deepseek-chat"
            analysis_model_name: 分析模型名称（可选，用于向后兼容，已废弃）
        """
        # 如果没有提供model_name，从环境变量读取
        if model_name is None:
            import os
            model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
            logger.info(f"Using model from environment: {model_name}")
        
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
        处理技能使用（解药/毒药决策）- 兼容游戏引擎格式
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 技能使用响应（格式：Save/Poison/Do Not Use）
        """
        action, target = self._make_skill_decision(req)
        
        # 转换为游戏引擎期望的格式（兼容模板）
        if action == "antidote" and target:
            result = f"Save {target}"
            skill_target = target
        elif action == "poison" and target:
            result = f"Poison {target}"
            skill_target = target
        else:
            result = "Do Not Use"
            skill_target = None
        
        logger.info(f"[WITCH SKILL] Result: {result}, SkillTarget: {skill_target}")
        return AgentResp(success=True, result=result, skillTargetPlayer=skill_target, errMsg=None)
    
    def _make_skill_decision(self, req: AgentReq) -> Tuple[str, str]:
        """
        技能决策（解药/毒药）- 简化版（符合女巫规则）
        
        女巫规则：
        - 解药只能用一次，可以救任何被狼人杀死的玩家（包括自己）
        - 毒药只能用一次，可以毒死任何玩家
        - 同一晚可以同时使用解药和毒药
        
        决策策略：
        1. 解药：优先救高价值目标（预言家>守卫>强力玩家），避免救自刀
        2. 毒药：毒确认狼人或高度可疑玩家
        
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
            logger.info(f"[SKILL] Night {current_night} begins")
            
            # 提取被杀玩家
            victim = self._extract_killed_player(req)
            
            if not victim:
                logger.warning(f"[SKILL] Night {current_night}: No victim identified")
                # 没有被杀玩家，只考虑毒药
                poison_action = self._decide_poison_action(req, current_night)
                if poison_action:
                    return poison_action
                return "none", ""
            
            logger.info(f"[SKILL] Night {current_night}: Victim identified: {victim}")
            
            # 解药决策（包括自救）
            antidote_action = self._decide_antidote_action(victim, current_night)
            if antidote_action:
                return antidote_action
            
            # 如果不救人，考虑毒药
            poison_action = self._decide_poison_action(req, current_night)
            if poison_action:
                return poison_action
            
            logger.info(f"[SKILL] Night {current_night}: No action taken")
            return "none", ""
            
        except AttributeError as e:
            logger.error(f"[SKILL] Attribute error: {e}")
            return "none", ""
        except ValueError as e:
            logger.error(f"[SKILL] Value error: {e}")
            return "none", ""
        except Exception as e:
            logger.error(f"[SKILL] Unexpected error: {e}", exc_info=True)
            return "none", ""
    
    def _decide_antidote_action(
        self,
        victim: Optional[str],
        current_night: int
    ) -> Optional[Tuple[str, str]]:
        """
        决定解药行动（企业级五星标准）
        
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
            # 更新药品状态
            self.memory_dao.set_has_antidote(False)
            self.memory_dao.add_saved_player(victim)
            
            # 添加到历史记录（重要：用于后续分析）
            # 注意：这里添加到内存历史，不是通过append_history（避免重复）
            saved_players = self.memory_dao.get_saved_players()
            logger.info(f"[ANTIDOTE] Saved players updated: {saved_players}")
            
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
        决定毒药行动（企业级五星标准）
        
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
            # 更新药品状态
            self.memory_dao.set_has_poison(False)
            self.memory_dao.add_poisoned_player(target)
            
            # 添加到历史记录（重要：用于后续分析）
            # 注意：这里添加到内存历史，不是通过append_history（避免重复）
            poisoned_players = self.memory_dao.get_poisoned_players()
            logger.info(f"[POISON] Poisoned players updated: {poisoned_players}")
            
            logger.info(
                f"[SKILL] Night {current_night}: POISON {target} "
                f"({reason}, score: {score:.1f})"
            )
            return "poison", target
        
        return None
    
    def _extract_killed_player(self, req: AgentReq) -> Optional[str]:
        """
        从请求中提取被杀玩家（企业级五星标准）
        
        优先级：
        1. req.message（主要来源）
        2. 历史记录最近10条
        3. 返回None（安全降级）
        
        Args:
            req: 请求对象
            
        Returns:
            被杀玩家名称，未找到返回None
        """
        try:
            # 优先从message中提取（最可靠）
            if hasattr(req, 'message') and req.message:
                msg = str(req.message)
                # 多语言支持：英文和中文
                kill_indicators = ["was killed", "died", "被杀", "death", "killed by"]
                
                if any(indicator in msg.lower() for indicator in kill_indicators):
                    # 提取玩家编号（支持多种格式）
                    patterns = [
                        r'No\.(\d+)',           # No.1
                        r'Player\s*(\d+)',      # Player 1
                        r'玩家\s*(\d+)',        # 玩家1
                        r'#(\d+)',              # #1
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, msg, re.IGNORECASE)
                        if match:
                            victim = f"No.{match.group(1)}"
                            logger.info(f"[EXTRACT] Found victim from message: {victim}")
                            return victim
            
            # 从历史中提取（备用方案）
            if hasattr(req, 'history') and req.history:
                for msg in reversed(req.history[-10:]):  # 最近10条
                    if not isinstance(msg, str):
                        continue
                    
                    kill_indicators = ["was killed", "died", "被杀", "death", "killed by"]
                    if any(indicator in msg.lower() for indicator in kill_indicators):
                        patterns = [
                            r'No\.(\d+)',
                            r'Player\s*(\d+)',
                            r'玩家\s*(\d+)',
                            r'#(\d+)',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, msg, re.IGNORECASE)
                            if match:
                                victim = f"No.{match.group(1)}"
                                logger.info(f"[EXTRACT] Found victim from history: {victim}")
                                return victim
            
            logger.warning("[EXTRACT] No victim found in message or history")
            return None
            
        except AttributeError as e:
            logger.error(f"[EXTRACT] Attribute error (req missing fields): {e}")
            return None
        except re.error as e:
            logger.error(f"[EXTRACT] Regex error: {e}")
            return None
        except Exception as e:
            logger.error(f"[EXTRACT] Unexpected error: {e}", exc_info=True)
            return None
    
    # 移除 _should_self_save 方法，自救逻辑整合到解药决策中
    
    # ==================== 上下文构建 ====================
    
    def _build_context(self) -> Dict[str, Any]:
        """
        构建女巫决策上下文（扩展父类方法）
        
        Returns:
            包含女巫特有信息的上下文字典
        """
        # 获取父类的基础上下文
        context = super()._build_context()
        
        # 添加女巫特有信息
        context.update({
            "has_antidote": self.memory_dao.get_has_antidote(),
            "has_poison": self.memory_dao.get_has_poison(),
            "saved_players": self.memory_dao.get_saved_players(),
            "poisoned_players": self.memory_dao.get_poisoned_players(),
            "current_night": self.memory_dao.get_current_night(),
            "current_day": self.memory_dao.get_current_day(),
            "wolves_eliminated": self.memory_dao.get("wolves_eliminated", 0),
            "good_players_lost": self.memory_dao.get("good_players_lost", 0),
        })
        
        return context
    
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
        elif "sheriff_election" in str(req.status).lower():
            return self._handle_sheriff_election(req)
        elif "sheriff_speech" in str(req.status).lower():
            return self._handle_sheriff_speech(req)
        elif "sheriff_vote" in str(req.status).lower():
            return self._handle_sheriff_vote(req)
        elif "sheriff_transfer" in str(req.status).lower():
            return self._handle_sheriff_transfer(req)
        elif "sheriff_pk" in str(req.status).lower():
            return self._handle_sheriff_pk(req)
        else:
            # 未知状态，返回默认响应
            logger.warning(f"[WITCH INTERACT] Unknown status: {req.status}, returning default response")
            return AgentResp(success=True, result="", errMsg=None)
    
    # ==================== 警长相关方法 ====================
    
    def _handle_sheriff_election(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选决策
        
        Args:
            req: 竞选请求
            
        Returns:
            AgentResp: 是否竞选
        """
        from werewolf.witch.prompt import SHERIFF_ELECTION_PROMPT
        
        history = self.memory.load_history()
        skill_info = self._format_skill_info()
        
        prompt = format_prompt(SHERIFF_ELECTION_PROMPT, {
            "history": "\n".join(history[-30:]),
            "name": self.memory_dao.get_my_name(),
            "skill_info": skill_info
        })
        
        result = self._llm_generate(prompt, temperature=0.3)
        
        # 解析结果
        if "run" in result.lower() and "not" not in result.lower():
            decision = "Run for Sheriff"
        else:
            decision = "Do Not Run"
        
        logger.info(f"[WITCH SHERIFF ELECTION] Decision: {decision}")
        return AgentResp(success=True, result=decision, errMsg=None)
    
    def _handle_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选演讲（企业级五星标准）
        
        ⚠️ 关键约束：警长选举发生在死亡公告之前！
        - 不能提及昨晚谁死了（主持人还未公布）
        - 不能引用夜晚击杀结果（主持人还未揭晓）
        - 只能基于：药品状态、角色、前一天的公开信息
        
        Args:
            req: 演讲请求
            
        Returns:
            AgentResp: 演讲内容
        """
        from werewolf.witch.prompt import SHERIFF_SPEECH_PROMPT
        
        history = self.memory.load_history()
        skill_info = self._format_skill_info()
        
        # 过滤历史记录：移除当前夜晚的死亡信息（如果有）
        # 警长选举时，昨晚的死亡信息还未公布
        filtered_history = []
        current_night = self.memory_dao.get_current_night()
        
        for msg in history[-30:]:
            # 跳过包含"killed"、"died"等关键词的最新消息
            if current_night > 0 and any(kw in msg.lower() for kw in ["killed", "died", "death"]):
                # 检查是否是最新的夜晚信息
                if f"Night {current_night}" in msg or "last night" in msg.lower():
                    logger.debug(f"[SHERIFF SPEECH] Filtering night info: {msg[:50]}...")
                    continue
            filtered_history.append(msg)
        
        prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
            "history": "\n".join(filtered_history),
            "name": self.memory_dao.get_my_name(),
            "skill_info": skill_info
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH SHERIFF SPEECH] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _handle_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举投票
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        from werewolf.witch.prompt import SHERIFF_VOTE_PROMPT
        
        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]
        
        if not choices:
            logger.warning("[WITCH SHERIFF VOTE] No valid choices")
            return AgentResp(success=True, result="", errMsg=None)
        
        # 优先投给救过的玩家（验证好人）
        saved_players = self.memory_dao.get_saved_players()
        for saved in saved_players:
            if saved in choices:
                logger.info(f"[WITCH SHERIFF VOTE] Voting for saved player: {saved}")
                return AgentResp(success=True, result=saved, errMsg=None)
        
        # 否则投给信任度最高的
        trust_scores = self.memory_dao.get_trust_scores()
        if trust_scores:
            best_candidate = max(choices, key=lambda x: trust_scores.get(x, 50))
            logger.info(f"[WITCH SHERIFF VOTE] Voting for highest trust: {best_candidate}")
            return AgentResp(success=True, result=best_candidate, errMsg=None)
        
        # 默认第一个
        logger.info(f"[WITCH SHERIFF VOTE] Default vote: {choices[0]}")
        return AgentResp(success=True, result=choices[0], errMsg=None)
    
    def _handle_sheriff_transfer(self, req: AgentReq) -> AgentResp:
        """
        处理警徽转交
        
        Args:
            req: 转交请求
            
        Returns:
            AgentResp: 转交目标
        """
        from werewolf.witch.prompt import SHERIFF_TRANSFER_PROMPT
        
        my_name = self.memory_dao.get_my_name()
        choices = [name for name in req.message.split(",") if name != my_name]
        
        if not choices:
            logger.warning("[WITCH SHERIFF TRANSFER] No valid choices, destroying badge")
            return AgentResp(success=True, result="Destroy Badge", errMsg=None)
        
        # 优先转给救过的玩家
        saved_players = self.memory_dao.get_saved_players()
        for saved in saved_players:
            if saved in choices:
                logger.info(f"[WITCH SHERIFF TRANSFER] Transferring to saved player: {saved}")
                return AgentResp(success=True, result=saved, errMsg=None)
        
        # 否则转给信任度最高的
        trust_scores = self.memory_dao.get_trust_scores()
        if trust_scores:
            best_candidate = max(choices, key=lambda x: trust_scores.get(x, 50))
            if trust_scores.get(best_candidate, 0) >= 60:
                logger.info(f"[WITCH SHERIFF TRANSFER] Transferring to highest trust: {best_candidate}")
                return AgentResp(success=True, result=best_candidate, errMsg=None)
        
        # 如果没有高信任玩家，撕毁警徽
        logger.info("[WITCH SHERIFF TRANSFER] No trustworthy candidate, destroying badge")
        return AgentResp(success=True, result="Destroy Badge", errMsg=None)
    
    def _handle_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK演讲
        
        Args:
            req: PK请求
            
        Returns:
            AgentResp: PK演讲内容
        """
        from werewolf.witch.prompt import SHERIFF_PK_PROMPT
        
        history = self.memory.load_history()
        skill_info = self._format_skill_info()
        
        prompt = format_prompt(SHERIFF_PK_PROMPT, {
            "history": "\n".join(history[-30:]),
            "name": self.memory_dao.get_my_name(),
            "skill_info": skill_info
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH SHERIFF PK] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)

    
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
        
        # 构建发言提示词
        history = self.memory.load_history()
        skill_info = self._format_skill_info()
        
        prompt = format_prompt(DESC_PROMPT, {
            "history": "\n".join(history[-50:]),  # 最近50条历史
            "name": self.memory_dao.get_my_name(),
            "skill_info": skill_info
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH DISCUSS] Generated speech (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _format_skill_info(self) -> str:
        """
        格式化药品状态信息
        
        Returns:
            药品状态描述
        """
        has_antidote = self.memory_dao.get_has_antidote()
        has_poison = self.memory_dao.get_has_poison()
        
        if has_antidote and has_poison:
            return "Antidote: Available, Poison: Available"
        elif has_antidote:
            return "Antidote: Available, Poison: Used"
        elif has_poison:
            return "Antidote: Used, Poison: Available"
        else:
            return "Antidote: Used, Poison: Used"
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        Returns:
            AgentResp: 遗言内容
        """
        history = self.memory.load_history()
        skill_info = self._format_skill_info()
        trust_summary = self._format_trust_summary()
        
        prompt = format_prompt(LAST_WORDS_PROMPT, {
            "history": "\n".join(history[-50:]),
            "name": self.memory_dao.get_my_name(),
            "skill_info": skill_info,
            "trust_summary": trust_summary
        })
        
        result = self._llm_generate(prompt)
        result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
        
        logger.info(f"[WITCH LAST WORDS] Generated (length: {len(result)})")
        return AgentResp(success=True, result=result, errMsg=None)
    
    def _format_trust_summary(self) -> str:
        """
        格式化信任分数摘要
        
        Returns:
            信任分数摘要
        """
        trust_scores = self.memory_dao.get_trust_scores()
        if not trust_scores:
            return "No trust data available"
        
        # 按信任分数排序
        sorted_players = sorted(trust_scores.items(), key=lambda x: x[1])
        
        # 最可疑的3个
        suspicious = sorted_players[:3]
        # 最可信的3个
        trustworthy = sorted_players[-3:]
        
        summary = "Trust Analysis:\n"
        summary += "Most Suspicious: " + ", ".join([f"{p} ({s:.0f})" for p, s in suspicious]) + "\n"
        summary += "Most Trustworthy: " + ", ".join([f"{p} ({s:.0f})" for p, s in reversed(trustworthy)])
        
        return summary
    
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
