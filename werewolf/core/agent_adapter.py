"""
Agent适配器

提供从旧架构到新架构的过渡支持
"""

from typing import Dict, Any, Optional
from abc import abstractmethod
import logging

try:
    from agent_build_sdk.sdk.role_agent import BasicRoleAgent
    from agent_build_sdk.model.werewolf_model import AgentResp, AgentReq
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    # 提供Mock类以支持独立测试
    class BasicRoleAgent:
        def __init__(self, role, model_name):
            self.role = role
            self.model_name = model_name
            self.memory = type('Memory', (), {
                'set_variable': lambda self, k, v: None,
                'load_variable': lambda self, k, default=None: default,
                'load_history': lambda self: [],
                'append_history': lambda self, msg: None,
                'clear': lambda self: None
            })()
            self.client = None
        
        def llm_caller(self, prompt):
            return "Mock response"
    
    class AgentResp:
        def __init__(self, success, result, errMsg):
            self.success = success
            self.result = result
            self.errMsg = errMsg
    
    class AgentReq:
        def __init__(self):
            self.status = None
            self.name = None
            self.message = None
            self.round = 0

from .base_agent import BaseAgent
from .config import BaseConfig
from .exceptions import WerewolfException


class AgentAdapter(BasicRoleAgent if SDK_AVAILABLE else object):
    """
    Agent适配器基类
    
    桥接旧SDK架构和新核心架构
    
    使用方法:
    1. 继承此类而不是直接继承BasicRoleAgent
    2. 实现_initialize_components方法
    3. 使用self.config访问配置
    4. 使用self.logger记录日志
    """
    
    def __init__(self, role: str, model_name: str, config: Optional[BaseConfig] = None):
        """
        初始化适配器
        
        Args:
            role: 角色名称
            model_name: 模型名称
            config: 配置对象(可选)
        """
        if SDK_AVAILABLE:
            super().__init__(role, model_name=model_name)
        
        # 使用提供的配置或创建默认配置
        self.config = config or BaseConfig()
        
        # 设置日志
        self.logger = self.config.get_logger(self.__class__.__name__)
        
        # 初始化组件(子类实现)
        try:
            self._initialize_components()
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    @abstractmethod
    def _initialize_components(self) -> None:
        """
        初始化组件(子类必须实现)
        
        在此方法中初始化:
        - Detectors
        - Analyzers
        - DecisionMakers
        等组件
        """
        pass
    
    def _validate_game_state(self, game_state: Dict[str, Any]) -> bool:
        """
        验证游戏状态
        
        Args:
            game_state: 游戏状态字典
            
        Returns:
            是否有效
        """
        if not isinstance(game_state, dict):
            self.logger.error("Game state is not a dictionary")
            return False
        
        # 基本验证
        if 'alive_players' not in game_state:
            self.logger.warning("Game state missing 'alive_players'")
            return False
        
        return True
    
    def _handle_error(
        self,
        error: Exception,
        context: str = "",
        default_result: Any = None
    ) -> Any:
        """
        统一的错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            default_result: 默认返回值
            
        Returns:
            默认结果
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"[{self.__class__.__name__}] {error_msg}")
        
        if isinstance(error, WerewolfException):
            self.logger.error(f"Werewolf exception details: {error}")
        
        return default_result
    
    def _build_context(self) -> Dict[str, Any]:
        """
        构建决策上下文
        
        Returns:
            上下文字典
        """
        return {
            "player_data": self.memory.load_variable("player_data") or {},
            "game_state": self.memory.load_variable("game_state") or {},
            "seer_checks": self.memory.load_variable("seer_checks") or {},
            "voting_results": self.memory.load_variable("voting_results") or {},
            "trust_scores": self.memory.load_variable("trust_scores") or {},
            "voting_history": self.memory.load_variable("voting_history") or {},
            "speech_history": self.memory.load_variable("speech_history") or {},
            "my_name": self.memory.load_variable("name") or "",
            "alive_players": self.memory.load_variable("alive_players") or [],
            "dead_players": self.memory.load_variable("dead_players") or [],
        }
    
    def _safe_get_variable(self, key: str, default: Any = None) -> Any:
        """
        安全地获取内存变量
        
        Args:
            key: 变量键
            default: 默认值
            
        Returns:
            变量值
        """
        try:
            value = self.memory.load_variable(key)
            return value if value is not None else default
        except Exception as e:
            self.logger.warning(f"Failed to load variable '{key}': {e}")
            return default
    
    def _safe_set_variable(self, key: str, value: Any) -> bool:
        """
        安全地设置内存变量
        
        Args:
            key: 变量键
            value: 变量值
            
        Returns:
            是否成功
        """
        try:
            self.memory.set_variable(key, value)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set variable '{key}': {e}")
            return False
    
    def log_action(self, action: str, details: str = "", phase: str = "") -> None:
        """
        记录行动日志
        
        Args:
            action: 行动类型
            details: 详细信息
            phase: 游戏阶段
        """
        phase_str = f"[{phase}]" if phase else ""
        my_name = self._safe_get_variable("name", "Unknown")
        
        log_msg = f"{phase_str} {my_name} - {action}"
        if details:
            log_msg += f": {details}"
        
        self.logger.info(log_msg)
