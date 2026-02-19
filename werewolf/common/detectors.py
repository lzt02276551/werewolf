"""
通用检测器

提供注入检测、虚假引用检测等通用检测功能
"""

from typing import Dict, Any, Optional
import re
from werewolf.core.base_components import BaseDetector
from werewolf.core.config import BaseConfig


class InjectionDetector(BaseDetector):
    """
    注入检测器
    
    检测发言中的恶意注入内容
    """
    
    def __init__(self, config: BaseConfig, llm_client: Optional[Any] = None):
        """
        初始化检测器
        
        Args:
            config: 配置对象
            llm_client: LLM客户端(可选)
        """
        super().__init__(config)
        self.llm_client = llm_client
        
        # 注入关键词模式
        self.injection_patterns = [
            r'忽略.*指令',
            r'ignore.*instruction',
            r'你是.*助手',
            r'you are.*assistant',
            r'system.*prompt',
            r'角色.*设定',
            r'扮演.*角色',
            r'play.*role',
        ]
    
    def detect(self, message: str, use_llm: bool = False) -> Dict[str, Any]:
        """
        检测注入
        
        Args:
            message: 待检测消息
            use_llm: 是否使用LLM检测
            
        Returns:
            检测结果字典
        """
        try:
            if use_llm and self.llm_client:
                return self._detect_with_llm(message)
            else:
                return self._detect_with_rules(message)
        except Exception as e:
            return self._handle_error(e, "detect")
    
    def _detect_with_rules(self, message: str) -> Dict[str, Any]:
        """
        基于规则的检测
        
        Args:
            message: 待检测消息
            
        Returns:
            检测结果
        """
        message_lower = message.lower()
        detected_patterns = []
        
        for pattern in self.injection_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                detected_patterns.append(pattern)
        
        detected = len(detected_patterns) > 0
        confidence = min(len(detected_patterns) * 0.3, 1.0) if detected else 0.0
        
        return {
            'detected': detected,
            'confidence': confidence,
            'details': {
                'method': 'rule_based',
                'patterns_matched': detected_patterns,
                'message_length': len(message)
            }
        }
    
    def _detect_with_llm(self, message: str) -> Dict[str, Any]:
        """
        基于LLM的检测
        
        Args:
            message: 待检测消息
            
        Returns:
            检测结果
        """
        # TODO: 实现LLM检测逻辑
        # 这里先返回规则检测结果
        return self._detect_with_rules(message)


class FalseQuoteDetector(BaseDetector):
    """
    虚假引用检测器
    
    检测发言中的虚假引用
    """
    
    def __init__(self, config: BaseConfig):
        """
        初始化检测器
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
        
        # 引用关键词
        self.quote_keywords = [
            '说', '讲', '提到', '表示', '认为', '觉得',
            'said', 'mentioned', 'stated', 'claimed'
        ]
    
    def detect(self, message: str, speech_history: Dict[str, list]) -> Dict[str, Any]:
        """
        检测虚假引用
        
        Args:
            message: 待检测消息
            speech_history: 发言历史
            
        Returns:
            检测结果字典
        """
        try:
            # 提取引用
            quotes = self._extract_quotes(message)
            
            if not quotes:
                return {
                    'detected': False,
                    'confidence': 0.0,
                    'details': {'quotes': []}
                }
            
            # 验证引用
            false_quotes = []
            for quote in quotes:
                if not self._verify_quote(quote, speech_history):
                    false_quotes.append(quote)
            
            detected = len(false_quotes) > 0
            confidence = len(false_quotes) / len(quotes) if quotes else 0.0
            
            return {
                'detected': detected,
                'confidence': confidence,
                'details': {
                    'total_quotes': len(quotes),
                    'false_quotes': false_quotes,
                    'verified_quotes': len(quotes) - len(false_quotes)
                }
            }
            
        except Exception as e:
            return self._handle_error(e, "detect")
    
    def _extract_quotes(self, message: str) -> list:
        """
        提取引用
        
        Args:
            message: 消息
            
        Returns:
            引用列表
        """
        quotes = []
        
        # 简单的引用提取逻辑
        # 查找"XX说YY"模式
        pattern = r'(No\.\d+|玩家\d+)(说|讲|提到|表示)(.{5,50})'
        matches = re.findall(pattern, message)
        
        for match in matches:
            player, verb, content = match
            quotes.append({
                'player': player,
                'verb': verb,
                'content': content.strip()
            })
        
        return quotes
    
    def _verify_quote(self, quote: Dict[str, str], speech_history: Dict[str, list]) -> bool:
        """
        验证引用是否真实
        
        Args:
            quote: 引用字典
            speech_history: 发言历史
            
        Returns:
            是否真实
        """
        player = quote['player']
        content = quote['content']
        
        if player not in speech_history:
            return False
        
        # 检查玩家的发言历史中是否包含类似内容
        player_speeches = speech_history[player]
        
        for speech in player_speeches:
            if content in speech or self._is_similar(content, speech):
                return True
        
        return False
    
    def _is_similar(self, text1: str, text2: str, threshold: float = 0.6) -> bool:
        """
        检查两段文本是否相似
        
        Args:
            text1: 文本1
            text2: 文本2
            threshold: 相似度阈值
            
        Returns:
            是否相似
        """
        # 简单的相似度计算
        words1 = set(text1)
        words2 = set(text2)
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold


class SpeechQualityDetector(BaseDetector):
    """
    发言质量检测器
    
    检测发言的逻辑性和质量
    """
    
    def __init__(self, config: BaseConfig):
        """
        初始化检测器
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
    
    def detect(self, message: str) -> Dict[str, Any]:
        """
        检测发言质量
        
        Args:
            message: 待检测消息
            
        Returns:
            检测结果字典
        """
        try:
            # 计算质量指标
            length_score = self._calculate_length_score(message)
            logic_score = self._calculate_logic_score(message)
            info_score = self._calculate_info_score(message)
            
            # 综合评分
            quality_score = (length_score + logic_score + info_score) / 3
            
            return {
                'detected': quality_score >= 0.6,  # 高质量发言
                'confidence': quality_score,
                'details': {
                    'length_score': length_score,
                    'logic_score': logic_score,
                    'info_score': info_score,
                    'message_length': len(message)
                }
            }
            
        except Exception as e:
            return self._handle_error(e, "detect")
    
    def _calculate_length_score(self, message: str) -> float:
        """计算长度得分"""
        length = len(message)
        if length < 20:
            return 0.2
        elif length < 50:
            return 0.5
        elif length < 200:
            return 1.0
        else:
            return 0.8  # 太长也不好
    
    def _calculate_logic_score(self, message: str) -> float:
        """计算逻辑性得分"""
        # 检查逻辑连接词
        logic_words = ['因为', '所以', '但是', '然而', '首先', '其次', '最后']
        score = sum(1 for word in logic_words if word in message)
        return min(score * 0.25, 1.0)
    
    def _calculate_info_score(self, message: str) -> float:
        """计算信息量得分"""
        # 检查是否包含具体信息
        info_patterns = [
            r'No\.\d+',  # 提到玩家
            r'第\d+天',  # 提到天数
            r'投票',     # 提到投票
            r'发言',     # 提到发言
        ]
        score = sum(1 for pattern in info_patterns if re.search(pattern, message))
        return min(score * 0.3, 1.0)
