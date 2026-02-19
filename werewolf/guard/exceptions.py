"""
守卫代理人自定义异常类

统一异常处理,提升代码可维护性和调试效率
"""


class GuardException(Exception):
    """守卫代理人基础异常类"""
    pass


class InvalidGameStateError(GuardException):
    """游戏状态无效异常"""
    
    def __init__(self, message: str = "Invalid game state"):
        self.message = message
        super().__init__(self.message)


class InvalidPlayerError(GuardException):
    """玩家数据无效异常"""
    
    def __init__(self, player: str, reason: str = "Invalid player data"):
        self.player = player
        self.reason = reason
        self.message = f"Player {player}: {reason}"
        super().__init__(self.message)


class DecisionError(GuardException):
    """决策失败异常"""
    
    def __init__(self, decision_type: str, reason: str):
        self.decision_type = decision_type
        self.reason = reason
        self.message = f"Decision failed ({decision_type}): {reason}"
        super().__init__(self.message)


class DetectionError(GuardException):
    """检测失败异常"""
    
    def __init__(self, detector_type: str, reason: str):
        self.detector_type = detector_type
        self.reason = reason
        self.message = f"Detection failed ({detector_type}): {reason}"
        super().__init__(self.message)


class AnalysisError(GuardException):
    """分析失败异常"""
    
    def __init__(self, analyzer_type: str, reason: str):
        self.analyzer_type = analyzer_type
        self.reason = reason
        self.message = f"Analysis failed ({analyzer_type}): {reason}"
        super().__init__(self.message)


class ConfigurationError(GuardException):
    """配置错误异常"""
    
    def __init__(self, config_key: str, reason: str):
        self.config_key = config_key
        self.reason = reason
        self.message = f"Configuration error ({config_key}): {reason}"
        super().__init__(self.message)


class MemoryError(GuardException):
    """内存操作异常"""
    
    def __init__(self, variable_name: str, reason: str):
        self.variable_name = variable_name
        self.reason = reason
        self.message = f"Memory error ({variable_name}): {reason}"
        super().__init__(self.message)
