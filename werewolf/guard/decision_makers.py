"""
决策引擎 - 应用策略模式和责任链模式
将守卫和投票决策逻辑独立出来
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from agent_build_sdk.utils.logger import logger


class DecisionStrategy(ABC):
    """
    决策策略抽象基类（策略模式）
    """
    
    @abstractmethod
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        执行决策
        
        Args:
            candidates: 候选人列表
            context: 决策上下文
        
        Returns:
            (目标, 原因, 置信度)
        """
        pass


class GuardDecisionStrategy(DecisionStrategy):
    """
    守卫决策策略
    
    决策流程：
    1. 首夜空守（防止奶穿）
    2. 计算守卫优先级
    3. 预测狼人击杀目标
    4. 选择最优守卫目标
    """
    
    def __init__(self, memory, priority_calculator, wolf_predictor):
        """
        初始化守卫决策策略
        
        Args:
            memory: 记忆系统
            priority_calculator: 优先级计算器
            wolf_predictor: 狼人目标预测器
        """
        self.memory = memory
        self.priority_calculator = priority_calculator
        self.wolf_predictor = wolf_predictor
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """执行守卫决策"""
        night_count = context.get('night_count', 0)
        
        # Step 1: 首夜空守
        if night_count == 1:
            return "", "First night empty guard - prevent milk penetration", 100
        
        # Step 2: 验证候选人
        if not candidates:
            return "", "No valid candidates available", 0
        
        my_name = context.get('my_name')
        valid_candidates = [c for c in candidates if c and isinstance(c, str) and c != my_name]
        
        if not valid_candidates:
            return "", "No valid candidates (cannot guard self)", 0
        
        # Step 3: 计算守卫优先级
        choices_with_priority = []
        
        for candidate in valid_candidates:
            try:
                priority = self.priority_calculator.calculate(candidate, context)
                
                if priority <= 0:
                    continue
                
                wolf_target_prob = self.wolf_predictor.predict_single(candidate, context)
                reason = self._get_guard_reason(candidate, priority, context)
                
                # 调整优先级（加入狼人目标预测）
                adjusted_priority = priority + (wolf_target_prob * 25)
                
                choices_with_priority.append((candidate, adjusted_priority, wolf_target_prob, reason))
                
            except Exception as e:
                logger.error(f"[GuardDecision] Failed to process {candidate}: {e}")
                continue
        
        # Step 4: 排序并选择
        if not choices_with_priority:
            return "", "No valid targets after filtering (empty guard)", 100
        
        choices_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        target, priority, wolf_prob, reason = choices_with_priority[0]
        
        # Step 5: 计算置信度
        confidence = self._calculate_confidence(priority, wolf_prob, context)
        
        logger.info(f"[GuardDecision] Selected {target} (priority: {priority:.1f}, confidence: {confidence})")
        
        return target, reason, confidence
    
    def _get_guard_reason(self, player: str, priority: float, context: Dict[str, Any]) -> str:
        """获取守卫原因"""
        role_checker = context.get('role_checker')
        
        if not role_checker:
            return f"Priority score: {priority:.1f}"
        
        if role_checker.is_confirmed_seer(player):
            return "Confirmed Seer - highest priority"
        elif role_checker.is_likely_seer(player):
            return "Suspected Seer - high priority"
        elif role_checker.is_sheriff(player):
            return "Sheriff - leadership role"
        elif role_checker.is_likely_witch(player):
            return "Suspected Witch - has poison"
        elif role_checker.is_likely_hunter(player):
            return "Hunter - low priority (let be bait)"
        elif priority >= 70:
            return "High trust strong villager"
        elif priority >= 50:
            return "Medium trust player"
        else:
            return "Low priority target"
    
    def _calculate_confidence(self, priority: float, wolf_prob: float, context: Dict[str, Any]) -> int:
        """计算置信度"""
        confidence = 70  # 基础置信度
        
        trust_score = context.get('trust_score', 50)
        
        if priority > 90:
            confidence += 15
        elif priority > 80:
            confidence += 10
        
        if wolf_prob > 0.70:
            confidence += 10
        elif wolf_prob > 0.60:
            confidence += 5
        
        if trust_score > 80:
            confidence += 10
        elif trust_score > 70:
            confidence += 5
        
        return min(100, max(0, confidence))


