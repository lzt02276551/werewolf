# -*- coding: utf-8 -*-
"""
增量学习系统 - 实现游戏结束后自动训练模型
"""

import os
import logging
from typing import Dict, List
import json
from werewolf.optimization.utils.safe_math import safe_divide

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
        self.data_dir = os.getenv('DATA_DIR', './game_data')
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
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {e}, 将创建新数据文件")
                self.collected_data = []
                self.game_count = 0
            except (IOError, OSError) as e:
                logger.warning(f"文件读取失败: {e}")
                self.collected_data = []
                self.game_count = 0
            except Exception as e:
                logger.warning(f"加载数据失败: {e}", exc_info=True)
                self.collected_data = []
                self.game_count = 0
    
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
        except (IOError, OSError) as e:
            logger.error(f"文件写入失败: {e}")
        except TypeError as e:
            logger.error(f"数据序列化失败: {e}")
        except Exception as e:
            logger.error(f"保存数据失败: {e}", exc_info=True)
    
    def on_game_end(self, game_id: str, players_data: List[Dict]) -> Dict:
        """
        游戏结束时调用
        
        Args:
            game_id: 游戏ID
            players_data: 玩家数据列表，每个元素包含 name, role, data
        
        Returns:
            dict: 处理结果
        """
        # 输入类型验证
        if not isinstance(game_id, str):
            logger.error(f"Invalid game_id type: {type(game_id)}, expected str")
            game_id = str(game_id) if game_id else f"game_{self.game_count}"
        
        if not isinstance(players_data, list):
            logger.error(f"Invalid players_data type: {type(players_data)}, expected list")
            players_data = []
        
        if not self.ml_agent or not self.ml_agent.enabled:
            return {
                'data_collected': False,
                'retrain_triggered': False,
                'game_count': self.game_count,
                'next_retrain_at': self.game_count + self.retrain_interval
            }
        
        # 收集数据（带验证）
        valid_players = 0
        for player in players_data:
            # 验证player是字典
            if not isinstance(player, dict):
                logger.warning(f"跳过无效的玩家数据（非字典）: {type(player)}")
                continue
            
            # 验证必需字段
            if 'name' not in player or 'role' not in player or 'data' not in player:
                logger.warning(f"跳过缺少必需字段的玩家数据: {player.keys() if isinstance(player, dict) else 'N/A'}")
                continue
            
            # 验证字段类型
            if not isinstance(player['name'], str):
                logger.warning(f"跳过无效的玩家名称类型: {type(player['name'])}")
                continue
            
            if not isinstance(player['role'], str):
                logger.warning(f"跳过无效的角色类型: {type(player['role'])}")
                continue
            
            if not isinstance(player['data'], dict):
                logger.warning(f"跳过无效的数据类型: {type(player['data'])}")
                continue
            
            # 添加有效数据
            self.collected_data.append({
                'game_id': game_id,
                'player_name': player['name'],
                'role': player['role'],
                'data': player['data']
            })
            valid_players += 1
        
        self.game_count += 1
        logger.info(f"✓ Collected data from game {game_id} ({valid_players}/{len(players_data)} valid players)")
        
        # 保存数据
        self._save_data()
        
        # 检查是否需要重训练
        retrain_triggered = False
        if self.game_count % self.retrain_interval == 0:
            logger.info(f"🎯 Reached {self.game_count} games, triggering model retraining...")
            retrain_triggered = self._retrain_models()
        
        return {
            'data_collected': True,
            'valid_players': valid_players,
            'total_players': len(players_data),
            'retrain_triggered': retrain_triggered,
            'game_count': self.game_count,
            'next_retrain_at': ((safe_divide(self.game_count, self.retrain_interval, default=0) + 1) * self.retrain_interval)
        }
    
    def _retrain_models(self) -> bool:
        """重训练模型"""
        if not self.collected_data:
            logger.warning("No data to train on")
            return False
        
        try:
            # 准备训练数据（增强验证）
            player_data_list = []
            labels = []
            sample_weights = []
            
            skipped_count = 0
            for item in self.collected_data:
                # 验证item是字典
                if not isinstance(item, dict):
                    logger.warning(f"跳过无效数据项（非字典）: {type(item)}")
                    skipped_count += 1
                    continue
                
                # 验证必需字段存在
                if 'data' not in item or 'role' not in item:
                    logger.warning(f"跳过缺少必要字段的数据项: {list(item.keys())}")
                    skipped_count += 1
                    continue
                
                # 验证data字段类型
                if not isinstance(item['data'], dict):
                    logger.warning(f"跳过无效的data类型: {type(item['data'])}")
                    skipped_count += 1
                    continue
                
                # 验证role字段类型
                if not isinstance(item['role'], str):
                    logger.warning(f"跳过无效的role类型: {type(item['role'])}")
                    skipped_count += 1
                    continue
                
                # 添加有效数据
                player_data_list.append(item['data'])
                # 标签：0=好人，1=狼人
                labels.append(1 if item['role'] == 'wolf' else 0)
                # 样本权重：最近的游戏权重更高
                sample_weights.append(1.0)
            
            if skipped_count > 0:
                logger.warning(f"跳过了 {skipped_count} 个无效数据项")
            
            if not player_data_list:
                logger.warning("没有有效的训练数据")
                return False
            
            # 应用时间衰减权重（最近的游戏权重更高）
            total_samples = len(sample_weights)
            for i in range(total_samples):
                # 线性衰减：最新的权重=1.0，最旧的权重=0.5
                decay = 0.5 + 0.5 * safe_divide(i, max(1, total_samples - 1), default=0.0)
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
            
            logger.info(f"✓ Model retrained with {len(player_data_list)} samples ({skipped_count} skipped)")
            return True
            
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"✗ 训练数据准备失败: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Model retraining failed: {e}", exc_info=True)
            return False
