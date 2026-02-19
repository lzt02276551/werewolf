#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 scikit-learn 1.4.2 训练基础模型
"""

import os
import sys
import json
import pickle
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 检查 scikit-learn 版本
try:
    import sklearn
    logger.info(f"scikit-learn version: {sklearn.__version__}")
except ImportError:
    logger.error("scikit-learn not installed")
    sys.exit(1)

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix


def load_game_data(data_file='game_data/collected_data.json'):
    """加载游戏数据"""
    logger.info(f"Loading data from {data_file}")
    
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return None, None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {data['game_count']} games with {len(data['data'])} samples")
    return data['data'], data['game_count']


def extract_features(player_data):
    """从玩家数据中提取特征"""
    data = player_data['data']
    
    # 计算平均发言长度
    speech_lengths = data.get('speech_lengths', [])
    avg_speech_length = np.mean(speech_lengths) if speech_lengths else 0
    
    features = [
        data.get('trust_score', 50),
        data.get('vote_accuracy', 0.5),
        data.get('contradiction_count', 0),
        data.get('injection_attempts', 0),
        data.get('false_quotation_count', 0),
        avg_speech_length,
        data.get('voting_speed_avg', 3.0),
        data.get('mentions_others_count', 0),
        data.get('mentioned_by_others_count', 0),
        data.get('aggressive_score', 0.5),
        data.get('defensive_score', 0.5),
        data.get('emotion_keyword_count', 0),
        data.get('logic_keyword_count', 0),
        data.get('night_survival_rate', 0.5),
        data.get('alliance_strength', 0.5),
        data.get('isolation_score', 0.5),
        data.get('speech_consistency_score', 0.5),
        data.get('avg_response_time', 3.0),
    ]
    
    return features


def prepare_training_data(samples):
    """准备训练数据"""
    X = []
    y = []
    
    for sample in samples:
        features = extract_features(sample)
        X.append(features)
        
        # 标签：1=狼人，0=好人
        label = 1 if sample['role'] == 'wolf' else 0
        y.append(label)
    
    X = np.array(X)
    y = np.array(y)
    
    logger.info(f"Training data shape: X={X.shape}, y={y.shape}")
    logger.info(f"Class distribution: Wolf={np.sum(y)}, Good={len(y) - np.sum(y)}")
    
    return X, y


def train_models(X, y):
    """训练集成模型"""
    logger.info("Training models...")
    
    # 随机森林
    logger.info("Training Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X, y)
    rf_score = cross_val_score(rf_model, X, y, cv=min(3, len(y))).mean()
    logger.info(f"Random Forest CV Score: {rf_score:.4f}")
    
    # 梯度提升
    logger.info("Training Gradient Boosting...")
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    gb_model.fit(X, y)
    gb_score = cross_val_score(gb_model, X, y, cv=min(3, len(y))).mean()
    logger.info(f"Gradient Boosting CV Score: {gb_score:.4f}")
    
    # 决策树（作为基准）
    logger.info("Training Decision Tree...")
    dt_model = DecisionTreeClassifier(
        max_depth=8,
        min_samples_split=2,
        random_state=42
    )
    dt_model.fit(X, y)
    dt_score = cross_val_score(dt_model, X, y, cv=min(3, len(y))).mean()
    logger.info(f"Decision Tree CV Score: {dt_score:.4f}")
    
    # 评估模型
    logger.info("\n=== Model Evaluation ===")
    for name, model in [('Random Forest', rf_model), ('Gradient Boosting', gb_model), ('Decision Tree', dt_model)]:
        y_pred = model.predict(X)
        logger.info(f"\n{name}:")
        logger.info(f"Accuracy: {np.mean(y_pred == y):.4f}")
        logger.info(f"\nClassification Report:\n{classification_report(y, y_pred, target_names=['Good', 'Wolf'])}")
        logger.info(f"\nConfusion Matrix:\n{confusion_matrix(y, y_pred)}")
    
    return {
        'random_forest': rf_model,
        'gradient_boosting': gb_model,
        'decision_tree': dt_model
    }


def save_models(models, output_dir='ml_models'):
    """保存模型"""
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, 'ensemble.pkl')
    
    # 保存模型
    with open(output_file, 'wb') as f:
        pickle.dump(models, f)
    
    logger.info(f"✓ Models saved to {output_file}")
    
    # 保存元数据
    metadata = {
        'sklearn_version': sklearn.__version__,
        'trained_at': datetime.now().isoformat(),
        'models': list(models.keys())
    }
    
    metadata_file = os.path.join(output_dir, 'model_metadata.json')
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✓ Metadata saved to {metadata_file}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Training Base Model with scikit-learn 1.4.2")
    logger.info("=" * 60)
    
    # 加载数据
    samples, game_count = load_game_data()
    if samples is None:
        return
    
    # 准备训练数据
    X, y = prepare_training_data(samples)
    
    if len(X) < 10:
        logger.warning(f"Only {len(X)} samples available, model may not be reliable")
    
    # 训练模型
    models = train_models(X, y)
    
    # 保存模型
    save_models(models)
    
    logger.info("=" * 60)
    logger.info("✓ Training completed successfully!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
