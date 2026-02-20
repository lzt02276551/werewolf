# -*- coding: utf-8 -*-
"""
狼人检测器模块
提供注入检测和消息分析功能
"""

from typing import Dict, Any, Optional
from agent_build_sdk.utils.logger import logger
from .config import WolfConfig


class InjectionDetector:
    """
    注入攻击检测器
    检测其他玩家是否试图伪造系统信息或状态信息
    """
    
    def __init__(self, config: WolfConfig, llm_client: Optional[Any] = None, 
                 llm_model: Optional[str] = None):
        """
        初始化检测器
        
        Args:
            config: 狼人配置
            llm_client: LLM客户端（可选）
            llm_model: LLM模型名称（可选）
        """
        self.config = config
        self.llm_client = llm_client
        self.llm_model = llm_model
        
        logger.info("✓ InjectionDetector initialized for Wolf")
        logger.info(f"  - LLM Available: {self.llm_client is not None}")
    
    def detect(self, message: str, player_name: str) -> Dict[str, Any]:
        """
        检测注入攻击
        
        Args:
            message: 玩家发言
            player_name: 玩家名称
            
        Returns:
            检测结果字典
        """
        if not message or not isinstance(message, str):
            return {
                'detected': False,
                'type': 'none',
                'confidence': 0.0,
                'details': {}
            }
        
        # 使用规则检测
        return self._detect_with_rules(message, player_name)
    
    def _detect_with_rules(self, message: str, player_name: str) -> Dict[str, Any]:
        """使用规则检测注入攻击"""
        message_lower = message.lower()
        
        # 检测系统伪造
        system_keywords = ['系统', 'system', '官方', '裁判', '主持人']
        if any(keyword in message_lower for keyword in system_keywords):
            return {
                'detected': True,
                'type': 'system_fake',
                'confidence': 0.7,
                'details': {'reason': '疑似伪造系统信息'}
            }
        
        # 检测状态伪造
        status_keywords = ['我是预言家', '我是女巫', '我是守卫', '我是猎人']
        if any(keyword in message for keyword in status_keywords):
            return {
                'detected': True,
                'type': 'status_fake',
                'confidence': 0.6,
                'details': {'reason': '疑似伪造身份'}
            }
        
        return {
            'detected': False,
            'type': 'none',
            'confidence': 0.0,
            'details': {}
        }


class DetectorManager:
    """
    检测器管理器
    统一管理所有检测器
    """
    
    def __init__(self, config: WolfConfig, llm_client: Optional[Any] = None,
                 llm_model: Optional[str] = None):
        """
        初始化检测器管理器
        
        Args:
            config: 狼人配置
            llm_client: LLM客户端（可选）
            llm_model: LLM模型名称（可选）
        """
        self.config = config
        self.injection_detector = InjectionDetector(config, llm_client, llm_model)
        
        logger.info("✓ DetectorManager initialized for Wolf")
    
    def detect_injection(self, message: str, player_name: str) -> Dict[str, Any]:
        """
        检测注入攻击
        
        Args:
            message: 玩家发言
            player_name: 玩家名称
            
        Returns:
            检测结果
        """
        return self.injection_detector.detect(message, player_name)
    
    def analyze_message(self, message: str, player_name: str) -> Dict[str, Any]:
        """
        分析消息
        
        Args:
            message: 玩家发言
            player_name: 玩家名称
            
        Returns:
            分析结果
        """
        # 检测注入
        injection_result = self.detect_injection(message, player_name)
        
        return {
            'injection': injection_result,
            'player': player_name,
            'message_length': len(message)
        }
