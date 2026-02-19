# -*- coding: utf-8 -*-
"""
通用工具函数 - 减少代码重复
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def read_json(filepath: Path, default: Any = None) -> Any:
        """
        安全读取JSON文件
        
        Args:
            filepath: 文件路径
            default: 读取失败时的默认值
        
        Returns:
            JSON数据或默认值
        """
        if not filepath.exists():
            return default
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            return default
    
    @staticmethod
    def write_json(filepath: Path, data: Any, indent: int = 2) -> bool:
        """
        安全写入JSON文件
        
        Args:
            filepath: 文件路径
            data: 要写入的数据
            indent: 缩进空格数
        
        Returns:
            是否成功
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except IOError as e:
            logger.error(f"Failed to write {filepath}: {e}")
            return False
    
    @staticmethod
    def read_text(filepath: Path, default: str = '') -> str:
        """
        安全读取文本文件
        
        Args:
            filepath: 文件路径
            default: 读取失败时的默认值
        
        Returns:
            文本内容或默认值
        """
        if not filepath.exists():
            return default
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except IOError as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            return default
    
    @staticmethod
    def write_text(filepath: Path, text: str) -> bool:
        """
        安全写入文本文件
        
        Args:
            filepath: 文件路径
            text: 要写入的文本
        
        Returns:
            是否成功
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            return True
        except IOError as e:
            logger.error(f"Failed to write {filepath}: {e}")
            return False


class DataValidator:
    """数据验证工具类"""
    
    @staticmethod
    def validate_player_data(player_data: Any) -> bool:
        """
        验证玩家数据格式
        
        Args:
            player_data: 玩家数据
        
        Returns:
            是否有效
        """
        if not isinstance(player_data, dict):
            return False
        
        if not player_data:
            return False
        
        # 检查必需字段
        required_fields = ['name', 'role']
        for field in required_fields:
            if field not in player_data:
                return False
        
        return True
    
    @staticmethod
    def validate_role(role: Any) -> bool:
        """
        验证角色名称
        
        Args:
            role: 角色名称
        
        Returns:
            是否有效
        """
        if not role or not isinstance(role, str):
            return False
        
        valid_roles = {
            'wolf', 'wolf_king', 'villager', 'seer',
            'witch', 'guard', 'hunter'
        }
        
        return role in valid_roles
    
    @staticmethod
    def is_wolf_role(role: str) -> bool:
        """
        判断是否为狼人角色
        
        Args:
            role: 角色名称
        
        Returns:
            是否为狼人
        """
        return role in ['wolf', 'wolf_king']


class StatisticsCalculator:
    """统计计算工具类"""
    
    @staticmethod
    def calculate_win_rate(wins: int, total: int) -> float:
        """
        计算胜率
        
        Args:
            wins: 胜利次数
            total: 总次数
        
        Returns:
            胜率（0-1）
        """
        if total == 0:
            return 0.0
        return wins / total
    
    @staticmethod
    def calculate_distribution(items: List[Any]) -> Dict[Any, int]:
        """
        计算分布
        
        Args:
            items: 项目列表
        
        Returns:
            分布字典
        """
        distribution = {}
        for item in items:
            distribution[item] = distribution.get(item, 0) + 1
        return distribution
    
    @staticmethod
    def calculate_percentage(part: int, total: int) -> float:
        """
        计算百分比
        
        Args:
            part: 部分
            total: 总数
        
        Returns:
            百分比（0-100）
        """
        if total == 0:
            return 0.0
        return (part / total) * 100


class TimestampUtils:
    """时间戳工具类"""
    
    @staticmethod
    def get_timestamp() -> str:
        """获取当前时间戳（ISO格式）"""
        return datetime.now().isoformat()
    
    @staticmethod
    def get_timestamp_str() -> str:
        """获取当前时间戳（文件名格式）"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """
        解析时间戳
        
        Args:
            timestamp_str: 时间戳字符串
        
        Returns:
            datetime对象或None
        """
        try:
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return None


class Logger:
    """日志工具类"""
    
    @staticmethod
    def log_section(title: str, width: int = 60):
        """打印分隔线标题"""
        logger.info("=" * width)
        logger.info(title)
        logger.info("=" * width)
    
    @staticmethod
    def log_subsection(title: str, width: int = 60):
        """打印子标题"""
        logger.info("-" * width)
        logger.info(title)
        logger.info("-" * width)
    
    @staticmethod
    def log_dict(data: Dict[str, Any], indent: int = 2):
        """打印字典内容"""
        for key, value in data.items():
            logger.info(f"{' ' * indent}{key}: {value}")
    
    @staticmethod
    def log_list(items: List[Any], indent: int = 2):
        """打印列表内容"""
        for item in items:
            logger.info(f"{' ' * indent}- {item}")


if __name__ == '__main__':
    # 测试工具函数
    logging.basicConfig(level=logging.INFO)
    
    Logger.log_section("Utils Test")
    
    # 测试文件操作
    test_file = Path('test_data.json')
    test_data = {'name': 'Player1', 'role': 'wolf'}
    
    if FileUtils.write_json(test_file, test_data):
        logger.info("✓ Write JSON success")
    
    loaded_data = FileUtils.read_json(test_file)
    if loaded_data == test_data:
        logger.info("✓ Read JSON success")
    
    # 清理测试文件
    if test_file.exists():
        test_file.unlink()
    
    # 测试数据验证
    if DataValidator.validate_player_data(test_data):
        logger.info("✓ Player data validation success")
    
    if DataValidator.is_wolf_role('wolf'):
        logger.info("✓ Wolf role detection success")
    
    # 测试统计计算
    win_rate = StatisticsCalculator.calculate_win_rate(7, 10)
    logger.info(f"✓ Win rate: {win_rate:.1%}")
    
    # 测试时间戳
    timestamp = TimestampUtils.get_timestamp()
    logger.info(f"✓ Timestamp: {timestamp}")
    
    Logger.log_section("Test Complete")