class VoteDecisionStrategy(DecisionStrategy):
    """
    投票决策策略
    
    决策流程：
    1. 计算每个候选人的狼人概率
    2. 分析投票模式
    3. 检查注入攻击、虚假引用等
    4. 计算综合投票分数
    5. 选择最可疑的目标
    """
    
    def __init__(self, memory, wolf_analyzer, voting_analyzer, trust_manager):
        """
        初始化投票决策策略
        
        Args:
            memory: 记忆系统
            wolf_analyzer: 狼人概率分析器
            voting_analyzer: 投票模式分析器
            trust_manager: 信任分数管理器
        """
        self.memory = memory
        self.wolf_analyzer = wolf_analyzer
        self.voting_analyzer = voting_analyzer
        self.trust_manager = trust_manager
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """执行投票决策"""
        # 验证候选人
        if not candidates:
            return "", "No valid candidates available", 0
        
        valid_candidates = [c for c in candidates if c and isinstance(c, str)]
        
        if not valid_candidates:
            return "", "No valid candidates available", 0
        
        # 分析每个候选人
        choices_with_analysis = []
        
        for candidate in valid_candidates:
            try:
                wolf_prob = self.wolf_analyzer.analyze(candidate)
                trust_score = self.trust_manager.get_score(candidate)
                voting_pattern = self.voting_analyzer.analyze(candidate)
                
                # 计算投票分数
                vote_score = self._calculate_vote_score(
                    candidate, wolf_prob, trust_score, voting_pattern
                )
                
                reason = self._get_vote_reason(candidate, wolf_prob, trust_score, voting_pattern)
                
                choices_with_analysis.append((candidate, wolf_prob, trust_score, vote_score, reason))
                
            except Exception as e:
                logger.error(f"[VoteDecision] Failed to analyze {candidate}: {e}")
                choices_with_analysis.append((candidate, 0.5, 50, 50, "Analysis failed"))
        
        # 排序并选择
        if not choices_with_analysis:
            return valid_candidates[0], "No valid targets", 0
        
        choices_with_analysis.sort(key=lambda x: x[3], reverse=True)
        
        target, wolf_prob, trust_score, vote_score, reason = choices_with_analysis[0]
        
        # 计算置信度
        confidence = self._calculate_confidence(target, vote_score, wolf_prob)
        
        logger.info(f"[VoteDecision] Selected {target} (wolf_prob: {wolf_prob:.2f}, confidence: {confidence})")
        
        return target, reason, confidence
    
    def _calculate_vote_score(self, player: str, wolf_prob: float, trust_score: float, 
                             voting_pattern: str) -> float:
        """计算投票分数"""
        # 基础分数（信任分数越低，投票分数越高）
        vote_score = 100 - trust_score
        
        # 投票模式加成
        pattern_bonus = {
            "protecting_wolves": 30,
            "charging": 20,
            "swaying": 15,
            "accurate": -25,
            "unknown": 0
        }
        vote_score += pattern_bonus.get(voting_pattern, 0)
        
        # 注入攻击加成（安全获取）
        injection_suspects = self.memory.load_variable("injection_suspects")
        if injection_suspects and isinstance(injection_suspects, dict) and player in injection_suspects:
            injection_type = injection_suspects[player]
            if injection_type == "system_fake":
                vote_score += 40
            elif injection_type == "status_fake":
                vote_score += 30
            else:  # benign
                vote_score -= 15
        
        # 虚假引用加成（安全获取）
        false_quotations = self.memory.load_variable("false_quotations")
        if false_quotations and isinstance(false_quotations, list):
            for fq in false_quotations:
                if isinstance(fq, dict) and fq.get("accuser") == player:
                    vote_score += 25
                    break
        
        # 状态矛盾加成（安全获取）
        player_status_claims = self.memory.load_variable("player_status_claims")
        if player_status_claims and isinstance(player_status_claims, dict):
            if player in player_status_claims and player_status_claims[player]:
                vote_score += 35
        
        return vote_score
    
    def _get_vote_reason(self, player: str, wolf_prob: float, trust_score: float, 
                        voting_pattern: str) -> str:
        """获取投票原因"""
        reasons = []
        
        if trust_score < 20:
            reasons.append("Very low trust score")
        elif trust_score < 40:
            reasons.append("Low trust score")
        
        if wolf_prob >= 0.85:
            reasons.append("Very high wolf probability")
        elif wolf_prob >= 0.70:
            reasons.append("High wolf probability")
        
        pattern_reasons = {
            "protecting_wolves": "Always votes good players (protecting wolves)",
            "charging": "Charging wolf behavior",
            "swaying": "Swaying/following behavior",
            "accurate": "Accurate voting (likely good)"
        }
        if voting_pattern in pattern_reasons:
            reasons.append(pattern_reasons[voting_pattern])
        
        # 注入攻击（安全获取）
        injection_suspects = self.memory.load_variable("injection_suspects")
        if injection_suspects and isinstance(injection_suspects, dict) and player in injection_suspects:
            injection_type = injection_suspects[player]
            if injection_type == "system_fake":
                reasons.append("Type 1 injection: Pretending to be Host")
            elif injection_type == "status_fake":
                reasons.append("Type 2 injection: Faking player status")
        
        # 虚假引用（安全获取）
        false_quotations = self.memory.load_variable("false_quotations")
        if false_quotations and isinstance(false_quotations, list):
            for fq in false_quotations:
                if isinstance(fq, dict) and fq.get("accuser") == player:
                    reasons.append("False quotation detected")
                    break
        
        # 状态矛盾（安全获取）
        player_status_claims = self.memory.load_variable("player_status_claims")
        if player_status_claims and isinstance(player_status_claims, dict):
            if player in player_status_claims and player_status_claims[player]:
                reasons.append("Status contradiction: Claims dead but still speaking")
        
        return "; ".join(reasons) if reasons else "Neutral analysis"
    
    def _calculate_confidence(self, target: str, vote_score: float, wolf_prob: float) -> int:
        """计算置信度"""
        confidence = 70  # 基础置信度
        
        if vote_score > 140:
            confidence += 15
        elif vote_score > 130:
            confidence += 10
        
        if wolf_prob > 0.90:
            confidence += 10
        elif wolf_prob > 0.85:
            confidence += 5
        
        # 检查系统伪造注入
        injection_suspects = self.memory.load_variable("injection_suspects") or {}
        if target in injection_suspects and injection_suspects[target] == "system_fake":
            confidence += 15
        
        # 检查状态矛盾
        player_status_claims = self.memory.load_variable("player_status_claims") or {}
        if target in player_status_claims and player_status_claims[target]:
            confidence += 10
        
        # 检查虚假引用
        false_quotations = self.memory.load_variable("false_quotations") or []
        for fq in false_quotations:
            if isinstance(fq, dict) and fq.get("accuser") == target:
                confidence += 5
                break
        
        return min(100, max(0, confidence))


