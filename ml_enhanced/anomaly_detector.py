"""
异常检测器 - 使用IsolationForest检测异常行为

通过学习好人的正常行为模式，识别偏离正常的狼人行为
"""

import logging
import pickle
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available")


class BehaviorAnomalyDetector:
    """
    行为异常检测器
    
    使用IsolationForest学习好人的正常行为模式
    将狼人识别为异常点
    """
    
    def __init__(self, contamination: float = 0.33):
        """
        初始化异常检测器
        
        Args:
            contamination: 异常比例（狼人占比，默认33%）
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for BehaviorAnomalyDetector")
        
        self.contamination = contamination
        
        # 初始化模型
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=100,
            max_samples='auto',
            random_state=42,
            n_jobs=-1
        )
        
        # 特征缩放器
        self.scaler = StandardScaler()
        
        # 训练状态
        self.is_fitted = False
        
        logger.info(f"✓ BehaviorAnomalyDetector initialized (contamination={contamination})")
    
    def _extract_features(self, player_data: Dict) -> np.ndarray:
        """
        从玩家数据中提取特征向量
        
        Args:
            player_data: 玩家数据字典
            
        Returns:
            特征向量
        """
        features = []
        
        # 1. 信任分数
        trust_score = player_data.get('trust_score', 50) / 100.0
        features.append(trust_score)
        
        # 2. 投票准确度
        vote_accuracy = player_data.get('vote_accuracy', 0.5)
        features.append(vote_accuracy)
        
        # 3. 矛盾次数
        contradiction_count = min(player_data.get('contradiction_count', 0) / 5.0, 1.0)
        features.append(contradiction_count)
        
        # 4. 注入攻击次数
        injection_attempts = min(player_data.get('injection_attempts', 0) / 3.0, 1.0)
        features.append(injection_attempts)
        
        # 5. 虚假引用次数
        false_quotation_count = min(player_data.get('false_quotation_count', 0) / 3.0, 1.0)
        features.append(false_quotation_count)
        
        # 6. 平均发言长度
        speech_lengths = player_data.get('speech_lengths', [100])
        avg_speech_length = sum(speech_lengths) / len(speech_lengths) if speech_lengths else 100
        features.append(min(avg_speech_length / 200.0, 1.0))
        
        # 7. 发言长度方差
        if len(speech_lengths) > 1:
            variance = np.var(speech_lengths)
            features.append(min(variance / 10000.0, 1.0))
        else:
            features.append(0.0)
        
        # 8. 提及他人次数
        mentions_others = min(player_data.get('mentions_others_count', 0) / 20.0, 1.0)
        features.append(mentions_others)
        
        # 9. 被提及次数
        mentioned_by_others = min(player_data.get('mentioned_by_others_count', 0) / 20.0, 1.0)
        features.append(mentioned_by_others)
        
        # 10. 攻击性分数
        aggressive_score = player_data.get('aggressive_score', 0.5)
        features.append(aggressive_score)
        
        # 11. 防御性分数
        defensive_score = player_data.get('defensive_score', 0.5)
        features.append(defensive_score)
        
        # 12. 情感关键词数量
        emotion_keywords = min(player_data.get('emotion_keyword_count', 0) / 15.0, 1.0)
        features.append(emotion_keywords)
        
        # 13. 逻辑关键词数量
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
        
        # 18. 平均响应时间
        avg_response_time = min(player_data.get('avg_response_time', 5.0) / 10.0, 1.0)
        features.append(avg_response_time)
        
        return np.array(features).reshape(1, -1)
    
    def fit(self, good_player_data_list: List[Dict]):
        """
        训练异常检测器（只使用好人数据）
        
        Args:
            good_player_data_list: 好人玩家数据列表
        """
        if len(good_player_data_list) < 5:
            logger.warning(f"Training data too small: {len(good_player_data_list)} samples")
            return
        
        # 提取特征
        X = np.vstack([self._extract_features(data) for data in good_player_data_list])
        
        # 特征缩放
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练模型
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        logger.info(f"✓ Anomaly detector fitted with {len(good_player_data_list)} good player samples")
    
    def get_anomaly_score(self, player_data: Dict) -> float:
        """
        获取异常分数
        
        Args:
            player_data: 玩家数据
            
        Returns:
            异常分数（越负越异常）
        """
        if not self.is_fitted:
            logger.warning("Model not fitted, returning 0.0")
            return 0.0
        
        # 提取特征
        X = self._extract_features(player_data)
        X_scaled = self.scaler.transform(X)
        
        # 获取异常分数
        score = self.model.score_samples(X_scaled)[0]
        
        return float(score)
    
    def get_wolf_probability(self, player_data: Dict) -> float:
        """
        获取狼人概率
        
        Args:
            player_data: 玩家数据
            
        Returns:
            狼人概率 (0-1)
        """
        if not self.is_fitted:
            logger.warning("Model not fitted, returning 0.5")
            return 0.5
        
        # 获取异常分数
        anomaly_score = self.get_anomaly_score(player_data)
        
        # 将异常分数转换为概率
        # 异常分数通常在[-0.5, 0.5]范围内
        # 越负越异常（越可能是狼人）
        wolf_prob = 1.0 / (1.0 + np.exp(anomaly_score * 10))
        
        return float(wolf_prob)
    
    def save_model(self, filepath: str):
        """保存模型"""
        if not self.is_fitted:
            logger.warning("Model not fitted, nothing to save")
            return
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'contamination': self.contamination,
            'is_fitted': self.is_fitted
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"✓ Anomaly detector saved to {filepath}")
    
    def load_model(self, filepath: str) -> bool:
        """
        加载模型
        
        Returns:
            是否成功加载
        """
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.contamination = model_data['contamination']
            self.is_fitted = model_data['is_fitted']
            
            logger.info(f"✓ Anomaly detector loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            return False
