"""
配置数据模型

使用Pydantic定义配置验证模型
验证需求: AC-2.3.2
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, Any


class DimensionConfig(BaseModel):
    """
    评分维度配置模型
    
    验证需求: AC-2.3.2
    """
    enabled: bool = True
    weight: float = Field(gt=0.0, le=10.0)
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ScoringConfig(BaseModel):
    """
    评分配置模型
    
    验证需求: AC-2.3.2
    """
    dimensions: Dict[str, DimensionConfig]


class CacheConfig(BaseModel):
    """
    缓存配置模型
    
    验证需求: AC-2.1.1
    """
    enabled: bool = True
    max_size: int = Field(default=1000, gt=0)


class LLMConfig(BaseModel):
    """
    LLM配置模型
    
    验证需求: AC-3.2.1
    """
    batch_size: int = Field(default=5, gt=0, le=20)
    timeout: float = Field(default=30.0, gt=0.0)


class OptimizationConfig(BaseModel):
    """
    优化配置总模型
    
    验证需求: AC-2.3.2
    """
    scoring: ScoringConfig
    cache: CacheConfig
    llm: LLMConfig
    
    @classmethod
    def default(cls) -> 'OptimizationConfig':
        """返回默认配置"""
        return cls(
            scoring=ScoringConfig(
                dimensions={
                    'trust_score': DimensionConfig(
                        enabled=True,
                        weight=2.0,
                        parameters={'decay_steepness': 0.1, 'decay_midpoint': 50.0}
                    ),
                    'werewolf_probability': DimensionConfig(
                        enabled=True,
                        weight=3.0,
                        parameters={'prior_probability': 0.25}
                    ),
                }
            ),
            cache=CacheConfig(),
            llm=LLMConfig()
        )