class DecisionEngine:
    """
    决策引擎（门面模式）
    
    统一管理各种决策策略
    """
    
    def __init__(self, guard_strategy: GuardDecisionStrategy, vote_strategy: VoteDecisionStrategy):
        """
        初始化决策引擎
        
        Args:
            guard_strategy: 守卫决策策略
            vote_strategy: 投票决策策略
        """
        self.guard_strategy = guard_strategy
        self.vote_strategy = vote_strategy
    
    def decide_guard(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        决定守卫目标
        
        Args:
            candidates: 候选人列表
            context: 决策上下文
        
        Returns:
            (目标, 原因, 置信度)
        """
        return self.guard_strategy.decide(candidates, context)
    
    def decide_vote(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        决定投票目标
        
        Args:
            candidates: 候选人列表
            context: 决策上下文
        
        Returns:
            (目标, 原因, 置信度)
        """
        return self.vote_strategy.decide(candidates, context)



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


class VoteDecisionMaker:
    """企业级投票决策器"""
    
    def __init__(self, config):
        self.config = config
        self.memory = None
        self.trust_manager = None
        
        # 延迟初始化分析器（避免循环依赖）
        self._wolf_analyzer = None
        self._voting_analyzer = None
    
    def set_dependencies(self, memory, trust_manager):
        """设置依赖（依赖注入）"""
        self.memory = memory
        self.trust_manager = trust_manager
    
    def set_analyzers(self, wolf_analyzer, voting_analyzer):
        """设置分析器（依赖注入）"""
        self._wolf_analyzer = wolf_analyzer
        self._voting_analyzer = voting_analyzer
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str, int]:
        """
        投票决策（企业级版本）
        
        Args:
            candidates: 候选人列表
            context: 决策上下文（包含my_name等）
            
        Returns:
            (目标, 原因, 置信度)
        """
        my_name = context.get('my_name', '')
        
        # 过滤候选人
        valid_candidates = [c for c in candidates if c and c != my_name]
        if not valid_candidates:
            return candidates[0] if candidates else "", "Fallback vote", 0
        
        # 如果依赖未设置，使用简化逻辑
        if not self.trust_manager or not self._wolf_analyzer or not self._voting_analyzer:
            if self.trust_manager:
                worst_target = min(valid_candidates, key=lambda p: self.trust_manager.get_score(p))
                trust_score = self.trust_manager.get_score(worst_target)
                return worst_target, f"Vote lowest trust player (trust: {trust_score:.1f})", 70
            else:
                return valid_candidates[0], "Fallback vote (no trust manager)", 50
        
        # 企业级决策逻辑
        choices_with_analysis = []
        
        for candidate in valid_candidates:
            try:
                # 分析狼人概率
                wolf_prob = self._wolf_analyzer.analyze(candidate)
                trust_score = self.trust_manager.get_score(candidate)
                voting_pattern = self._voting_analyzer.analyze(candidate)
                
                # 计算投票分数
                vote_score = self._calculate_vote_score(candidate, wolf_prob, trust_score, voting_pattern)
                
                # 生成原因
                reason = self._get_vote_reason(candidate, wolf_prob, trust_score, voting_pattern)
                
                choices_with_analysis.append((candidate, wolf_prob, trust_score, vote_score, reason))
                
            except Exception as e:
                logger.error(f"[VoteDecision] Failed to analyze {candidate}: {e}")
                choices_with_analysis.append((candidate, 0.5, 50, 50, "Analysis failed"))
        
        if not choices_with_analysis:
            return valid_candidates[0], "No valid targets", 0
        
        # 排序并选择
        choices_with_analysis.sort(key=lambda x: x[3], reverse=True)
        target, wolf_prob, trust_score, vote_score, reason = choices_with_analysis[0]
        
        # 计算置信度
        confidence = 70
        if vote_score > 140:
            confidence = 90
        elif vote_score > 130:
            confidence = 85
        elif vote_score > 120:
            confidence = 80
        
        logger.info(f"[VoteDecision] Selected {target} (wolf_prob: {wolf_prob:.2f}, vote_score: {vote_score:.1f}, confidence: {confidence})")
        
        return target, reason, confidence
    
    def _calculate_vote_score(self, player: str, wolf_prob: float, trust_score: float, voting_pattern: str) -> float:
        """计算投票分数"""
        from .validators import MemoryValidator
        
        # 基础分数（信任分数越低，投票分数越高）
        vote_score = 100 - trust_score
        
        # 狼人概率加成
        vote_score += wolf_prob * 50
        
        # 投票模式加成
        pattern_bonus = {
            "protecting_wolves": self.config.VOTE_BONUS_PROTECTING_WOLVES,
            "charging": self.config.VOTE_BONUS_CHARGING,
            "swaying": self.config.VOTE_BONUS_SWAYING,
            "accurate": self.config.VOTE_PENALTY_ACCURATE,
            "unknown": 0
        }
        vote_score += pattern_bonus.get(voting_pattern, 0)
        
        # 注入攻击加成
        injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
        if player in injection_suspects:
            injection_type = injection_suspects[player]
            if injection_type == "system_fake":
                vote_score += self.config.VOTE_BONUS_SYSTEM_FAKE
            elif injection_type == "status_fake":
                vote_score += self.config.VOTE_BONUS_STATUS_FAKE
            else:  # benign
                vote_score += self.config.VOTE_PENALTY_BENIGN
        
        # 虚假引用加成
        false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
        for fq in false_quotations:
            if isinstance(fq, dict) and fq.get("accuser") == player:
                vote_score += self.config.VOTE_BONUS_FALSE_QUOTATION
                break
        
        # 状态矛盾加成
        player_status_claims = MemoryValidator.safe_load_dict(self.memory, "player_status_claims")
        if player in player_status_claims and player_status_claims[player]:
            vote_score += self.config.VOTE_BONUS_STATUS_CONTRADICTION
        
        return vote_score
    
    def _get_vote_reason(self, player: str, wolf_prob: float, trust_score: float, voting_pattern: str) -> str:
        """获取投票原因"""
        from .validators import MemoryValidator
        
        reasons = []
        
        # 信任分数
        if trust_score < self.config.TRUST_VERY_LOW:
            reasons.append("Very low trust score")
        elif trust_score < self.config.TRUST_LOW:
            reasons.append("Low trust score")
        
        # 狼人概率
        if wolf_prob >= self.config.WOLF_PROB_VERY_HIGH:
            reasons.append("Very high wolf probability")
        elif wolf_prob >= self.config.WOLF_PROB_HIGH:
            reasons.append("High wolf probability")
        
        # 投票模式
        pattern_reasons = {
            "protecting_wolves": "Always votes good players (protecting wolves)",
            "charging": "Charging wolf behavior",
            "swaying": "Swaying/following behavior",
            "accurate": "Accurate voting (likely good)"
        }
        if voting_pattern in pattern_reasons:
            reasons.append(pattern_reasons[voting_pattern])
        
        # 注入攻击
        injection_suspects = MemoryValidator.safe_load_dict(self.memory, "injection_suspects")
        if player in injection_suspects:
            injection_type = injection_suspects[player]
            if injection_type == "system_fake":
                reasons.append("Type 1 injection: Pretending to be Host")
            elif injection_type == "status_fake":
                reasons.append("Type 2 injection: Faking player status")
        
        # 虚假引用
        false_quotations = MemoryValidator.safe_load_list(self.memory, "false_quotations")
        for fq in false_quotations:
            if isinstance(fq, dict) and fq.get("accuser") == player:
                reasons.append("False quotation detected")
                break
        
        # 状态矛盾
        player_status_claims = MemoryValidator.safe_load_dict(self.memory, "player_status_claims")
        if player in player_status_claims and player_status_claims[player]:
            reasons.append("Status contradiction: Claims dead but still speaking")
        
        return "; ".join(reasons) if reasons else "Neutral analysis"
