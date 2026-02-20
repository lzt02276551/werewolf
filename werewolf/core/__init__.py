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
from .base_good_config import BaseGoodConfig
from .base_good_agent import BaseGoodAgent
from .base_wolf_config import BaseWolfConfig
from .base_wolf_agent import BaseWolfAgent
from .llm_detectors import (
    BaseLLMDetector,
    InjectionDetector,
    FalseQuoteDetector,
    SpeechQualityEvaluator,
    MessageParser,
    create_llm_detectors
)
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
    'BaseGoodConfig',
    'BaseGoodAgent',
    'BaseWolfConfig',
    'BaseWolfAgent',
    'BaseLLMDetector',
    'InjectionDetector',
    'FalseQuoteDetector',
    'SpeechQualityEvaluator',
    'MessageParser',
    'create_llm_detectors',
    'WerewolfException',
    'InvalidGameStateError',
    'InvalidPlayerError',
    'ConfigurationError',
    'ComponentError',
]
