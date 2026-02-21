"""
主Agent决策器模块

本模块实现了完整的决策流程，集成了输入验证、决策引擎、缓存等组件。
提供统一的决策接口，处理各种决策场景（投票、击杀、保护等）。

主要功能：
- 输入验证：使用Pydantic验证输入数据
- 决策执行：使用决策引擎评估候选人并选择最佳选项
- 缓存管理：自动管理决策上下文缓存
- 错误处理：捕获并记录各种异常情况
- 日志记录：记录决策过程的关键信息

验证需求：AC-1.2.4, AC-1.1.3
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import ValidationError

from ..models.validation import (
    VoteDecisionInput,
    CandidateList,
    PlayerName,
    GameState
)
from ..core.decision_engine import DecisionEngine
from ..core.decision_context import DecisionContext
from ..core.scoring_strategy import (
    ScoringDimension,
    TrustScoreDimension,
    WerewolfProbabilityDimension,
    VotingAccuracyDimension
)
from ..config.config_loader import load_config, ConfigurationError

logger = logging.getLogger(__name__)


class DecisionAgentError(Exception):
    """决策Agent错误基类"""
    pass


class InputValidationError(DecisionAgentError):
    """输入验证错误"""
    pass


class DecisionExecutionError(DecisionAgentError):
    """决策执行错误"""
    pass


class DecisionAgent:
    """
    主Agent决策器
    
    决策Agent负责协调整个决策流程，从输入验证到最终决策输出。
    它集成了配置管理、输入验证、决策引擎和缓存机制。
    
    属性:
        config: 优化配置对象
        decision_engine: 决策引擎实例
    
    示例:
        >>> # 创建决策Agent
        >>> agent = DecisionAgent()
        >>> 
        >>> # 准备输入数据
        >>> decision_input = {
        ...     'candidates': {
        ...         'candidates': [
        ...             {'name': 'No.1'},
        ...             {'name': 'No.2'},
        ...             {'name': 'No.3'}
        ...         ]
        ...     },
        ...     'game_state': {
        ...         'day': 3,
        ...         'phase': 'voting',
        ...         'players': {
        ...             'No.1': {'name': 'No.1', 'is_alive': True},
        ...             'No.2': {'name': 'No.2', 'is_alive': True},
        ...             'No.3': {'name': 'No.3', 'is_alive': True}
        ...         }
        ...     },
        ...     'player_profiles': {
        ...         'No.1': {'trust_score': 75.0},
        ...         'No.2': {'trust_score': 60.0},
        ...         'No.3': {'trust_score': 90.0}
        ...     }
        ... }
        >>> 
        >>> # 执行决策
        >>> result = agent.make_decision(decision_input)
        >>> print(result['selected_candidate'])  # 'No.3'
        >>> print(result['scores'])  # 各候选人的详细分数
    
    验证需求：AC-1.2.4, AC-1.1.3
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化决策Agent
        
        参数:
            config_path: 配置文件路径（可选）
                如果不提供，将使用默认配置路径
        
        异常:
            ConfigurationError: 配置加载失败
        """
        try:
            # 加载配置
            self.config = load_config(config_path)
            logger.info("决策Agent配置加载成功")
            
            # 创建评分维度
            dimensions = self._create_dimensions()
            
            # 创建决策引擎
            self.decision_engine = DecisionEngine(dimensions)
            
            logger.info("决策Agent初始化完成")
            
        except ConfigurationError as e:
            logger.error(f"配置加载失败: {e}")
            raise
        except Exception as e:
            logger.error(f"决策Agent初始化失败: {e}", exc_info=True)
            raise DecisionAgentError(f"初始化失败: {e}")
    
    def _create_dimensions(self) -> List[ScoringDimension]:
        """
        根据配置创建评分维度
        
        返回:
            评分维度列表
        """
        dimensions = []
        
        # 获取评分维度配置
        scoring_config = self.config.scoring.dimensions
        
        # 创建信任分数维度
        if 'trust_score' in scoring_config:
            trust_config = scoring_config['trust_score'].model_dump()
            dimensions.append(TrustScoreDimension(trust_config))
            logger.debug(f"创建信任分数维度: {trust_config}")
        
        # 创建狼人概率维度
        if 'werewolf_probability' in scoring_config:
            werewolf_config = scoring_config['werewolf_probability'].model_dump()
            dimensions.append(WerewolfProbabilityDimension(werewolf_config))
            logger.debug(f"创建狼人概率维度: {werewolf_config}")
        
        # 创建投票准确率维度
        if 'voting_accuracy' in scoring_config:
            voting_config = scoring_config['voting_accuracy'].model_dump()
            dimensions.append(VotingAccuracyDimension(voting_config))
            logger.debug(f"创建投票准确率维度: {voting_config}")
        
        return dimensions
    
    def validate_input(self, raw_input: Dict[str, Any]) -> VoteDecisionInput:
        """
        验证输入数据
        
        使用Pydantic模型验证输入数据的格式和内容。
        
        参数:
            raw_input: 原始输入字典，应包含以下键：
                - candidates: 候选人列表
                - game_state: 游戏状态
                - player_profiles: 玩家档案（可选）
        
        返回:
            验证后的输入对象
        
        异常:
            InputValidationError: 输入验证失败
        
        验证需求：AC-1.2.4
        """
        try:
            # 使用Pydantic验证输入
            validated_input = VoteDecisionInput(**raw_input)
            
            logger.info(
                f"输入验证成功: {len(validated_input.candidates.candidates)} 个候选人, "
                f"游戏第 {validated_input.game_state.day} 天, "
                f"阶段: {validated_input.game_state.phase}"
            )
            
            return validated_input
            
        except ValidationError as e:
            # 提取错误信息
            error_details = []
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                message = error['msg']
                error_details.append(f"{field}: {message}")
            
            error_message = "输入验证失败: " + "; ".join(error_details)
            logger.error(error_message)
            
            raise InputValidationError(error_message)
        
        except Exception as e:
            logger.error(f"输入验证过程中发生未知错误: {e}", exc_info=True)
            raise InputValidationError(f"输入验证失败: {e}")
    
    def make_decision(
        self,
        raw_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行决策
        
        这是主要的决策接口，执行完整的决策流程：
        1. 验证输入数据
        2. 创建决策上下文
        3. 使用决策引擎评估候选人
        4. 选择最佳候选人
        5. 清理缓存
        6. 返回决策结果
        
        参数:
            raw_input: 原始输入字典，格式见 validate_input 方法
        
        返回:
            决策结果字典，包含以下键：
            - success: 是否成功（布尔值）
            - selected_candidate: 选中的候选人名称（字符串）
            - scores: 所有候选人的详细分数（字典）
            - error: 错误信息（如果失败）
        
        示例:
            >>> agent = DecisionAgent()
            >>> result = agent.make_decision({
            ...     'candidates': {
            ...         'candidates': [{'name': 'No.1'}, {'name': 'No.2'}]
            ...     },
            ...     'game_state': {
            ...         'day': 1,
            ...         'phase': 'voting',
            ...         'players': {
            ...             'No.1': {'name': 'No.1', 'is_alive': True},
            ...             'No.2': {'name': 'No.2', 'is_alive': True}
            ...         }
            ...     },
            ...     'player_profiles': {}
            ... })
            >>> print(result['success'])  # True
            >>> print(result['selected_candidate'])  # 'No.1' 或 'No.2'
        
        验证需求：AC-1.2.4, AC-1.1.3
        """
        context = None
        
        try:
            # 步骤1: 验证输入
            logger.info("开始决策流程")
            validated_input = self.validate_input(raw_input)
            
            # 步骤2: 创建决策上下文
            context = DecisionContext(
                game_state=validated_input.game_state.model_dump(),
                player_profiles=validated_input.player_profiles
            )
            logger.debug("决策上下文创建成功")
            
            # 步骤3: 提取候选人列表
            candidates = [
                player.name
                for player in validated_input.candidates.candidates
            ]
            logger.info(f"候选人列表: {candidates}")
            
            # 步骤4: 评估所有候选人
            all_scores = {}
            for candidate in candidates:
                scores = self.decision_engine.evaluate_candidate(candidate, context)
                all_scores[candidate] = scores
            
            # 步骤5: 选择最佳候选人
            best_candidate = self.decision_engine.select_best_candidate(
                candidates,
                context
            )
            
            if best_candidate is None:
                raise DecisionExecutionError("无法选择最佳候选人")
            
            # 步骤6: 构建返回结果
            result = {
                'success': True,
                'selected_candidate': best_candidate,
                'scores': all_scores,
                'final_score': all_scores[best_candidate]['final_score']
            }
            
            logger.info(
                f"决策完成: 选择 {best_candidate}, "
                f"分数: {result['final_score']:.2f}"
            )
            
            return result
            
        except InputValidationError as e:
            # 输入验证错误
            logger.error(f"输入验证失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'INPUT_VALIDATION_ERROR'
            }
        
        except DecisionExecutionError as e:
            # 决策执行错误
            logger.error(f"决策执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'DECISION_EXECUTION_ERROR'
            }
        
        except Exception as e:
            # 未知错误
            logger.error(f"决策过程中发生未知错误: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"未知错误: {e}",
                'error_type': 'UNKNOWN_ERROR'
            }
        
        finally:
            # 步骤7: 清理缓存
            if context is not None:
                context.clear_cache()
                logger.debug("决策上下文缓存已清理")
    
    def make_simple_decision(
        self,
        candidates: List[str],
        game_state: Dict[str, Any],
        player_profiles: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        简化的决策接口
        
        提供更简单的API，直接接受Python对象而不是字典。
        适用于已经有验证过的数据的场景。
        
        参数:
            candidates: 候选人名称列表，例如 ['No.1', 'No.2']
            game_state: 游戏状态字典
            player_profiles: 玩家档案字典（可选）
        
        返回:
            选中的候选人名称，如果失败则返回 None
        
        示例:
            >>> agent = DecisionAgent()
            >>> best = agent.make_simple_decision(
            ...     candidates=['No.1', 'No.2'],
            ...     game_state={
            ...         'day': 1,
            ...         'phase': 'voting',
            ...         'players': {
            ...             'No.1': {'name': 'No.1', 'is_alive': True},
            ...             'No.2': {'name': 'No.2', 'is_alive': True}
            ...         }
            ...     },
            ...     player_profiles={}
            ... )
            >>> print(best)  # 'No.1' 或 'No.2'
        
        验证需求：AC-1.2.4
        """
        try:
            # 构建输入字典
            raw_input = {
                'candidates': {
                    'candidates': [{'name': name} for name in candidates]
                },
                'game_state': game_state,
                'player_profiles': player_profiles or {}
            }
            
            # 调用完整的决策流程
            result = self.make_decision(raw_input)
            
            # 返回选中的候选人
            if result['success']:
                return result['selected_candidate']
            else:
                logger.error(f"简化决策失败: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"简化决策过程中发生错误: {e}", exc_info=True)
            return None
    
    def get_candidate_scores(
        self,
        candidates: List[str],
        game_state: Dict[str, Any],
        player_profiles: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        获取所有候选人的详细分数
        
        不进行最终选择，只返回所有候选人的评分详情。
        适用于需要展示所有候选人分数的场景。
        
        参数:
            candidates: 候选人名称列表
            game_state: 游戏状态字典
            player_profiles: 玩家档案字典（可选）
        
        返回:
            候选人分数字典，格式：
            {
                'No.1': {
                    'trust_score': 75.0,
                    'werewolf_probability': 25.0,
                    'final_score': 60.0
                },
                'No.2': {...}
            }
        
        示例:
            >>> agent = DecisionAgent()
            >>> scores = agent.get_candidate_scores(
            ...     candidates=['No.1', 'No.2'],
            ...     game_state={...},
            ...     player_profiles={...}
            ... )
            >>> for candidate, score_details in scores.items():
            ...     print(f"{candidate}: {score_details['final_score']}")
        
        验证需求：AC-1.2.4
        """
        try:
            # 构建输入字典
            raw_input = {
                'candidates': {
                    'candidates': [{'name': name} for name in candidates]
                },
                'game_state': game_state,
                'player_profiles': player_profiles or {}
            }
            
            # 调用完整的决策流程
            result = self.make_decision(raw_input)
            
            # 返回分数详情
            if result['success']:
                return result['scores']
            else:
                logger.error(f"获取候选人分数失败: {result.get('error')}")
                return {}
                
        except Exception as e:
            logger.error(f"获取候选人分数过程中发生错误: {e}", exc_info=True)
            return {}
