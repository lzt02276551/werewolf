"""
决策上下文模块

提供决策过程中的缓存和共享数据管理功能。

主要功能：
- 缓存决策周期内的计算结果，避免重复计算
- 提供统一的数据访问接口
- 管理游戏状态和玩家档案

验证需求：AC-2.1.1, AC-2.1.2
"""

from typing import Any, Callable, Dict, Optional


class DecisionContext:
    """
    决策上下文，提供缓存和共享数据
    
    决策上下文在单个决策周期内维护计算结果的缓存，避免重复计算相同的值。
    例如，多个评分维度可能都需要某个玩家的信任分数，通过缓存可以只计算一次。
    
    属性：
        game_state: 游戏状态字典，包含当前游戏的所有状态信息
        player_profiles: 玩家档案字典，包含所有玩家的历史信息
        target_player: 当前评估的目标玩家名称（可选）
        _cache: 内部缓存字典，存储计算结果
    
    示例：
        >>> game_state = {'day': 3, 'phase': 'voting'}
        >>> player_profiles = {'No.1': {'role': 'villager'}}
        >>> context = DecisionContext(game_state, player_profiles)
        >>> 
        >>> # 使用缓存获取或计算值
        >>> trust_score = context.get_cached(
        ...     'trust_score_No.1',
        ...     lambda: calculate_trust_score('No.1')
        ... )
        >>> 
        >>> # 决策周期结束后清空缓存
        >>> context.clear_cache()
    
    验证需求：AC-2.1.1, AC-2.1.2
    """
    
    def __init__(self, game_state: dict, player_profiles: dict):
        """
        初始化决策上下文
        
        参数：
            game_state: 游戏状态字典，包含当前游戏的所有状态信息
                例如：{'day': 3, 'phase': 'voting', 'players': {...}}
            player_profiles: 玩家档案字典，包含所有玩家的历史信息
                例如：{'No.1': {'voting_history': [...], 'speech_history': [...]}}
        """
        self.game_state = game_state
        self.player_profiles = player_profiles
        self.target_player: Optional[str] = None
        self._cache: Dict[str, Any] = {}
    
    def get_cached(
        self,
        key: str,
        compute_fn: Callable[[], Any]
    ) -> Any:
        """
        获取缓存值，如果不存在则计算并缓存
        
        使用惰性计算模式：只有在缓存中找不到值时才调用计算函数。
        这样可以避免重复计算相同的值，提高性能。
        
        参数：
            key: 缓存键，应该是唯一的字符串标识符
                建议格式：'{metric_name}_{player_name}'
                例如：'trust_score_No.1', 'werewolf_prob_No.2'
            compute_fn: 计算函数，无参数，返回要缓存的值
                只有在缓存未命中时才会被调用
        
        返回：
            缓存值或计算结果
        
        示例：
            >>> context = DecisionContext({}, {})
            >>> call_count = 0
            >>> def expensive_computation():
            ...     nonlocal call_count
            ...     call_count += 1
            ...     return 42
            >>> 
            >>> # 第一次调用，执行计算
            >>> result1 = context.get_cached('key1', expensive_computation)
            >>> print(result1, call_count)  # 42, 1
            >>> 
            >>> # 第二次调用，使用缓存
            >>> result2 = context.get_cached('key1', expensive_computation)
            >>> print(result2, call_count)  # 42, 1 (call_count没有增加)
        
        验证需求：AC-2.1.2
        """
        if key not in self._cache:
            self._cache[key] = compute_fn()
        return self._cache[key]
    
    def clear_cache(self) -> None:
        """
        清空缓存
        
        应该在每个决策周期结束后调用，以确保下一个决策周期使用新的数据。
        缓存的数据可能依赖于特定的游戏状态，如果状态改变，缓存的数据可能不再有效。
        
        示例：
            >>> context = DecisionContext({}, {})
            >>> context.get_cached('key1', lambda: 42)
            >>> print(len(context._cache))  # 1
            >>> 
            >>> context.clear_cache()
            >>> print(len(context._cache))  # 0
        
        验证需求：AC-2.1.4
        """
        self._cache.clear()
    
    def get_player_profile(self, player_name: str) -> dict:
        """
        获取玩家档案
        
        提供统一的接口访问玩家档案数据。如果玩家不存在，返回空字典。
        
        参数：
            player_name: 玩家名称，例如 'No.1'
        
        返回：
            玩家档案字典，如果玩家不存在则返回空字典 {}
        
        示例：
            >>> player_profiles = {
            ...     'No.1': {'role': 'villager', 'trust_score': 50.0},
            ...     'No.2': {'role': 'werewolf', 'trust_score': 30.0}
            ... }
            >>> context = DecisionContext({}, player_profiles)
            >>> 
            >>> profile1 = context.get_player_profile('No.1')
            >>> print(profile1['role'])  # 'villager'
            >>> 
            >>> profile3 = context.get_player_profile('No.3')
            >>> print(profile3)  # {}
        
        验证需求：AC-2.1.1
        """
        return self.player_profiles.get(player_name, {})
