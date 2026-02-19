"""
Wolf Base Components - Wolf基础组件

提供Wolf角色使用的基础类和工具，符合企业级标准
"""

from typing import Any, Dict, List, Optional
from werewolf.core.base_components import BaseMemoryDAO
from werewolf.common.utils import DataValidator as CommonDataValidator


class WolfMemoryDAO(BaseMemoryDAO):
    """
    Wolf专用的内存数据访问对象
    
    职责:
    1. 封装对Wolf Agent内存的访问
    2. 提供类型安全的数据访问方法
    3. 管理Wolf特定的数据结构
    
    Attributes:
        memory: Agent的内存对象
    """
    
    def __init__(self, memory: Any):
        """
        初始化DAO
        
        Args:
            memory: Agent的内存对象
        """
        super().__init__(memory)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取内存中的值
        
        Args:
            key: 键名
            default: 默认值
            
        Returns:
            内存中的值，不存在则返回默认值
        """
        if hasattr(self.memory, 'load_variable'):
            value = self.memory.load_variable(key)
            return value if value is not None else default
        return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置内存中的值
        
        Args:
            key: 键名
            value: 值
        """
        if hasattr(self.memory, 'set_variable'):
            self.memory.set_variable(key, value)
    
    def get_my_name(self) -> str:
        """
        获取自己的名字
        
        Returns:
            玩家名称，默认"Unknown"
        """
        return self.get("name", "Unknown")
    
    def get_teammates(self) -> List[str]:
        """
        获取队友列表
        
        Returns:
            队友名称列表
        """
        return self.get_list("teammates")
    
    def set_teammates(self, teammates: List[str]) -> None:
        """
        设置队友列表
        
        Args:
            teammates: 队友名称列表
        """
        if not isinstance(teammates, list):
            raise TypeError("teammates must be a list")
        self.set("teammates", teammates)
    
    def get_teammate_intelligence(self) -> Dict[str, int]:
        """
        获取队友智商评分
        
        Returns:
            队友智商评分字典 {player_name: intelligence_score}
        """
        return self.get_dict("teammate_intelligence")
    
    def set_teammate_intelligence(self, intelligence: Dict[str, int]) -> None:
        """
        设置队友智商评分
        
        Args:
            intelligence: 队友智商评分字典
        """
        if not isinstance(intelligence, dict):
            raise TypeError("intelligence must be a dict")
        self.set("teammate_intelligence", intelligence)
    
    def get_threat_levels(self) -> Dict[str, int]:
        """
        获取威胁等级
        
        Returns:
            威胁等级字典 {player_name: threat_level}
        """
        return self.get_dict("threat_levels")
    
    def set_threat_levels(self, levels: Dict[str, int]) -> None:
        """
        设置威胁等级
        
        Args:
            levels: 威胁等级字典
        """
        if not isinstance(levels, dict):
            raise TypeError("levels must be a dict")
        self.set("threat_levels", levels)
    
    def get_breakthrough_values(self) -> Dict[str, int]:
        """
        获取可突破值
        
        Returns:
            可突破值字典 {player_name: breakthrough_value}
        """
        return self.get_dict("breakthrough_values")
    
    def set_breakthrough_values(self, values: Dict[str, int]) -> None:
        """
        设置可突破值
        
        Args:
            values: 可突破值字典
        """
        if not isinstance(values, dict):
            raise TypeError("values must be a dict")
        self.set("breakthrough_values", values)
    
    def get_identified_roles(self) -> Dict[str, str]:
        """
        获取已识别的角色
        
        Returns:
            已识别角色字典 {player_name: role}
        """
        return self.get_dict("identified_roles")
    
    def set_identified_roles(self, roles: Dict[str, str]) -> None:
        """
        设置已识别的角色
        
        Args:
            roles: 已识别角色字典
        """
        if not isinstance(roles, dict):
            raise TypeError("roles must be a dict")
        self.set("identified_roles", roles)
    
    def get_voting_history(self) -> Dict[str, List[str]]:
        """
        获取投票历史
        
        Returns:
            投票历史字典 {player_name: [voted_targets]}
        """
        return self.get_dict("voting_history")
    
    def get_speech_quality(self) -> Dict[str, int]:
        """
        获取发言质量评分
        
        Returns:
            发言质量字典 {player_name: quality_score}
        """
        return self.get_dict("speech_quality")


class DataValidator(CommonDataValidator):
    """
    数据验证器（继承通用验证器）
    
    职责:
    1. 提供Wolf特定的数据验证方法
    2. 继承通用验证器的所有功能
    """
    
    @staticmethod
    def validate_intelligence_score(score: Any) -> bool:
        """
        验证智商评分
        
        Args:
            score: 智商评分
            
        Returns:
            是否有效
        """
        if not isinstance(score, (int, float)):
            return False
        return 0 <= score <= 100
    
    @staticmethod
    def validate_threat_level(level: Any) -> bool:
        """
        验证威胁等级
        
        Args:
            level: 威胁等级
            
        Returns:
            是否有效
        """
        if not isinstance(level, (int, float)):
            return False
        return 0 <= level <= 100
    
    @staticmethod
    def validate_breakthrough_value(value: Any) -> bool:
        """
        验证可突破值
        
        Args:
            value: 可突破值
            
        Returns:
            是否有效
        """
        if not isinstance(value, (int, float)):
            return False
        return 0 <= value <= 100
