"""
轻量级ML智能体 - 魔搭平台专用
只使用sklearn-based模块，内存占用小，速度快
"""
import os
import sys
import logging
import numpy as np

logger = logging.getLogger(__name__)

# 尝试导入ML模块
try:
    # 添加项目根目录到路径（如果需要）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from ml_enhanced.ensemble_detector import WolfDetectionEnsemble
    from ml_enhanced.anomaly_detector import BehaviorAnomalyDetector
    from ml_enhanced.bayesian_inference import BayesianAnalyzer
    ML_AVAILABLE = True
    logger.info("✓ ML modules loaded successfully")
except ImportError as e:
    ML_AVAILABLE = False
    logger.warning(f"⚠ ML modules not available: {e}")


class LightweightMLAgent:
    """轻量级ML智能体"""
    
    def __init__(self, model_dir=None):
        """
        Args:
            model_dir: 预训练模型目录（可选）
        """
        self.enabled = ML_AVAILABLE
        
        if not self.enabled:
            logger.warning("ML enhancement disabled - modules not available")
            return
        
        try:
            # 初始化模块
            self.ensemble = WolfDetectionEnsemble()
            self.anomaly = BehaviorAnomalyDetector(contamination=0.33)
            self.bayesian = BayesianAnalyzer()
            
            # 模块权重
            self.weights = {
                'ensemble': 0.40,
                'anomaly': 0.30,
                'bayesian': 0.30
            }
            
            # 尝试加载预训练模型
            if model_dir and os.path.exists(model_dir):
                try:
                    self.load_models(model_dir)
                except Exception as e:
                    logger.warning(f"Failed to load pre-trained models: {e}")
            
            logger.info("✓ LightweightMLAgent initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize ML agent: {e}")
            self.enabled = False
    
    def predict_wolf_probability(self, player_data):
        """预测狼人概率"""
        if not self.enabled:
            return 0.5
        
        predictions = {}
        
        # 1. Ensemble预测
        if hasattr(self.ensemble, 'is_trained') and self.ensemble.is_trained:
            try:
                pred = self.ensemble.predict_wolf_probability(player_data)
                predictions['ensemble'] = pred
            except Exception as e:
                logger.debug(f"Ensemble prediction failed: {e}")
        
        # 2. 异常检测
        if hasattr(self.anomaly, 'is_fitted') and self.anomaly.is_fitted:
            try:
                pred = self.anomaly.get_wolf_probability(player_data)
                predictions['anomaly'] = pred
            except Exception as e:
                logger.debug(f"Anomaly prediction failed: {e}")
        
        # 3. 贝叶斯推理
        try:
            pred = self.bayesian.analyze_player(player_data)
            predictions['bayesian'] = pred
        except Exception as e:
            logger.debug(f"Bayesian prediction failed: {e}")
        
        # 加权融合
        if not predictions:
            return 0.5
        
        total_weight = sum(self.weights[k] for k in predictions.keys())
        if total_weight == 0:
            return 0.5
        normalized_weights = {k: self.weights[k] / total_weight for k in predictions.keys()}
        
        final_prob = sum(predictions[k] * normalized_weights[k] for k in predictions.keys())
        
        logger.debug(f"Wolf prob: {final_prob:.3f} (from {len(predictions)} models)")
        return final_prob
    
    def train(self, training_data):
        """训练模型 - 优化：支持样本权重"""
        if not self.enabled:
            logger.warning("Cannot train - ML not available")
            return
        
        try:
            player_data_list = training_data['player_data_list']
            labels = training_data['labels']
            sample_weights = training_data.get('sample_weights', None)
            
            # 训练Ensemble（传递样本权重）
            logger.info("Training Ensemble...")
            if sample_weights:
                logger.info(f"  Using sample weights (avg: {sum(sample_weights)/len(sample_weights):.2f})")
            self.ensemble.train(player_data_list, labels, sample_weights=sample_weights)
            
            # 训练Anomaly Detector（使用好人数据，优先使用高置信度样本）
            logger.info("Training Anomaly Detector...")
            if sample_weights:
                # 优先使用高置信度好人，如果数量不足则降低阈值
                high_conf_good = [
                    player_data_list[i] for i in range(len(labels)) 
                    if labels[i] == 0 and sample_weights[i] >= 0.7
                ]
                if len(high_conf_good) >= 5:  # 至少需要5个样本
                    good_players = high_conf_good
                    logger.info(f"  Using {len(good_players)} high-confidence good players")
                else:
                    # 降低阈值到0.5
                    good_players = [
                        player_data_list[i] for i in range(len(labels)) 
                        if labels[i] == 0 and sample_weights[i] >= 0.5
                    ]
                    logger.info(f"  Using {len(good_players)} medium-confidence good players (threshold=0.5)")
            else:
                good_players = [player_data_list[i] for i in range(len(labels)) if labels[i] == 0]
                logger.info(f"  Using {len(good_players)} good players (no weights)")
            
            if good_players:
                self.anomaly.fit(good_players)
            else:
                logger.warning("  No good player data available for anomaly detector")
            
            logger.info("✓ Training completed")
        except Exception as e:
            logger.error(f"✗ Training failed: {e}")
            import traceback
            traceback.print_exc()
    
    def save_models(self, directory):
        """保存模型"""
        if not self.enabled:
            return
        
        try:
            os.makedirs(directory, exist_ok=True)
            self.ensemble.save_models(f"{directory}/ensemble.pkl")
            logger.info(f"✓ Models saved to {directory}")
        except Exception as e:
            logger.error(f"✗ Failed to save models: {e}")
    
    def load_models(self, directory):
        """加载模型 - 增强错误处理，兼容版本不匹配"""
        if not self.enabled:
            return
        
        try:
            model_path = f"{directory}/ensemble.pkl"
            if os.path.exists(model_path):
                success = self.ensemble.load_models(model_path)  # 修复：检查返回值
                if success:
                    logger.info(f"✓ Models loaded from {directory}")
                else:
                    logger.warning(f"⚠ Failed to load models from {directory}")
                    # 删除不兼容的模型文件
                    try:
                        os.remove(model_path)
                        logger.info(f"  Removed incompatible model file: {model_path}")
                    except Exception as remove_error:
                        logger.debug(f"  Could not remove model file: {remove_error}")
            else:
                logger.info(f"ℹ No pre-trained model found at {model_path}, will train from scratch")
        except Exception as e:
            logger.error(f"✗ Error in load_models: {e}")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("Testing LightweightMLAgent...")
    agent = LightweightMLAgent()
    
    if agent.enabled:
        print("✓ Agent initialized successfully")
        
        # 测试预测
        test_player = {
            'trust_score': 30,
            'vote_accuracy': 0.3,
            'contradiction_count': 5,
            'injection_attempts': 2,
            'false_quotation_count': 1,
            'speech_lengths': [60, 70, 65],
            'voting_speed_avg': 2.0,
            'vote_targets': ['No.3', 'No.5'],
            'mentions_others_count': 15,
            'mentioned_by_others_count': 3,
            'aggressive_score': 0.8,
            'defensive_score': 0.9,
            'emotion_keyword_count': 12,
            'logic_keyword_count': 4,
            'night_survival_rate': 0.9,
            'alliance_strength': 0.8,
            'isolation_score': 0.7,
            'speech_consistency_score': 0.3,
            'avg_response_time': 2.0
        }
        
        wolf_prob = agent.predict_wolf_probability(test_player)
        print(f"✓ Test prediction: {wolf_prob:.3f}")
    else:
        print("✗ Agent not available")
