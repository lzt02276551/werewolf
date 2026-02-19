"""
Core module - 核心基础设施

提供所有角色共用的抽象基类和核心功能
"""

from .base_agent import BaseAgent
from .base_components import (
    BaseDetector,
    BaseAnalyzer,
    BaseDecisionMaker,
    BaseTrustManager,
    BaseMemoryDAO
)
from .game_state import GameState, GamePhase
from .config import BaseConfig
from .exceptions import (
    WerewolfException,
    InvalidGameStateError,
    InvalidPlayerError,
    ConfigurationError,
    ComponentError
)

__all__ = [
    'BaseAgent',
    'BaseDetector',
    'BaseAnalyzer',
    'BaseDecisionMaker',
    'BaseTrustManager',
    'BaseMemoryDAO',
    'GameState',
    'GamePhase',
    'BaseConfig',
    'WerewolfException',
    'InvalidGameStateError',
    'InvalidPlayerError',
    'ConfigurationError',
    'ComponentError',
]
