"""
集成检测器 - 使用多个ML模型的集成学习

组合RandomForest、GradientBoosting和XGBoost三个模型
提供更准确的狼人检测能力
"""

import logging
import pickle
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# 尝试导入sklearn
try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available")

# 尝试导入xgboost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("xgboost not available, using sklearn only")


class WolfDetectionEnsemble:
    """
    狼人检测集成模型
    
    使用三个模型的加权投票：
    - RandomForest: 40%权重
    - GradientBoosting: 40%权重  
    - XGBoost: 20%权重（如果可用）
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化集成检测器
        
        Args:
            weights: 模型权重字典 {'rf': 0.4, 'gb': 0.4, 'xgb': 0.2}
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for WolfDetectionEnsemble")
        
        # 设置权重
        if weights is None:
            if XGBOOST_AVAILABLE:
                self.weights = {'rf': 0.4, 'gb': 0.4, 'xgb': 0.2}
            else:
                self.weights = {'rf': 0.5, 'gb': 0.5, 'xgb': 0.0}
        else:
            self.weights = weights
        
        # 初始化模型
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        
        if XGBOOST_AVAILABLE:
            self.xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1,
                eval_metric='logloss'
            )
        else:
            self.xgb_model = None
        
        # 特征缩放器
        self.scaler = StandardScaler()
        
        # 训练状态
        self.is_trained = False
        self.feature_names = None
        
        logger.info(f"✓ WolfDetectionEnsemble initialized (XGBoost: {XGBOOST_AVAILABLE})")
    
    def _extract_features(self, player_data: Dict) -> np.ndarray:
        """
        从玩家数据中提取特征向量
        
        Args:
            player_data: 玩家数据字典
            
        Returns:
            特征向量
        """
        features = []
        
        # 1. 信任分数 (归一化到0-1)
        trust_score = player_data.get('trust_score', 50) / 100.0
        features.append(trust_score)
        
        # 2. 投票准确度
        vote_accuracy = player_data.get('vote_accuracy', 0.5)
        features.append(vote_accuracy)
        
        # 3. 矛盾次数 (归一化)
        contradiction_count = min(player_data.get('contradiction_count', 0) / 5.0, 1.0)
        features.append(contradiction_count)
        
        # 4. 注入攻击次数 (归一化)
        injection_attempts = min(player_data.get('injection_attempts', 0) / 3.0, 1.0)
        features.append(injection_attempts)
        
        # 5. 虚假引用次数 (归一化)
        false_quotation_count = min(player_data.get('false_quotation_count', 0) / 3.0, 1.0)
        features.append(false_quotation_count)
        
        # 6. 平均发言长度 (归一化)
        speech_lengths = player_data.get('speech_lengths', [100])
        avg_speech_length = sum(speech_lengths) / len(speech_lengths) if speech_lengths else 100
        features.append(min(avg_speech_length / 200.0, 1.0))
        
        # 7. 发言长度方差 (归一化)
        if len(speech_lengths) > 1:
            variance = np.var(speech_lengths)
            features.append(min(variance / 10000.0, 1.0))
        else:
            features.append(0.0)
        
        # 8. 提及他人次数 (归一化)
        mentions_others = min(player_data.get('mentions_others_count', 0) / 20.0, 1.0)
        features.append(mentions_others)
        
        # 9. 被提及次数 (归一化)
        mentioned_by_others = min(player_data.get('mentioned_by_others_count', 0) / 20.0, 1.0)
        features.append(mentioned_by_others)
        
        # 10. 攻击性分数
        aggressive_score = player_data.get('aggressive_score', 0.5)
        features.append(aggressive_score)
        
        # 11. 防御性分数
        defensive_score = player_data.get('defensive_score', 0.5)
        features.append(defensive_score)
        
        # 12. 情感关键词数量 (归一化)
        emotion_keywords = min(player_data.get('emotion_keyword_count', 0) / 15.0, 1.0)
        features.append(emotion_keywords)
        
        # 13. 逻辑关键词数量 (归一化)
        logic_keywords = min(player_data.get('logic_keyword_count', 0) / 15.0, 1.0)
        features.append(logic_keywords)
        
        # 14. 夜间存活率
        night_survival_rate = player_data.get('night_survival_rate', 0.5)
        features.append(night_survival_rate)
        
        # 15. 联盟强度
        alliance_strength = player_data.get('alliance_strength', 0.5)
        features.append(alliance_strength)
        
        # 16. 孤立分数
        isolation_score = player_data.get('isolation_score', 0.5)
        features.append(isolation_score)
        
        # 17. 发言一致性分数
        speech_consistency = player_data.get('speech_consistency_score', 0.5)
        features.append(speech_consistency)
        
        # 18. 平均响应时间 (归一化)
        avg_response_time = min(player_data.get('avg_response_time', 5.0) / 10.0, 1.0)
        features.append(avg_response_time)
        
        return np.array(features).reshape(1, -1)
    
    def train(
        self, 
        player_data_list: List[Dict], 
        labels: List[int],
        sample_weights: Optional[List[float]] = None
    ):
        """
        训练集成模型
        
        Args:
            player_data_list: 玩家数据列表
            labels: 标签列表 (0=好人, 1=狼人)
            sample_weights: 样本权重（可选）
        """
        if len(player_data_list) < 10:
            logger.warning(f"Training data too small: {len(player_data_list)} samples")
            return
        
        # 提取特征
        X = np.vstack([self._extract_features(data) for data in player_data_list])
        y = np.array(labels)
        
        # 特征缩放
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练RandomForest
        logger.info("Training RandomForest...")
        if sample_weights:
            self.rf_model.fit(X_scaled, y, sample_weight=sample_weights)
        else:
            self.rf_model.fit(X_scaled, y)
        
        # 训练GradientBoosting
        logger.info("Training GradientBoosting...")
        if sample_weights:
            self.gb_model.fit(X_scaled, y, sample_weight=sample_weights)
        else:
            self.gb_model.fit(X_scaled, y)
        
        # 训练XGBoost（如果可用）
        if self.xgb_model is not None:
            logger.info("Training XGBoost...")
            if sample_weights:
                self.xgb_model.fit(X_scaled, y, sample_weight=sample_weights)
            else:
                self.xgb_model.fit(X_scaled, y)
        
        self.is_trained = True
        logger.info(f"✓ Ensemble trained with {len(player_data_list)} samples")
    
    def predict_wolf_probability(self, player_data: Dict) -> float:
        """
        预测狼人概率
        
        Args:
            player_data: 玩家数据
            
        Returns:
            狼人概率 (0-1)
        """
        if not self.is_trained:
            logger.warning("Model not trained, returning default 0.5")
            return 0.5
        
        # 提取特征
        X = self._extract_features(player_data)
        X_scaled = self.scaler.transform(X)
        
        # 获取各模型预测
        rf_prob = self.rf_model.predict_proba(X_scaled)[0][1]
        gb_prob = self.gb_model.predict_proba(X_scaled)[0][1]
        
        if self.xgb_model is not None:
            xgb_prob = self.xgb_model.predict_proba(X_scaled)[0][1]
        else:
            xgb_prob = 0.0
        
        # 加权平均
        total_weight = self.weights['rf'] + self.weights['gb'] + self.weights['xgb']
        wolf_prob = (
            rf_prob * self.weights['rf'] +
            gb_prob * self.weights['gb'] +
            xgb_prob * self.weights['xgb']
        ) / total_weight
        
        return float(wolf_prob)
    
    def save_models(self, filepath: str):
        """保存模型"""
        if not self.is_trained:
            logger.warning("Model not trained, nothing to save")
            return
        
        models = {
            'rf': self.rf_model,
            'gb': self.gb_model,
            'xgb': self.xgb_model,
            'scaler': self.scaler,
            'weights': self.weights,
            'is_trained': self.is_trained
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(models, f)
        
        logger.info(f"✓ Models saved to {filepath}")
    
    def load_models(self, filepath: str) -> bool:
        """
        加载模型
        
        Returns:
            是否成功加载
        """
        try:
            with open(filepath, 'rb') as f:
                models = pickle.load(f)
            
            self.rf_model = models['rf']
            self.gb_model = models['gb']
            self.xgb_model = models.get('xgb')
            self.scaler = models['scaler']
            self.weights = models['weights']
            self.is_trained = models['is_trained']
            
            logger.info(f"✓ Models loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to load models: {e}")
            return False
