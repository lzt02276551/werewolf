"""
输入验证数据模型

使用Pydantic验证游戏输入数据
验证需求: AC-1.2.1, AC-1.2.2, AC-1.2.3
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any


class PlayerName(BaseModel):
    """
    玩家名称验证模型
    
    验证需求: AC-1.2.2
    格式要求: No.\\d+ (例如: No.1, No.10)
    """
    name: str = Field(..., pattern=r"^No\.\d+$")


class CandidateList(BaseModel):
    """
    候选人列表验证模型
    
    验证需求: AC-1.2.3
    长度限制: 1-20个候选人
    """
    candidates: List[PlayerName] = Field(..., min_length=1, max_length=20)
    
    @field_validator('candidates')
    @classmethod
    def unique_candidates(cls, v: List[PlayerName]) -> List[PlayerName]:
        """验证候选人列表不包含重复项"""
        names = [c.name for c in v]
        if len(names) != len(set(names)):
            raise ValueError("候选人列表包含重复项")
        return v


class PlayerState(BaseModel):
    """
    玩家状态模型
    
    验证需求: AC-1.2.1
    """
    name: str = Field(..., pattern=r"^No\.\d+$")
    role: Optional[str] = None
    is_alive: bool = True
    trust_score: float = Field(default=50.0, ge=0.0, le=100.0)


class GameState(BaseModel):
    """
    游戏状态模型
    
    验证需求: AC-1.2.1
    """
    day: int = Field(ge=1)
    phase: str  # "day", "night", "voting"
    players: Dict[str, PlayerState]
    dead_players: List[str] = Field(default_factory=list)
    voting_history: List[Dict[str, Any]] = Field(default_factory=list)
    speech_history: List[Dict[str, Any]] = Field(default_factory=list)


class VoteDecisionInput(BaseModel):
    """
    投票决策输入验证模型
    
    验证需求: AC-1.2.1, AC-1.2.2, AC-1.2.3
    """
    candidates: CandidateList
    game_state: GameState
    player_profiles: Dict[str, Any] = Field(default_factory=dict)
