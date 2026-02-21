# -*- coding: utf-8 -*-
"""
预言家专用内存数据访问对象

提供对Agent内存的统一访问接口
"""

from typing import Any, Dict, List, Set, Optional
from werewolf.core.base_components import BaseMemoryDAO


class SeerMemoryDAO(BaseMemoryDAO):
    """
    预言家专用的内存数据访问对象
    
    封装对预言家Agent内存的所有访问操作
    
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
            key: 键
            default: 默认值
            
        Returns:
            值
        """
        if hasattr(self.memory, 'load_variable'):
            try:
                return self.memory.load_variable(key)
            except (KeyError, AttributeError):
                return default
        return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置内存中的值
        
        Args:
            key: 键
            value: 值
        """
        if hasattr(self.memory, 'set_variable'):
            self.memory.set_variable(key, value)
    
    def append_history(self, message: str) -> None:
        """
        添加历史记录
        
        Args:
            message: 消息内容
        """
        if hasattr(self.memory, 'append_history'):
            self.memory.append_history(message)
    
    def get_history(self) -> List[str]:
        """
        获取历史记录
        
        Returns:
            历史记录列表
        """
        if hasattr(self.memory, 'load_history'):
            return self.memory.load_history()
        return []
    
    def get_my_name(self) -> str:
        """
        获取自己的名字
        
        Returns:
            玩家名称
        """
        return self.get("name", "Unknown")
    
    def get_checked_players(self) -> Dict[str, Dict]:
        """
        获取已检查的玩家
        
        Returns:
            检查结果字典 {player_name: {is_wolf: bool, night: int}}
        """
        return self.get("checked_players", {})
    
    def add_checked_player(self, player: str, is_wolf: bool, night: int) -> None:
        """
        添加检查结果
        
        Args:
            player: 玩家名称
            is_wolf: 是否是狼人
            night: 检查的夜晚
        """
        checked = self.get_checked_players()
        if checked is None:
            checked = {}
        checked[player] = {"is_wolf": is_wolf, "night": night}
        self.set("checked_players", checked)
    
    def get_trust_scores(self) -> Dict[str, int]:
        """
        获取信任分数
        
        Returns:
            信任分数字典
        """
        return self.get("trust_scores", {})
    
    def set_trust_scores(self, scores: Dict[str, int]) -> None:
        """
        设置信任分数
        
        Args:
            scores: 信任分数字典
        """
        self.set("trust_scores", scores)
    
    def get_trust_history(self) -> Dict[str, List[Dict]]:
        """
        获取信任历史
        
        Returns:
            信任历史字典
        """
        return self.get("trust_history", {})
    
    def set_trust_history(self, history: Dict[str, List[Dict]]) -> None:
        """
        设置信任历史
        
        Args:
            history: 信任历史字典
        """
        self.set("trust_history", history)
    
    def get_voting_history(self) -> Dict[str, List[str]]:
        """
        获取投票历史
        
        Returns:
            投票历史字典
        """
        return self.get("voting_history", {})
    
    def set_voting_history(self, history: Dict[str, List[str]]) -> None:
        """
        设置投票历史
        
        Args:
            history: 投票历史字典
        """
        self.set("voting_history", history)
    
    def get_voting_results(self) -> Dict[str, List]:
        """
        获取投票结果
        
        Returns:
            投票结果字典
        """
        return self.get("voting_results", {})
    
    def set_voting_results(self, results: Dict[str, List]) -> None:
        """
        设置投票结果
        
        Args:
            results: 投票结果字典
        """
        self.set("voting_results", results)
    
    def get_speech_history(self) -> Dict[str, List[str]]:
        """
        获取发言历史
        
        Returns:
            发言历史字典
        """
        return self.get("speech_history", {})
    
    def set_speech_history(self, history: Dict[str, List[str]]) -> None:
        """
        设置发言历史
        
        Args:
            history: 发言历史字典
        """
        self.set("speech_history", history)
    
    def get_player_data(self) -> Dict[str, Dict]:
        """
        获取玩家数据
        
        Returns:
            玩家数据字典
        """
        return self.get("player_data", {})
    
    def set_player_data(self, data: Dict[str, Dict]) -> None:
        """
        设置玩家数据
        
        Args:
            data: 玩家数据字典
        """
        self.set("player_data", data)
    
    def get_game_state(self) -> Dict[str, Any]:
        """
        获取游戏状态
        
        Returns:
            游戏状态字典
        """
        return self.get("game_state", {})
    
    def set_game_state(self, state: Dict[str, Any]) -> None:
        """
        设置游戏状态
        
        Args:
            state: 游戏状态字典
        """
        self.set("game_state", state)
    
    def get_night_count(self) -> int:
        """
        获取夜晚计数
        
        Returns:
            夜晚计数
        """
        return self.get("night_count", 0)
    
    def set_night_count(self, count: int) -> None:
        """
        设置夜晚计数
        
        Args:
            count: 夜晚计数
        """
        self.set("night_count", count)
    
    def get_day_count(self) -> int:
        """
        获取白天计数
        
        Returns:
            白天计数
        """
        return self.get("day_count", 0)
    
    def set_day_count(self, count: int) -> None:
        """
        设置白天计数
        
        Args:
            count: 白天计数
        """
        self.set("day_count", count)
    
    def get_dead_players(self) -> Set[str]:
        """
        获取死亡玩家
        
        Returns:
            死亡玩家集合
        """
        dead = self.get("dead_players", set())
        if not isinstance(dead, set):
            dead = set(dead) if dead else set()
        return dead
    
    def add_dead_player(self, player: str) -> None:
        """
        添加死亡玩家
        
        Args:
            player: 玩家名称
        """
        dead = self.get_dead_players()
        dead.add(player)
        self.set("dead_players", dead)
    
    def get_sheriff(self) -> Optional[str]:
        """
        获取警长
        
        Returns:
            警长名称，如果没有则返回None
        """
        return self.get("sheriff", None)
    
    def set_sheriff(self, sheriff: str) -> None:
        """
        设置警长
        
        Args:
            sheriff: 警长名称
        """
        self.set("sheriff", sheriff)
    
    def get_injection_attempts(self) -> List[Dict]:
        """
        获取注入尝试记录
        
        Returns:
            注入尝试列表
        """
        return self.get("injection_attempts", [])
    
    def add_injection_attempt(self, attempt: Dict) -> None:
        """
        添加注入尝试记录
        
        Args:
            attempt: 注入尝试信息
        """
        attempts = self.get_injection_attempts()
        attempts.append(attempt)
        self.set("injection_attempts", attempts)
    
    def get_false_quotations(self) -> List[Dict]:
        """
        获取虚假引用记录
        
        Returns:
            虚假引用列表
        """
        return self.get("false_quotations", [])
    
    def add_false_quotation(self, quotation: Dict) -> None:
        """
        添加虚假引用记录
        
        Args:
            quotation: 虚假引用信息
        """
        quotations = self.get_false_quotations()
        quotations.append(quotation)
        self.set("false_quotations", quotations)
    
    def get_game_data_collected(self) -> List[Dict]:
        """
        获取收集的游戏数据
        
        Returns:
            游戏数据列表
        """
        return self.get("game_data_collected", [])
    
    def set_game_data_collected(self, data: List[Dict]) -> None:
        """
        设置收集的游戏数据
        
        Args:
            data: 游戏数据列表
        """
        self.set("game_data_collected", data)
