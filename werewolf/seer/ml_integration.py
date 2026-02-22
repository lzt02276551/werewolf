# -*- coding: utf-8 -*-
"""
预言家代理人ML集成模块

处理ML模型的初始化、训练、预测和数据收集
符合企业级标准
"""

from typing import Dict, List, Optional, Any
from agent_build_sdk.utils.logger import logger
from .config import SeerConfig
from .memory_dao import SeerMemoryDAO
import os
import json
from pathlib import Path


class MLAgent:
    """
    ML代理封装类
    
    封装ML模型的初始化、预测等功能
    """
    
    def __init__(self, config: SeerConfig, memory_dao: SeerMemoryDAO):
        """
        初始化ML代理
        
        Args:
            config: 配置对象
            memory_dao: 内存DAO对象
        """
        self.config = config
        self.memory_dao = memory_dao
        self.ml_agent = None
        self.enabled = False
        self.confidence = config.ML_INITIAL_CONFIDENCE
        
        self._initialize()
    
    def _initialize(self) -> None:
        """初始化ML增强系统"""
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from ml_agent import LightweightMLAgent
            
            from game_utils import MLConfig
            model_dir = MLConfig.get_model_dir()
            
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.enabled = self.ml_agent.enabled
            self.confidence = self._calculate_confidence()
            
            if self.enabled:
                logger.info(f"✓ ML enhancement enabled for Seer (confidence: {self.confidence:.2%})")
            else:
                logger.info("⚠ ML enhancement initialized but not enabled")
        except ImportError as e:
            logger.warning(f"ML agent not available: {e}")
            self.enabled = False
        except Exception as e:
            logger.error(f"✗ Failed to initialize ML enhancement: {e}")
            self.enabled = False
    
    def _calculate_confidence(self) -> float:
        """
        根据训练样本数动态调整ML权重
        
        Returns:
            置信度 (0.40-0.85)
        """
        if not self.ml_agent or not self.enabled:
            return 0.0
        
        try:
            training_history_file = Path('./ml_models/training_history.json')
            
            if not training_history_file.exists():
                logger.info("[ML CONFIDENCE] No training history, using initial weight: 0.40")
                return 0.40
            
            try:
                with open(training_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"[ML CONFIDENCE] Failed to read training history: {e}, using default 0.40")
                return 0.40
            
            if not history or not isinstance(history, list):
                logger.warning("[ML CONFIDENCE] Invalid training history format, using default 0.40")
                return 0.40
            
            last_train = history[-1]
            total_samples = last_train.get('total_samples', 0)
            training_sessions = len(history)
            
            import math
            if total_samples > 0:
                sample_bonus = min(0.40, 0.15 * math.log10(total_samples + 1))
            else:
                sample_bonus = 0.0
            
            session_bonus = min(0.15, training_sessions * 0.015)
            
            quality_bonus = 0.0
            # 渐进式质量加成：准确率越高，加成越大
            if 'accuracy' in last_train:
                accuracy = last_train['accuracy']
                if accuracy > 0.7:
                    # 线性映射：0.7->0, 1.0->0.10
                    quality_bonus = min(0.10, (accuracy - 0.7) / 0.3 * 0.10)
                    logger.debug(f"[ML CONFIDENCE] High accuracy detected: {accuracy:.2%}, bonus +{quality_bonus:.2%}")
            
            confidence = 0.40 + sample_bonus + session_bonus + quality_bonus
            confidence = min(0.85, max(0.40, confidence))
            
            logger.info(
                f"[ML CONFIDENCE] Samples: {total_samples}, Sessions: {training_sessions}, "
                f"Confidence: {confidence:.2f} (Sample: +{sample_bonus:.2f}, "
                f"Session: +{session_bonus:.2f}, Quality: +{quality_bonus:.2f})"
            )
            
            return confidence
            
        except Exception as e:
            logger.warning(f"[ML CONFIDENCE] Calculation failed: {e}, using default 0.40")
            return 0.40
    
    def predict_wolf_probability(self, player_data: Dict[str, Any]) -> float:
        """
        预测玩家是狼人的概率
        
        Args:
            player_data: 玩家数据
            
        Returns:
            狼人概率 (0.0-1.0)
        """
        if not self.enabled or not self.ml_agent:
            return 0.5
        
        try:
            return self.ml_agent.predict_wolf_probability(player_data)
        except Exception as e:
            logger.warning(f"ML prediction failed: {e}")
            return 0.5


