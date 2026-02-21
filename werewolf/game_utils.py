"""
游戏工具模块 - 提供统一的游戏管理功能
"""
import os
import time
import logging
from collections import deque
from typing import Set, Optional
from werewolf.optimization.utils.safe_math import safe_divide

logger = logging.getLogger(__name__)


class GameEndTrigger:
    """
    统一的游戏结束触发器
    
    使用deque + set双数据结构:
    - deque: 保持时间顺序,自动限制大小
    - set: 提供O(1)查找性能
    
    优化说明:
    - 时间复杂度: O(1) 插入和查找
    - 空间复杂度: O(n) 其中n=100
    - 线程安全: 需要在多线程环境中加锁
    """
    
    # 使用deque自动保持最近100个游戏
    _triggered_games_queue: deque = deque(maxlen=100)
    
    # 使用set提供快速查找
    _triggered_games_set: Set[str] = set()
    
    # 统计信息
    _total_games_processed: int = 0
    _last_cleanup_time: float = 0
    
    @classmethod
    def trigger_game_end(cls, req, memory, role_name: str) -> bool:
        """
        触发游戏结束处理
        
        Args:
            req: 请求对象
            memory: 记忆对象
            role_name: 角色名称
            
        Returns:
            bool: 是否成功触发
        """
        try:
            from game_end_handler import get_game_end_handler
            handler = get_game_end_handler()
            
            if not handler or not handler.learning_system:
                logger.debug(f"[{role_name}] Learning system not available")
                return False
            
            # 获取游戏ID
            game_id = memory.load_variable("game_id")
            if not game_id:
                game_id = f"game_{int(time.time())}_{role_name}"
                logger.warning(f"[{role_name}] Game ID not found, generated: {game_id}")
            
            # 验证game_id类型
            if not isinstance(game_id, str):
                logger.error(f"[{role_name}] Invalid game_id type: {type(game_id)}")
                return False
            
            # 检查是否已触发 (O(1)查找)
            if game_id in cls._triggered_games_set:
                logger.debug(f"[{role_name}] Game {game_id} already triggered, skipping")
                return False
            
            # 添加到队列和集合
            cls._add_game(game_id)
            
            # 触发游戏结束处理
            handler.on_game_end(req.message)
            
            # 更新统计
            cls._total_games_processed += 1
            
            logger.info(
                f"[{role_name}] ✓ Game end triggered "
                f"(game_id: {game_id}, total: {cls._total_games_processed})"
            )
            
            return True
            
        except ImportError as e:
            logger.debug(f"[{role_name}] 无法导入game_end_handler: {e}")
            return False
        except AttributeError as e:
            logger.debug(f"[{role_name}] 属性访问错误: {e}")
            return False
        except Exception as e:
            logger.error(f"[{role_name}] Incremental learning failed: {e}", exc_info=True)
            return False
    
    @classmethod
    def _add_game(cls, game_id: str) -> None:
        """
        添加游戏ID到追踪系统
        
        Args:
            game_id: 游戏ID
        """
        # 如果队列已满,deque会自动移除最旧的元素
        # 我们需要同步更新set
        if len(cls._triggered_games_queue) >= 100:
            # 获取即将被移除的元素
            oldest_game = cls._triggered_games_queue[0]
            # 从set中移除
            cls._triggered_games_set.discard(oldest_game)
        
        # 添加新游戏
        cls._triggered_games_queue.append(game_id)
        cls._triggered_games_set.add(game_id)
        
        # 定期清理set(防止不同步)
        current_time = time.time()
        if current_time - cls._last_cleanup_time > 3600:  # 每小时清理一次
            cls._cleanup_set()
            cls._last_cleanup_time = current_time
    
    @classmethod
    def _cleanup_set(cls) -> None:
        """
        清理set,确保与deque同步
        
        这个方法定期执行,防止set和deque不同步
        """
        # 重建set,只包含deque中的元素
        valid_games = set(cls._triggered_games_queue)
        removed_count = len(cls._triggered_games_set) - len(valid_games)
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} stale game IDs from set")
            cls._triggered_games_set = valid_games
    
    @classmethod
    def get_stats(cls) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            'total_processed': cls._total_games_processed,
            'queue_size': len(cls._triggered_games_queue),
            'set_size': len(cls._triggered_games_set),
            'in_sync': len(cls._triggered_games_queue) == len(cls._triggered_games_set)
        }
    
    @classmethod
    def reset(cls) -> None:
        """重置追踪系统(用于测试)"""
        cls._triggered_games_queue.clear()
        cls._triggered_games_set.clear()
        cls._total_games_processed = 0
        cls._last_cleanup_time = 0


