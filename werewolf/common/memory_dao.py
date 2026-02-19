"""
内存数据访问对象

提供统一的内存访问接口
"""

from typing import Any, Dict, List, Optional
from werewolf.core.base_components import BaseMemoryDAO


class StandardMemoryDAO(BaseMemoryDAO):
    """
    标准内存DAO实现
    
    适配SDK的memory对象
    """
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取内存中的值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            值
        """
        try:
            value = self.memory.load_variable(key)
            return value if value is not None else default
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置内存中的值
        
        Args:
            key: 键
            value: 值
        """
        try:
            self.memory.set_variable(key, value)
        except Exception as e:
            # 静默失败,避免中断游戏流程
            pass
    
    def get_player_data(self, player: Optional[str] = None) -> Dict[str, Any]:
        """
        获取玩家数据
        
        Args:
            player: 玩家名称(可选)
            
        Returns:
            玩家数据字典
        """
        all_data = self.get("player_data", {})
        
        if player:
            return all_data.get(player, {})
        
        return all_data
    
    def set_player_data(self, player: str, data: Dict[str, Any]) -> None:
        """
        设置玩家数据
        
        Args:
            player: 玩家名称
            data: 玩家数据
        """
        all_data = self.get("player_data", {})
        all_data[player] = data
        self.set("player_data", all_data)
    
    def update_player_data(self, player: str, updates: Dict[str, Any]) -> None:
        """
        更新玩家数据
        
        Args:
            player: 玩家名称
            updates: 更新字典
        """
        all_data = self.get("player_data", {})
        
        if player not in all_data:
            all_data[player] = {}
        
        all_data[player].update(updates)
        self.set("player_data", all_data)
    
    def get_game_state(self) -> Dict[str, Any]:
        """
        获取游戏状态
        
        Returns:
            游戏状态字典
        """
        return self.get("game_state", {})
    
    def update_game_state(self, updates: Dict[str, Any]) -> None:
        """
        更新游戏状态
        
        Args:
            updates: 更新字典
        """
        state = self.get_game_state()
        state.update(updates)
        self.set("game_state", state)
    
    def get_alive_players(self) -> List[str]:
        """
        获取存活玩家列表
        
        Returns:
            存活玩家列表
        """
        return self.get_list("alive_players", [])
    
    def get_dead_players(self) -> List[str]:
        """
        获取死亡玩家列表
        
        Returns:
            死亡玩家列表
        """
        return self.get_list("dead_players", [])
    
    def get_my_name(self) -> str:
        """
        获取自己的名称
        
        Returns:
            玩家名称
        """
        return self.get("name", "")
    
    def get_sheriff(self) -> Optional[str]:
        """
        获取警长
        
        Returns:
            警长名称
        """
        return self.get("sheriff")
    
    def is_sheriff(self) -> bool:
        """
        判断自己是否是警长
        
        Returns:
            是否是警长
        """
        return self.get_my_name() == self.get_sheriff()
    
    def get_seer_checks(self) -> Dict[str, str]:
        """
        获取预言家验证结果
        
        Returns:
            验证结果字典
        """
        return self.get_dict("seer_checks", {})
    
    def get_voting_results(self) -> Dict[int, Dict[str, Any]]:
        """
        获取投票结果
        
        Returns:
            投票结果字典
        """
        return self.get_dict("voting_results", {})
    
    def get_current_day(self) -> int:
        """
        获取当前天数
        
        Returns:
            天数
        """
        game_state = self.get_game_state()
        return game_state.get("current_day", 1)
    
    def get_history(self) -> List[str]:
        """
        获取历史记录
        
        Returns:
            历史记录列表
        """
        try:
            history = self.memory.load_history()
            return history if isinstance(history, list) else []
        except Exception:
            return []
    
    def append_history(self, message: str) -> None:
        """
        添加历史记录
        
        Args:
            message: 消息
        """
        try:
            self.memory.append_history(message)
        except Exception:
            pass
