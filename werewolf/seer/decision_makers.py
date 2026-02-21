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










# IdentityRevealDecisionMaker 已删除
# 原因：该类从未被使用，已在 seer_agent.py 中注释掉
# 如需实现身份公开决策功能，请重新设计并集成到 Seer 的讨论发言逻辑中
