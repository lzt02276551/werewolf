"""
ML Enhanced Werewolf AI System
轻量级机器学习增强系统 - 仅使用sklearn
"""

from .ensemble_detector import WolfDetectionEnsemble
from .anomaly_detector import BehaviorAnomalyDetector
from .bayesian_inference import BayesianAnalyzer

__all__ = [
    'WolfDetectionEnsemble',
    'BehaviorAnomalyDetector',
    'BayesianAnalyzer'
]

__version__ = '1.0.0'