class GameStartHandler:
    """
    统一的游戏开始处理器
    
    使用与GameEndTrigger相同的双数据结构策略
    """
    
    _started_games_queue: deque = deque(maxlen=100)
    _started_games_set: Set[str] = set()
    _total_games_started: int = 0
    _last_cleanup_time: float = 0
    
    @classmethod
    def handle_game_start(cls, req, memory, role_name: str) -> bool:
        """
        统一的游戏开始处理
        
        Args:
            req: 请求对象
            memory: 记忆对象
            role_name: 角色名称
            
        Returns:
            bool: 是否成功处理
        """
        try:
            # 检查是否已经有game_id
            existing_game_id = memory.load_variable("game_id")
            if existing_game_id:
                logger.debug(f"[{role_name}] Game ID already exists: {existing_game_id}")
                return False
            
            # 生成统一的游戏ID
            game_id = f"game_{int(time.time())}_{req.name}"
            
            # 验证game_id类型
            if not isinstance(game_id, str):
                logger.error(f"[{role_name}] Invalid game_id type: {type(game_id)}")
                return False
            
            # 检查是否已经处理过
            if game_id in cls._started_games_set:
                logger.debug(f"[{role_name}] Game {game_id} already started, skipping")
                return False
            
            # 添加到追踪系统
            cls._add_game(game_id)
            
            # 设置game_id到内存
            memory.set_variable("game_id", game_id)
            
            # 通知游戏结束处理器
            from game_end_handler import get_game_end_handler
            handler = get_game_end_handler()
            if handler:
                handler.on_game_start(game_id)
                logger.info(f"[{role_name}] Game started with ID: {game_id}")
            
            # 更新统计
            cls._total_games_started += 1
            
            return True
            
        except ImportError as e:
            logger.debug(f"[{role_name}] 无法导入game_end_handler: {e}")
            return False
        except AttributeError as e:
            logger.debug(f"[{role_name}] 属性访问错误: {e}")
            return False
        except Exception as e:
            logger.error(f"[{role_name}] Game start handler failed: {e}", exc_info=True)
            return False
    
    @classmethod
    def _add_game(cls, game_id: str) -> None:
        """添加游戏ID到追踪系统"""
        if len(cls._started_games_queue) >= 100:
            oldest_game = cls._started_games_queue[0]
            cls._started_games_set.discard(oldest_game)
        
        cls._started_games_queue.append(game_id)
        cls._started_games_set.add(game_id)
        
        # 定期清理
        current_time = time.time()
        if current_time - cls._last_cleanup_time > 3600:
            cls._cleanup_set()
            cls._last_cleanup_time = current_time
    
    @classmethod
    def _cleanup_set(cls) -> None:
        """清理set,确保与deque同步"""
        valid_games = set(cls._started_games_queue)
        removed_count = len(cls._started_games_set) - len(valid_games)
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} stale game IDs from started set")
            cls._started_games_set = valid_games
    
    @classmethod
    def get_stats(cls) -> dict:
        """获取统计信息"""
        return {
            'total_started': cls._total_games_started,
            'queue_size': len(cls._started_games_queue),
            'set_size': len(cls._started_games_set),
            'in_sync': len(cls._started_games_queue) == len(cls._started_games_set)
        }
    
    @classmethod
    def reset(cls) -> None:
        """重置追踪系统(用于测试)"""
        cls._started_games_queue.clear()
        cls._started_games_set.clear()
        cls._total_games_started = 0
        cls._last_cleanup_time = 0


class MLConfig:
    """统一的ML配置"""
    
    # ML融合比例：ML预测权重（默认60%）
    FUSION_RATIO = float(os.getenv('ML_FUSION_RATIO', '0.6'))
    
    # ML模型目录（统一路径）
    MODEL_DIR = os.getenv('ML_MODEL_DIR', './ml_models')
    
    @classmethod
    def get_model_dir(cls):
        """获取ML模型目录的绝对路径"""
        if os.path.isabs(cls.MODEL_DIR):
            return cls.MODEL_DIR
        
        # 相对路径：从werewolf目录向上一级到项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, '..', cls.MODEL_DIR)


