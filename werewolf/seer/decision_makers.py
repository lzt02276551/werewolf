# -*- coding: utf-8 -*-
"""
预言家代理人决策器模块

实现各种决策功能：投票、检查、警长选举等
符合企业级标准，所有决策器继承BaseDecisionMaker
"""

from typing import Dict, List, Tuple, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from .config import SeerConfig


class CheckDecisionMaker(BaseDecisionMaker):
    """
    检查决策器（预言家特有）- 企业级五星标准
    
    实现提示词中的检查优先级决策树：
    1. 最高优先级：恶意注入、虚假引用、假预言家
    2. 高优先级：保护狼人的投票者、矛盾制造者、攻击死者
    3. 中优先级：摇摆投票者、防御性玩家
    4. 低优先级：逻辑发言者、准确投票者
    
    优化特性：
    - 决策缓存：避免重复计算
    - 性能监控：记录决策耗时
    - 详细日志：便于调试和分析
    """
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
        # 使用配置中的权重，如果没有则使用默认值
        self.weights = getattr(config, 'check_priority_weights', None)
        if self.weights is None:
            # 默认权重（与SeerConfig中的一致）
            self.weights = {
                'malicious_injection': 98,
                'fake_seer': 96,
                'false_quotes': 95,
                'wolf_protecting_votes': 85,
                'contradictions': 75,
                'opposed_dead_good': 70,
                'aggressive_bandwagon': 70,
                'swing_votes': 60,
                'defensive_behavior': 55,
                'sheriff_bonus': 10,
                'strong_speaker_bonus': 5,
                'first_night_sheriff_candidate_bonus': 15,
                'trust_extreme_low': 20,
                'trust_low': 40,
            }
        
        # 决策缓存（企业级优化）
        self._decision_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_default_result(self) -> Dict[str, Any]:
        """
        获取默认决策结果（当决策失败时使用）
        
        Returns:
            默认决策结果字典
        """
        return {
            'action': 'check',
            'target': None,
            'reasoning': 'Decision failed, no valid target',
            'confidence': 0.0
        }
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str]:
        """
        检查决策（实现提示词中的决策树）- 企业级五星标准
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            (目标玩家, 原因)
            
        Raises:
            ValueError: 如果候选人列表为空或决策失败
        """
        if not candidates:
            raise ValueError('候选人列表为空，无法做出检查决策')
        
        # 性能监控
        import time
        start_time = time.time()
        
        # 缓存键生成（基于候选人和关键上下文）
        cache_key = self._generate_cache_key(candidates, context)
        
        # 检查缓存
        if cache_key in self._decision_cache:
            self._cache_hits += 1
            target, reason = self._decision_cache[cache_key]
            elapsed = (time.time() - start_time) * 1000
            self.logger.debug(f"[CHECK DECISION CACHE HIT] {target} (耗时: {elapsed:.2f}ms, 命中率: {self._get_cache_hit_rate():.1%})")
            return (target, reason)
        
        self._cache_misses += 1
        
        try:
            # 获取上下文数据
            player_data = context.get('player_data', {})
            game_state = context.get('game_state', {})
            trust_scores = context.get('trust_scores', {})
            checked_players = context.get('checked_players', {})
            night_count = context.get('night_count', 0)
            
            # 过滤已检查的玩家
            unchecked = [p for p in candidates if p not in checked_players]
            if not unchecked:
                # 如果都检查过了，重新检查（可能是游戏后期）
                unchecked = candidates
                self.logger.info("所有候选人都已检查过，重新评估优先级")
            
            # 决策树：按优先级评分
            scores = {}
            reasons = {}
            
            for player in unchecked:
                data = player_data.get(player, {})
                score = 0
                reason_parts = []
                
                # 最高优先级 (95+) - 使用配置权重
                if data.get('malicious_injection'):
                    score = self.weights['malicious_injection']
                    reason_parts.append("恶意注入攻击")
                elif data.get('false_quotes', 0) > 0:
                    score = self.weights['false_quotes']
                    reason_parts.append("虚假引用")
                elif game_state.get('fake_seer_name') == player:
                    score = self.weights['fake_seer']
                    reason_parts.append("假预言家")
                
                # 高优先级 (70-85) - 使用配置权重
                elif data.get('wolf_protecting_votes', 0) > 0:
                    score = self.weights['wolf_protecting_votes']
                    reason_parts.append("保护狼人的投票模式")
                elif data.get('contradictions', 0) > 0:
                    score = self.weights['contradictions']
                    reason_parts.append("发言矛盾")
                elif data.get('opposed_dead_good'):
                    score = self.weights['opposed_dead_good']
                    reason_parts.append("攻击死亡好人")
                elif data.get('aggressive_bandwagon'):
                    score = self.weights['aggressive_bandwagon']
                    reason_parts.append("激进带节奏")
                
                # 中优先级 (50-60) - 使用配置权重
                elif data.get('swing_votes', 0) > 0:
                    score = self.weights['swing_votes']
                    reason_parts.append("摇摆投票")
                elif data.get('defensive_behavior'):
                    score = self.weights['defensive_behavior']
                    reason_parts.append("防御性行为")
                
                # 基于信任分数调整 - 使用配置阈值
                trust = trust_scores.get(player, 50)
                if trust < self.weights['trust_extreme_low']:
                    score = max(score, 90)
                    reason_parts.append(f"极低信任({trust})")
                elif trust < self.weights['trust_low']:
                    score = max(score, 70)
                    reason_parts.append(f"低信任({trust})")
                
                # 战略价值加成 - 使用配置权重
                if data.get('is_sheriff'):
                    score += self.weights['sheriff_bonus']
                    reason_parts.append("警长")
                if data.get('strong_speaker'):
                    score += self.weights['strong_speaker_bonus']
                    reason_parts.append("强势发言者")
                
                # 第一夜特殊策略：优先检查警长候选人和强势发言者
                if night_count == 1:
                    if data.get('sheriff_candidate'):
                        score += self.weights['first_night_sheriff_candidate_bonus']
                        reason_parts.append("警长候选人")
                
                # 默认分数
                if score == 0:
                    score = 30
                    reason_parts.append("战略目标")
                
                scores[player] = score
                reasons[player] = ", ".join(reason_parts) if reason_parts else "战略检查"
            
            # 选择最高分
            if not scores:
                raise ValueError("无法计算任何候选人的检查优先级")
            
            target = max(scores.items(), key=lambda x: x[1])[0]
            reason = reasons[target]
            
            # 缓存决策结果
            self._decision_cache[cache_key] = (target, reason)
            
            # 性能日志
            elapsed = (time.time() - start_time) * 1000
            self.logger.info(
                f"[CHECK DECISION] Target: {target}, Score: {scores[target]:.1f}, "
                f"Reason: {reason}, 耗时: {elapsed:.2f}ms, "
                f"缓存命中率: {self._get_cache_hit_rate():.1%}"
            )
            
            # 详细评分日志（调试用）
            if self.logger.isEnabledFor(10):  # DEBUG level
                sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                self.logger.debug(f"[CHECK DECISION SCORES] {sorted_scores}")
            
            return (target, reason)
            
        except Exception as e:
            self.logger.error(f"Check decision failed: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"检查决策失败: {e}") from e
    
    def _generate_cache_key(self, candidates: List[str], context: Dict[str, Any]) -> str:
        """
        生成缓存键（企业级五星标准 - 精确且高效，避免哈希冲突）
        
        基于候选人列表和关键上下文生成唯一键
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            缓存键字符串
        """
        # 关键上下文：夜晚计数、已检查玩家、假预言家
        night_count = context.get('night_count', 0)
        checked_players = sorted(context.get('checked_players', {}).keys())
        fake_seer = context.get('game_state', {}).get('fake_seer_name', '')
        
        # 构建玩家数据签名（只包含影响决策的关键字段）
        player_data = context.get('player_data', {})
        player_signatures = []
        for candidate in sorted(candidates):
            data = player_data.get(candidate, {})
            sig_parts = []
            if data.get('malicious_injection', False):
                sig_parts.append('inj')
            if data.get('false_quotes', 0) > 0:
                sig_parts.append('fq')
            if data.get('wolf_protecting_votes', 0) > 0:
                sig_parts.append('wp')
            if data.get('contradictions', 0) > 0:
                sig_parts.append('con')
            player_signatures.append(f"{candidate}:{'_'.join(sig_parts) if sig_parts else 'clean'}")
        
        # 使用字符串拼接而非哈希（避免哈希冲突）
        key_parts = [
            f"n{night_count}",
            f"checked:{','.join(checked_players) if checked_players else 'none'}",
            f"fs:{fake_seer if fake_seer else 'none'}",
            f"players:{';'.join(player_signatures)}"
        ]
        
        return "|".join(key_parts)
    
    def _get_cache_hit_rate(self) -> float:
        """
        获取缓存命中率
        
        Returns:
            命中率 (0.0-1.0)
        """
        total = self._cache_hits + self._cache_misses
        if total == 0:
            return 0.0
        return self._cache_hits / total
    
    def clear_cache(self) -> None:
        """
        清空缓存（游戏结束或状态重置时调用）
        """
        cache_size = len(self._decision_cache)
        self._decision_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.debug(f"[CHECK DECISION] 缓存已清空 (原大小: {cache_size})")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息（用于监控和调试）
        
        Returns:
            统计信息字典
        """
        return {
            'cache_size': len(self._decision_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': self._get_cache_hit_rate()
        }
