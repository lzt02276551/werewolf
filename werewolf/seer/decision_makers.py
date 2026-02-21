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
    检查决策器（预言家特有）
    
    实现提示词中的检查优先级决策树：
    1. 最高优先级：恶意注入、虚假引用、假预言家
    2. 高优先级：保护狼人的投票者、矛盾制造者、攻击死者
    3. 中优先级：摇摆投票者、防御性玩家
    4. 低优先级：逻辑发言者、准确投票者
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
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str]:
        """
        检查决策（实现提示词中的决策树）
        
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
            self.logger.info(f"[CHECK DECISION] Target: {target}, Score: {scores[target]}, Reason: {reason}")
            return (target, reason)
            
        except Exception as e:
            self.logger.error(f"Check decision failed: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"检查决策失败: {e}") from e










# IdentityRevealDecisionMaker 已删除
# 原因：该类从未被使用，已在 seer_agent.py 中注释掉
# 如需实现身份公开决策功能，请重新设计并集成到 Seer 的讨论发言逻辑中
