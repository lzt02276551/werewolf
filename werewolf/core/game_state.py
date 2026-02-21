"""
游戏状态封装

提供游戏状态的标准化访问接口
"""

from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from .exceptions import InvalidGameStateError


class GamePhase(Enum):
    """游戏阶段枚举"""
    EARLY = "early"      # 早期(1-2天)
    MID = "mid"          # 中期(3-5天)
    LATE = "late"        # 后期(6+天)
    CRITICAL = "critical"  # 关键期(剩余玩家<=5)


@dataclass
class GameState:
    """
    游戏状态封装类
    
    提供统一的游戏状态访问接口
    
    Attributes:
        day_count: 当前天数
        alive_players: 存活玩家列表
        dead_players: 死亡玩家列表
        speech_history: 发言历史
        vote_history: 投票历史
        night_result: 夜晚结果
        sheriff: 警长
        phase: 游戏阶段
    """
    
    day_count: int = 1
    alive_players: List[str] = field(default_factory=list)
    dead_players: List[str] = field(default_factory=list)
    speech_history: Dict[str, List[str]] = field(default_factory=dict)
    vote_history: List[Dict[str, Any]] = field(default_factory=list)
    night_result: Dict[str, Any] = field(default_factory=dict)
    sheriff: Optional[str] = None
    phase: GamePhase = GamePhase.EARLY
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """
        从字典创建GameState对象
        
        Args:
            data: 游戏状态字典
            
        Returns:
            GameState对象
            
        Raises:
            InvalidGameStateError: 数据无效时抛出
        """
        try:
            day_count = data.get('day_count', 1)
            alive_players = data.get('alive_players', [])
            dead_players = data.get('dead_players', [])
            speech_history = data.get('speech_history', {})
            vote_history = data.get('vote_history', [])
            night_result = data.get('night_result', {})
            sheriff = data.get('sheriff')
            
            # 推断游戏阶段
            phase = cls._infer_phase(day_count, len(alive_players))
            
            return cls(
                day_count=day_count,
                alive_players=alive_players,
                dead_players=dead_players,
                speech_history=speech_history,
                vote_history=vote_history,
                night_result=night_result,
                sheriff=sheriff,
                phase=phase
            )
        except Exception as e:
            raise InvalidGameStateError(f"Failed to create GameState: {e}")
    
    @staticmethod
    def _infer_phase(day_count: int, alive_count: int) -> GamePhase:
        """
        推断游戏阶段
        
        Args:
            day_count: 天数
            alive_count: 存活人数
            
        Returns:
            游戏阶段
        """
        if alive_count <= 5:
            return GamePhase.CRITICAL
        elif day_count >= 6:
            return GamePhase.LATE
        elif day_count >= 3:
            return GamePhase.MID
        else:
            return GamePhase.EARLY
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            游戏状态字典
        """
        return {
            'day_count': self.day_count,
            'alive_players': self.alive_players,
            'dead_players': self.dead_players,
            'speech_history': self.speech_history,
            'vote_history': self.vote_history,
            'night_result': self.night_result,
            'sheriff': self.sheriff,
            'phase': self.phase.value
        }
    
    def validate(self) -> bool:
        """
        验证游戏状态有效性（优化版 - 复用set）
        
        Returns:
            状态是否有效
            
        Raises:
            InvalidGameStateError: 状态无效时抛出
        """
        if self.day_count < 1:
            raise InvalidGameStateError("day_count must be >= 1")
        
        if not self.alive_players:
            raise InvalidGameStateError("alive_players cannot be empty")
        
        # 一次性创建set，复用（性能优化）
        alive_set = set(self.alive_players)
        dead_set = set(self.dead_players)
        
        # 检查alive_players内部重复
        if len(self.alive_players) != len(alive_set):
            raise InvalidGameStateError("Duplicate players in alive_players list")
        
        # 检查dead_players内部重复
        if len(self.dead_players) != len(dead_set):
            raise InvalidGameStateError("Duplicate players in dead_players list")
        
        # 检查alive和dead之间的重复（复用已创建的set）
        overlap = alive_set & dead_set
        if overlap:
            raise InvalidGameStateError(f"Players in both alive and dead lists: {overlap}")
        
        # 检查警长是否在存活玩家中（复用alive_set）
        if self.sheriff and self.sheriff not in alive_set:
            raise InvalidGameStateError(f"Sheriff {self.sheriff} is not in alive players")
        
        return True
    
    def get_alive_count(self) -> int:
        """获取存活玩家数量"""
        return len(self.alive_players)
    
    def get_dead_count(self) -> int:
        """获取死亡玩家数量"""
        return len(self.dead_players)
    
    def is_player_alive(self, player: str) -> bool:
        """检查玩家是否存活"""
        return player in self.alive_players
    
    def is_player_dead(self, player: str) -> bool:
        """检查玩家是否死亡"""
        return player in self.dead_players
    
    def get_player_speeches(self, player: str) -> List[str]:
        """获取玩家的发言历史"""
        return self.speech_history.get(player, [])
    
    def get_last_vote_result(self) -> Optional[Dict[str, Any]]:
        """获取最后一次投票结果"""
        return self.vote_history[-1] if self.vote_history else None
    
    def is_critical_phase(self) -> bool:
        """是否处于关键阶段"""
        return self.phase == GamePhase.CRITICAL
    
    def is_early_phase(self) -> bool:
        """是否处于早期阶段"""
        return self.phase == GamePhase.EARLY
