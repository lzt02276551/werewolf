"""
特征提取器 - 从游戏数据中提取ML特征

标准化特征提取流程，确保所有ML模型使用一致的特征
"""

import logging
import numpy as np
from typing import Dict, List

logger = logging.getLogger(__name__)


class StandardFeatureExtractor:
    """
    标准特征提取器
    
    提取19个标准特征：
    1. 信任分数
    2. 投票准确度
    3. 矛盾次数
    4. 注入攻击次数
    5. 虚假引用次数
    6. 平均发言长度
    7. 发言长度方差
    8. 提及他人次数
    9. 被提及次数
    10. 攻击性分数
    11. 防御性分数
    12. 情感关键词数量
    13. 逻辑关键词数量
    14. 夜间存活率
    15. 联盟强度
    16. 孤立分数
    17. 发言一致性分数
    18. 平均响应时间
    19. 投票目标数量
    """
    
    FEATURE_NAMES = [
        'trust_score',
        'vote_accuracy',
        'contradiction_count',
        'injection_attempts',
        'false_quotation_count',
        'avg_speech_length',
        'speech_length_variance',
        'mentions_others_count',
        'mentioned_by_others_count',
        'aggressive_score',
        'defensive_score',
        'emotion_keyword_count',
        'logic_keyword_count',
        'night_survival_rate',
        'alliance_strength',
        'isolation_score',
        'speech_consistency_score',
        'avg_response_time',
        'vote_target_count',
    ]
    
    @staticmethod
    def extract_features(player_data: Dict) -> np.ndarray:
        """
        提取特征向量
        
        Args:
            player_data: 玩家数据字典
            
        Returns:
            特征向量 (19维)
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
        
        # 19. 投票目标数量 (归一化)
        vote_targets = player_data.get('vote_targets', [])
        vote_target_count = min(len(set(vote_targets)) / 8.0, 1.0) if vote_targets else 0.0
        features.append(vote_target_count)
        
        return np.array(features)
    
    @staticmethod
    def extract_batch_features(player_data_list: List[Dict]) -> np.ndarray:
        """
        批量提取特征
        
        Args:
            player_data_list: 玩家数据列表
            
        Returns:
            特征矩阵 (N x 19)
        """
        return np.vstack([
            StandardFeatureExtractor.extract_features(data)
            for data in player_data_list
        ])
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """获取特征名称列表"""
        return StandardFeatureExtractor.FEATURE_NAMES.copy()
