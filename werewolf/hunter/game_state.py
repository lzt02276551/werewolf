"""
Hunter游戏状态管理器

管理游戏状态的跟踪和分析，提供游戏阶段评估和玩家状态管理
"""

from typing import List, Set, Dict, Any
from agent_build_sdk.utils.logger import logger
import re


class GameStateManager:
    """
    游戏状态管理器
    
    职责：
    - 跟踪死亡玩家
    - 评估游戏阶段
    - 统计存活人数
    - 分析游戏局势
    
    Attributes:
        config: 配置对象
        memory_dao: 内存数据访问对象
    """
    
    def __init__(self, config, memory_dao):
        """
        初始化游戏状态管理器
        
        Args:
            config: HunterConfig配置对象
            memory_dao: MemoryDAO内存访问对象
        """
        self.config = config
        self.memory_dao = memory_dao
    
    def update_dead_players(self) -> None:
        """
        从历史记录中更新死亡玩家列表
        
        扫描游戏历史，识别所有死亡玩家并更新到内存中
        """
        try:
            history = self.memory_dao.get_history()
            dead_players = set()
            
            # 扫描历史记录中的死亡关键词
            death_keywords = ["died", "killed", "eliminated", "shot", "poisoned", "voted out"]
            
            for msg in history:
                # 检查是否包含死亡关键词
                if any(keyword in msg.lower() for keyword in death_keywords):
                    # 提取玩家编号
                    player_matches = re.findall(r'No\.(\d+)', msg)
                    for player_num in player_matches:
                        dead_players.add(f"No.{player_num}")
            
            # 更新到内存
            self.memory_dao.set("dead_players", dead_players)
            
            if dead_players:
                logger.debug(f"[GameState] Dead players updated: {dead_players}")
                
        except Exception as e:
            logger.error(f"[GameState] Failed to update dead players: {e}")
    
    def get_current_day(self) -> int:
        """
        获取当前天数
        
        从游戏历史中提取当前是第几天
        
        Returns:
            当前天数，至少为1
        """
        try:
            history = self.memory_dao.get_history()
            current_day = 0
            
            # 扫描历史记录中的天数信息
            for msg in history:
                # 匹配 "Day X" 或 "第X天" 等模式
                match = re.search(r'day\s+(\d+)', msg.lower())
                if match:
                    day = int(match.group(1))
                    if day > current_day:
                        current_day = day
            
            # 至少返回第1天
            return max(1, current_day)
            
        except Exception as e:
            logger.error(f"[GameState] Failed to get current day: {e}")
            return 1
    
    def count_alive_players(self) -> int:
        """
        统计存活玩家数量
        
        Returns:
            存活玩家数量
        """
        try:
            dead_players = self.memory_dao.get_dead_players()
            # 假设总共12个玩家（标准12人局）
            total_players = 12
            alive_count = total_players - len(dead_players)
            
            logger.debug(f"[GameState] Alive players: {alive_count}/{total_players}")
            return alive_count
            
        except Exception as e:
            logger.error(f"[GameState] Failed to count alive players: {e}")
            return 12  # 默认返回初始人数
    
    def assess_game_phase(self) -> str:
        """
        评估游戏阶段
        
        根据当前天数和存活人数判断游戏处于哪个阶段
        
        Returns:
            游戏阶段: "early" | "mid" | "late" | "critical"
        """
        current_day = self.get_current_day()
        alive_count = self.count_alive_players()
        
        # 危急阶段：存活人数≤6
        if alive_count <= self.config.critical_alive_threshold:
            return "critical"
        
        # 晚期：第6天及以后
        elif current_day >= self.config.late_game_day_threshold:
            return "late"
        
        # 中期：第3-5天
        elif current_day >= self.config.early_game_reveal_threshold:
            return "mid"
        
        # 早期：第1-2天
        else:
            return "early"
    
    def evaluate_game_situation(self) -> Dict[str, Any]:
        """
        评估游戏局势
        
        综合评估当前游戏状态，返回详细信息
        
        Returns:
            包含游戏状态信息的字典：
            - current_day: 当前天数
            - alive_count: 存活人数
            - phase: 游戏阶段
            - dead_players: 死亡玩家集合
        """
        return {
            "current_day": self.get_current_day(),
            "alive_count": self.count_alive_players(),
            "phase": self.assess_game_phase(),
            "dead_players": self.memory_dao.get_dead_players()
        }
