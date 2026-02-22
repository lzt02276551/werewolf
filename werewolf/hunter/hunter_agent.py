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
from werewolf.hunter.prompt import (
    DESC_PROMPT, 
    VOTE_PROMPT,
    SKILL_PROMPT,
    SHERIFF_ELECTION_PROMPT,
    SHERIFF_SPEECH_PROMPT,
    SHERIFF_VOTE_PROMPT,
    SHERIFF_PK_PROMPT,
    SHERIFF_SPEECH_ORDER_PROMPT,
    SHERIFF_TRANSFER_PROMPT,
    LAST_WORDS_PROMPT
)
from werewolf.hunter.decision_makers import ShootDecisionMaker
from werewolf.hunter.analyzers import (
    ThreatLevelAnalyzer, WolfProbabilityCalculator
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

    def __init__(self, model_name: str = None):
        """
        初始化猎人代理
        
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
    
    def _safe_load_variable(self, key: str, default=None):
        """
        安全地从内存加载变量，如果不存在则返回默认值
        
        Args:
            key: 变量名
            default: 默认值
            
        Returns:
            变量值或默认值
        """
        try:
            return self.memory.load_variable(key)
        except (KeyError, AttributeError):
            return default
    
    def _init_specific_components(self):
        """
        初始化猎人特有组件
        
        猎人特有组件：
        - ShootDecisionMaker: 开枪决策器
        - ThreatLevelAnalyzer: 威胁等级分析器
        - WolfProbabilityCalculator: 狼人概率计算器（使用父类的分析器）
        """
        try:
            # 创建猎人特有的MemoryDAO
            from werewolf.hunter.analyzers import MemoryDAO
            
            self.hunter_memory_dao = MemoryDAO(self.memory)
            self.cache_manager = CacheManager()
            
            # 创建猎人特有的高级分析器
            self.threat_analyzer = ThreatLevelAnalyzer(
                self.config, self.hunter_memory_dao, self.cache_manager
            )
            
            # 验证父类分析器已初始化（必须存在）
            if not hasattr(self, 'trust_score_calculator') or self.trust_score_calculator is None:
                raise RuntimeError("Parent analyzers not initialized - trust_score_calculator is required")
            
            if not hasattr(self, 'voting_pattern_analyzer') or self.voting_pattern_analyzer is None:
                raise RuntimeError("Parent analyzers not initialized - voting_pattern_analyzer is required")
            
            if not hasattr(self, 'speech_quality_evaluator') or self.speech_quality_evaluator is None:
                raise RuntimeError("Parent analyzers not initialized - speech_quality_evaluator is required")
            
            # 创建WolfProbabilityCalculator，传入分析器
            self.wolf_prob_calculator = WolfProbabilityCalculator(
                self.config,
                self.trust_score_calculator,
                self.voting_pattern_analyzer,
                self.speech_quality_evaluator,
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
        # 输入验证
        if not req or not hasattr(req, 'status'):
            logger.error("Invalid request: missing status attribute")
            return AgentResp(success=False, result="", errMsg="Invalid request")
        
        # 猎人特有事件：技能使用（开枪）
        if req.status == STATUS_SKILL:
            return self._handle_shoot_skill(req)
        
        # 处理讨论阶段的消息（包含注入检测、虚假引用检测等）
        if req.status == STATUS_DISCUSS and hasattr(req, 'name') and req.name:
            # 检查是否是遗言阶段（使用统一的遗言检测方法）
            if self._is_last_words_phase(req):
                my_name = self._safe_load_variable("name")
                if req.name == my_name:
                    self.memory.set_variable("giving_last_words", True)
                    logger.info("[LAST WORDS] Hunter is being eliminated, preparing final words")
            
            # 使用基类的消息处理方法（包含注入检测、虚假引用检测、消息解析、发言质量评估）
            if hasattr(req, 'message') and req.message:
                self._process_player_message(req.message, req.name)
        
        # 其他事件使用父类处理（如果父类有perceive方法）
        try:
            return super().perceive(req)
        except AttributeError:
            # 如果父类没有perceive方法，返回默认响应
            return AgentResp(success=True, result="", errMsg=None)
    
    def _is_last_words_phase(self, req: AgentReq) -> bool:
        """
        统一的遗言阶段检测方法（企业级五星增强版 - 修复逻辑漏洞）
        
        遗言阶段的特征（多重验证）：
        1. 消息中包含 "last words", "final words", "遗言" 等关键词
        2. 消息中包含 "leaves their last words" 等短语
        3. 玩家名称后跟 "Last Words:" 或 "遗言："
        4. 玩家名称必须匹配（避免误判）
        5. 排除注入攻击（玩家伪造的遗言消息）
        
        Args:
            req: 游戏事件请求
            
        Returns:
            是否是遗言阶段
        """
        if not req or not hasattr(req, 'message') or not req.message:
            return False
        
        message = req.message
        message_lower = message.lower()
        
        # 关键词检测
        last_words_keywords = [
            "last words", "final words", "遗言",
            "leaves their last words", "leaves his last words", "leaves her last words",
            "'s last words", "最后的话", "final statement"
        ]
        
        has_keyword = any(keyword in message_lower for keyword in last_words_keywords)
        
        if not has_keyword:
            return False
        
        # 验证玩家名称匹配（避免误判）
        if hasattr(req, 'name') and req.name:
            player_name_lower = req.name.lower()
            if player_name_lower not in message_lower:
                logger.debug(f"[LAST WORDS] Rejected: Player name {req.name} not in message")
                return False
        
        # 排除注入攻击：检查消息是否以玩家名称开头（如"No.X: ..."）
        # 真实的遗言消息应该是Host发送的，不会以玩家名称开头
        if hasattr(req, 'name') and req.name:
            # 如果消息以"No.X:"开头，这是玩家发言，不是Host的遗言通知
            if message.strip().startswith(f"{req.name}:"):
                logger.debug(f"[LAST WORDS] Rejected: Message starts with player name (injection attack)")
                return False
        
        # 额外验证：检查是否包含Host特征词（修复：不应该在没有Host特征时返回True）
        host_indicators = ["host:", "system:", "game master:", "宣布", "announces", "host"]
        has_host_indicator = any(indicator in message_lower for indicator in host_indicators)
        
        # 修复逻辑漏洞：如果有关键词但没有Host特征，可能是注入攻击，应该返回False
        if not has_host_indicator:
            logger.debug(f"[LAST WORDS] Rejected: Last words keyword found but no host indicator (possible injection)")
            return False
        
        # 所有验证通过
        logger.debug(f"[LAST WORDS] Confirmed: Valid last words phase for {req.name}")
        return True
    
    def _handle_shoot_skill(self, req: AgentReq) -> AgentResp:
        """
        处理开枪技能
        
        Args:
            req: 技能请求
            
        Returns:
            AgentResp: 开枪目标
        """
        # 检查是否可以开枪
        can_shoot = self._safe_load_variable("can_shoot", True)
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
        shoot_history = self._safe_load_variable("shoot_history", [])
        shoot_history.append(target)
        self.memory.set_variable("shoot_history", shoot_history)
        
        logger.info(f"[HUNTER] Shooting: {target}")
        return AgentResp(success=True, result=target, errMsg=None)
    
    def _make_shoot_decision(self, candidates: List[str]) -> str:
        """
        开枪决策（企业级五星版 - 与SKILL_PROMPT中的决策树一致）
        
        决策流程：
        1. 候选人过滤（排除自己、已死亡、高信任度玩家）
        2. 狼人概率计算（信任分数、投票历史、发言逻辑、死亡关联）
        3. 特殊情况处理（预言家查杀、假预言家、错误投票、狼王嫌疑）
        4. 开枪优先级评分（狼人概率 × 100 + 威胁等级 × 50）
        5. 开枪或放弃决策（分数≥70开枪，<50放弃，默认开枪）
        
        Args:
            candidates: 候选玩家列表
            
        Returns:
            开枪目标（或 "Do Not Shoot"）
        """
        if not candidates:
            logger.warning("[SHOOT DECISION] No candidates provided")
            return "Do Not Shoot"
        
        # 验证决策器存在（必须）
        if not self.shoot_decision_maker:
            logger.error("[SHOOT DECISION] Shoot decision maker not initialized")
            raise RuntimeError("Shoot decision maker not initialized - cannot make shoot decision")
        
        # 获取基本信息（带类型验证）
        my_name = self._safe_load_variable("name", "")
        if not my_name:
            logger.error("[SHOOT DECISION] Player name not set")
            return "Do Not Shoot"
        
        # 获取游戏状态（多源验证）
        game_state = self._safe_load_variable("game_state", {})
        
        # 优先使用day_count（更可靠）
        current_day = self._get_current_day()
        
        # 获取存活玩家（带验证）
        alive_players = self._safe_load_variable("alive_players", [])
        if not isinstance(alive_players, list):
            logger.warning(f"[SHOOT DECISION] alive_players is not list: {type(alive_players)}")
            alive_players = []
        
        alive_count = len(alive_players) if alive_players else 12  # 默认12人局
        
        # 评估游戏阶段（企业级五星算法 - 多维度判断）
        game_phase = self._assess_game_phase_for_shoot(current_day, alive_count)
        
        # 执行决策（带异常处理）
        try:
            target, reason, scores = self.shoot_decision_maker.decide(
                candidates, 
                my_name,
                game_phase,
                current_day,
                alive_count
            )
            
            logger.info(f"[SHOOT DECISION] Target: {target}, Reason: {reason}, Phase: {game_phase}")
            logger.info(f"[SHOOT DECISION] Day: {current_day}, Alive: {alive_count}, Candidates: {len(candidates)}")
            logger.debug(f"[SHOOT DECISION] All scores: {scores}")
            
            return target
            
        except Exception as e:
            logger.error(f"[SHOOT DECISION] Decision failed: {e}")
            import traceback
            traceback.print_exc()
            return "Do Not Shoot"
    
    def _assess_game_phase_for_shoot(self, current_day: int, alive_count: int) -> str:
        """
        评估游戏阶段（用于开枪决策 - 企业级五星算法）
        
        多维度判断：
        1. 天数维度：Day 1-2 = early, Day 3-5 = mid, Day 6+ = late
        2. 人数维度：≤6人 = late（危急），7-9人 = mid，10-12人 = early
        3. 综合判断：取更严重的阶段（如Day 2但只剩6人 → late）
        
        Args:
            current_day: 当前天数
            alive_count: 存活人数
            
        Returns:
            游戏阶段: "early" | "mid" | "late"
        """
        # 天数维度
        if current_day <= 2:
            day_phase = "early"
        elif current_day >= 6:
            day_phase = "late"
        else:
            day_phase = "mid"
        
        # 人数维度
        if alive_count <= 6:
            count_phase = "late"
        elif alive_count <= 9:
            count_phase = "mid"
        else:
            count_phase = "early"
        
        # 综合判断：取更严重的阶段
        phase_priority = {"early": 0, "mid": 1, "late": 2}
        
        day_priority = phase_priority[day_phase]
        count_priority = phase_priority[count_phase]
        
        final_priority = max(day_priority, count_priority)
        
        for phase, priority in phase_priority.items():
            if priority == final_priority:
                logger.debug(
                    f"[GAME PHASE] Day: {current_day} ({day_phase}), "
                    f"Alive: {alive_count} ({count_phase}), "
                    f"Final: {phase}"
                )
                return phase
        
        return "mid"  # 默认中期
    
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
            logger.warning(f"[HUNTER INTERACT] Unknown status: {req.status}, returning default response")
            return AgentResp(success=True, result="", errMsg=None)
    
    def _interact_discuss(self, req: AgentReq) -> AgentResp:
        """
        处理讨论阶段的发言（使用父类的LLM生成方法）
        
        发言策略（与DESC_PROMPT中的决策树一致）：
        - Early Game (Day 1-3): 保持隐藏，以强力平民身份发言
        - Mid Game (Day 4-6): 考虑暗示能力，创造威慑
        - Late Game (Day 7+, ≤6人): 必须暴露身份，建立信任和领导力
        
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
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            current_day = self._get_current_day()
            
            # 获取开枪信息（简化版，不透露过多）
            can_shoot = self._safe_load_variable("can_shoot", True)
            shot_used = self._safe_load_variable("shot_used", False)
            shoot_target = self._safe_load_variable("shoot_target")
            
            shoot_info = self._format_shoot_info_simple(shot_used, shoot_target, can_shoot)
            
            # 确定游戏阶段和策略（与提示词决策树一致）
            game_phase, phase_strategy = self._determine_game_phase(current_day, len(alive_players))
            
            # 获取注入攻击嫌疑人（需要在发言中纠正）
            injection_suspects = self._get_injection_suspects()
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt（使用DESC_PROMPT）
            prompt = format_prompt(DESC_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info,
                "injection_suspects": injection_suspects
            })
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[HUNTER DISCUSS] Generated speech (length: {len(result)}, phase: {game_phase})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER DISCUSS] Error generating speech: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate discussion speech: {e}")
    
    def _get_current_day(self) -> int:
        """
        获取当前天数（企业级五星版 - 多源验证）
        
        优先级：
        1. day_count（最可靠，直接记录）
        2. game_state.current_day（次可靠）
        3. 历史记录分析（最后手段）
        
        Returns:
            当前天数（至少为1）
        """
        # 优先使用day_count（最可靠）
        day_count = self._safe_load_variable("day_count")
        if day_count and isinstance(day_count, int) and day_count > 0:
            return day_count
        
        # 回退到game_state
        game_state = self._safe_load_variable("game_state", {})
        if isinstance(game_state, dict):
            current_day = game_state.get("current_day")
            if isinstance(current_day, int) and current_day > 0:
                return current_day
        
        # 最后手段：从历史记录分析
        try:
            history = self._safe_load_variable("history", [])
            if isinstance(history, list):
                import re
                max_day = 0
                for msg in history:
                    if isinstance(msg, str):
                        # 匹配 "Day X" 或 "第X天"
                        match = re.search(r'[Dd]ay\s+(\d+)', msg)
                        if match:
                            day = int(match.group(1))
                            max_day = max(max_day, day)
                
                if max_day > 0:
                    logger.debug(f"[CURRENT DAY] Extracted from history: {max_day}")
                    return max_day
        except Exception as e:
            logger.debug(f"[CURRENT DAY] Failed to extract from history: {e}")
        
        # 默认返回第1天
        logger.warning("[CURRENT DAY] Unable to determine day, defaulting to 1")
        return 1
    
    def _format_shoot_info_simple(
        self, 
        shot_used: bool, 
        shoot_target: Optional[str], 
        can_shoot: bool
    ) -> str:
        """
        简单格式化开枪信息（用于讨论阶段）
        
        注意：不要在讨论阶段透露过多信息，保持神秘感
        
        Args:
            shot_used: 是否已使用开枪
            shoot_target: 开枪目标
            can_shoot: 是否可以开枪
            
        Returns:
            格式化的开枪信息字符串
        """
        if shot_used and shoot_target:
            # 已经开枪，但不透露目标（除非在遗言阶段）
            return "Already used shooting ability"
        elif can_shoot:
            # 还可以开枪，保持威慑力
            return "Can still shoot (deterrence active)"
        else:
            # 不能开枪（被毒或已使用）
            return "Cannot shoot (poisoned or already used)"
    
    def _get_injection_suspects(self) -> str:
        """
        获取注入攻击嫌疑人列表
        
        Returns:
            格式化的嫌疑人字符串
        """
        player_data = self._safe_load_variable("player_data", {})
        injection_suspects = {}
        
        for player, data in player_data.items():
            if isinstance(data, dict) and data.get("malicious_injection"):
                injection_type = data.get("injection_type", "UNKNOWN")
                injection_suspects[player] = injection_type
        
        return ", ".join([f"{p}({t})" for p, t in injection_suspects.items()]) if injection_suspects else "None"
    
    def _determine_game_phase(self, current_day: int, alive_count: int) -> tuple:
        """
        确定游戏阶段和策略（企业级五星版 - 与提示词中的决策树一致）
        
        游戏阶段划分（多维度判断）：
        - Early Game: Day 1-3 AND 10-12人存活 - 保持隐藏
        - Mid Game: Day 4-6 OR 7-9人存活 - 考虑暗示
        - Late Game: Day 7+ OR ≤6人存活 - 必须暴露
        
        Args:
            current_day: 当前天数
            alive_count: 存活人数
            
        Returns:
            (游戏阶段, 阶段策略)
        """
        # 验证输入
        if not isinstance(current_day, int) or current_day < 1:
            logger.warning(f"[GAME PHASE] Invalid current_day: {current_day}, using 1")
            current_day = 1
        
        if not isinstance(alive_count, int) or alive_count < 1:
            logger.warning(f"[GAME PHASE] Invalid alive_count: {alive_count}, using 12")
            alive_count = 12
        
        # 晚期游戏：天数>=7 OR 存活人数<=6（任一条件满足即进入晚期）
        if current_day >= self.config.late_game_day_threshold or alive_count <= self.config.critical_alive_threshold:
            return (
                "Late Game", 
                "REVEAL identity immediately - establish trust and leadership, warn wolves of retaliation"
            )
        
        # 早期游戏：天数<=3 AND 存活人数>=10（两个条件都满足才是早期）
        elif current_day <= self.config.early_game_reveal_threshold and alive_count >= 10:
            return (
                "Early Game", 
                "STAY HIDDEN - speak as strong villager, avoid revealing Hunter role, become bait for wolves"
            )
        
        # 中期游戏：其他情况
        else:
            return (
                "Mid Game", 
                "CONSIDER revealing - subtle hints like 'I have backup', create deterrence without full reveal"
            )
    
    def _generate_last_words(self) -> AgentResp:
        """
        生成遗言（使用父类的LLM生成方法）
        
        猎人的遗言必须包含（与LAST_WORDS_PROMPT一致）：
        1. 身份确认（"I am the Hunter"）
        2. 开枪决策说明（详细解释为什么射击或不射击）
        3. 淘汰分析（谁推动了投票，为什么被淘汰）
        4. 嫌疑人指导（剩余嫌疑人列表和推荐目标）
        5. 战略建议（帮助好人阵营获胜）
        
        Returns:
            AgentResp: 遗言内容
        """
        try:
            # 获取基本信息
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            
            # 获取开枪历史和状态
            shoot_history = self._safe_load_variable("shoot_history", [])
            shot_used = self._safe_load_variable("shot_used", False)
            shoot_target = self._safe_load_variable("shoot_target")
            can_shoot = self._safe_load_variable("can_shoot", True)
            
            # 详细格式化开枪信息（用于遗言）
            shoot_info = self._format_shoot_info_detailed(
                shot_used, shoot_target, can_shoot, shoot_history
            )
            
            # 构建历史记录（包含完整的游戏历史）
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=15)  # 遗言阶段需要更多历史
            
            # 格式化prompt（使用LAST_WORDS_PROMPT）
            prompt = format_prompt(LAST_WORDS_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info
            })
            
            result = self._llm_generate(prompt)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[HUNTER LAST WORDS] Generated (length: {len(result)})")
            logger.info(f"[HUNTER LAST WORDS] Shoot info: {shoot_info}")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER LAST WORDS] Error generating: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate last words: {e}")
    
    def _format_shoot_info_detailed(
        self, 
        shot_used: bool, 
        shoot_target: Optional[str], 
        can_shoot: bool,
        shoot_history: List[str]
    ) -> str:
        """
        详细格式化开枪信息（用于遗言阶段）
        
        遗言阶段需要详细说明开枪决策，帮助好人阵营
        
        Args:
            shot_used: 是否已使用开枪
            shoot_target: 开枪目标
            can_shoot: 是否可以开枪
            shoot_history: 开枪历史
            
        Returns:
            格式化的开枪信息字符串
        """
        if shot_used and shoot_target:
            # 已经开枪，详细说明原因
            reason = self._get_shoot_reason(shoot_target)
            return f"I shot {shoot_target}. Reason: {reason}. This was my strategic choice to eliminate a high-probability wolf."
        elif can_shoot:
            # 可以开枪但选择不开（不确定目标）
            return "I can still shoot but chose not to use it yet due to uncertainty about remaining players. I wanted to preserve this ability for a clearer target."
        else:
            # 不能开枪（被毒）
            return "I cannot shoot because I was poisoned by the Witch. This prevented me from using my shooting ability."
    
    def _get_shoot_reason(self, target: str) -> str:
        """
        获取开枪原因（详细版，用于遗言）
        
        Args:
            target: 开枪目标
            
        Returns:
            开枪原因（详细说明）
        """
        # 获取目标的信任分数
        trust_scores = self._safe_load_variable("trust_scores", {})
        trust_score = trust_scores.get(target, 50)
        
        # 获取注入攻击和虚假引用
        player_data = self._safe_load_variable("player_data", {})
        target_data = player_data.get(target, {})
        
        reasons = []
        
        # 信任分数
        if trust_score < 20:
            reasons.append(f"extremely low trust score ({trust_score:.0f}/100)")
        elif trust_score < 30:
            reasons.append(f"very low trust score ({trust_score:.0f}/100)")
        elif trust_score < 50:
            reasons.append(f"low trust score ({trust_score:.0f}/100)")
        
        # 注入攻击
        if target_data.get("malicious_injection"):
            injection_type = target_data.get("injection_type", "UNKNOWN")
            reasons.append(f"used injection attack ({injection_type})")
        
        # 虚假引用
        if target_data.get("false_quotes", 0) > 0:
            count = target_data.get("false_quotes", 0)
            reasons.append(f"made {count} false quotation(s)")
        
        # 投票历史（狼人保护行为）
        voting_history = self._safe_load_variable("voting_history", {})
        if target in voting_history:
            votes = voting_history[target]
            if isinstance(votes, list) and len(votes) >= 3:
                # 检查是否总是投好人
                reasons.append("suspicious voting pattern (consistently voted for good players)")
        
        # 如果没有具体原因，使用通用描述
        if not reasons:
            reasons.append(f"highest wolf probability among candidates (trust: {trust_score:.0f})")
        
        return ", ".join(reasons)
    
    def _format_trust_summary(self, alive_players: List[str], my_name: str) -> str:
        """
        格式化信任分数摘要（统一格式）
        
        Args:
            alive_players: 存活玩家列表
            my_name: 自己的名字
            
        Returns:
            格式化的信任分数摘要
        """
        trust_scores = self._safe_load_variable("trust_scores", {})
        if not trust_scores or not alive_players:
            return "No trust data"
        
        sorted_players = sorted(
            [(p, trust_scores.get(p, 50)) for p in alive_players if p != my_name],
            key=lambda x: x[1],
            reverse=True
        )
        
        trust_lines = [f"{p}: {score:.0f}" for p, score in sorted_players[:8]]
        return "\n".join(trust_lines) if trust_lines else "No trust data"
    
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
    
    def _interact_vote(self, req: AgentReq) -> AgentResp:
        """
        处理投票决策（使用父类的投票决策方法）
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        my_name = self._safe_load_variable("name")
        
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
        return AgentResp(success=True, result=target, errMsg=None)
    
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
        
        return AgentResp(success=True, result=None, errMsg=None)

    # ==================== 警长相关方法 ====================
    
    def _interact_sheriff_election(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举决策（与SHERIFF_ELECTION_PROMPT一致）
        
        决策因素（与提示词决策树一致）：
        - 能力状态：can_shoot = True → 高威慑力，适合竞选
        - 游戏阶段：Early (Day 1) → 保持隐藏；Mid/Late → 考虑竞选
        - 好人阵营需求：缺乏领导 → 竞选；已有强力候选人 → 不竞选
        - 战略价值：建立信任 vs 保持神秘
        
        Args:
            req: 选举请求
            
        Returns:
            AgentResp: 是否参选（"Run for Sheriff" 或 "Do Not Run"）
        """
        try:
            # 构建上下文
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            can_shoot = self._safe_load_variable("can_shoot", True)
            current_day = self._get_current_day()
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化开枪信息
            shoot_info = "can shoot" if can_shoot else "already shot"
            
            # 格式化prompt（使用SHERIFF_ELECTION_PROMPT）
            prompt = format_prompt(SHERIFF_ELECTION_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info
            })
            
            result = self._llm_generate(prompt, temperature=0.3)
            
            # 解析结果
            decision = "Run for Sheriff" if "run" in result.lower() else "Do Not Run"
            
            logger.info(f"[HUNTER SHERIFF ELECTION] Decision: {decision} (day: {current_day}, can_shoot: {can_shoot})")
            return AgentResp(success=True, result=decision, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF ELECTION] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to make sheriff election decision: {e}")
    
    def _interact_sheriff_speech(self, req: AgentReq) -> AgentResp:
        """
        处理警长竞选演讲（与SHERIFF_SPEECH_PROMPT一致）
        
        ⚠️ 关键时序约束：警长选举发生在死亡公告之前！
        - 不能引用当晚的死亡信息（Host还未公布）
        - 只能使用之前天数的公开信息
        - 重点：分析能力、领导力、威慑力
        
        身份暴露策略（与提示词决策树一致）：
        - Early Game (Day 1): 隐藏身份，以强力平民身份竞选
        - Mid Game (Day 2-3): 部分暗示（"I have retaliation power"）
        - Late Game (Day 4+): 完全暴露（"I am the Hunter"）
        
        Args:
            req: 演讲请求
            
        Returns:
            AgentResp: 演讲内容
        """
        try:
            # 构建上下文
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            can_shoot = self._safe_load_variable("can_shoot", True)
            current_day = self._get_current_day()
            
            # 构建历史记录（只包含之前的信息，不包含当晚死亡）
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化开枪信息（用于演讲策略）
            shoot_info = "can shoot" if can_shoot else "already shot"
            
            # 添加时序约束提醒（确保LLM不会引用未公布的信息）
            timing_reminder = (
                "⚠️ CRITICAL: Sheriff election happens BEFORE death announcements. "
                "Do NOT mention who died last night - Host hasn't revealed it yet!"
            )
            
            # 格式化prompt（使用SHERIFF_SPEECH_PROMPT）
            prompt = format_prompt(SHERIFF_SPEECH_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info
            })
            
            # 在prompt前添加时序约束
            prompt = f"{timing_reminder}\n\n{prompt}"
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[HUNTER SHERIFF SPEECH] Generated (length: {len(result)}, day: {current_day})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF SPEECH] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate sheriff speech: {e}")
    
    def _interact_sheriff_vote(self, req: AgentReq) -> AgentResp:
        """
        处理警长选举投票（与SHERIFF_VOTE_PROMPT一致）
        
        投票标准（与提示词决策树一致）：
        - 优先考虑：确认好人（预言家验证）、强逻辑发言者、准确投票历史、领导能力
        - 避免投票：可疑玩家（信任<50）、矛盾发言者、保护狼人的投票者、注入攻击者
        - 战略考虑：谁能保护我、谁能有效领导、谁让狼人害怕、谁能团结好人
        
        Args:
            req: 投票请求
            
        Returns:
            AgentResp: 投票目标
        """
        try:
            my_name = self._safe_load_variable("name")
            
            # 获取候选人列表并过滤掉自己
            if req.message:
                choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
            else:
                choices = []
            
            if not choices:
                logger.warning("[HUNTER SHERIFF VOTE] No valid choices available")
                return AgentResp(success=True, result="", errMsg=None)
            
            # 构建上下文
            alive_players = self._safe_load_variable("alive_players", [])
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt（使用SHERIFF_VOTE_PROMPT）
            prompt = format_prompt(SHERIFF_VOTE_PROMPT, {
                "history": history_str,
                "name": my_name,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            target = self._validate_player_name(result.strip(), choices)
            
            logger.info(f"[HUNTER SHERIFF VOTE] Target: {target}")
            return AgentResp(success=True, result=target, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF VOTE] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to make sheriff vote decision: {e}")
    
    def _interact_sheriff_pk(self, req: AgentReq) -> AgentResp:
        """
        处理警长PK演讲（与SHERIFF_PK_PROMPT一致）
        
        PK演讲策略（与提示词结构一致）：
        1. 反驳对手（20%）：指出逻辑漏洞、可疑行为、投票历史问题
        2. 自我倡导（40%）：游戏状态分析、嫌疑人列表、领导计划
        3. 威慑展示（20%）：暗示能力、警告狼人、展示信心
        4. 结尾呼吁（20%）：为何值得当选、呼吁好人团结、最终诉求
        
        身份暴露决策：
        - 对手可疑 + 需要强威慑 → 完全暴露
        - 对手似乎是好人 + 中期游戏 → 部分暗示
        - 战略压力 → 战略暗示
        
        Args:
            req: PK请求
            
        Returns:
            AgentResp: PK演讲内容
        """
        try:
            # 构建上下文
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            can_shoot = self._safe_load_variable("can_shoot", True)
            current_day = self._get_current_day()
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化开枪信息
            shoot_info = "can shoot" if can_shoot else "already shot"
            
            # 格式化prompt（使用SHERIFF_PK_PROMPT）
            prompt = format_prompt(SHERIFF_PK_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info
            })
            
            result = self._llm_generate(prompt, temperature=0.7)
            result = self._truncate_output(result, self.config.MAX_SPEECH_LENGTH)
            
            logger.info(f"[HUNTER SHERIFF PK] Generated (length: {len(result)}, day: {current_day})")
            return AgentResp(success=True, result=result, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF PK] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to generate sheriff PK speech: {e}")
    
    def _interact_sheriff_speech_order(self, req: AgentReq) -> AgentResp:
        """
        处理警长发言顺序选择（与SHERIFF_SPEECH_ORDER_PROMPT一致）
        
        战略考虑：
        - 后发言者有信息优势（可以听到其他人的发言）
        - 先发言者设定基调
        - 考虑哪些玩家应该后发言（可疑玩家先发言，减少信息优势）
        - 考虑哪些玩家应该先发言（可信玩家后发言，可以总结）
        
        Args:
            req: 顺序请求
            
        Returns:
            AgentResp: 发言顺序（"Clockwise" 或 "Counter-clockwise"）
        """
        try:
            # 构建上下文
            my_name = self._safe_load_variable("name", "Unknown")
            alive_players = self._safe_load_variable("alive_players", [])
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化prompt（使用SHERIFF_SPEECH_ORDER_PROMPT）
            prompt = format_prompt(SHERIFF_SPEECH_ORDER_PROMPT, {
                "history": history_str,
                "name": my_name
            })
            
            result = self._llm_generate(prompt, temperature=0.3)
            
            # 解析结果
            order = "Clockwise" if "clockwise" in result.lower() and "counter" not in result.lower() else "Counter-clockwise"
            
            logger.info(f"[HUNTER SHERIFF ORDER] Order: {order}")
            return AgentResp(success=True, result=order, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF ORDER] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to make sheriff speech order decision: {e}")
    
    def _interact_sheriff_transfer(self, req: AgentReq) -> AgentResp:
        """
        处理警徽转移（与SHERIFF_TRANSFER_PROMPT一致）
        
        候选人评估标准：
        - 信任阈值：≥75优秀，60-74良好，50-59可接受，<50避免
        - 高优先级：确认好人、强逻辑分析、准确投票历史、领导能力、关键角色
        - 避免：可疑玩家、弱发言者、不一致投票者、边缘玩家
        
        特殊考虑：
        - 谁能有效使用2倍投票权
        - 谁能领导好人阵营
        - 谁让狼人害怕
        - 谁有清晰思维
        
        警徽销毁：仅在没有合适候选人时（最后手段）
        
        Args:
            req: 转移请求
            
        Returns:
            AgentResp: 转移目标（或 "tear" 销毁警徽）
        """
        try:
            my_name = self._safe_load_variable("name")
            
            # 获取候选人列表并过滤掉自己
            if req.message:
                choices = [name.strip() for name in req.message.split(",") if name.strip() and name.strip() != my_name]
            else:
                choices = []
            
            if not choices:
                logger.warning("[HUNTER SHERIFF TRANSFER] No valid choices available")
                return AgentResp(success=True, result="tear", errMsg=None)
            
            # 构建上下文
            alive_players = self._safe_load_variable("alive_players", [])
            can_shoot = self._safe_load_variable("can_shoot", True)
            
            # 构建历史记录
            speech_history = self._safe_load_variable("speech_history", {})
            history_str = self._format_history(speech_history, max_entries=10)
            
            # 格式化开枪信息
            shoot_info = "can shoot" if can_shoot else "already shot"
            
            # 格式化prompt（使用SHERIFF_TRANSFER_PROMPT）
            prompt = format_prompt(SHERIFF_TRANSFER_PROMPT, {
                "history": history_str,
                "name": my_name,
                "shoot_info": shoot_info,
                "choices": ", ".join(choices)
            })
            
            result = self._llm_generate(prompt, temperature=0.2)
            
            # 解析结果
            if "tear" in result.lower() or "destroy" in result.lower():
                target = "tear"
            else:
                target = self._validate_player_name(result.strip(), choices)
            
            logger.info(f"[HUNTER SHERIFF TRANSFER] Target: {target}")
            return AgentResp(success=True, result=target, errMsg=None)
            
        except Exception as e:
            logger.error(f"[HUNTER SHERIFF TRANSFER] Error: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to make sheriff transfer decision: {e}")
