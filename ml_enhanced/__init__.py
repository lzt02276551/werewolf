"""
ML增强模块 - 提供高级机器学习能力

包含组件：
- ensemble_detector: 集成检测器（RandomForest + GradientBoosting + XGBoost）
- anomaly_detector: 异常检测器（IsolationForest）
- bayesian_inference: 增强贝叶斯推理
- feature_extractor: 特征提取器
"""

__version__ = "1.0.0"
__author__ = "Werewolf AI Team"

from .ensemble_detector import WolfDetectionEnsemble
from .anomaly_detector import BehaviorAnomalyDetector
from .bayesian_inference import BayesianAnalyzer
from .feature_extractor import StandardFeatureExtractor

__all__ = [
    'WolfDetectionEnsemble',
    'BehaviorAnomalyDetector',
    'BayesianAnalyzer',
    'StandardFeatureExtractor',
]
