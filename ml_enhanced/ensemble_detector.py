"""
Ensemble Learning for Wolf Detection
集成学习：Random Forest + Gradient Boosting + XGBoost
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


class WolfDetectionEnsemble:
    """集成多个模型预测狼人概率"""
    
    def __init__(self, model_weights=None):
        """
        Args:
            model_weights: 模型权重字典 {'rf': 0.4, 'gb': 0.4, 'xgb': 0.2}
        """
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.gb_model = GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        # XGBoost (optional, fallback to GB if not available)
        try:
            from xgboost import XGBClassifier
            self.xgb_model = XGBClassifier(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
            self.use_xgb = True
        except ImportError:
            logger.warning("XGBoost not available, using only RF and GB")
            self.xgb_model = None
            self.use_xgb = False
        
        # 模型权重
        if model_weights is None:
            if self.use_xgb:
                self.weights = {'rf': 0.4, 'gb': 0.4, 'xgb': 0.2}
            else:
                self.weights = {'rf': 0.5, 'gb': 0.5}
        else:
            self.weights = model_weights
        
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = [
            'trust_score',
            'speech_length_avg',
            'speech_length_std',
            'vote_accuracy',
            'contradiction_count',
            'injection_attempts',
            'false_quotation_count',
            'voting_speed_avg',
            'speech_similarity_avg',
            'night_survival_rate',
            'sheriff_votes_received',
            'aggressive_score',
            'defensive_score',
            'logic_keyword_count',
            'emotion_keyword_count'
        ]
    
    def extract_features(self, player_data):
        """
        提取玩家特征向量 - 优化版本，减少中间变量
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            numpy array of features (shape: 1x15)
        
        Raises:
            ValueError: 如果数据格式不正确
        """
        # 验证输入
        if not isinstance(player_data, dict):
            raise ValueError(f"player_data must be dict, got {type(player_data)}")
        
        if not player_data:
            raise ValueError("player_data is empty")
        
        # 发言特征 - 向量化计算
        speech_lengths = player_data.get('speech_lengths', [100])
        if not speech_lengths or len(speech_lengths) == 0:
            speech_lengths = [100]
        speech_arr = np.array(speech_lengths, dtype=np.float32)
        
        # 投票速度 - 向量化计算
        voting_speeds = player_data.get('voting_speeds', [5.0])
        if not voting_speeds or len(voting_speeds) == 0:
            voting_speeds = [5.0]
        
        # 直接构建numpy数组（避免中间变量）
        features = np.array([
            player_data.get('trust_score', 50),
            speech_arr.mean(),
            speech_arr.std() if len(speech_lengths) > 1 else 0,
            player_data.get('vote_accuracy', 0.5),
            player_data.get('contradiction_count', 0),
            player_data.get('injection_attempts', 0),
            player_data.get('false_quotation_count', 0),
            np.mean(voting_speeds),
            player_data.get('speech_similarity_avg', 0.5),
            player_data.get('night_survival_rate', 0.5),
            player_data.get('sheriff_votes_received', 0),
            player_data.get('aggressive_score', 0),
            player_data.get('defensive_score', 0),
            player_data.get('logic_keyword_count', 0),
            player_data.get('emotion_keyword_count', 0)
        ], dtype=np.float32)
        
        # 验证特征向量
        if features.shape[0] != 15:
            raise ValueError(f"Expected 15 features, got {features.shape[0]}")
        
        # 检查是否有NaN或Inf
        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
            logger.warning(f"Features contain NaN or Inf, replacing with defaults")
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=0.0)
        
        return features.reshape(1, -1)
    
    def train(self, training_data, labels, sample_weights=None):
        """
        训练集成模型
        
        Args:
            training_data: List of player_data dicts
            labels: List of labels (0=good, 1=wolf)
            sample_weights: Optional sample weights for training
        """
        logger.info(f"Training ensemble models with {len(training_data)} samples")
        
        if len(training_data) == 0:
            logger.error("No training data provided")
            return
        
        # 提取特征
        X = np.vstack([self.extract_features(data) for data in training_data])
        y = np.array(labels)
        
        if X.shape[0] == 0:
            logger.error("Failed to extract features from training data")
            return
        
        # 验证特征维度
        expected_features = 15
        if X.shape[1] != expected_features:
            logger.error(f"Feature dimension mismatch: expected {expected_features}, got {X.shape[1]}")
            return
        
        # 检查特征中是否有异常值
        if np.any(np.isnan(X)) or np.any(np.isinf(X)):
            logger.warning("Training data contains NaN or Inf, cleaning...")
            X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=0.0)
        
        # CRITICAL: 检查类别数量
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            logger.error(f"Training data only has {len(unique_classes)} class(es): {unique_classes}. Need at least 2 classes (good and wolf).")
            logger.error("Skipping training - insufficient class diversity")
            return
        
        # 如果有样本权重，检查是否会导致某个类别权重为0
        if sample_weights is not None:
            sample_weights = np.array(sample_weights)
            for cls in unique_classes:
                cls_weight = np.sum(sample_weights[y == cls])
                if cls_weight == 0:
                    logger.warning(f"Class {cls} has zero total weight, adjusting weights")
                    # 给该类别的样本添加最小权重
                    sample_weights[y == cls] = 0.1
        
        # 标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练各个模型
        logger.info("Training Random Forest...")
        self.rf_model.fit(X_scaled, y, sample_weight=sample_weights)
        
        logger.info("Training Gradient Boosting...")
        self.gb_model.fit(X_scaled, y, sample_weight=sample_weights)
        
        if self.use_xgb:
            logger.info("Training XGBoost...")
            self.xgb_model.fit(X_scaled, y, sample_weight=sample_weights)
        
        self.is_trained = True
        logger.info("Ensemble training completed")
        
        # 输出特征重要性
        self._log_feature_importance()
    
    def _log_feature_importance(self):
        """记录特征重要性"""
        rf_importance = self.rf_model.feature_importances_
        gb_importance = self.gb_model.feature_importances_
        
        logger.info("\n=== Feature Importance (Random Forest) ===")
        for name, importance in sorted(
            zip(self.feature_names, rf_importance),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            logger.info(f"{name}: {importance:.4f}")
        
        logger.info("\n=== Feature Importance (Gradient Boosting) ===")
        for name, importance in sorted(
            zip(self.feature_names, gb_importance),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            logger.info(f"{name}: {importance:.4f}")
    
    def predict_wolf_probability(self, player_data):
        """
        预测狼人概率（集成）
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            float: 狼人概率 (0-1)
        """
        if not self.is_trained:
            logger.warning("Models not trained, returning default probability")
            return 0.5
        
        try:
            # 提取并标准化特征
            features = self.extract_features(player_data)
            features_scaled = self.scaler.transform(features)
            
            # 各模型预测 - 添加类别检查
            rf_proba = self.rf_model.predict_proba(features_scaled)[0]
            # 检查是否只有一个类别
            if len(rf_proba) == 1:
                logger.warning("RF model only has 1 class, returning default probability")
                rf_prob = 0.5
            else:
                rf_prob = rf_proba[1]
            
            gb_proba = self.gb_model.predict_proba(features_scaled)[0]
            if len(gb_proba) == 1:
                logger.warning("GB model only has 1 class, returning default probability")
                gb_prob = 0.5
            else:
                gb_prob = gb_proba[1]
            
            # 加权平均
            if self.use_xgb and self.xgb_model is not None:
                xgb_proba = self.xgb_model.predict_proba(features_scaled)[0]
                if len(xgb_proba) == 1:
                    logger.warning("XGB model only has 1 class, returning default probability")
                    xgb_prob = 0.5
                else:
                    xgb_prob = xgb_proba[1]
                
                ensemble_prob = (
                    self.weights['rf'] * rf_prob +
                    self.weights['gb'] * gb_prob +
                    self.weights['xgb'] * xgb_prob
                )
                logger.debug(f"Wolf probability - RF: {rf_prob:.3f}, GB: {gb_prob:.3f}, "
                            f"XGB: {xgb_prob:.3f}, Ensemble: {ensemble_prob:.3f}")
            else:
                ensemble_prob = (
                    self.weights['rf'] * rf_prob +
                    self.weights['gb'] * gb_prob
                )
                logger.debug(f"Wolf probability - RF: {rf_prob:.3f}, GB: {gb_prob:.3f}, "
                            f"Ensemble: {ensemble_prob:.3f}")
            
            return ensemble_prob
        except Exception as e:
            logger.error(f"Prediction failed: {e}, returning default probability")
            return 0.5
    
    def predict_batch(self, player_data_list):
        """批量预测 - 优化版本，避免重复特征提取和标准化"""
        if not self.is_trained:
            logger.warning("Models not trained, returning default probabilities")
            return [0.5] * len(player_data_list)
        
        if not player_data_list:
            return []
        
        try:
            # 批量提取特征
            features_list = [self.extract_features(data) for data in player_data_list]
            X = np.vstack(features_list)
            X_scaled = self.scaler.transform(X)
            
            # 批量预测
            rf_probs = self.rf_model.predict_proba(X_scaled)[:, 1]
            gb_probs = self.gb_model.predict_proba(X_scaled)[:, 1]
            
            if self.use_xgb and self.xgb_model is not None:
                xgb_probs = self.xgb_model.predict_proba(X_scaled)[:, 1]
                ensemble_probs = (
                    self.weights['rf'] * rf_probs +
                    self.weights['gb'] * gb_probs +
                    self.weights['xgb'] * xgb_probs
                )
            else:
                ensemble_probs = (
                    self.weights['rf'] * rf_probs +
                    self.weights['gb'] * gb_probs
                )
            
            return ensemble_probs.tolist()
        except Exception as e:
            logger.error(f"Batch prediction failed: {e}, returning default probabilities")
            return [0.5] * len(player_data_list)
    
    def save_models(self, filepath):
        """保存模型"""
        model_data = {
            'rf_model': self.rf_model,
            'gb_model': self.gb_model,
            'xgb_model': self.xgb_model if self.use_xgb else None,
            'scaler': self.scaler,
            'weights': self.weights,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained
        }
        joblib.dump(model_data, filepath)
        logger.info(f"Models saved to {filepath}")
    
    def load_models(self, filepath):
        """加载模型 - 增强错误处理,兼容版本不匹配"""
        try:
            model_data = joblib.load(filepath)
            self.rf_model = model_data['rf_model']
            self.gb_model = model_data['gb_model']
            self.xgb_model = model_data.get('xgb_model')
            self.scaler = model_data['scaler']
            self.weights = model_data['weights']
            self.feature_names = model_data['feature_names']
            self.is_trained = model_data['is_trained']
            self.use_xgb = self.xgb_model is not None
            logger.info(f"✓ Models loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to load models from {filepath}: {e}")
            logger.warning("⚠ Models remain uninitialized, will train from scratch")
            
            # 尝试清理不兼容的模型文件
            self._cleanup_incompatible_model(filepath)
            return False
    
    def _cleanup_incompatible_model(self, filepath):
        """清理不兼容的模型文件（独立方法，提高可维护性）"""
        import os
        import time
        
        if not os.path.exists(filepath):
            return
        
        try:
            # 生成带时间戳的备份文件名
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            backup_path = f"{filepath}.incompatible_{timestamp}"
            
            # 尝试重命名（备份）
            try:
                os.rename(filepath, backup_path)
                logger.info(f"  Moved incompatible model to: {backup_path}")
                return
            except (OSError, PermissionError) as e:
                logger.debug(f"  Rename failed: {e}, trying deletion")
            
            # 如果重命名失败，尝试删除
            try:
                os.remove(filepath)
                logger.info(f"  Removed incompatible model file: {filepath}")
                return
            except (OSError, PermissionError) as e:
                logger.debug(f"  Deletion failed: {e}")
            
            # 如果都失败，记录警告
            logger.warning(f"  Could not clean up file: {filepath}")
            logger.warning(f"  File may be locked. Please manually delete or rename it.")
            
        except Exception as e:
            logger.debug(f"  Cleanup error: {type(e).__name__}: {e}")
            logger.debug(f"  Continuing without cleanup - model will be retrained")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 模拟训练数据
    training_data = []
    labels = []
    
    # 生成模拟好人数据
    for _ in range(100):
        training_data.append({
            'trust_score': np.random.normal(65, 10),
            'speech_lengths': [np.random.randint(80, 150) for _ in range(5)],
            'vote_accuracy': np.random.uniform(0.6, 0.9),
            'contradiction_count': np.random.randint(0, 2),
            'injection_attempts': 0,
            'false_quotation_count': 0,
            'voting_speeds': [np.random.uniform(3, 8) for _ in range(3)],
            'speech_similarity_avg': np.random.uniform(0.4, 0.6),
            'night_survival_rate': np.random.uniform(0.3, 0.6),
            'sheriff_votes_received': np.random.randint(0, 3),
            'aggressive_score': np.random.uniform(0, 0.3),
            'defensive_score': np.random.uniform(0.3, 0.6),
            'logic_keyword_count': np.random.randint(5, 15),
            'emotion_keyword_count': np.random.randint(0, 5)
        })
        labels.append(0)
    
    # 生成模拟狼人数据
    for _ in range(50):
        training_data.append({
            'trust_score': np.random.normal(35, 10),
            'speech_lengths': [np.random.randint(60, 120) for _ in range(5)],
            'vote_accuracy': np.random.uniform(0.2, 0.5),
            'contradiction_count': np.random.randint(2, 5),
            'injection_attempts': np.random.randint(0, 3),
            'false_quotation_count': np.random.randint(0, 2),
            'voting_speeds': [np.random.uniform(1, 4) for _ in range(3)],
            'speech_similarity_avg': np.random.uniform(0.6, 0.8),
            'night_survival_rate': np.random.uniform(0.6, 0.9),
            'sheriff_votes_received': np.random.randint(0, 2),
            'aggressive_score': np.random.uniform(0.4, 0.8),
            'defensive_score': np.random.uniform(0.5, 0.8),
            'logic_keyword_count': np.random.randint(2, 8),
            'emotion_keyword_count': np.random.randint(3, 10)
        })
        labels.append(1)
    
    # 训练模型
    ensemble = WolfDetectionEnsemble()
    ensemble.train(training_data, labels)
    
    # 测试预测
    test_player = training_data[0]
    wolf_prob = ensemble.predict_wolf_probability(test_player)
    print(f"\nTest prediction - Wolf probability: {wolf_prob:.3f}")