class MLDataCollector:
    """
    ML数据收集器
    
    收集游戏数据用于ML训练
    """
    
    def __init__(self, config: SeerConfig, memory_dao: SeerMemoryDAO):
        """
        初始化数据收集器
        
        Args:
            config: 配置对象
            memory_dao: 内存DAO对象
        """
        self.config = config
        self.memory_dao = memory_dao
    
    def collect_game_data(self) -> None:
        """收集当前游戏数据用于ML训练"""
        try:
            checked_players = self.memory_dao.get_checked_players()
            
            if not checked_players:
                logger.info("[DATA COLLECTION] No checked players, skipping data collection")
                return
            
            context = self._build_context()
            game_data_collected = self.memory_dao.get_game_data_collected()
            
            for player_name, check_data in checked_players.items():
                try:
                    player_features = self._build_player_features(player_name, context)
                    
                    player_features['label'] = 1 if check_data.get('is_wolf') else 0
                    player_features['confidence'] = 1.0
                    player_features['player_name'] = player_name
                    player_features['label_source'] = 'seer_check'
                    
                    game_data_collected.append(player_features)
                    logger.info(f"[DATA COLLECTION] Collected data for {player_name} (label: {player_features['label']})")
                except Exception as e:
                    logger.error(f"[DATA COLLECTION] Failed to collect data for {player_name}: {e}")
            
            self.memory_dao.set_game_data_collected(game_data_collected)
            logger.info(f"[DATA COLLECTION] Total samples collected: {len(game_data_collected)}")
            
        except Exception as e:
            logger.error(f"[DATA COLLECTION] Critical failure: {e}")
    
    def _build_context(self) -> Dict[str, Any]:
        """构建完整上下文"""
        return {
            'checked_players': self.memory_dao.get_checked_players(),
            'player_data': self.memory_dao.get_player_data(),
            'game_state': self.memory_dao.get_game_state(),
            'trust_scores': self.memory_dao.get_trust_scores(),
            'voting_history': self.memory_dao.get_voting_history(),
            'voting_results': self.memory_dao.get_voting_results(),
            'speech_history': self.memory_dao.get_speech_history(),
            'injection_attempts': self.memory_dao.get_injection_attempts(),
            'false_quotations': self.memory_dao.get_false_quotations(),
            'night_count': self.memory_dao.get_night_count()
        }
    
    def _build_player_features(self, player_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """构建ML模型所需的玩家特征"""
        trust_scores = context.get('trust_scores', {})
        voting_history = context.get('voting_history', {})
        speech_history = context.get('speech_history', {})
        injection_attempts = context.get('injection_attempts', [])
        false_quotations = context.get('false_quotations', [])
        voting_results = context.get('voting_results', {})
        player_data_dict = context.get('player_data', {})
        player_data = player_data_dict.get(player_name, {})
        game_state = context.get('game_state', {})
        
        speeches = speech_history.get(player_name, [])
        if not speeches:
            speeches = [""]
        speech_lengths = [len(s) for s in speeches]
        
        # 1. 计算投票准确度
        vote_accuracy = 0.5
        player_vote_results = voting_results.get(player_name, [])
        if player_vote_results and isinstance(player_vote_results, list) and len(player_vote_results) > 0:
            correct_votes = sum(1 for _, was_wolf in player_vote_results if was_wolf)
            total_votes = len(player_vote_results)
            vote_accuracy = correct_votes / total_votes if total_votes > 0 else 0.5
        
        # 2. 计算矛盾次数
        contradiction_count = 1 if player_data.get('contradictions') else 0
        
        # 3. 安全获取投票目标列表
        vote_targets = voting_history.get(player_name, [])
        if not isinstance(vote_targets, list):
            vote_targets = []
        
        # 4. 计算攻击性分数
        aggressive_keywords = {"狼", "wolf", "怀疑", "suspect", "投", "vote", "出局", "eliminate"}
        aggressive_score = 0.5
        if speeches:
            aggressive_count = sum(
                sum(1 for kw in aggressive_keywords if kw in s.lower())
                for s in speeches
            )
            total_words = sum(len(s.split()) for s in speeches)
            aggressive_score = min(1.0, aggressive_count / max(1, total_words / 10))
        
        # 5. 计算防御性分数
        defensive_keywords = {"不是", "not", "我是", "i am", "相信我", "trust me", "真的", "really"}
        defensive_score = 0.5
        if speeches:
            defensive_count = sum(
                sum(1 for kw in defensive_keywords if kw in s.lower())
                for s in speeches
            )
            total_words = sum(len(s.split()) for s in speeches)
            defensive_score = min(1.0, defensive_count / max(1, total_words / 10))
        
        # 6. 计算夜晚存活率
        night_survival_rate = 0.5
        total_nights = game_state.get('day', 1)
        if total_nights > 0:
            nights_survived = total_nights - (1 if player_data.get('killed_at_night') else 0)
            night_survival_rate = nights_survived / total_nights
        
        # 7. 计算联盟强度
        alliance_strength = 0.5
        if vote_targets:
            other_votes = {
                p: set(v) for p, v in voting_history.items() 
                if p != player_name and isinstance(v, list) and v
            }
            if other_votes:
                player_vote_set = set(vote_targets)
                overlap_scores = [
                    len(player_vote_set & other_set) / max(len(player_vote_set), len(other_set))
                    for other_set in other_votes.values()
                ]
                if overlap_scores:
                    alliance_strength = sum(overlap_scores) / len(overlap_scores)
        
        # 8. 计算孤立分数
        mentioned_by_others_count = sum(
            1 for p, ss in speech_history.items() 
            if p != player_name 
            for s in ss 
            if player_name in s
        )
        isolation_score = 1.0 / (1.0 + mentioned_by_others_count)
        
        # 9. 计算发言一致性分数
        speech_consistency_score = 0.5
        if len(speech_lengths) > 1:
            avg_length = sum(speech_lengths) / len(speech_lengths)
            variance = sum((l - avg_length) ** 2 for l in speech_lengths) / len(speech_lengths)
            std_dev = variance ** 0.5
            speech_consistency_score = 1.0 / (1.0 + std_dev / max(1, avg_length))
        
        # 10. 计算情感和逻辑关键词
        emotion_keywords = {"trust", "believe", "definitely", "absolutely"}
        emotion_keyword_count = sum(
            sum(1 for kw in emotion_keywords if kw in s.lower())
            for s in speeches
        )
        
        logic_keywords = {"because", "therefore", "analyze", "evidence"}
        logic_keyword_count = sum(
            sum(1 for kw in logic_keywords if kw in s.lower())
            for s in speeches
        )
        
        # 构建完整特征字典
        features = {
            'name': player_name,
            'trust_score': trust_scores.get(player_name, 50),
            'vote_accuracy': vote_accuracy,
            'contradiction_count': contradiction_count,
            'injection_attempts': sum(1 for att in injection_attempts if att.get('player') == player_name),
            'false_quotation_count': sum(1 for fq in false_quotations if fq.get('accuser') == player_name),
            'speech_lengths': speech_lengths,
            'voting_speed_avg': 5.0,
            'vote_targets': vote_targets,
            'mentions_others_count': sum(s.count("No.") for s in speeches),
            'mentioned_by_others_count': mentioned_by_others_count,
            'aggressive_score': aggressive_score,
            'defensive_score': defensive_score,
            'emotion_keyword_count': emotion_keyword_count,
            'logic_keyword_count': logic_keyword_count,
            'night_survival_rate': night_survival_rate,
            'alliance_strength': alliance_strength,
            'isolation_score': isolation_score,
            'speech_consistency_score': speech_consistency_score,
            'avg_response_time': 5.0
        }
        
        # 边界检查
        for key, value in features.items():
            if isinstance(value, (int, float)) and key not in ['name', 'trust_score', 'contradiction_count']:
                if value < 0:
                    features[key] = 0.0
                elif value > 1.0 and (key.endswith('_score') or key.endswith('_rate')):
                    features[key] = 1.0
        
        return features
    
    def save_to_file(self) -> None:
        """保存游戏数据到文件"""
        try:
            game_data_collected = self.memory_dao.get_game_data_collected()
            
            if not game_data_collected:
                logger.info("[DATA SAVE] No data to save")
                return
            
            # 数据验证
            valid_samples = []
            invalid_count = 0
            
            for idx, sample in enumerate(game_data_collected):
                try:
                    required_fields = ['player_name', 'label', 'confidence', 'trust_score', 
                                      'vote_accuracy', 'aggressive_score', 'defensive_score']
                    missing = [f for f in required_fields if f not in sample]
                    if missing:
                        logger.warning(f"[DATA SAVE] Sample {idx} missing fields: {missing}")
                        invalid_count += 1
                        continue
                    
                    if not isinstance(sample['label'], (int, float)) or sample['label'] not in [-1, 0, 1]:
                        logger.warning(f"[DATA SAVE] Sample {idx} invalid label: {sample['label']}")
                        invalid_count += 1
                        continue
                    
                    if not (0.0 <= sample['confidence'] <= 1.0):
                        logger.warning(f"[DATA SAVE] Sample {idx} invalid confidence: {sample['confidence']}")
                        invalid_count += 1
                        continue
                    
                    if 'speech_lengths' in sample and not isinstance(sample['speech_lengths'], list):
                        sample['speech_lengths'] = [100]
                    
                    if 'vote_targets' in sample and not isinstance(sample['vote_targets'], list):
                        sample['vote_targets'] = []
                    
                    valid_samples.append(sample)
                    
                except Exception as e:
                    logger.error(f"[DATA SAVE] Sample {idx} validation failed: {e}")
                    invalid_count += 1
                    continue
            
            if not valid_samples:
                logger.warning("[DATA SAVE] No valid samples to save")
                return
            
            logger.info(f"[DATA SAVE] Validated {len(valid_samples)}/{len(game_data_collected)} samples")
            if invalid_count > 0:
                logger.warning(f"[DATA SAVE] Skipped {invalid_count} invalid samples")
            
            # 构建完整的游戏数据结构
            import time
            
            game_state = self.memory_dao.get_game_state()
            game_metadata = {
                'game_id': f"seer_{int(time.time())}",
                'timestamp': int(time.time()),
                'agent_type': 'seer',
                'total_players': len(valid_samples),
                'labeled_samples': sum(1 for s in valid_samples if s['label'] != -1),
                'game_day': game_state.get('day', 0) if game_state else 0,
                'data_version': '2.0'
            }
            
            full_data = {
                'metadata': game_metadata,
                'samples': valid_samples
            }
            
            # 保存到game_data目录
            data_dir = os.getenv('DATA_DIR', './game_data')
            os.makedirs(data_dir, exist_ok=True)
            
            filename = f"{game_metadata['game_id']}.json"
            filepath = os.path.join(data_dir, filename)
            
            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(full_data, f, ensure_ascii=False, indent=2)
                    
                    if os.path.exists(filepath):
                        file_size = os.path.getsize(filepath)
                        if file_size > 0:
                            logger.info(f"[DATA SAVE] Successfully saved to {filepath}")
                            logger.info(f"  - File size: {file_size} bytes")
                            logger.info(f"  - Valid samples: {len(valid_samples)}")
                            logger.info(f"  - Labeled: {game_metadata['labeled_samples']}")
                            return
                        else:
                            logger.warning(f"[DATA SAVE] File is empty, retry {attempt+1}/{max_retries}")
                    else:
                        logger.warning(f"[DATA SAVE] File not found after write, retry {attempt+1}/{max_retries}")
                    
                except IOError as e:
                    logger.warning(f"[DATA SAVE] Write failed (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)
                    continue
            
            logger.error(f"[DATA SAVE] Failed after {max_retries} attempts")
            
        except Exception as e:
            logger.error(f"[DATA SAVE] Critical failure: {e}")


class MLTrainer:
    """
    ML训练器
    
    负责ML模型的训练和更新
    """
    
    def __init__(self, config: SeerConfig, memory_dao: SeerMemoryDAO, ml_agent: MLAgent):
        """
        初始化训练器
        
        Args:
            config: 配置对象
            memory_dao: 内存DAO对象
            ml_agent: ML代理对象
        """
        self.config = config
        self.memory_dao = memory_dao
        self.ml_agent = ml_agent
    
    def train(self) -> None:
        """增量学习：使用收集的数据更新ML模型"""
        if not self.ml_agent.enabled or not self.ml_agent.ml_agent:
            logger.debug("[INCREMENTAL LEARNING] ML not enabled, skipping")
            return
        
        try:
            game_data_collected = self.memory_dao.get_game_data_collected()
            
            if not game_data_collected:
                logger.info("[INCREMENTAL LEARNING] No data available")
                return
            
            # 准备训练数据
            player_data_list = []
            labels = []
            sample_weights = []
            
            for data in game_data_collected:
                label = data.get('label', -1)
                confidence = data.get('confidence', 0.0)
                
                if label is not None and label != -1:
                    feature_data = {k: v for k, v in data.items() 
                                   if k not in ['label', 'confidence', 'player_name', 'label_source']}
                    
                    player_data_list.append(feature_data)
                    labels.append(label)
                    sample_weights.append(confidence)
            
            if len(player_data_list) < 3:
                logger.info(f"[INCREMENTAL LEARNING] Insufficient samples: {len(player_data_list)}/3 minimum")
                return
            
            wolf_count = sum(1 for l in labels if l == 1)
            good_count = sum(1 for l in labels if l == 0)
            
            if wolf_count == 0 or good_count == 0:
                logger.warning(f"[INCREMENTAL LEARNING] Imbalanced classes: wolves={wolf_count}, goods={good_count}")
                logger.warning("[INCREMENTAL LEARNING] Need both classes for training, skipping")
                return
            
            # 构建训练数据
            training_data = {
                'player_data_list': player_data_list,
                'labels': labels,
                'sample_weights': sample_weights
            }
            
            avg_confidence = sum(sample_weights) / len(sample_weights)
            high_conf_count = sum(1 for w in sample_weights if w >= 0.8)
            
            logger.info(f"[INCREMENTAL LEARNING] ===== Training Summary =====")
            logger.info(f"  Total samples: {len(labels)}")
            logger.info(f"  Class distribution: wolves={wolf_count}, goods={good_count}")
            logger.info(f"  Avg confidence: {avg_confidence:.3f}")
            logger.info(f"  High confidence (≥0.8): {high_conf_count}/{len(labels)}")
            
            # 执行训练
            try:
                self.ml_agent.ml_agent.train(training_data)
                logger.info("[INCREMENTAL LEARNING] Training completed successfully")
            except Exception as train_error:
                logger.error(f"[INCREMENTAL LEARNING] Training failed: {train_error}")
                return
            
            # 保存模型
            try:
                from game_utils import MLConfig
                model_dir = MLConfig.get_model_dir()
                self.ml_agent.ml_agent.save_models(model_dir)
                logger.info(f"[INCREMENTAL LEARNING] Model saved to {model_dir}")
            except Exception as save_error:
                logger.error(f"[INCREMENTAL LEARNING] Model save failed: {save_error}")
            
            logger.info("[INCREMENTAL LEARNING] ===============================")
            
        except Exception as e:
            logger.error(f"[INCREMENTAL LEARNING] Critical failure: {e}")
