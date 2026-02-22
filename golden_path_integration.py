# -*- coding: utf-8 -*-
"""
黄金路径学习系统 - 向后兼容的占位符实现
用于魔搭平台部署时的兼容性
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GoldenPathLearningSystem:
    """
    黄金路径学习系统（轻量级兼容版本）
    
    在资源受限环境下提供基础的增量学习功能
    """
    
    def __init__(
        self,
        model_dir: str = './ml_models',
        data_dir: str = './game_data',
        retrain_interval: int = 10,
        min_samples: int = 50,
        enable_golden_path: bool = False
    ):
        """
        初始化学习系统
        
        Args:
            model_dir: 模型保存目录
            data_dir: 数据保存目录
            retrain_interval: 重训练间隔（游戏场数）
            min_samples: 最小训练样本数
            enable_golden_path: 是否启用黄金路径（轻量级版本忽略此参数）
        """
        self.model_dir = Path(model_dir)
        self.data_dir = Path(data_dir)
        self.retrain_interval = retrain_interval
        self.min_samples = min_samples
        self.enable_golden_path = enable_golden_path
        
        # 创建必要的目录
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前阶段（兼容性）
        self.current_stage = 1
        
        # 游戏计数器
        self.game_count = 0
        
        logger.info(f"GoldenPathLearningSystem initialized (compatibility mode)")
        logger.info(f"  Model dir: {self.model_dir}")
        logger.info(f"  Data dir: {self.data_dir}")
        logger.info(f"  Retrain interval: {self.retrain_interval}")
        logger.info(f"  Min samples: {self.min_samples}")
        logger.info(f"  Golden path enabled: {self.enable_golden_path}")
    
    def collect_game_data(self, game_data: dict) -> None:
        """
        收集游戏数据
        
        Args:
            game_data: 游戏数据字典
        """
        try:
            import json
            from datetime import datetime
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.data_dir / f"game_{timestamp}.json"
            
            # 保存数据
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, ensure_ascii=False, indent=2)
            
            self.game_count += 1
            logger.info(f"Game data collected: {filename}")
            
            # 检查是否需要重训练
            if self.game_count % self.retrain_interval == 0:
                logger.info(f"Reached retrain interval ({self.game_count} games)")
                self.retrain_models()
        
        except Exception as e:
            logger.error(f"Failed to collect game data: {e}")
    
    def retrain_models(self) -> None:
        """
        重训练模型（占位符实现）
        """
        try:
            # 统计数据文件数量
            data_files = list(self.data_dir.glob("game_*.json"))
            
            if len(data_files) < self.min_samples:
                logger.info(
                    f"Not enough samples for training: "
                    f"{len(data_files)}/{self.min_samples}"
                )
                return
            
            logger.info(f"Starting model retraining with {len(data_files)} samples...")
            
            # 在轻量级版本中，这里只是记录日志
            # 实际的ML训练由各个角色智能体自己处理
            logger.info("Model retraining completed (compatibility mode)")
        
        except Exception as e:
            logger.error(f"Failed to retrain models: {e}")
    
    def print_statistics(self) -> None:
        """打印统计信息"""
        try:
            # 统计数据文件
            data_files = list(self.data_dir.glob("game_*.json"))
            
            logger.info("=" * 60)
            logger.info("Learning System Statistics")
            logger.info("=" * 60)
            logger.info(f"  Total games collected: {len(data_files)}")
            logger.info(f"  Games since last train: {self.game_count % self.retrain_interval}")
            logger.info(f"  Current stage: {self.current_stage}")
            logger.info(f"  Golden path enabled: {self.enable_golden_path}")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"Failed to print statistics: {e}")
    
    def get_stage_info(self) -> dict:
        """
        获取当前阶段信息
        
        Returns:
            阶段信息字典
        """
        return {
            'stage': self.current_stage,
            'name': 'Basic Learning',
            'description': 'Compatibility mode for resource-constrained environments',
            'golden_path_enabled': self.enable_golden_path
        }


# 向后兼容的别名
IncrementalLearningSystem = GoldenPathLearningSystem


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    system = GoldenPathLearningSystem(
        model_dir='./test_models',
        data_dir='./test_data',
        enable_golden_path=False
    )
    
    system.print_statistics()
    
    # 模拟收集数据
    test_game_data = {
        'game_id': 'test_001',
        'winner': 'good',
        'players': []
    }
    
    system.collect_game_data(test_game_data)
    
    logger.info("✓ GoldenPathLearningSystem test completed")
