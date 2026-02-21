# -*- coding: utf-8 -*-
"""
预言家代理人决策器模块

实现各种决策功能：投票、检查、警长选举等
符合企业级标准，所有决策器继承BaseDecisionMaker
"""

from typing import Dict, List, Tuple, Optional, Any
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDecisionMaker
from .config import SeerConfig
from .analyzers import WolfProbabilityEstimator
import re


    



class CheckDecisionMaker(BaseDecisionMaker):
    """检查决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, candidates: List[str], context: Dict[str, Any]) -> Tuple[str, str]:
        """
        检查决策
        
        Args:
            candidates: 候选人列表
            context: 上下文信息
            
        Returns:
            (目标玩家, 原因)
        """
        try:
            if not candidates:
                return ('No.1', 'No candidates available')
            
            return (candidates[0], 'First available candidate')
        except Exception as e:
            self.logger.error(f"Check decision failed: {e}")
            return ('No.1', f"Decision error: {e}")










class IdentityRevealDecisionMaker(BaseDecisionMaker):
    """身份揭示决策器"""
    
    def __init__(self, config: SeerConfig):
        super().__init__(config)
    
    def decide(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        身份揭示决策
        
        Args:
            context: 上下文信息
            
        Returns:
            (是否揭示, 原因)
        """
        try:
            checked_players = context.get('checked_players', {})
            game_state = context.get('game_state', {})
            
            # 有狼人检查 → 立即揭示
            for player, data in checked_players.items():
                if data.get('is_wolf'):
                    return (True, 'Have wolf check - must reveal to guide voting')
            
            # 假预言家出现 → 反击
            if game_state.get('fake_seer_present'):
                return (True, 'Fake seer appeared - must counter-claim')
            
            # 好人阵营劣势 → 必须揭示
            wolves_dead = game_state.get('wolves_dead', 0)
            goods_dead = game_state.get('goods_dead', 0)
            if wolves_dead == 0 and goods_dead >= 3:
                return (True, 'Good faction losing - must provide leadership')
            
            # 警长选举 → 考虑揭示
            if game_state.get('sheriff_election'):
                if len(checked_players) >= 2:
                    return (True, 'Sheriff election with multiple checks - good timing')
            
            return (False, 'Stay hidden to gather more information')
        except Exception as e:
            self.logger.error(f"Identity reveal decision failed: {e}")
            return (False, f"Decision error: {e}")
