# -*- coding: utf-8 -*-
"""
增量学习系统 - 实现游戏结束后自动训练模型
"""

import os
import logging
from typing import Dict, List
import json

logger = logging.getLogger(__name__)


class IncrementalLearningSystem:
    """增量学习系统 - 收集数据并定期重训练模型"""
    
    def __init__(self, ml_agent, retrain_interval=5):
        """
        Args:
            ml_agent: LightweightMLAgent实例
            retrain_interval: 每N局游戏重训练一次模型
        """
        self.ml_agent = ml_agent
        self.retrain_interval = retrain_interval
        self.game_count = 0
        self.collected_data = []
        
        # 数据存储目录
        self.data_dir = os.getenv('ML_DATA_DIR', './game_data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载已有数据
        self._load_existing_data()
        
        logger.info(f"✓ IncrementalLearningSystem initialized (retrain every {retrain_interval} games)")
    
    def _load_existing_data(self):
        """加载已有的游戏数据"""
        data_file = os.path.join(self.data_dir, 'collected_data.json')
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    self.collected_data = saved_data.get('data', [])
                    self.game_count = saved_data.get('game_count', 0)
                logger.info(f"✓ Loaded {len(self.collected_data)} samples from {self.game_count} games")
            except Exception as e:
                logger.warning(f"Failed to load existing data: {e}")
    
    def _save_data(self):
        """保存收集的数据"""
        data_file = os.path.join(self.data_dir, 'collected_data.json')
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'game_count': self.game_count,
                    'data': self.collected_data
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"Data saved to {data_file}")
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def on_game_end(self, game_id: str, players_data: List[Dict]) -> Dict:
        """
        游戏结束时调用
        
        Args:
            game_id: 游戏ID
            players_data: 玩家数据列表，每个元素包含 name, role, data
        
        Returns:
            dict: 处理结果
        """
        if not self.ml_agent or not self.ml_agent.enabled:
            return {
                'data_collected': False,
                'retrain_triggered': False,
                'game_count': self.game_count,
                'next_retrain_at': self.game_count + self.retrain_interval
            }
        
        # 收集数据
        for player in players_data:
            self.collected_data.append({
                'game_id': game_id,
                'player_name': player['name'],
                'role': player['role'],
                'data': player['data']
            })
        
        self.game_count += 1
        logger.info(f"✓ Collected data from game {game_id} ({len(players_data)} players)")
        
        # 保存数据
        self._save_data()
        
        # 检查是否需要重训练
        retrain_triggered = False
        if self.game_count % self.retrain_interval == 0:
            logger.info(f"🎯 Reached {self.game_count} games, triggering model retraining...")
            retrain_triggered = self._retrain_models()
        
        return {
            'data_collected': True,
            'retrain_triggered': retrain_triggered,
            'game_count': self.game_count,
            'next_retrain_at': ((self.game_count // self.retrain_interval) + 1) * self.retrain_interval
        }
    
    def _retrain_models(self) -> bool:
        """重训练模型"""
        if not self.collected_data:
            logger.warning("No data to train on")
            return False
        
        try:
            # 准备训练数据
            player_data_list = []
            labels = []
            sample_weights = []
            
            for item in self.collected_data:
                player_data_list.append(item['data'])
                # 标签：0=好人，1=狼人
                labels.append(1 if item['role'] == 'wolf' else 0)
                # 样本权重：最近的游戏权重更高
                sample_weights.append(1.0)
            
            # 应用时间衰减权重（最近的游戏权重更高）
            total_samples = len(sample_weights)
            for i in range(total_samples):
                # 线性衰减：最新的权重=1.0，最旧的权重=0.5
                decay = 0.5 + 0.5 * (i / max(1, total_samples - 1))
                sample_weights[i] = decay
            
            # 训练模型
            training_data = {
                'player_data_list': player_data_list,
                'labels': labels,
                'sample_weights': sample_weights
            }
            
            self.ml_agent.train(training_data)
            
            # 保存模型
            model_dir = os.getenv('ML_MODEL_DIR', './ml_models')
            self.ml_agent.save_models(model_dir)
            
            logger.info(f"✓ Model retrained with {len(player_data_list)} samples")
            return True
            
        except Exception as e:
            logger.error(f"✗ Model retraining failed: {e}")
            import traceback
            traceback.print_exc()
            return False
