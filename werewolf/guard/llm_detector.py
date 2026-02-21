# -*- coding: utf-8 -*-
"""
LLM检测器工厂模块
为其他角色提供统一的检测器创建接口
"""

from typing import Optional, Any, Dict
from werewolf.core.llm_detectors import (
    InjectionDetector,
    FalseQuoteDetector,
    SpeechQualityEvaluator,
    MessageParser,
    create_llm_detectors
)


class DetectorFactory:
    """检测器工厂类 - 为守卫提供统一的检测器创建接口"""
    
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
        if not llm_client or not model_name:
            raise ValueError("llm_client and model_name are required")
        return InjectionDetector(llm_client, model_name)
    
    @staticmethod
    def create_false_quote_detector(
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None
    ) -> FalseQuoteDetector:
        """
        创建虚假引用检测器
        
        Args:
            llm_client: LLM客户端（可选）
            model_name: 模型名称（可选）
            
        Returns:
            FalseQuoteDetector实例
        """
        if not llm_client or not model_name:
            raise ValueError("llm_client and model_name are required")
        return FalseQuoteDetector(llm_client, model_name)
    
    @staticmethod
    def create_all_detectors(
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建所有检测器
        
        Args:
            llm_client: LLM客户端（可选）
            model_name: 模型名称（可选）
            
        Returns:
            检测器字典
        """
        if not llm_client or not model_name:
            raise ValueError("llm_client and model_name are required")
        return create_llm_detectors(llm_client, model_name)
