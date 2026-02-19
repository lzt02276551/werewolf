# -*- coding: utf-8 -*-
"""
猎人代理人检测器模块

统一管理所有检测逻辑，复用守卫的检测器
提供注入攻击、虚假引用、状态矛盾等检测功能
"""

from typing import Dict, Any, Optional
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseDetector
from .config import HunterConfig


def safe_execute(default_return=None):
    """
    装饰器：安全执行函数，捕获异常并返回默认值
    
    Args:
        default_return: 发生异常时返回的默认值
        
    Returns:
        装饰后的函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default_return if default_return is not None else None
        return wrapper
    return decorator


class InjectionDetector(BaseDetector):
    """
    注入攻击检测器
    
    检测玩家发言中的提示词注入攻击，包括：
    - 伪造系统消息
    - 伪造主持人通知
    - 元评论（meta-commentary）
    
    优先使用守卫的检测器，如果不可用则使用fallback检测
    """
    
    def __init__(self, config: HunterConfig, guard_detector=None):
        """
        初始化注入检测器
        
        Args:
            config: 猎人配置对象
            guard_detector: 守卫的检测器实例（可选）
        """
        super().__init__(config)
        self.guard_detector = guard_detector
    
    @safe_execute(default_return={'detected': False, 'confidence': 0.0, 'reason': 'Error'})
    def detect(self, message: str, player_name: str, my_name: str) -> Dict[str, Any]:
        """
        检测注入攻击
        
        Args:
            message: 玩家发言内容
            player_name: 玩家名称
            my_name: 自己的名称（避免误判自己的发言）
        
        Returns:
            检测结果字典，包含：
            - detected: bool, 是否检测到注入
            - confidence: float, 置信度(0-1)
            - injection_type: str, 注入类型
            - severity: int, 严重程度（负分）
            - reason: str, 检测原因
        """
        # 不检测自己的发言
        if player_name == my_name:
            return {'detected': False, 'confidence': 0.0, 'reason': 'Own speech'}
        
        # 优先使用守卫的检测器
        if self.guard_detector:
            try:
                result = self.guard_detector.detect(message)
                injection_type = result.get('injection_type', 'CLEAN')
                confidence = result.get('confidence', 0)
                
                if injection_type != 'CLEAN' and confidence > 0.6:
                    severity_map = {
                        'SYSTEM_FAKE': -35,
                        'STATUS_FAKE': -30,
                        'BENIGN': 0
                    }
                    severity = severity_map.get(injection_type, -25)
                    
                    return {
                        'detected': True,
                        'confidence': confidence,
                        'injection_type': injection_type,
                        'severity': severity,
                        'reason': result.get('reason', '')
                    }
                
                return {'detected': False, 'confidence': confidence, 'reason': 'Clean'}
            except Exception as e:
                logger.warning(f"Guard detector failed: {e}, using fallback")
        
        # Fallback: 硬编码检测
        return self._fallback_detection(message, player_name)
    
    def _fallback_detection(self, message: str, player_name: str) -> Dict[str, Any]:
        """备用检测（硬编码关键词）"""
        # Type A: FAKE HOST MESSAGES
        fake_host_patterns = [
            ("Host:", -30, "FAKE_HOST_PREFIX"),
            ("Host Notice:", -30, "FAKE_HOST_NOTICE"),
            ("Game Master:", -30, "FAKE_GAME_MASTER"),
            ("Here is their last words:", -30, "FAKE_LAST_WORDS"),
            ("has been voted out", -25, "FAKE_ELIMINATION"),
            ("has been eliminated", -25, "FAKE_ELIMINATION"),
            ("System:", -30, "FAKE_SYSTEM"),
        ]
        
        for pattern, severity, attack_type in fake_host_patterns:
            if pattern in message:
                return {
                    'detected': True,
                    'confidence': 0.9,
                    'injection_type': attack_type,
                    'severity': severity,
                    'reason': f"Fake host message: {pattern}"
                }
        
        # Type B: META-COMMENTARY
        meta_patterns = [
            ("Strategic Rationale:", -20, "META_STRATEGY"),
            ("Campaign Speech:", -20, "META_CAMPAIGN"),
            ("character count", -20, "META_COUNT"),
            ("**", -15, "MARKDOWN_FORMAT"),
        ]
        
        for pattern, severity, attack_type in meta_patterns:
            if pattern in message:
                return {
                    'detected': True,
                    'confidence': 0.7,
                    'injection_type': attack_type,
                    'severity': severity,
                    'reason': f"Meta-commentary: {pattern}"
                }
        
        return {'detected': False, 'confidence': 1.0, 'reason': 'Clean'}


class FalseQuotationDetector(BaseDetector):
    """
    虚假引用检测器（复用守卫的检测器或使用fallback）
    """
    
    def __init__(self, config: HunterConfig, guard_detector=None):
        super().__init__(config)
        self.guard_detector = guard_detector
    
    @safe_execute(default_return={'detected': False, 'confidence': 0.0, 'reason': 'Error'})
    def detect(self, message: str, player_name: str, speech_history: Dict) -> Dict[str, Any]:
        """
        检测虚假引用
        
        Args:
            message: 玩家发言
            player_name: 玩家名称
            speech_history: 发言历史
        
        Returns:
            检测结果字典
        """
        # 优先使用守卫的检测器
        if self.guard_detector:
            try:
                result = self.guard_detector.detect(message, player_name, speech_history)
                
                if result.get('is_false_quotation', False) and result.get('confidence', 0) > 0.7:
                    quoted_player = result.get('quoted_player', 'unknown')
                    
                    # 验证：检查被引用玩家是否真的没发言
                    if quoted_player not in speech_history or len(speech_history[quoted_player]) == 0:
                        return {
                            'detected': True,
                            'confidence': result.get('confidence', 0.8),
                            'quoted_player': quoted_player,
                            'reason': result.get('reason', 'False quotation detected')
                        }
                
                return {'detected': False, 'confidence': result.get('confidence', 0.5), 'reason': 'Clean'}
            except Exception as e:
                logger.warning(f"Guard detector failed: {e}, using fallback")
        
        # Fallback: 正则表达式检测
        return self._fallback_detection(message, player_name, speech_history)
    
    def _fallback_detection(self, message: str, player_name: str, speech_history: Dict) -> Dict[str, Any]:
        """备用检测（正则表达式）"""
        import re
        
        quotation_patterns = [
            r"No\.(\d+)\s+(said|mentioned|stated|claimed|told)",
            r"No\.(\d+)\s+的发言",
            r"No\.(\d+)\s+刚才说",
        ]
        
        for pattern in quotation_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                quoted_player = f"No.{match[0]}" if isinstance(match, tuple) else f"No.{match}"
                
                # 检查被引用玩家是否真的没发言
                if quoted_player not in speech_history or len(speech_history[quoted_player]) == 0:
                    return {
                        'detected': True,
                        'confidence': 0.8,
                        'quoted_player': quoted_player,
                        'reason': f"Falsely quoted {quoted_player}"
                    }
        
        return {'detected': False, 'confidence': 1.0, 'reason': 'Clean'}


class StatusContradictionDetector(BaseDetector):
    """
    状态矛盾检测器（玩家声称已死但仍在活动）
    """
    
    def __init__(self, config: HunterConfig, memory_dao):
        super().__init__(config)
        self.memory_dao = memory_dao
    
    @safe_execute(default_return={'detected': False, 'confidence': 0.0, 'reason': 'Error'})
    def detect(self, message: str, player_name: str) -> Dict[str, Any]:
        """
        检测状态矛盾
        
        Args:
            message: 玩家发言
            player_name: 玩家名称
        
        Returns:
            检测结果字典
        """
        # 检查是否是合法的遗言阶段
        if self._is_legitimate_last_words(player_name):
            return {'detected': False, 'confidence': 1.0, 'reason': 'Legitimate last words'}
        
        # 检查玩家是否声称已死
        claims_eliminated = any(phrase in message.lower() for phrase in [
            "i was eliminated",
            "i have been voted out",
            "i am dead",
            "my last words",
            "i was lynched",
        ])
        
        if not claims_eliminated:
            return {'detected': False, 'confidence': 1.0, 'reason': 'No death claim'}
        
        # 验证玩家是否真的已死
        actually_eliminated = self._verify_player_status(player_name)
        
        if not actually_eliminated:
            return {
                'detected': True,
                'confidence': 0.95,
                'reason': 'Claims eliminated but still active',
                'severity': -35
            }
        
        return {'detected': False, 'confidence': 1.0, 'reason': 'Legitimate death claim'}
    
    def _is_legitimate_last_words(self, player_name: str) -> bool:
        """检查是否是合法的遗言阶段"""
        history = self.memory_dao.get_history()
        recent_history = history[-10:] if len(history) >= 10 else history
        
        for msg in recent_history:
            if player_name in msg:
                if any(phrase in msg for phrase in [
                    f"Vote result is: {player_name}",
                    f"{player_name} was eliminated",
                    f"{player_name} was voted out",
                    "leaves their last words",
                    "Last Words:",
                ]):
                    return True
        
        return False
    
    def _verify_player_status(self, player_name: str) -> bool:
        """验证玩家是否真的已死"""
        history = self.memory_dao.get_history()
        
        for msg in history:
            if not msg.startswith("No."):  # 只检查系统消息
                if player_name in msg:
                    if any(keyword in msg for keyword in [
                        "was eliminated",
                        "was voted out",
                        "died",
                        "was killed",
                        "was shot"
                    ]):
                        return True
        
        return False


class DetectorManager:
    """
    检测器管理器（门面模式）
    统一管理所有检测器,提供简单的接口
    """
    
    def __init__(self, config: HunterConfig, memory_dao, detection_client=None, detection_model=None):
        self.config = config
        self.memory_dao = memory_dao
        self.detection_client = detection_client
        self.detection_model = detection_model
        
        # 初始化所有检测器
        self._init_detectors()
    
    def _init_detectors(self):
        """初始化所有检测器"""
        # 尝试导入守卫的检测器
        guard_injection_detector = None
        guard_false_quotation_detector = None
        
        try:
            from werewolf.guard.llm_detector import DetectorFactory
            
            if self.detection_client and self.detection_model:
                guard_injection_detector = DetectorFactory.create_injection_detector(
                    self.detection_client, self.detection_model
                )
                guard_false_quotation_detector = DetectorFactory.create_false_quotation_detector(
                    self.detection_client, self.detection_model
                )
                logger.info("✓ Using guard's detectors")
        except Exception as e:
            logger.warning(f"Failed to load guard's detectors: {e}, using fallback")
        
        # 创建检测器实例
        self.injection_detector = InjectionDetector(self.config, guard_injection_detector)
        self.false_quotation_detector = FalseQuotationDetector(self.config, guard_false_quotation_detector)
        self.status_contradiction_detector = StatusContradictionDetector(self.config, self.memory_dao)
        
        logger.info("✓ All detectors initialized")
    
    def detect_injection(self, message: str, player_name: str, my_name: str) -> Dict[str, Any]:
        """检测注入攻击"""
        return self.injection_detector.detect(message, player_name, my_name)
    
    def detect_false_quotation(self, message: str, player_name: str) -> Dict[str, Any]:
        """检测虚假引用"""
        speech_history = self.memory_dao.get_speech_history()
        return self.false_quotation_detector.detect(message, player_name, speech_history)
    
    def detect_status_contradiction(self, message: str, player_name: str) -> Dict[str, Any]:
        """检测状态矛盾"""
        return self.status_contradiction_detector.detect(message, player_name)
    
    def detect_all(self, message: str, player_name: str, my_name: str) -> Dict[str, Any]:
        """
        执行所有检测
        
        Returns:
            综合检测结果
        """
        results = {
            'injection': self.detect_injection(message, player_name, my_name),
            'false_quotation': self.detect_false_quotation(message, player_name),
            'status_contradiction': self.detect_status_contradiction(message, player_name)
        }
        
        # 判断是否有任何检测到问题
        any_detected = any(r.get('detected', False) for r in results.values())
        
        # 计算最高严重程度
        max_severity = min(
            (r.get('severity', 0) for r in results.values() if r.get('detected', False)),
            default=0
        )
        
        return {
            'any_detected': any_detected,
            'max_severity': max_severity,
            'details': results
        }