class MLDataBuilder:
    """统一的ML数据构建器"""
    
    @staticmethod
    def build_player_data_for_ml(player_name, context):
        """
        构建ML模型所需的玩家数据（统一方法）
        
        性能优化说明 (2026-02-21):
        - 使用一次遍历构建eliminated_wolves集合: O(n)，其中n=投票结果数
        - 使用集合查找correct_votes: O(1) per lookup
        - 总体时间复杂度: O(n + m)，其中n=投票结果数，m=玩家投票数
        - 避免了嵌套循环，显著提升性能
        
        Args:
            player_name: 玩家名称
            context: 上下文字典，包含各种游戏数据
        
        Returns:
            dict: ML模型所需的19个特征
        """
        # 输入类型验证
        if not isinstance(player_name, str):
            logger.error(f"Invalid player_name type: {type(player_name)}, expected str")
            player_name = str(player_name) if player_name else "Unknown"
        
        if not isinstance(context, dict):
            logger.error(f"Invalid context type: {type(context)}, expected dict")
            context = {}
        
        # 从context中提取各种数据
        trust_scores = context.get('trust_scores', {})
        voting_history = context.get('voting_history', {})
        speech_history = context.get('speech_history', {})
        injection_attempts = context.get('injection_attempts', [])
        false_quotations = context.get('false_quotations', [])
        voting_results = context.get('voting_results', {})
        player_data = context.get('player_data', {}).get(player_name, {})
        
        # 计算投票准确度（优化版 - 避免嵌套循环）
        vote_accuracy = 0.5
        player_votes = voting_history.get(player_name, [])
        
        # 验证数据结构
        if not isinstance(voting_history, dict):
            logger.warning(f"Invalid voting_history type: {type(voting_history)}, expected dict")
            voting_history = {}
            player_votes = []
        
        if not isinstance(voting_results, dict):
            logger.warning(f"Invalid voting_results type: {type(voting_results)}, expected dict")
            voting_results = {}
        
        if player_votes and isinstance(player_votes, list) and len(player_votes) > 0:
            # 性能关键部分：构建被淘汰狼人的集合（一次遍历，O(n)）
            eliminated_wolves = set()
            invalid_results = 0
            
            for day_key, day_result in voting_results.items():
                if not isinstance(day_result, dict):
                    logger.debug(f"Skipping invalid day_result for {day_key}: {type(day_result)}")
                    invalid_results += 1
                    continue
                
                # 投票淘汰的狼人
                voted_out = day_result.get('voted_out')
                was_wolf = day_result.get('was_wolf', False)
                if voted_out and isinstance(voted_out, str) and was_wolf:
                    eliminated_wolves.add(voted_out)
                
                # 被击杀的狼人
                shot_player = day_result.get('shot_player')
                shot_was_wolf = day_result.get('shot_was_wolf', False)
                if shot_player and isinstance(shot_player, str) and shot_was_wolf:
                    eliminated_wolves.add(shot_player)
            
            if invalid_results > 0:
                logger.debug(f"Skipped {invalid_results} invalid voting results")
            
            # 统计正确投票数（一次遍历，每次查找O(1)，总计O(m)）
            correct_votes = 0
            invalid_votes = 0
            for vote_target in player_votes:
                if not isinstance(vote_target, str):
                    logger.debug(f"Skipping invalid vote_target: {type(vote_target)}")
                    invalid_votes += 1
                    continue
                if vote_target in eliminated_wolves:
                    correct_votes += 1
            
            if invalid_votes > 0:
                logger.debug(f"Skipped {invalid_votes} invalid votes for {player_name}")
            
            # 使用safe_divide防止除零
            valid_votes = len(player_votes) - invalid_votes
            if valid_votes > 0:
                vote_accuracy = safe_divide(correct_votes, valid_votes, default=0.5)
            else:
                logger.debug(f"No valid votes for {player_name}, using default 0.5")
                vote_accuracy = 0.5
        
        # 获取发言长度列表（防止空列表）
        speeches = speech_history.get(player_name, [])
        speech_lengths = [len(s) for s in speeches if s] if speeches else [100]
        if not speech_lengths:
            speech_lengths = [100]
        
        # 计算矛盾次数
        contradiction_count = 1 if player_data.get('contradictions') else 0
        
        # 安全获取投票目标
        vote_targets = voting_history.get(player_name, [])
        if not isinstance(vote_targets, list):
            vote_targets = []
        
        # 计算提及次数（防止空列表和None）
        mentions_others_count = 0
        if speeches:
            mentions_others_count = sum(s.count("No.") for s in speeches if s)
        
        mentioned_by_others_count = 0
        if speech_history:
            for p, ss in speech_history.items():
                if p != player_name and ss:
                    for s in ss:
                        if s and player_name in s:
                            mentioned_by_others_count += 1
        
        # 计算关键词数量
        emotion_keywords = ["trust", "believe", "definitely", "absolutely", "相信", "肯定"]
        logic_keywords = ["because", "therefore", "analyze", "evidence", "因为", "所以", "分析", "证据"]
        
        emotion_count = 0
        logic_count = 0
        
        if speeches:
            for speech in speeches:
                speech_lower = speech.lower()
                for kw in emotion_keywords:
                    emotion_count += speech_lower.count(kw.lower())
                for kw in logic_keywords:
                    logic_count += speech_lower.count(kw.lower())
        
        # 构建19个特征
        return {
            'name': player_name,
            'trust_score': trust_scores.get(player_name, 50),
            'vote_accuracy': vote_accuracy,
            'contradiction_count': contradiction_count,
            'injection_attempts': sum(1 for att in injection_attempts if isinstance(att, dict) and att.get('player') == player_name),
            'false_quotation_count': sum(1 for fq in false_quotations if isinstance(fq, dict) and fq.get('accuser') == player_name),
            'speech_lengths': speech_lengths,
            'voting_speed_avg': 5.0,
            'vote_targets': vote_targets,
            'mentions_others_count': mentions_others_count,
            'mentioned_by_others_count': mentioned_by_others_count,
            'aggressive_score': player_data.get('aggressive_score', 0.5),
            'defensive_score': player_data.get('defensive_score', 0.5),
            'emotion_keyword_count': emotion_count,
            'logic_keyword_count': logic_count,
            'night_survival_rate': player_data.get('night_survival_rate', 0.5),
            'alliance_strength': player_data.get('alliance_strength', 0.5),
            'isolation_score': player_data.get('isolation_score', 0.5),
            'speech_consistency_score': player_data.get('speech_consistency_score', 0.5),
            'avg_response_time': 5.0
        }
