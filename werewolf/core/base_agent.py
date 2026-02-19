"""
Agent抽象基类

定义所有角色Agent的标准接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from .config import BaseConfig
from .game_state import GameState
from .exceptions import InvalidGameStateError, ComponentError


class BaseAgent(ABC):
    """
    Agent抽象基类
    
    所有角色Agent都应该继承此类
    
    职责:
    1. 定义Agent的标准接口
    2. 提供通用的错误处理
    3. 管理Agent的生命周期
    
    Attributes:
        player_id: 玩家ID
        config: 配置对象
        logger: 日志对象
    """
    
    def __init__(self, player_id: int, config: BaseConfig):
        """
        初始化Agent
        
        Args:
            player_id: 玩家ID
            config: 配置对象
        """
        self.player_id = player_id
        self.config = config
        self.logger = config.get_logger(self.__class__.__name__)
        
        # 初始化组件(子类实现)
        try:
            self._initialize_components()
            self.logger.info(f"Agent initialized: player_id={player_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise ComponentError(self.__class__.__name__, f"Initialization failed: {e}")
    
    @abstractmethod
    def _initialize_components(self) -> None:
        """
        初始化角色特定组件(子类必须实现)
        
        在此方法中初始化:
        - Detector
        - Analyzer
        - DecisionMaker
        - TrustManager
        等组件
        """
        pass
    
    @abstractmethod
    def get_action(self, game_state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        获取角色行动(子类必须实现)
        
        Args:
            game_state: 游戏状态字典
            **kwargs: 额外参数(如phase, candidates等)
            
        Returns:
            行动字典,至少包含:
            - action: str, 行动类型
            - reasoning: str, 推理过程
            - 其他角色特定字段
            
        Raises:
            InvalidGameStateError: 游戏状态无效时抛出
        """
        pass
    
    @abstractmethod
    def update_state(self, game_state: Dict[str, Any]) -> None:
        """
        更新内部状态(子类必须实现)
        
        Args:
            game_state: 游戏状态字典
        """
        pass
    
    def _validate_game_state(self, game_state: Dict[str, Any]) -> bool:
        """
        验证游戏状态有效性
        
        Args:
            game_state: 游戏状态字典
            
        Returns:
            状态是否有效
        """
        try:
            state = GameState.from_dict(game_state)
            state.validate()
            return True
        except InvalidGameStateError as e:
            self.logger.error(f"Invalid game state: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating game state: {e}")
            return False
    
    def _handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        统一的错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            默认行动
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"[{self.__class__.__name__}] {error_msg}")
        return self._get_default_action()
    
    @abstractmethod
    def _get_default_action(self) -> Dict[str, Any]:
        """
        获取默认行动(子类必须实现)
        
        Returns:
            默认行动字典
        """
        pass
    
    def get_player_name(self) -> str:
        """
        获取玩家名称
        
        Returns:
            玩家名称(如"No.1")
        """
        return f"No.{self.player_id}"
    
    def log_action(self, action: Dict[str, Any], phase: str = "") -> None:
        """
        记录行动日志
        
        Args:
            action: 行动字典
            phase: 游戏阶段
        """
        phase_str = f"[{phase}]" if phase else ""
        self.logger.info(
            f"{phase_str} Player {self.get_player_name()} action: "
            f"{action.get('action', 'unknown')}"
        )
        if 'reasoning' in action:
            self.logger.debug(f"Reasoning: {action['reasoning'][:100]}...")
