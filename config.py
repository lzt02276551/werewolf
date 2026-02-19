# -*- coding: utf-8 -*-
"""
全局配置管理 - 统一管理所有配置项
采用单例模式，确保配置一致性
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """全局配置类（单例模式）"""
    
    _instance: Optional['Config'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # ==================== 路径配置 ====================
        self.PROJECT_ROOT = Path(__file__).parent
        self.DATA_DIR = Path(os.getenv('DATA_DIR', self.PROJECT_ROOT / 'game_data'))
        self.MODEL_DIR = Path(os.getenv('ML_MODEL_DIR', self.PROJECT_ROOT / 'ml_models'))
        
        # 确保目录存在
        self.DATA_DIR.mkdir(exist_ok=True)
        self.MODEL_DIR.mkdir(exist_ok=True)
        
        # ==================== ML配置 ====================
        self.ML_ENABLED = os.getenv('ENABLE_ML', 'true').lower() == 'true'
        self.GOLDEN_PATH_ENABLED = os.getenv('ENABLE_GOLDEN_PATH', 'true').lower() == 'true'
        
        # 训练配置
        self.MIN_SAMPLES = int(os.getenv('ML_MIN_SAMPLES', '1800'))
        self.RETRAIN_INTERVAL = int(os.getenv('ML_TRAIN_INTERVAL', '30'))
        self.KEEP_TRAINING_DATA = os.getenv('ML_KEEP_DATA', 'true').lower() == 'true'
        
        # 模型配置
        self.CONTAMINATION = float(os.getenv('ML_CONTAMINATION', '0.33'))
        self.ENSEMBLE_WEIGHTS = {
            'rf': float(os.getenv('ML_RF_WEIGHT', '0.4')),
            'gb': float(os.getenv('ML_GB_WEIGHT', '0.4')),
            'xgb': float(os.getenv('ML_XGB_WEIGHT', '0.2'))
        }
        
        # ==================== 数据收集配置 ====================
        self.COLLECT_GAME_DATA = os.getenv('COLLECT_DATA', 'true').lower() == 'true'
        self.AUTO_MERGE_DATA = os.getenv('AUTO_MERGE', 'true').lower() == 'true'
        
        # ==================== 训练数据生成配置 ====================
        self.SYNTHETIC_GOOD_SAMPLES = int(os.getenv('SYNTHETIC_GOOD', '150'))
        self.SYNTHETIC_WOLF_SAMPLES = int(os.getenv('SYNTHETIC_WOLF', '75'))
        
        # ==================== 日志配置 ====================
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', '')
        
        self._initialized = True
    
    def get_model_path(self, model_name: str) -> Path:
        """获取模型文件路径"""
        return self.MODEL_DIR / model_name
    
    def get_data_path(self, data_name: str) -> Path:
        """获取数据文件路径"""
        return self.DATA_DIR / data_name
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'PROJECT_ROOT': str(self.PROJECT_ROOT),
            'DATA_DIR': str(self.DATA_DIR),
            'MODEL_DIR': str(self.MODEL_DIR),
            'ML_ENABLED': self.ML_ENABLED,
            'GOLDEN_PATH_ENABLED': self.GOLDEN_PATH_ENABLED,
            'MIN_SAMPLES': self.MIN_SAMPLES,
            'RETRAIN_INTERVAL': self.RETRAIN_INTERVAL,
            'KEEP_TRAINING_DATA': self.KEEP_TRAINING_DATA,
            'CONTAMINATION': self.CONTAMINATION,
            'ENSEMBLE_WEIGHTS': self.ENSEMBLE_WEIGHTS,
            'COLLECT_GAME_DATA': self.COLLECT_GAME_DATA,
            'AUTO_MERGE_DATA': self.AUTO_MERGE_DATA,
            'SYNTHETIC_GOOD_SAMPLES': self.SYNTHETIC_GOOD_SAMPLES,
            'SYNTHETIC_WOLF_SAMPLES': self.SYNTHETIC_WOLF_SAMPLES,
            'LOG_LEVEL': self.LOG_LEVEL
        }
    
    def __repr__(self) -> str:
        return f"Config({self.to_dict()})"


# 全局配置实例
config = Config()


# 向后兼容：提供旧的MLConfig类
class MLConfig:
    """ML配置类（向后兼容）"""
    
    @staticmethod
    def get_model_dir() -> str:
        return str(config.MODEL_DIR)
    
    @staticmethod
    def get_data_dir() -> str:
        return str(config.DATA_DIR)
    
    @staticmethod
    def is_enabled() -> bool:
        return config.ML_ENABLED
    
    @staticmethod
    def get_min_samples() -> int:
        return config.MIN_SAMPLES
    
    @staticmethod
    def get_retrain_interval() -> int:
        return config.RETRAIN_INTERVAL


if __name__ == '__main__':
    # 测试配置
    print("=" * 60)
    print("Global Configuration")
    print("=" * 60)
    
    for key, value in config.to_dict().items():
        print(f"{key:25s}: {value}")
    
    print("=" * 60)
