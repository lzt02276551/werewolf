# -*- coding: utf-8 -*-
"""
LLM检测器工厂模块
为其他角色提供统一的检测器创建接口
"""

from typing import Optional, Any
from .detectors import InjectionDetector, FalseQuotationDetector
from .config import GuardConfig


class DetectorFactory:
    """检测器工厂类"""
    
    @staticmethod
    def create_injection_detector(
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None
    ) -> InjectionDetector:
        """
        创建注入检测器
        
        Args:
            llm_client: LLM客户端（可选）
            model_name: 模型名称（可选）
            
        Returns:
            InjectionDetector实例
        """
        config = GuardConfig()
        return InjectionDetector(config, llm_client, model_name)
    
    @staticmethod
    def create_false_quotation_detector(
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None
    ) -> FalseQuotationDetector:
        """
        创建虚假引用检测器
        
        Args:
            llm_client: LLM客户端（可选）
            model_name: 模型名称（可选）
            
        Returns:
            FalseQuotationDetector实例
        """
        config = GuardConfig()
        return FalseQuotationDetector(config, llm_client, model_name)
