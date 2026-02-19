"""
组件抽象基类

定义所有组件的标准接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
from .config import BaseConfig
from .exceptions import ComponentError


class BaseComponent(ABC):
    """
    组件基类
    
    所有组件都应该继承此类
    
    Attributes:
        config: 配置对象
        logger: 日志对象
    """
    
    def __init__(self, config: BaseConfig):
        """
        初始化组件
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = config.get_logger(self.__class__.__name__)
    
    def _handle_error(self, error: Exception, context: str = "") -> Any:
        """
        统一的错误处理
        
        Args:
            error: 异常对象
            context: 错误上下文
            
        Returns:
            默认结果
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"[{self.__class__.__name__}] {error_msg}")
        return self._get_default_result()
    
    @abstractmethod
    def _get_default_result(self) -> Any:
        """
        获取默认结果(子类必须实现)
        
        Returns:
            默认结果
        """
        pass


class BaseDetector(BaseComponent):
    """
    检测器抽象基类
    
    职责: 检测特定模式或异常
    """
    
    @abstractmethod
    def detect(self, *args, **kwargs) -> Dict[str, Any]:
        """
        执行检测(子类必须实现)
        
        Returns:
            检测结果字典,至少包含:
            - detected: bool, 是否检测到
            - confidence: float, 置信度(0-1)
            - details: dict, 详细信息
        """
        pass
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认检测结果"""
        return {
            'detected': False,
            'confidence': 0.0,
            'details': {},
            'error': 'Detection failed'
        }


class BaseAnalyzer(BaseComponent):
    """
    分析器抽象基类
    
    职责: 分析数据并生成洞察
    """
    
    def analyze(self, *args, **kwargs) -> Any:
        """
        模板方法: 执行分析流程
        
        Returns:
            分析结果
        """
        try:
            # 1. 验证输入
            if not self._validate_input(*args, **kwargs):
                self.logger.warning("Input validation failed")
                return self._get_default_result()
            
            # 2. 执行分析(子类实现)
            result = self._do_analyze(*args, **kwargs)
            
            # 3. 验证结果
            if not self._validate_result(result):
                self.logger.warning("Result validation failed")
                return self._get_default_result()
            
            return result
            
        except Exception as e:
            return self._handle_error(e, "analyze")
    
    def _validate_input(self, *args, **kwargs) -> bool:
        """
        验证输入(子类可选实现)
        
        Returns:
            输入是否有效
        """
        return True
    
    def _validate_result(self, result: Any) -> bool:
        """
        验证结果(子类可选实现)
        
        Args:
            result: 分析结果
            
        Returns:
            结果是否有效
        """
        return result is not None
    
    @abstractmethod
    def _do_analyze(self, *args, **kwargs) -> Any:
        """
        执行分析逻辑(子类必须实现)
        
        Returns:
            分析结果
        """
        pass


class BaseDecisionMaker(BaseComponent):
    """
    决策器抽象基类
    
    职责: 基于分析结果做出决策
    """
    
    @abstractmethod
    def decide(self, *args, **kwargs) -> Dict[str, Any]:
        """
        执行决策(子类必须实现)
        
        Returns:
            决策结果字典,至少包含:
            - action: str, 行动
            - target: str, 目标(如果适用)
            - reasoning: str, 推理过程
            - confidence: float, 置信度(0-1)
        """
        pass
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认决策结果"""
        return {
            'action': 'none',
            'target': None,
            'reasoning': 'Decision failed, using default action',
            'confidence': 0.0
        }


class BaseTrustManager(BaseComponent):
    """
    信任管理器抽象基类
    
    职责: 管理玩家信任分数
    """
    
    def __init__(self, config: BaseConfig):
        super().__init__(config)
        self.trust_scores: Dict[str, float] = {}
    
    @abstractmethod
    def initialize_players(self, players: List[str]) -> None:
        """
        初始化玩家信任分数(子类必须实现)
        
        Args:
            players: 玩家列表
        """
        pass
    
    @abstractmethod
    def update_score(self, player: str, delta: float, reason: str = "") -> float:
        """
        更新玩家信任分数(子类必须实现)
        
        Args:
            player: 玩家名称
            delta: 分数变化
            reason: 更新原因
            
        Returns:
            更新后的分数
        """
        pass
    
    @abstractmethod
    def get_score(self, player: str) -> float:
        """
        获取玩家信任分数(子类必须实现)
        
        Args:
            player: 玩家名称
            
        Returns:
            信任分数
        """
        pass
    
    def clamp_score(self, score: float) -> float:
        """
        限制分数在有效范围内
        
        Args:
            score: 原始分数
            
        Returns:
            限制后的分数
        """
        return max(
            self.config.trust_score_min,
            min(score, self.config.trust_score_max)
        )
    
    def _get_default_result(self) -> float:
        """获取默认信任分数"""
        return self.config.trust_score_default


class BaseMemoryDAO(ABC):
    """
    内存数据访问对象抽象基类
    
    职责: 封装对Agent内存的访问
    """
    
    def __init__(self, memory: Any):
        """
        初始化DAO
        
        Args:
            memory: Agent的内存对象
        """
        self.memory = memory
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取内存中的值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            值
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        设置内存中的值
        
        Args:
            key: 键
            value: 值
        """
        pass
    
    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """
        获取列表类型的值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            列表
        """
        return self.get(key, default or [])
    
    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """
        获取字典类型的值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            字典
        """
        return self.get(key, default or {})
