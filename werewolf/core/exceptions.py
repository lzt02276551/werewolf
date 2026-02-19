"""
自定义异常类

定义项目中使用的所有自定义异常
"""

from typing import Optional


class WerewolfException(Exception):
    """狼人杀项目基础异常类"""
    
    def __init__(self, message: str = "An error occurred in Werewolf game"):
        self.message = message
        super().__init__(self.message)


class InvalidGameStateError(WerewolfException):
    """游戏状态无效异常"""
    
    def __init__(self, message: str = "Invalid game state", details: Optional[dict] = None):
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class InvalidPlayerError(WerewolfException):
    """玩家数据无效异常"""
    
    def __init__(self, player: str, reason: str = "Invalid player data"):
        self.player = player
        self.reason = reason
        super().__init__(f"Player '{player}': {reason}")


class ConfigurationError(WerewolfException):
    """配置错误异常"""
    
    def __init__(self, message: str = "Configuration error", config_key: Optional[str] = None):
        self.config_key = config_key
        if config_key:
            message = f"{message} (key: {config_key})"
        super().__init__(message)


class ComponentError(WerewolfException):
    """组件错误异常"""
    
    def __init__(self, component_name: str, message: str = "Component error"):
        self.component_name = component_name
        super().__init__(f"[{component_name}] {message}")


class DetectionError(ComponentError):
    """检测器错误异常"""
    
    def __init__(self, detector_name: str, message: str = "Detection failed"):
        super().__init__(detector_name, message)


class AnalysisError(ComponentError):
    """分析器错误异常"""
    
    def __init__(self, analyzer_name: str, message: str = "Analysis failed"):
        super().__init__(analyzer_name, message)


class DecisionError(ComponentError):
    """决策器错误异常"""
    
    def __init__(self, decision_maker_name: str, message: str = "Decision failed"):
        super().__init__(decision_maker_name, message)
