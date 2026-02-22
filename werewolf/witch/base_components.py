# -*- coding: utf-8 -*-
"""
Witch基础组件

提供Witch角色使用的基础类和工具
"""

from typing import Any, Dict, List, Optional
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_components import BaseMemoryDAO
from werewolf.common.utils import DataValidator as CommonDataValidator


class WitchMemoryDAO(BaseMemoryDAO):
    """
    Witch专用的内存数据访问对象
    
    提供女巫角色特定的内存访问方法
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
        except Exception:
            pass
    
    # ==================== 基础信息 ====================
    
    def get_my_name(self) -> str:
        """
        获取自己的名字
        
        Returns:
            玩家名称
        """
        return self.get("name", "Unknown")
    
    # ==================== 药品状态 ====================
    
    def get_has_antidote(self) -> bool:
        """
        是否还有解药
        
        Returns:
            是否有解药
        """
        return self.get("has_antidote", True)
    
    def set_has_antidote(self, value: bool) -> None:
        """
        设置解药状态
        
        Args:
            value: 是否有解药
        """
        self.set("has_antidote", value)
    
    def get_has_poison(self) -> bool:
        """
        是否还有毒药
        
        Returns:
            是否有毒药
        """
        return self.get("has_poison", True)
    
    def set_has_poison(self, value: bool) -> None:
        """
        设置毒药状态
        
        Args:
            value: 是否有毒药
        """
        self.set("has_poison", value)
    
    # ==================== 信任分数 ====================
    
    def get_trust_scores(self) -> Dict[str, float]:
        """
        获取信任分数
        
        Returns:
            信任分数字典
        """
        return self.get_dict("trust_scores", {})
    
    def set_trust_scores(self, scores: Dict[str, float]) -> None:
        """
        设置信任分数
        
        Args:
            scores: 信任分数字典
        """
        self.set("trust_scores", scores)
    
    # ==================== 玩家数据 ====================
    
    def get_player_data(self) -> Dict[str, Dict[str, Any]]:
        """
        获取玩家数据
        
        Returns:
            玩家数据字典
        """
        return self.get_dict("player_data", {})
    
    def set_player_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        设置玩家数据
        
        Args:
            data: 玩家数据字典
        """
        self.set("player_data", data)
    
    # ==================== 预言家验证 ====================
    
    def get_seer_checks(self) -> Dict[str, str]:
        """
        获取预言家验证结果
        
        Returns:
            验证结果字典
        """
        return self.get_dict("seer_checks", {})
    
    # ==================== 药品使用历史 ====================
    
    def get_saved_players(self) -> List[str]:
        """
        获取已救玩家列表
        
        Returns:
            已救玩家列表
        """
        return self.get_list("saved_players", [])
    
    def add_saved_player(self, player: str) -> None:
        """
        添加已救玩家
        
        Args:
            player: 玩家名称
        """
        saved = self.get_saved_players()
        if player not in saved:
            saved.append(player)
            self.set("saved_players", saved)
    
    def get_poisoned_players(self) -> List[str]:
        """
        获取已毒玩家列表
        
        Returns:
            已毒玩家列表
        """
        return self.get_list("poisoned_players", [])
    
    def add_poisoned_player(self, player: str) -> None:
        """
        添加已毒玩家
        
        Args:
            player: 玩家名称
        """
        poisoned = self.get_poisoned_players()
        if player not in poisoned:
            poisoned.append(player)
            self.set("poisoned_players", poisoned)
    
    # ==================== 游戏进度 ====================
    
    def get_current_night(self) -> int:
        """
        获取当前夜晚数
        
        Returns:
            夜晚数
        """
        return self.get("current_night", 0)
    
    def increment_night(self) -> int:
        """
        增加夜晚计数
        
        Returns:
            新的夜晚数
        """
        current = self.get_current_night()
        new_night = current + 1
        self.set("current_night", new_night)
        return new_night
    
    def get_current_day(self) -> int:
        """
        获取当前天数
        
        Returns:
            天数
        """
        return self.get("current_day", 0)
    
    def increment_day(self) -> int:
        """
        增加天数计数
        
        Returns:
            新的天数
        """
        current = self.get_current_day()
        new_day = current + 1
        self.set("current_day", new_day)
        return new_day
    
    def get_wolves_eliminated(self) -> int:
        """
        获取已淘汰狼人数
        
        Returns:
            狼人数
        """
        return self.get("wolves_eliminated", 0)
    
    def get_good_players_lost(self) -> int:
        """
        获取已损失好人数
        
        Returns:
            好人数
        """
        return self.get("good_players_lost", 0)


class DataValidator(CommonDataValidator):
    """
    数据验证器（继承通用验证器）- 企业级五星标准
    
    提供女巫角色特定的数据验证方法
    """
    
    @staticmethod
    def validate_potion_status(has_antidote: Any, has_poison: Any) -> bool:
        """
        验证药品状态（企业级五星标准）
        
        Args:
            has_antidote: 解药状态
            has_poison: 毒药状态
            
        Returns:
            是否有效
        """
        if not isinstance(has_antidote, bool) or not isinstance(has_poison, bool):
            logger.error(f"Invalid potion status types: antidote={type(has_antidote)}, poison={type(has_poison)}")
            return False
        return True
    
    @staticmethod
    def validate_saved_players(saved_players: Any) -> bool:
        """
        验证已救玩家列表（企业级五星标准）
        
        Args:
            saved_players: 已救玩家列表
            
        Returns:
            是否有效
        """
        if not isinstance(saved_players, list):
            logger.error(f"Invalid saved_players type: {type(saved_players)}")
            return False
        
        # 验证每个玩家名称
        for player in saved_players:
            if not DataValidator.validate_player_name(player):
                logger.error(f"Invalid player name in saved_players: {player}")
                return False
        
        return True
    
    @staticmethod
    def validate_poisoned_players(poisoned_players: Any) -> bool:
        """
        验证已毒玩家列表（企业级五星标准）
        
        Args:
            poisoned_players: 已毒玩家列表
            
        Returns:
            是否有效
        """
        if not isinstance(poisoned_players, list):
            logger.error(f"Invalid poisoned_players type: {type(poisoned_players)}")
            return False
        
        # 验证每个玩家名称
        for player in poisoned_players:
            if not DataValidator.validate_player_name(player):
                logger.error(f"Invalid player name in poisoned_players: {player}")
                return False
        
        return True
    
    @staticmethod
    def validate_night_number(night: Any) -> bool:
        """
        验证夜晚数（企业级五星标准）
        
        Args:
            night: 夜晚数
            
        Returns:
            是否有效
        """
        if not isinstance(night, int):
            logger.error(f"Invalid night type: {type(night)}")
            return False
        
        if night < 0:
            logger.error(f"Invalid night number: {night} (must be >= 0)")
            return False
        
        if night > 20:  # 合理上限（12人局不太可能超过20夜）
            logger.warning(f"Unusually high night number: {night}")
        
        return True
