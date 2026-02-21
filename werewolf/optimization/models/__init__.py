"""
数据模型模块

使用Pydantic定义输入验证和配置数据模型
"""

from .validation import PlayerName, CandidateList, VoteDecisionInput, GameState, PlayerState
from .config import DimensionConfig, ScoringConfig, CacheConfig, LLMConfig, OptimizationConfig

__all__ = [
    'PlayerName',
    'CandidateList',
    'VoteDecisionInput',
    'GameState',
    'PlayerState',
    'DimensionConfig',
    'ScoringConfig',
    'CacheConfig',
    'LLMConfig',
    'OptimizationConfig',
]
