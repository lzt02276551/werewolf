"""
决策引擎 - 应用策略模式和责任链模式
将守卫和投票决策逻辑独立出来

守卫决策策略：
1. 首夜空守（防止奶穿）
2. 优先守护确认预言家
3. 其次守护疑似预言家
4. 再次守护警长
5. 最后守护高信任玩家
6. 避免守护猎人（让其成为诱饵）
7. 不能连续守护同一人
"""
from typing import List, Tuple, Optional, Dict, Any
from agent_build_sdk.utils.logger import logger


class GuardDecisionMaker:
    """
    企业级守卫决策器
    
    职责：
    1. 首夜空守策略（防止奶穿）
    2. 守护目标优先级计算
    3. 狼人击杀预测
    4. 守护历史管理
    5. 守护约束验证（不能连续守护同一人）
    """
    
    def __init__(self, config):
        """
        初始化守卫决策器
        
        Args:
            config: 守卫配置对象
        """
        if not config:
            raise ValueError("Config is required for GuardDecisionMaker")
        self.config = config
        self.memory = None
        self.trust_manager = None
        
        # 延迟初始化分析器（避免循环依赖）
        self._role_estimator = None
        self._wolf_kill_predictor = None
        self._guard_priority_calculator = None
    
    def set_dependencies(self, memory, trust_manager):
        """
        设置依赖（依赖注入）
        
        Args:
            memory: 记忆系统
            trust_manager: 信任分数管理器
        """
        if not memory:
            raise ValueError("Memory is required")
        if not trust_manager:
            raise ValueError("Trust manager is required")
        self.memory = memory
        self.trust_manager = trust_manager
    
    def set_analyzers(self, role_estimator, wolf_kill_predictor, guard_priority_calculator):
        """
        设置分析器（依赖注入）
        
        Args:
            role_estimator: 角色估计器
            wolf_kill_predictor: 狼人击杀预测器
            guard_priority_calculator: 守卫优先级计算器
        """
        if not role_estimator:
            raise ValueError("Role estimator is required")
        if not wolf_kill_predictor:
            raise ValueError("Wolf kill predictor is required")
        if not guard_priority_calculator:
            raise ValueError("Guard priority calculator is required")
        
        self._role_estimator = role_estimator
        self._wolf_kill_predictor = wolf_kill_predictor
        self._guard_priority_calculator = guard_priority_calculator
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        守卫决策（企业级版本）
        
        决策流程：
        1. 验证输入
        2. 首夜空守检查
        3. 过滤无效候选人（自己、上次守护的人）
        4. 计算每个候选人的守护优先级
        5. 预测狼人击杀目标
        6. 综合决策
        7. 生成决策原因
        
        Args:
            candidates: 候选人列表
            context: 决策上下文（包含my_name, night_count, last_guarded等）
            
        Returns:
            (目标, 原因, 置信度)
        """
        # 1. 验证输入
        if not candidates:
            logger.warning("[GuardDecision] No candidates provided")
            return "", "No candidates available", 0
        
        if not isinstance(context, dict):
            logger.error("[GuardDecision] Invalid context type")
            return "", "Invalid context", 0
        
        my_name = context.get('my_name', '')
        night_count = context.get('night_count', 0)
        last_guarded = context.get('last_guarded', '')
        
        logger.info(f"[GuardDecision] Night {night_count}: Deciding guard target from {len(candidates)} candidates")
        
        # 2. 首夜空守（防止奶穿）
        if night_count == 1:
            logger.info("[GuardDecision] Night 1: Empty guard to prevent milk penetration")
            return "", "First night empty guard - prevent milk penetration", 100
        
        # 3. 过滤候选人
        valid_candidates = [c for c in candidates if c and c != my_name and c != last_guarded]
        if not valid_candidates:
            logger.warning(f"[GuardDecision] No valid candidates after filtering (my_name={my_name}, last_guarded={last_guarded})")
            return "", "No valid candidates (cannot guard self or repeat)", 0
        
        logger.info(f"[GuardDecision] Valid candidates after filtering: {valid_candidates}")
        
        # 4. 验证依赖完整性（必须全部设置）
        if not self.trust_manager:
            raise ValueError("[GuardDecision] Trust manager is required but not set")
        if not self._guard_priority_calculator:
            raise ValueError("[GuardDecision] Guard priority calculator is required but not set")
        if not self._wolf_kill_predictor:
            raise ValueError("[GuardDecision] Wolf kill predictor is required but not set")
        
        # 5. 企业级决策逻辑
        try:
            choices_with_priority = []
            
            for candidate in valid_candidates:
                try:
                    # 计算守卫优先级
                    priority = self._guard_priority_calculator.calculate(candidate, {
                        "my_name": my_name,
                        "night_count": night_count,
                        "role_checker": self._role_estimator,
                        "trust_scores": context.get('trust_scores', {}),
                        "sheriff": context.get('sheriff')
                    })
                    
                    # 预测狼人击杀概率
                    wolf_target_prob = self._wolf_kill_predictor.predict_single(candidate, {
                        "night_count": night_count,
                        "trust_scores": context.get('trust_scores', {}),
                        "sheriff": context.get('sheriff'),
                        "role_checker": self._role_estimator
                    })
                    
                    # 调整优先级（被击杀概率越高，优先级越高）
                    adjusted_priority = priority + (wolf_target_prob * self.config.GUARD_PRIORITY_WOLF_TARGET_BONUS)
                    
                    choices_with_priority.append((candidate, adjusted_priority, wolf_target_prob, priority))
                    
                    logger.debug(f"[GuardDecision] {candidate}: base_priority={priority:.1f}, "
                               f"wolf_prob={wolf_target_prob:.2f}, adjusted={adjusted_priority:.1f}")
                    
                except Exception as e:
                    logger.error(f"[GuardDecision] Failed to process {candidate}: {e}", exc_info=True)
                    continue
            
            if not choices_with_priority:
                logger.warning("[GuardDecision] No valid targets after analysis, using empty guard")
                return "", "No valid targets after filtering (empty guard)", 100
            
            # 6. 排序并选择最高优先级
            choices_with_priority.sort(key=lambda x: x[1], reverse=True)
            target, adjusted_priority, wolf_prob, base_priority = choices_with_priority[0]
            
            # 7. 生成决策原因
            reason = self._generate_reason(target, base_priority, wolf_prob)
            
            # 8. 计算置信度
            confidence = self._calculate_confidence(adjusted_priority)
            
            logger.info(f"[GuardDecision] ✓ Target: {target}, Priority: {adjusted_priority:.1f}, "
                       f"Confidence: {confidence}, Reason: {reason}")
            
            # 9. 记录决策详情（用于调试）
            logger.debug(f"[GuardDecision] All candidates with priorities: {[(c, p) for c, p, _, _ in choices_with_priority]}")
            
            return target, reason, confidence
            
        except Exception as e:
            logger.error(f"[GuardDecision] Decision failed with exception: {e}", exc_info=True)
            # 重新抛出异常，不使用降级
            raise RuntimeError(f"Guard decision failed: {e}") from e
    
    def _generate_reason(self, target: str, priority: float, wolf_prob: float) -> str:
        """
        生成决策原因
        
        Args:
            target: 守护目标
            priority: 基础优先级
            wolf_prob: 狼人击杀概率
            
        Returns:
            决策原因字符串
        """
        if not self._role_estimator:
            return f"Priority: {priority:.1f}, Wolf target prob: {wolf_prob:.2f}"
        
        # 根据角色生成原因
        if self._role_estimator.is_confirmed_seer(target):
            return "Confirmed Seer - highest priority"
        elif self._role_estimator.is_likely_seer(target):
            return "Suspected Seer - high priority"
        elif self._role_estimator.is_sheriff(target):
            return "Sheriff - leadership role"
        elif priority > 70:
            return f"High value target (priority: {priority:.1f}, wolf target prob: {wolf_prob:.2f})"
        else:
            return f"Priority score: {priority:.1f}"
    
    def _calculate_confidence(self, adjusted_priority: float) -> int:
        """
        计算决策置信度
        
        Args:
            adjusted_priority: 调整后的优先级
            
        Returns:
            置信度 (0-100)
        """
        if adjusted_priority > 90:
            return 90
        elif adjusted_priority > 80:
            return 85
        elif adjusted_priority > 70:
            return 80
        elif adjusted_priority > 60:
            return 75
        else:
            return 70


