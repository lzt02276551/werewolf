"""
游戏结束处理器 - 自动集成增量学习

当游戏状态为 STATUS_RESULT 时，自动触发数据收集和模型训练
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GameEndHandler:
    """游戏结束处理器"""
    
    def __init__(self, learning_system=None):
        """
        Args:
            learning_system: IncrementalLearningSystem实例
        """
        self.learning_system = learning_system
        self.current_game_id = None
        self.players_stats = {}  # 存储玩家统计数据
        
        logger.info("GameEndHandler initialized")
    
    def on_game_start(self, game_id: str):
        """游戏开始时调用"""
        self.current_game_id = game_id
        self.players_stats = {}
        logger.info(f"Game started: {game_id}")
    
    def update_player_stats(self, player_name: str, stats: Dict):
        """更新玩家统计数据"""
        if player_name not in self.players_stats:
            self.players_stats[player_name] = {}
        
        self.players_stats[player_name].update(stats)
    
    def on_game_end(self, result_message: str):
        """
        游戏结束时调用（STATUS_RESULT）
        
        Args:
            result_message: 游戏结果消息（包含获胜方信息）
        """
        if not self.learning_system:
            logger.debug("Learning system not available, skipping data collection")
            return
        
        if not self.current_game_id:
            logger.warning("No game ID set, cannot collect data")
            return
        
        try:
            # 从结果消息中提取信息
            winner = self._extract_winner(result_message)
            logger.info(f"Game {self.current_game_id} ended, winner: {winner}")
            
            # 准备玩家数据
            players_data = self._prepare_players_data()
            
            if not players_data:
                logger.warning("No player data collected, skipping")
                return
            
            # 调用增量学习系统
            result = self.learning_system.on_game_end(
                self.current_game_id,
                players_data
            )
            
            # 记录结果
            logger.info("=" * 60)
            logger.info(f"✓ 游戏 {self.current_game_id} 数据收集完成")
            logger.info(f"  - 数据已收集: {result['data_collected']}")
            logger.info(f"  - 触发重训练: {result['retrain_triggered']}")
            logger.info(f"  - 总游戏数: {result['game_count']}")
            logger.info(f"  - 下次重训练: 第{result['next_retrain_at']}局")
            
            if result['retrain_triggered']:
                logger.info("🎉 模型已更新！ML变得更强了！")
            
            logger.info("=" * 60)
            
            # 重置状态
            self.current_game_id = None
            self.players_stats = {}
            
        except Exception as e:
            logger.error(f"Failed to handle game end: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_winner(self, result_message: str) -> str:
        """从结果消息中提取获胜方"""
        message_lower = result_message.lower()
        
        # 优先检查明确的获胜方表述
        # 检查好人阵营获胜
        good_win_patterns = [
            'good side win', 'good camp win', 'villager win', 'villagers win',
            '好人胜利', '好人获胜', '好人阵营胜利', '好人阵营获胜',
            'good guys win', 'village win'
        ]
        for pattern in good_win_patterns:
            if pattern in message_lower:
                return 'good'
        
        # 检查狼人阵营获胜
        wolf_win_patterns = [
            'wolf side win', 'wolf camp win', 'wolves win', 'werewolves win',
            '狼人胜利', '狼人获胜', '狼人阵营胜利', '狼人阵营获胜',
            'wolf team win'
        ]
        for pattern in wolf_win_patterns:
            if pattern in message_lower:
                return 'wolf'
        
        # 如果没有明确的模式，使用原来的逻辑（但更谨慎）
        has_wolf = 'wolf' in message_lower or '狼人' in message_lower
        has_good = 'good' in message_lower or '好人' in message_lower or 'villager' in message_lower
        has_win = 'win' in message_lower or '胜利' in message_lower or '获胜' in message_lower
        
        if has_win:
            # 如果只提到狼人，没有提到好人，可能是狼人胜利
            if has_wolf and not has_good:
                return 'wolf'
            # 如果只提到好人，没有提到狼人，可能是好人胜利
            elif has_good and not has_wolf:
                return 'good'
        
        logger.warning(f"Could not determine winner from message: {result_message}")
        return 'unknown'
    
    def _prepare_players_data(self):
        """准备玩家数据用于增量学习"""
        players_data = []
        
        for player_name, stats in self.players_stats.items():
            # 判断角色（从stats中获取，如果没有则跳过该玩家）
            role = stats.get('role', 'unknown')
            if role == 'unknown':
                logger.warning(f"Player {player_name} has unknown role, skipping")
                continue
            
            is_wolf = role in ['wolf', 'wolf_king']
            
            # 提取19个特征
            player_data = {
                "name": player_name,
                "role": "wolf" if is_wolf else "good",
                "data": {
                    "trust_score": stats.get('trust_score', 50),
                    "vote_accuracy": stats.get('vote_accuracy', 0.5),
                    "contradiction_count": stats.get('contradiction_count', 0),
                    "injection_attempts": stats.get('injection_attempts', 0),
                    "false_quotation_count": stats.get('false_quotation_count', 0),
                    "speech_lengths": stats.get('speech_lengths', [100]),
                    "voting_speed_avg": stats.get('voting_speed_avg', 5.0),
                    "vote_targets": stats.get('vote_targets', []),
                    "mentions_others_count": stats.get('mentions_others_count', 0),
                    "mentioned_by_others_count": stats.get('mentioned_by_others_count', 0),
                    "aggressive_score": stats.get('aggressive_score', 0.5),
                    "defensive_score": stats.get('defensive_score', 0.5),
                    "emotion_keyword_count": stats.get('emotion_keyword_count', 0),
                    "logic_keyword_count": stats.get('logic_keyword_count', 0),
                    "night_survival_rate": stats.get('night_survival_rate', 0.5),
                    "alliance_strength": stats.get('alliance_strength', 0.5),
                    "isolation_score": stats.get('isolation_score', 0.5),
                    "speech_consistency_score": stats.get('speech_consistency_score', 0.5),
                    "avg_response_time": stats.get('avg_response_time', 5.0)
                }
            }
            
            players_data.append(player_data)
        
        return players_data


# 全局游戏结束处理器实例
_game_end_handler = None


def get_game_end_handler(learning_system=None):
    """获取全局游戏结束处理器实例"""
    global _game_end_handler
    
    if _game_end_handler is None:
        _game_end_handler = GameEndHandler(learning_system)
    elif learning_system is not None and _game_end_handler.learning_system is None:
        # 如果实例已存在但没有learning_system，则更新它
        _game_end_handler.learning_system = learning_system
    
    return _game_end_handler


def set_learning_system(learning_system):
    """设置增量学习系统"""
    global _game_end_handler
    
    if _game_end_handler is None:
        _game_end_handler = GameEndHandler(learning_system)
    else:
        _game_end_handler.learning_system = learning_system
    
    logger.info("Learning system attached to GameEndHandler")
