"""
游戏数据收集器（重构版）
负责收集、存储和管理游戏数据
采用工具类减少代码重复
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from config import config
from utils import FileUtils, DataValidator, StatisticsCalculator, TimestampUtils, Logger

logger = logging.getLogger(__name__)


class GameDataCollector:
    """游戏数据收集器（重构版）"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化数据收集器
        
        Args:
            data_dir: 数据目录路径（可选，默认使用配置）
        """
        self.data_dir = Path(data_dir) if data_dir else config.DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        
        self.merged_file = self.data_dir / 'merged_history.json'
        
        logger.info(f"GameDataCollector initialized: {self.data_dir}")
    
    def collect_game_data(self, game_id, players_data):
        """
        收集单局游戏数据
        
        Args:
            game_id: 游戏ID
            players_data: 玩家数据列表
        """
        # 验证输入
        if not players_data or not isinstance(players_data, list):
            logger.error(f"Invalid players_data: {type(players_data)}")
            return False
        
        if len(players_data) == 0:
            logger.error("Empty players_data")
            return False
        
        # 构建游戏数据
        game_data = {
            'game_id': game_id,
            'timestamp': TimestampUtils.get_timestamp(),
            'players': []
        }
        
        # 处理每个玩家的数据
        for player in players_data:
            if not isinstance(player, dict):
                logger.warning(f"Skipping invalid player data: {type(player)}")
                continue
            
            # 安全获取角色信息
            role = player.get('role', 'unknown')
            if role is None or role == '':
                role = 'unknown'
            
            # 判断是否为狼人（使用工具类）
            is_wolf = DataValidator.is_wolf_role(role)
            
            # 统一使用behaviors字段，优先使用behaviors，其次使用data
            behaviors = player.get('behaviors')
            if behaviors is None:
                behaviors = player.get('data', {})
            
            # 确保behaviors是字典且非空
            if not isinstance(behaviors, dict):
                behaviors = {}
            
            player_info = {
                'name': player.get('name', 'Unknown'),
                'role': role,
                'is_wolf': is_wolf,
                'data': behaviors,  # 保持向后兼容
                'speeches': player.get('speeches', []),
                'votes': player.get('votes', []),
                'behaviors': behaviors
            }
            
            game_data['players'].append(player_info)
        
        # 验证至少有一个有效玩家
        if len(game_data['players']) == 0:
            logger.error("No valid players in game data")
            return False
        
        # 保存到文件
        timestamp = TimestampUtils.get_timestamp_str()
        filename = f"game_{game_id}_{timestamp}.json"
        filepath = self.data_dir / filename
        
        if FileUtils.write_json(filepath, game_data):
            logger.info(f"✓ Game data collected: {filename}")
            logger.info(f"  - Players: {len(game_data['players'])}")
            logger.info(f"  - Wolves: {sum(1 for p in game_data['players'] if p['is_wolf'])}")
            return True
        else:
            logger.error(f"✗ Failed to collect game data")
            return False
    
    def merge_all_games(self):
        """
        合并所有游戏数据（优化：批量读取，减少文件I/O）
        
        Returns:
            dict: 合并后的数据
        """
        merged_data = {
            'merged_at': TimestampUtils.get_timestamp(),
            'games': []
        }
        
        # 读取所有游戏文件（优化：提前过滤，避免重复检查）
        game_files = [f for f in sorted(self.data_dir.glob('game_*.json')) 
                      if f.name != 'merged_history.json']
        
        # 批量读取（使用工具类）
        games_list = []
        for game_file in game_files:
            game_data = FileUtils.read_json(game_file)
            if game_data:
                games_list.append(game_data)
        
        merged_data['games'] = games_list
        
        # 保存合并文件
        if FileUtils.write_json(self.merged_file, merged_data):
            logger.info(f"✓ Merged {len(games_list)} games")
        else:
            logger.error(f"✗ Failed to save merged data")
        
        return merged_data
    
    def get_statistics(self):
        """
        获取统计信息
        
        Returns:
            dict: 统计数据
        """
        merged_data = self.merge_all_games()
        
        total_games = len(merged_data.get('games', []))
        total_players = sum(len(g.get('players', [])) for g in merged_data.get('games', []))
        
        # 统计角色分布
        role_counts = {}
        for game in merged_data.get('games', []):
            for player in game.get('players', []):
                role = player.get('role', 'unknown')
                role_counts[role] = role_counts.get(role, 0) + 1
        
        # 统计胜率
        wolf_wins = 0
        good_wins = 0
        for game in merged_data.get('games', []):
            winner = game.get('winner', None)
            if winner == 'wolf':
                wolf_wins += 1
            elif winner == 'good':
                good_wins += 1
        
        # 如果没有胜率数据，设置为0
        if total_games == 0:
            wolf_wins = 0
            good_wins = 0
        
        stats = {
            'total_games': total_games,
            'total_players': total_players,
            'role_distribution': role_counts,
            'wolf_wins': wolf_wins,
            'good_wins': good_wins,
            'win_rate': {
                'wolf': StatisticsCalculator.calculate_win_rate(wolf_wins, total_games),
                'good': StatisticsCalculator.calculate_win_rate(good_wins, total_games)
            }
        }
        
        return stats
    
    def print_statistics(self):
        """打印统计信息（使用Logger工具类）"""
        stats = self.get_statistics()
        
        Logger.log_section("Game Data Statistics")
        logger.info(f"Total Games:    {stats['total_games']}")
        logger.info(f"Total Players:  {stats['total_players']}")
        logger.info(f"\nRole Distribution:")
        for role, count in stats['role_distribution'].items():
            logger.info(f"  {role:12s}: {count:4d}")
        logger.info(f"\nWin Statistics:")
        logger.info(f"  Wolf Wins:  {stats['wolf_wins']:4d} ({stats['win_rate']['wolf']:.1%})")
        logger.info(f"  Good Wins:  {stats['good_wins']:4d} ({stats['win_rate']['good']:.1%})")
        Logger.log_section("End Statistics")
    
    def clear_all_data(self):
        """清除所有数据（慎用）"""
        game_files = list(self.data_dir.glob('game_*.json'))
        
        for game_file in game_files:
            try:
                game_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete {game_file.name}: {e}")
        
        if self.merged_file.exists():
            try:
                self.merged_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete merged file: {e}")
        
        logger.info(f"✓ Cleared {len(game_files)} game files")
    
    def export_for_training(self, output_file=None):
        """
        导出训练数据
        
        Args:
            output_file: 输出文件路径（可选）
        
        Returns:
            dict: 训练数据
        """
        merged_data = self.merge_all_games()
        
        training_data = {
            'samples': [],
            'labels': []
        }
        
        for game in merged_data.get('games', []):
            for player in game.get('players', []):
                # 提取特征 - 统一使用behaviors字段
                behaviors = player.get('behaviors')
                if behaviors is None:
                    behaviors = player.get('data', {})
                
                # 跳过没有行为数据的玩家
                if not behaviors or len(behaviors) == 0:
                    logger.debug(f"Skipping player {player.get('name', 'unknown')} - no behavior data")
                    continue
                
                # 获取角色信息
                role = player.get('role', 'unknown')
                if role == 'unknown':
                    logger.debug(f"Skipping player {player.get('name', 'unknown')} - unknown role")
                    continue
                
                sample = {
                    'game_id': game.get('game_id', 'unknown'),
                    'player_name': player.get('name', 'Unknown'),
                    'role': role,
                    'behaviors': behaviors,
                    'speeches': player.get('speeches', []),
                    'votes': player.get('votes', [])
                }
                
                # 标签：判断是否为狼人
                is_wolf = player.get('is_wolf', False)
                # 双重验证：如果is_wolf字段不存在，从role推断（使用工具类）
                if 'is_wolf' not in player:
                    is_wolf = DataValidator.is_wolf_role(role)
                
                label = 1 if is_wolf else 0
                
                training_data['samples'].append(sample)
                training_data['labels'].append(label)
        
        # 保存（如果指定了输出文件）
        if output_file:
            output_path = Path(output_file)
            
            if FileUtils.write_json(output_path, training_data):
                logger.info(f"✓ Training data exported to {output_file}")
                logger.info(f"  - Samples: {len(training_data['samples'])}")
                logger.info(f"  - Wolves: {sum(training_data['labels'])}")
                logger.info(f"  - Goods: {len(training_data['labels']) - sum(training_data['labels'])}")
        
        return training_data


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 示例使用
    collector = GameDataCollector('./game_data')
    
    # 模拟收集数据
    sample_players = [
        {
            'name': 'Player1',
            'role': 'wolf',
            'data': {'trust_score': 30, 'vote_accuracy': 0.4},
            'speeches': ['我是好人', '我觉得2号可疑'],
            'votes': [2, 3]
        },
        {
            'name': 'Player2',
            'role': 'villager',
            'data': {'trust_score': 70, 'vote_accuracy': 0.8},
            'speeches': ['我相信1号', '我们要团结'],
            'votes': [1, 1]
        }
    ]
    
    collector.collect_game_data('test_001', sample_players)
    collector.print_statistics()
