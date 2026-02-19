"""
通用工具类

提供数据验证、缓存管理等工具功能
"""

from typing import Any, Optional, Dict
import time
import re


class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_player_name(player_name: Any) -> bool:
        """
        验证玩家名称格式
        
        Args:
            player_name: 玩家名称
            
        Returns:
            是否有效
        """
        if not isinstance(player_name, str):
            return False
        
        # 支持格式: "No.1", "No.12", "Player1"等
        pattern = r'^(No\.\d+|Player\d+|玩家\d+)$'
        return bool(re.match(pattern, player_name))
    
    @staticmethod
    def validate_trust_score(score: Any) -> bool:
        """
        验证信任分数
        
        Args:
            score: 信任分数
            
        Returns:
            是否有效
        """
        if not isinstance(score, (int, float)):
            return False
        return 0 <= score <= 100
    
    @staticmethod
    def validate_confidence(confidence: Any) -> bool:
        """
        验证置信度
        
        Args:
            confidence: 置信度
            
        Returns:
            是否有效
        """
        if not isinstance(confidence, (int, float)):
            return False
        return 0 <= confidence <= 1
    
    @staticmethod
    def validate_day_count(day_count: Any) -> bool:
        """
        验证天数
        
        Args:
            day_count: 天数
            
        Returns:
            是否有效
        """
        if not isinstance(day_count, int):
            return False
        return day_count >= 1
    
    @staticmethod
    def validate_player_list(players: Any) -> bool:
        """
        验证玩家列表
        
        Args:
            players: 玩家列表
            
        Returns:
            是否有效
        """
        if not isinstance(players, list):
            return False
        
        if not players:
            return False
        
        # 检查是否都是有效的玩家名称
        return all(DataValidator.validate_player_name(p) for p in players)
    
    @staticmethod
    def validate_voting_record(record: Any) -> bool:
        """
        验证投票记录格式
        
        Args:
            record: 投票记录（应该是(target, was_wolf)元组）
            
        Returns:
            是否有效
        """
        if not isinstance(record, tuple):
            return False
        
        if len(record) != 2:
            return False
        
        target, was_wolf = record
        
        # 验证target是有效的玩家名称
        if not DataValidator.validate_player_name(target):
            return False
        
        # 验证was_wolf是布尔值
        if not isinstance(was_wolf, bool):
            return False
        
        return True
    
    @staticmethod
    def safe_get_dict(value: Any, default: Optional[Dict] = None) -> Dict:
        """
        安全获取字典值
        
        Args:
            value: 原始值
            default: 默认值
            
        Returns:
            字典值或默认值
        """
        if isinstance(value, dict):
            return value
        return default if default is not None else {}
    
    @staticmethod
    def safe_get_list(value: Any, default: Optional[list] = None) -> list:
        """
        安全获取列表值
        
        Args:
            value: 原始值
            default: 默认值
            
        Returns:
            列表值或默认值
        """
        if isinstance(value, list):
            return value
        return default if default is not None else []
    
    @staticmethod
    def safe_get_int(value: Any, default: int = 0) -> int:
        """
        安全获取整数值
        
        Args:
            value: 原始值
            default: 默认值
            
        Returns:
            整数值或默认值
        """
        if isinstance(value, int):
            return value
        if isinstance(value, (float, str)):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        return default
    
    @staticmethod
    def safe_get_float(value: Any, default: float = 0.0) -> float:
        """
        安全获取浮点数值
        
        Args:
            value: 原始值
            default: 默认值
            
        Returns:
            浮点数值或默认值
        """
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        return default
    
    @staticmethod
    def safe_get_str(value: Any, default: str = "") -> str:
        """
        安全获取字符串值
        
        Args:
            value: 原始值
            default: 默认值
            
        Returns:
            字符串值或默认值
        """
        if isinstance(value, str):
            return value
        if value is not None:
            return str(value)
        return default


class CacheManager:
    """
    缓存管理器(单例模式)
    
    提供简单的内存缓存功能
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
            cls._instance._timestamps = {}
        return cls._instance
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            ttl: 过期时间(秒),None表示不检查过期
            
        Returns:
            缓存值,不存在或过期返回None
        """
        if key not in self._cache:
            return None
        
        # 检查是否过期
        if ttl is not None and key in self._timestamps:
            if time.time() - self._timestamps[key] > ttl:
                self.delete(key)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """
        删除缓存
        
        Args:
            key: 缓存键
        """
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._timestamps.clear()
    
    def has(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        return key in self._cache
    
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存项数量
        """
        return len(self._cache)


def extract_player_number(player_name: str) -> Optional[int]:
    """
    从玩家名称中提取编号
    
    Args:
        player_name: 玩家名称(如"No.5")
        
    Returns:
        玩家编号,提取失败返回None
    """
    match = re.search(r'\d+', player_name)
    return int(match.group()) if match else None


def format_player_name(player_id: int) -> str:
    """
    格式化玩家名称
    
    Args:
        player_id: 玩家ID
        
        Returns:
        格式化的玩家名称(如"No.5")
    """
    return f"No.{player_id}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
