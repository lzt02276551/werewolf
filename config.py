# -*- coding: utf-8 -*-
"""
全局配置管理 - 统一管理所有配置项
采用单例模式，确保配置一致性
"""

import os
from pathlib import Path
from typing import Optional
import threading


class Config:
    """全局配置类（单例模式 - 线程安全）"""
    
    # 定义常量
    EPSILON = 1e-10  # 浮点数比较阈值
    MIN_WEIGHT_SUM = 0.99  # 权重和最小值
    MAX_WEIGHT_SUM = 1.01  # 权重和最大值
    
    # 权重归一化相关常量
    WEIGHT_TOLERANCE = 0.01  # 权重总和容差
    MIN_VALID_WEIGHT_SUM = 0.1  # 最小有效权重总和
    MAX_SINGLE_WEIGHT = 1.0  # 单个权重最大值
    MIN_SINGLE_WEIGHT = 0.0  # 单个权重最小值
    
    _instance: Optional['Config'] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定模式
                if cls._instance is None:
                    instance = super().__new__(cls)
                    cls._instance = instance
        return cls._instance
    
    @staticmethod
    def _validate_weight(weight: float, name: str) -> float:
        """
        验证单个权重值
        
        Args:
            weight: 权重值
            name: 权重名称(用于日志)
            
        Returns:
            验证后的权重值
        """
        try:
            weight = float(weight)
        except (ValueError, TypeError) as e:
            print(f"Warning: Invalid {name} weight type: {e}, using 0.0")
            return 0.0
        
        if not (Config.MIN_SINGLE_WEIGHT <= weight <= Config.MAX_SINGLE_WEIGHT):
            print(
                f"Warning: {name} weight {weight} out of range "
                f"[{Config.MIN_SINGLE_WEIGHT}, {Config.MAX_SINGLE_WEIGHT}], "
                f"clamping"
            )
            weight = max(Config.MIN_SINGLE_WEIGHT, min(Config.MAX_SINGLE_WEIGHT, weight))
        
        return weight
    
    @staticmethod
    def _normalize_weights(rf: float, gb: float, xgb: float) -> tuple:
        """
        归一化权重,确保总和为1
        
        Args:
            rf: RandomForest权重
            gb: GradientBoosting权重
            xgb: XGBoost权重
            
        Returns:
            (rf, gb, xgb) 归一化后的权重元组
        """
        total = rf + gb + xgb
        
        # 检查总和是否有效
        if total < Config.MIN_VALID_WEIGHT_SUM:
            print(
                f"Warning: Weight sum too small ({total:.6f}), using default weights"
            )
            return (0.4, 0.4, 0.2)
        
        # 归一化
        rf_norm = rf / total
        gb_norm = gb / total
        xgb_norm = xgb / total
        
        # 验证归一化结果
        final_sum = rf_norm + gb_norm + xgb_norm
        if abs(final_sum - 1.0) > Config.WEIGHT_TOLERANCE:
            print(
                f"Error: Normalization failed: sum={final_sum:.6f}, using defaults"
            )
            return (0.4, 0.4, 0.2)
        
        print(
            f"Info: Weights normalized: RF={rf_norm:.3f}, GB={gb_norm:.3f}, XGB={xgb_norm:.3f}"
        )
        return (rf_norm, gb_norm, xgb_norm)
    
    def __init__(self):
        # 线程安全的初始化检查
        with self._lock:
            if self._initialized:
                return
        
            # ==================== 路径配置 ====================
            self.PROJECT_ROOT = Path(__file__).parent
            self.DATA_DIR = Path(os.getenv('DATA_DIR', self.PROJECT_ROOT / 'game_data'))
            self.MODEL_DIR = Path(os.getenv('ML_MODEL_DIR', self.PROJECT_ROOT / 'ml_models'))
            
            # 确保目录存在（带异常处理）
            try:
                self.DATA_DIR.mkdir(exist_ok=True)
                self.MODEL_DIR.mkdir(exist_ok=True)
            except (OSError, PermissionError) as e:
                print(f"Warning: Failed to create directories: {e}")
                # 使用临时目录作为后备
                import tempfile
                temp_base = Path(tempfile.gettempdir()) / 'werewolf'
                self.DATA_DIR = temp_base / 'game_data'
                self.MODEL_DIR = temp_base / 'ml_models'
                self.DATA_DIR.mkdir(parents=True, exist_ok=True)
                self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
                print(f"Using temporary directories: DATA_DIR={self.DATA_DIR}, MODEL_DIR={self.MODEL_DIR}")
        
            
            # ==================== ML配置 ====================
            self.ML_ENABLED = os.getenv('ENABLE_ML', 'true').lower() == 'true'
            self.GOLDEN_PATH_ENABLED = os.getenv('ENABLE_GOLDEN_PATH', 'true').lower() == 'true'
            
            # 训练配置（带异常处理）
            try:
                self.MIN_SAMPLES = int(os.getenv('ML_MIN_SAMPLES', '1800'))
                if self.MIN_SAMPLES < 1:
                    raise ValueError("MIN_SAMPLES must be positive")
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid ML_MIN_SAMPLES, using default 1800: {e}")
                self.MIN_SAMPLES = 1800
            
            try:
                self.RETRAIN_INTERVAL = int(os.getenv('ML_TRAIN_INTERVAL', '30'))
                if self.RETRAIN_INTERVAL < 1:
                    raise ValueError("RETRAIN_INTERVAL must be positive")
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid ML_TRAIN_INTERVAL, using default 30: {e}")
                self.RETRAIN_INTERVAL = 30
            
            self.KEEP_TRAINING_DATA = os.getenv('ML_KEEP_DATA', 'true').lower() == 'true'
            
            # 模型配置（带异常处理和范围验证）
            try:
                self.CONTAMINATION = float(os.getenv('ML_CONTAMINATION', '0.33'))
                if not 0.0 < self.CONTAMINATION < 1.0:
                    raise ValueError("CONTAMINATION must be between 0 and 1")
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid ML_CONTAMINATION, using default 0.33: {e}")
                self.CONTAMINATION = 0.33
            
            try:
                # 1. 读取环境变量
                rf_weight = float(os.getenv('ML_RF_WEIGHT', '0.4'))
                gb_weight = float(os.getenv('ML_GB_WEIGHT', '0.4'))
                xgb_weight = float(os.getenv('ML_XGB_WEIGHT', '0.2'))
                
                print(f"Debug: Raw weights from env: RF={rf_weight}, GB={gb_weight}, XGB={xgb_weight}")
                
                # 2. 验证单个权重
                rf_weight = self._validate_weight(rf_weight, 'RF')
                gb_weight = self._validate_weight(gb_weight, 'GB')
                xgb_weight = self._validate_weight(xgb_weight, 'XGB')
                
                # 3. 检查是否需要归一化
                total_weight = rf_weight + gb_weight + xgb_weight
                
                if abs(total_weight - 1.0) > self.WEIGHT_TOLERANCE:
                    print(
                        f"Info: Weights sum to {total_weight:.3f}, normalizing..."
                    )
                    rf_weight, gb_weight, xgb_weight = self._normalize_weights(
                        rf_weight, gb_weight, xgb_weight
                    )
                else:
                    print(
                        f"Info: Weights already normalized: sum={total_weight:.3f}"
                    )
                
                # 4. 最终验证
                final_sum = rf_weight + gb_weight + xgb_weight
                if not (self.MIN_WEIGHT_SUM <= final_sum <= self.MAX_WEIGHT_SUM):
                    print(
                        f"Error: Final weight sum {final_sum:.3f} out of valid range "
                        f"[{self.MIN_WEIGHT_SUM}, {self.MAX_WEIGHT_SUM}], using defaults"
                    )
                    rf_weight, gb_weight, xgb_weight = 0.4, 0.4, 0.2
                
                # 5. 设置权重
                self.ENSEMBLE_WEIGHTS = {
                    'rf': rf_weight,
                    'gb': gb_weight,
                    'xgb': xgb_weight
                }
                
                print(f"Info: ✓ Ensemble weights configured: {self.ENSEMBLE_WEIGHTS}")
                
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid ensemble weights: {e}, using defaults")
                self.ENSEMBLE_WEIGHTS = {
                    'rf': 0.4,
                    'gb': 0.4,
                    'xgb': 0.2
                }
            except Exception as e:
                print(f"Error: Unexpected error in weight configuration: {e}")
                self.ENSEMBLE_WEIGHTS = {
                    'rf': 0.4,
                    'gb': 0.4,
                    'xgb': 0.2
                }
            
            # ==================== 数据收集配置 ====================
            self.COLLECT_GAME_DATA = os.getenv('COLLECT_DATA', 'true').lower() == 'true'
            self.AUTO_MERGE_DATA = os.getenv('AUTO_MERGE', 'true').lower() == 'true'
            
            # ==================== 训练数据生成配置 ====================
            try:
                self.SYNTHETIC_GOOD_SAMPLES = int(os.getenv('SYNTHETIC_GOOD', '150'))
                if self.SYNTHETIC_GOOD_SAMPLES < 0:
                    raise ValueError("SYNTHETIC_GOOD_SAMPLES must be non-negative")
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid SYNTHETIC_GOOD, using default 150: {e}")
                self.SYNTHETIC_GOOD_SAMPLES = 150
            
            try:
                self.SYNTHETIC_WOLF_SAMPLES = int(os.getenv('SYNTHETIC_WOLF', '75'))
                if self.SYNTHETIC_WOLF_SAMPLES < 0:
                    raise ValueError("SYNTHETIC_WOLF_SAMPLES must be non-negative")
            except (ValueError, TypeError) as e:
                print(f"Warning: Invalid SYNTHETIC_WOLF, using default 75: {e}")
                self.SYNTHETIC_WOLF_SAMPLES = 75
            
            # ==================== 日志配置 ====================
            log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
            valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
            
            if log_level_str not in valid_levels:
                print(f"Warning: Invalid LOG_LEVEL '{log_level_str}', using INFO")
                log_level_str = 'INFO'
            
            self.LOG_LEVEL = log_level_str
            self.LOG_FILE = os.getenv('LOG_FILE', '')
            
            self._initialized = True
    
    def get_model_path(self, model_name: str) -> Path:
        """获取模型文件路径"""
        return self.MODEL_DIR / model_name
    
    def get_data_path(self, data_name: str) -> Path:
        """获取数据文件路径"""
        return self.DATA_DIR / data_name
    
    def validate_ensemble_weights(self) -> bool:
        """
        验证ensemble权重配置
        
        Returns:
            bool: 权重是否有效
        """
        try:
            weights = self.ENSEMBLE_WEIGHTS
            
            # 检查是否包含所有必需的键
            required_keys = {'rf', 'gb', 'xgb'}
            if not required_keys.issubset(weights.keys()):
                print(f"Error: Missing weight keys: {required_keys - weights.keys()}")
                return False
            
            # 检查每个权重的范围
            for key, value in weights.items():
                if not isinstance(value, (int, float)):
                    print(f"Error: Weight {key} is not numeric: {type(value)}")
                    return False
                
                if not (self.MIN_SINGLE_WEIGHT <= value <= self.MAX_SINGLE_WEIGHT):
                    print(f"Error: Weight {key}={value} out of range")
                    return False
            
            # 检查总和
            total = sum(weights.values())
            if not (self.MIN_WEIGHT_SUM <= total <= self.MAX_WEIGHT_SUM):
                print(f"Error: Weight sum {total:.3f} out of valid range")
                return False
            
            print("Debug: ✓ Ensemble weights validation passed")
            return True
            
        except Exception as e:
            print(f"Error: Weight validation error: {e}")
            return False
    
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
