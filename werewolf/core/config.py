"""
配置基类

提供配置管理的基础功能
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import logging


@dataclass
class BaseConfig:
    """
    配置基类
    
    所有角色配置都应该继承此类
    
    Attributes:
        log_level: 日志级别
        enable_cache: 是否启用缓存
        cache_ttl: 缓存过期时间(秒)
        enable_ml: 是否启用机器学习增强
    """
    
    # 通用配置
    log_level: str = "INFO"
    enable_cache: bool = True
    cache_ttl: int = 300
    enable_ml: bool = False
    
    # 信任分数配置
    trust_score_min: int = 0
    trust_score_max: int = 100
    trust_score_default: int = 50
    
    # LLM配置
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    llm_timeout: int = 30
    
    def validate(self) -> bool:
        """
        验证配置有效性
        
        Returns:
            配置是否有效
            
        Raises:
            ValueError: 配置无效时抛出
        """
        # 验证日志级别
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}")
        
        # 验证信任分数范围
        if self.trust_score_min >= self.trust_score_max:
            raise ValueError("trust_score_min must be less than trust_score_max")
        
        if not (self.trust_score_min <= self.trust_score_default <= self.trust_score_max):
            raise ValueError("trust_score_default must be between min and max")
        
        # 验证LLM配置
        if not (0 <= self.llm_temperature <= 2):
            raise ValueError("llm_temperature must be between 0 and 2")
        
        if self.llm_max_tokens <= 0:
            raise ValueError("llm_max_tokens must be positive")
        
        if self.llm_timeout <= 0:
            raise ValueError("llm_timeout must be positive")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置字典
        """
        return {
            'log_level': self.log_level,
            'enable_cache': self.enable_cache,
            'cache_ttl': self.cache_ttl,
            'enable_ml': self.enable_ml,
            'trust_score_min': self.trust_score_min,
            'trust_score_max': self.trust_score_max,
            'trust_score_default': self.trust_score_default,
            'llm_temperature': self.llm_temperature,
            'llm_max_tokens': self.llm_max_tokens,
            'llm_timeout': self.llm_timeout,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseConfig':
        """
        从字典创建配置对象
        
        Args:
            config_dict: 配置字典
            
        Returns:
            配置对象
        """
        return cls(**config_dict)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取配置好的logger
        
        Args:
            name: logger名称
            
        Returns:
            配置好的logger对象
        """
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
