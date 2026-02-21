"""
决策引擎 - 应用策略模式和责任链模式
将守卫和投票决策逻辑独立出来
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from agent_build_sdk.utils.logger import logger











class GuardDecisionMaker:
    """企业级守卫决策器"""
    
    def __init__(self, config):
        self.config = config
        self.memory = None
        self.trust_manager = None
        
        # 延迟初始化分析器（避免循环依赖）
        self._role_estimator = None
        self._wolf_kill_predictor = None
        self._guard_priority_calculator = None
    
    def set_dependencies(self, memory, trust_manager):
        """设置依赖（依赖注入）"""
        self.memory = memory
        self.trust_manager = trust_manager
    
    def set_analyzers(self, role_estimator, wolf_kill_predictor, guard_priority_calculator):
        """设置分析器（依赖注入）"""
        self._role_estimator = role_estimator
        self._wolf_kill_predictor = wolf_kill_predictor
        self._guard_priority_calculator = guard_priority_calculator
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        守卫决策（企业级版本）
        
        Args:
            candidates: 候选人列表
            context: 决策上下文（包含my_name, night_count, last_guarded等）
            
        Returns:
            (目标, 原因, 置信度)
        """
        my_name = context.get('my_name', '')
        night_count = context.get('night_count', 0)
        last_guarded = context.get('last_guarded', '')
        
        # 首夜空守
        if night_count == 1:
            return "", "First night empty guard - prevent milk penetration", 100
        
        # 过滤候选人
        valid_candidates = [c for c in candidates if c and c != my_name and c != last_guarded]
        if not valid_candidates:
            return "", "No valid candidates (cannot guard self or repeat)", 0
        
        # 如果依赖未设置，使用简化逻辑
        if not self.trust_manager or not self._guard_priority_calculator or not self._wolf_kill_predictor:
            if self.trust_manager:
                best_target = max(valid_candidates, key=lambda p: self.trust_manager.get_score(p))
                trust_score = self.trust_manager.get_score(best_target)
                return best_target, f"Guard highest trust player (trust: {trust_score:.1f})", 70
            else:
                return valid_candidates[0], "Fallback guard (no trust manager)", 50
        
        # 企业级决策逻辑
        choices_with_priority = []
        
        for candidate in valid_candidates:
            try:
                # 计算守卫优先级
                priority = self._guard_priority_calculator.calculate(candidate, {
                    "my_name": my_name,
                    "night_count": night_count,
                    "role_checker": self._role_estimator
                })
                
                # 预测狼人击杀概率
                wolf_target_prob = self._wolf_kill_predictor.predict_single(candidate, {
                    "night_count": night_count
                })
                
                # 调整优先级
                adjusted_priority = priority + (wolf_target_prob * self.config.GUARD_PRIORITY_WOLF_TARGET_BONUS)
                
                choices_with_priority.append((candidate, adjusted_priority, wolf_target_prob))
                
            except Exception as e:
                logger.error(f"[GuardDecision] Failed to process {candidate}: {e}")
                continue
        
        if not choices_with_priority:
            return "", "No valid targets after filtering (empty guard)", 100
        
        # 排序并选择
        choices_with_priority.sort(key=lambda x: x[1], reverse=True)
        target, priority, wolf_prob = choices_with_priority[0]
        
        # 生成原因
        if self._role_estimator:
            if self._role_estimator.is_confirmed_seer(target):
                reason = "Confirmed Seer - highest priority"
            elif self._role_estimator.is_likely_seer(target):
                reason = "Suspected Seer - high priority"
            elif self._role_estimator.is_sheriff(target):
                reason = "Sheriff - leadership role"
            else:
                reason = f"High priority target (priority: {priority:.1f}, wolf target prob: {wolf_prob:.2f})"
        else:
            reason = f"Priority score: {priority:.1f}"
        
        # 计算置信度
        confidence = 70
        if priority > 90:
            confidence = 90
        elif priority > 80:
            confidence = 85
        elif priority > 70:
            confidence = 80
        
        return target, reason, confidence


