"""
游戏工具模块 - 提供统一的游戏管理功能
"""
import os
import time
import logging

logger = logging.getLogger(__name__)


class GameEndTrigger:
    """统一的游戏结束触发器"""
    
    _triggered_games = set()  # 记录已触发的游戏ID，避免重复处理
    
    @staticmethod
    def trigger_game_end(req, memory, role_name):
        """
        统一的游戏结束处理
        
        Args:
            req: 请求对象
            memory: 记忆对象
            role_name: 角色名称（用于日志）
        """
        try:
            from game_end_handler import get_game_end_handler
            handler = get_game_end_handler()
            
            if not handler or not handler.learning_system:
                logger.debug(f"[{role_name}] Learning system not available")
                return
            
            # 获取游戏ID（如果没有则生成）
            game_id = memory.load_variable("game_id")
            if not game_id:
                game_id = f"game_{int(time.time())}"
                logger.warning(f"[{role_name}] Game ID not found, generated: {game_id}")
            
            # 检查是否已经触发过（避免重复处理）
            if game_id in GameEndTrigger._triggered_games:
                logger.debug(f"[{role_name}] Game {game_id} already triggered, skipping")
                return
            
            # 标记为已触发
            GameEndTrigger._triggered_games.add(game_id)
            
            # 触发游戏结束处理
            handler.on_game_end(req.message)
            logger.info(f"[{role_name}] ✓ Game end triggered for incremental learning (game_id: {game_id})")
            
            # 清理旧的游戏ID（保留最近100个）
            if len(GameEndTrigger._triggered_games) > 100:
                # 移除最旧的50个
                old_games = list(GameEndTrigger._triggered_games)[:50]
                for old_game in old_games:
                    GameEndTrigger._triggered_games.discard(old_game)
            
        except ImportError as e:
            logger.debug(f"[{role_name}] 无法导入game_end_handler: {e}")
        except AttributeError as e:
            logger.debug(f"[{role_name}] 属性访问错误: {e}")
        except Exception as e:
            logger.debug(f"[{role_name}] Incremental learning not triggered: {e}")


class GameStartHandler:
    """统一的游戏开始处理器"""
    
    _started_games = set()  # 记录已开始的游戏ID，避免重复处理
    
    @staticmethod
    def handle_game_start(req, memory, role_name):
        """
        统一的游戏开始处理
        
        Args:
            req: 请求对象
            memory: 记忆对象
            role_name: 角色名称
        """
        try:
            # 检查是否已经有game_id（避免重复生成）
            existing_game_id = memory.load_variable("game_id")
            if existing_game_id:
                logger.debug(f"[{role_name}] Game ID already exists: {existing_game_id}")
                return
            
            # 生成统一的游戏ID
            game_id = f"game_{int(time.time())}_{req.name}"
            
            # 检查是否已经处理过（避免重复）
            if game_id in GameStartHandler._started_games:
                logger.debug(f"[{role_name}] Game {game_id} already started, skipping")
                return
            
            # 标记为已开始
            GameStartHandler._started_games.add(game_id)
            memory.set_variable("game_id", game_id)
            
            # 通知游戏结束处理器
            from game_end_handler import get_game_end_handler
            handler = get_game_end_handler()
            if handler:
                handler.on_game_start(game_id)
                logger.info(f"[{role_name}] Game started with ID: {game_id}")
            
            # 清理旧的游戏ID（保留最近100个）
            if len(GameStartHandler._started_games) > 100:
                old_games = list(GameStartHandler._started_games)[:50]
                for old_game in old_games:
                    GameStartHandler._started_games.discard(old_game)
            
        except ImportError as e:
            logger.debug(f"[{role_name}] 无法导入game_end_handler: {e}")
        except AttributeError as e:
            logger.debug(f"[{role_name}] 属性访问错误: {e}")
        except Exception as e:
            logger.debug(f"[{role_name}] Game start handler failed: {e}")


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
        
        Args:
            player_name: 玩家名称
            context: 上下文字典，包含各种游戏数据
        
        Returns:
            dict: ML模型所需的19个特征
        """
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
        
        if player_votes and isinstance(player_votes, list) and len(player_votes) > 0:
            # 构建被淘汰狼人的集合（一次遍历）
            eliminated_wolves = set()
            for day_result in voting_results.values():
                if isinstance(day_result, dict):
                    # 投票淘汰的狼人
                    if day_result.get('voted_out') and day_result.get('was_wolf', False):
                        eliminated_wolves.add(day_result['voted_out'])
                    # 被击杀的狼人
                    if day_result.get('shot_player') and day_result.get('shot_was_wolf', False):
                        eliminated_wolves.add(day_result['shot_player'])
            
            # 统计正确投票数（一次遍历）
            correct_votes = sum(1 for vote_target in player_votes if vote_target in eliminated_wolves)
            # 防止除零
            vote_accuracy = correct_votes / len(player_votes) if len(player_votes) > 0 else 0.5
        
        # 获取发言长度列表
        speeches = speech_history.get(player_name, [])
        speech_lengths = [len(s) for s in speeches] if speeches else [100]
        if not speech_lengths:
            speech_lengths = [100]
        
        # 计算矛盾次数
        contradiction_count = 1 if player_data.get('contradictions') else 0
        
        # 安全获取投票目标
        vote_targets = voting_history.get(player_name, [])
        if not isinstance(vote_targets, list):
            vote_targets = []
        
        # 计算提及次数
        mentions_others_count = sum(s.count("No.") for s in speeches) if speeches else 0
        mentioned_by_others_count = sum(
            1 for p, ss in speech_history.items() 
            if p != player_name 
            for s in ss 
            if player_name in s
        )
        
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
