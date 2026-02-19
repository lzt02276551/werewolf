"""
Anomaly Detection for Behavior Analysis
异常检测：识别狼人的异常行为模式
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope
import logging

logger = logging.getLogger(__name__)


class BehaviorAnomalyDetector:
    """行为异常检测器 - 集成多种异常检测算法"""
    
    def __init__(self, contamination=0.33, ensemble_weights=None):
        """
        Args:
            contamination: 异常比例（狼人比例，默认33%）
            ensemble_weights: 各模型权重 {'iso': 0.4, 'svm': 0.3, 'elliptic': 0.3}
        """
        # Isolation Forest - 基于树的异常检测
        self.iso_forest = IsolationForest(
            contamination=contamination,
            n_estimators=200,
            max_samples='auto',
            random_state=42,
            n_jobs=-1
        )
        
        # One-Class SVM - 基于支持向量的异常检测
        self.ocsvm = OneClassSVM(
            nu=contamination,  # nu ≈ contamination
            kernel='rbf',
            gamma='auto'
        )
        
        # Elliptic Envelope - 基于协方差的异常检测（假设高斯分布）
        self.elliptic = EllipticEnvelope(
            contamination=contamination,
            random_state=42
        )
        
        # 模型权重
        if ensemble_weights is None:
            self.weights = {'iso': 0.4, 'svm': 0.3, 'elliptic': 0.3}
        else:
            self.weights = ensemble_weights
        
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        logger.info(f"BehaviorAnomalyDetector initialized - Contamination: {contamination}")
    
    def extract_behavior_features(self, player_data):
        """
        提取行为特征 - 优化版本，使用向量化操作和缓存
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            numpy array of behavior features (shape: 1x18)
        
        Raises:
            ValueError: 如果数据格式不正确
        """
        # 验证输入
        if not isinstance(player_data, dict):
            raise ValueError(f"player_data must be dict, got {type(player_data)}")
        
        if not player_data:
            raise ValueError("player_data is empty")
        
        # 发言特征 - 向量化计算（优化：直接使用numpy函数）
        speech_lengths = player_data.get('speech_lengths', [100])
        if not speech_lengths or len(speech_lengths) == 0:
            speech_lengths = [100]
        speech_arr = np.array(speech_lengths, dtype=np.float32)
        
        # 投票特征 - 向量化计算
        voting_speeds = player_data.get('voting_speeds', [5.0])
        if not voting_speeds or len(voting_speeds) == 0:
            voting_speeds = [5.0]
        voting_arr = np.array(voting_speeds, dtype=np.float32)
        
        # 投票目标多样性（优化：使用集合操作）
        vote_targets = player_data.get('vote_targets', [])
        vote_diversity = len(set(vote_targets)) if vote_targets else 0
        
        # 直接构建numpy数组（避免列表append）
        features = np.array([
            speech_arr.mean(),
            speech_arr.std() if len(speech_lengths) > 1 else 0,
            speech_arr.max(),
            speech_arr.min(),
            voting_arr.mean(),
            voting_arr.std() if len(voting_speeds) > 1 else 0,
            vote_diversity,
            player_data.get('contradiction_count', 0),
            player_data.get('speech_consistency_score', 0.5),
            player_data.get('mentions_others_count', 0),
            player_data.get('mentioned_by_others_count', 0),
            player_data.get('aggressive_score', 0),
            player_data.get('defensive_score', 0),
            player_data.get('avg_response_time', 5.0),
            player_data.get('logic_keyword_count', 0),
            player_data.get('emotion_keyword_count', 0),
            player_data.get('alliance_strength', 0),
            player_data.get('isolation_score', 0)
        ], dtype=np.float32)
        
        # 验证特征向量
        if features.shape[0] != 18:
            raise ValueError(f"Expected 18 features, got {features.shape[0]}")
        
        # 检查是否有NaN或Inf
        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
            logger.warning(f"Features contain NaN or Inf, replacing with defaults")
            features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=0.0)
        
        return features.reshape(1, -1)
    
    def fit(self, normal_player_behaviors):
        """
        训练异常检测器（使用好人行为数据）
        
        Args:
            normal_player_behaviors: List of player_data dicts (good players only)
        """
        if len(normal_player_behaviors) < 10:
            logger.warning(f"Not enough samples for anomaly detection ({len(normal_player_behaviors)} < 10), skipping")
            return
        
        logger.info(f"Training anomaly detectors with {len(normal_player_behaviors)} samples")
        
        # 提取特征
        try:
            X = np.vstack([self.extract_behavior_features(data) 
                          for data in normal_player_behaviors])
        except ValueError as e:
            logger.error(f"Failed to extract features: {e}")
            return
        
        if X.shape[0] == 0:
            logger.error("No valid features extracted")
            return
        
        # 标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练各个模型
        logger.info("Training Isolation Forest...")
        self.iso_forest.fit(X_scaled)
        
        logger.info("Training One-Class SVM...")
        self.ocsvm.fit(X_scaled)
        
        logger.info("Training Elliptic Envelope...")
        try:
            self.elliptic.fit(X_scaled)
        except Exception as e:
            logger.warning(f"Elliptic Envelope training failed: {e}, using default")
        
        self.is_fitted = True
        logger.info("Anomaly detector training completed")
    
    def detect_anomaly(self, player_data):
        """
        检测异常行为
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            float: 异常分数（越低越异常，范围约-1到1）
        """
        if not self.is_fitted:
            logger.warning("Detector not fitted, returning neutral score")
            return 0.0
        
        try:
            # 提取并标准化特征
            features = self.extract_behavior_features(player_data)
            features_scaled = self.scaler.transform(features)
            
            # 各模型评分
            iso_score = self.iso_forest.score_samples(features_scaled)[0]
            svm_score = self.ocsvm.score_samples(features_scaled)[0]
            
            try:
                elliptic_score = self.elliptic.score_samples(features_scaled)[0]
            except Exception as e:
                logger.debug(f"Elliptic envelope scoring failed: {e}")
                elliptic_score = 0.0
            
            # 加权平均
            ensemble_score = (
                self.weights['iso'] * iso_score +
                self.weights['svm'] * svm_score +
                self.weights['elliptic'] * elliptic_score
            )
            
            logger.debug(f"Anomaly scores - ISO: {iso_score:.3f}, SVM: {svm_score:.3f}, "
                        f"Elliptic: {elliptic_score:.3f}, Ensemble: {ensemble_score:.3f}")
            
            return ensemble_score
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}, returning neutral score")
            return 0.0
    
    def predict_is_wolf(self, player_data):
        """
        预测是否为狼人
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            bool: True if wolf, False if good
        """
        anomaly_score = self.detect_anomaly(player_data)
        return anomaly_score < 0  # 负分表示异常
    
    def get_wolf_probability(self, player_data):
        """
        将异常分数转换为狼人概率
        
        Args:
            player_data: 玩家数据字典
        
        Returns:
            float: 狼人概率 (0-1)
        """
        anomaly_score = self.detect_anomaly(player_data)
        
        # 使用sigmoid函数将分数映射到[0, 1]
        # 分数越低（越异常），概率越高
        wolf_prob = 1 / (1 + np.exp(anomaly_score * 2))
        
        return wolf_prob
    
    def batch_detect(self, player_data_list):
        """批量检测 - 优化版本"""
        if not self.is_fitted:
            logger.warning("Detector not fitted, returning neutral scores")
            return [0.0] * len(player_data_list)
        
        if not player_data_list:
            return []
        
        try:
            # 批量提取特征
            features_list = [self.extract_behavior_features(data) for data in player_data_list]
            X = np.vstack(features_list)
            X_scaled = self.scaler.transform(X)
            
            # 批量评分
            iso_scores = self.iso_forest.score_samples(X_scaled)
            svm_scores = self.ocsvm.score_samples(X_scaled)
            
            try:
                elliptic_scores = self.elliptic.score_samples(X_scaled)
            except Exception as e:
                logger.debug(f"Elliptic envelope batch scoring failed: {e}")
                elliptic_scores = np.zeros(len(player_data_list))
            
            # 加权平均
            ensemble_scores = (
                self.weights['iso'] * iso_scores +
                self.weights['svm'] * svm_scores +
                self.weights['elliptic'] * elliptic_scores
            )
            
            return ensemble_scores.tolist()
        except Exception as e:
            logger.error(f"Batch anomaly detection failed: {e}, returning neutral scores")
            return [0.0] * len(player_data_list)
    
    def get_feature_importance(self):
        """获取特征重要性（仅Isolation Forest支持）"""
        if not self.is_fitted:
            return None
        
        # Isolation Forest没有直接的feature_importances_
        # 但可以通过扰动特征来估计重要性
        logger.info("Feature importance estimation not implemented for ensemble")
        return None


class SequentialAnomalyDetector:
    """序列异常检测器 - 检测行为模式的时序异常"""
    
    def __init__(self, window_size=5):
        """
        Args:
            window_size: 滑动窗口大小
        """
        self.window_size = window_size
        self.behavior_history = {}  # {player: [behavior_vectors]}
        
        logger.info(f"SequentialAnomalyDetector initialized - Window size: {window_size}")
    
    def update_history(self, player, behavior_vector):
        """更新玩家行为历史"""
        if player not in self.behavior_history:
            self.behavior_history[player] = []
        
        self.behavior_history[player].append(behavior_vector)
        
        # 保持窗口大小
        if len(self.behavior_history[player]) > self.window_size:
            self.behavior_history[player].pop(0)
    
    def detect_behavior_shift(self, player):
        """
        检测行为突变（优化：使用numpy向量化操作）
        
        Returns:
            float: 突变分数（0-1，越高越可疑）
        """
        if player not in self.behavior_history:
            return 0.0
        
        history = self.behavior_history[player]
        
        if len(history) < 2:
            return 0.0
        
        try:
            # 转换为numpy数组（一次性操作）
            history_array = np.array(history, dtype=np.float32)
            recent_behavior = history_array[-1]
            
            if len(history) == 2:
                historical_avg = history_array[0]
            else:
                historical_avg = history_array[:-1].mean(axis=0)
            
            # 欧氏距离（向量化计算）
            distance = np.linalg.norm(recent_behavior - historical_avg)
            
            # 归一化到[0, 1]
            shift_score = min(1.0, distance / 10.0)
            
            return shift_score
        except Exception as e:
            logger.warning(f"Failed to calculate behavior shift: {e}")
            return 0.0
    
    def detect_pattern_anomaly(self, player):
        """
        检测模式异常（优化：减少重复计算）
        
        Returns:
            float: 异常分数（0-1）
        """
        if player not in self.behavior_history:
            return 0.0
        
        history = self.behavior_history[player]
        
        if len(history) < self.window_size:
            return 0.0
        
        try:
            # 转换为numpy数组并计算方差（一次性操作）
            history_array = np.array(history, dtype=np.float32)
            variance = history_array.var(axis=0).mean()
            
            # 归一化
            anomaly_score = min(1.0, variance / 5.0)
            return anomaly_score
        except Exception as e:
            logger.warning(f"Failed to calculate variance: {e}")
            return 0.0


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 模拟好人行为数据
    good_behaviors = []
    for _ in range(100):
        good_behaviors.append({
            'speech_lengths': [np.random.randint(80, 150) for _ in range(5)],
            'voting_speeds': [np.random.uniform(3, 8) for _ in range(3)],
            'vote_targets': [f'No.{np.random.randint(1, 13)}' for _ in range(3)],
            'contradiction_count': np.random.randint(0, 2),
            'speech_consistency_score': np.random.uniform(0.6, 0.9),
            'mentions_others_count': np.random.randint(3, 10),
            'mentioned_by_others_count': np.random.randint(2, 8),
            'aggressive_score': np.random.uniform(0, 0.3),
            'defensive_score': np.random.uniform(0.3, 0.6),
            'avg_response_time': np.random.uniform(4, 7),
            'speech_time_variance': np.random.uniform(0.5, 2.0),
            'wolf_keyword_count': np.random.randint(5, 15),
            'logic_keyword_count': np.random.randint(8, 20),
            'emotion_keyword_count': np.random.randint(0, 5),
            'alliance_strength': np.random.uniform(0.3, 0.7),
            'isolation_score': np.random.uniform(0, 0.3)
        })
    
    # 训练检测器
    detector = BehaviorAnomalyDetector(contamination=0.33)
    detector.fit(good_behaviors)
    
    # 测试：好人行为
    good_test = good_behaviors[0]
    good_score = detector.detect_anomaly(good_test)
    good_prob = detector.get_wolf_probability(good_test)
    print(f"\nGood player - Anomaly score: {good_score:.3f}, Wolf prob: {good_prob:.3f}")
    
    # 测试：狼人行为（模拟异常）
    wolf_test = {
        'speech_lengths': [50, 60, 55, 58, 52],  # 更短
        'voting_speeds': [1.5, 2.0, 1.8, 2.2, 1.9],  # 更快
        'vote_targets': ['No.3', 'No.3', 'No.3'],  # 重复目标
        'contradiction_count': 5,  # 更多矛盾
        'speech_consistency_score': 0.3,  # 更低一致性
        'mentions_others_count': 15,  # 更多提及
        'mentioned_by_others_count': 2,  # 更少被提及
        'aggressive_score': 0.8,  # 更激进
        'defensive_score': 0.9,  # 更防御
        'avg_response_time': 2.0,  # 更快响应
        'speech_time_variance': 3.5,  # 更大方差
        'wolf_keyword_count': 25,  # 更多狼人关键词
        'logic_keyword_count': 3,  # 更少逻辑关键词
        'emotion_keyword_count': 12,  # 更多情绪关键词
        'alliance_strength': 0.9,  # 更强联盟
        'isolation_score': 0.7  # 更孤立
    }
    
    wolf_score = detector.detect_anomaly(wolf_test)
    wolf_prob = detector.get_wolf_probability(wolf_test)
    print(f"Wolf player - Anomaly score: {wolf_score:.3f}, Wolf prob: {wolf_prob:.3f}")
