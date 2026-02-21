"""
BaseGoodAgent - 好人阵营基类

提供所有好人角色的共享功能：
- ML增强
- 检测系统（注入检测、虚假引用检测、消息解析、发言质量评估）
- 分析系统（信任分数管理、投票模式分析、游戏阶段分析）
- 决策系统（投票决策、警长选举决策、警长投票决策）
- 工具方法

子类只需实现角色特有功能
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import json
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_good_config import BaseGoodConfig

# ML Enhancement Integration
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class BaseGoodAgent(BasicRoleAgent):
    """
    好人阵营基类
    
    所有好人角色（平民、预言家、女巫、守卫、猎人）都应该继承此类
    
    职责:
    1. 提供共享的ML增强功能
    2. 提供共享的检测系统
    3. 提供共享的分析系统
    4. 提供共享的决策系统
    5. 提供共享的工具方法
    
    子类职责:
    1. 覆盖 _init_memory_variables() 添加角色特有的内存变量
    2. 实现 _init_specific_components() 初始化角色特有组件
    3. 实现角色特有的技能方法（如预言家的验人、女巫的药水等）
    
    Attributes:
        config: 配置对象
        detection_client: 检测专用LLM客户端
        detection_model: 检测模型名称
        ml_agent: ML代理
        ml_enabled: ML是否启用
        injection_detector: 注入检测器
        false_quote_detector: 虚假引用检测器
        message_parser: 消息解析器
        speech_quality_evaluator: 发言质量评估器
        trust_score_manager: 信任分数管理器
        trust_score_calculator: 信任分数计算器
        voting_pattern_analyzer: 投票模式分析器
        game_phase_analyzer: 游戏阶段分析器
        vote_decision_maker: 投票决策器
        sheriff_election_decision_maker: 警长选举决策器
        sheriff_vote_decision_maker: 警长投票决策器
    """
    
    def __init__(self, role: str, model_name: str):
        """
        初始化好人基类
        
        Args:
            role: 角色名称（如ROLE_VILLAGER, ROLE_SEER等）
            model_name: LLM模型名称
        """
        super().__init__(role, model_name=model_name)
        
        # 配置（子类可以覆盖为角色特有配置）
        self.config = BaseGoodConfig()
        
        # 初始化内存变量（子类可以覆盖扩展）
        self._init_memory_variables()
        
        # 初始化双模型架构（在super().__init__之后，self.client已经存在）
        self.detection_client, self.detection_model = self._init_detection_client()
        
        # 初始化ML增强
        self.ml_agent = None
        self.ml_enabled = False
        self._init_ml_enhancement()
        
        # 初始化共享组件
        self._init_shared_components()
        
        # 初始化角色特有组件（钩子方法，由子类实现）
        self._init_specific_components()
        
        logger.info(f"✓ {role} agent initialized with BaseGoodAgent")
    
    # ==================== 初始化方法 ====================
    
    def _init_memory_variables(self):
        """
        初始化内存变量
        
        子类可以覆盖此方法来添加角色特有的内存变量
        覆盖时应该先调用 super()._init_memory_variables()
        """
        self.memory.set_variable("player_data", {})
        self.memory.set_variable("game_state", {})
        self.memory.set_variable("seer_checks", {})
        self.memory.set_variable("voting_results", {})
        self.memory.set_variable("trust_scores", {})
        self.memory.set_variable("voting_history", {})
        self.memory.set_variable("speech_history", {})
        self.memory.set_variable("all_players", [])
        self.memory.set_variable("alive_players", [])
        self.memory.set_variable("dead_players", [])
        self.memory.set_variable("game_data_collected", [])
        self.memory.set_variable("game_result", None)
        self.memory.set_variable("giving_last_words", False)
        self.memory.set_variable("sheriff", None)
    
    def _init_detection_client(self) -> Tuple[Optional[Any], str]:
        """
        初始化双模型架构
        
        - 分析模型: 用于消息分析、检测、推理（DeepSeek Reasoner）
        - 生成模型: 用于发言生成（DeepSeek Chat）
        
        Returns:
            (detection_client, detection_model_name) 元组
        """
        detection_model = os.getenv('DETECTION_MODEL_NAME')
        
        if not detection_model:
            logger.warning("⚠️ 未配置DETECTION_MODEL_NAME，将使用主模型进行分析")
            return (getattr(self, 'client', None), self.model_name)
        
        try:
            from openai import OpenAI
            
            # 优先使用检测专用配置，否则回退到主模型配置
            api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if not api_key or not base_url:
                logger.warning("⚠️ 检测模型API未配置，将使用主模型")
                return (getattr(self, 'client', None), self.model_name)
            
            # 创建检测专用客户端
            detection_client = OpenAI(api_key=api_key, base_url=base_url)
            
            logger.info("✓ 双模型架构已初始化")
            logger.info(f"  - 生成模型: {self.model_name} (用于发言生成)")
            logger.info(f"  - 分析模型: {detection_model} (用于消息分析)")
            logger.info(f"  - API地址: {base_url}")
            
            return (detection_client, detection_model)
            
        except Exception as e:
            logger.error(f"✗ 初始化分析模型失败: {e}")
            return (getattr(self, 'client', None), self.model_name)
    
    def _init_ml_enhancement(self):
        """
        初始化ML增强系统
        
        包括：
        - LightweightMLAgent
        - 增量学习系统
        
        如果初始化失败，系统将降级运行（不影响游戏）
        """
        if not ML_AGENT_AVAILABLE:
            logger.info("ML enhancement disabled - module not available")
            return
        
        try:
            model_dir = os.getenv('ML_MODEL_DIR', './ml_models')
            self.ml_agent = LightweightMLAgent(model_dir=model_dir)
            self.ml_enabled = self.ml_agent.enabled
            
            if self.ml_enabled:
                logger.info(f"✓ ML enhancement enabled for {self.role}")
                
                # 初始化增量学习系统
                try:
                    from incremental_learning import IncrementalLearningSystem
                    from game_end_handler import set_learning_system
                    
                    retrain_interval = int(os.getenv('ML_TRAIN_INTERVAL', str(self.config.ML_RETRAIN_INTERVAL)))
                    learning_system = IncrementalLearningSystem(self.ml_agent, retrain_interval)
                    set_learning_system(learning_system)
                    
                    logger.info(f"✓ Incremental learning enabled (retrain every {retrain_interval} games)")
                except Exception as e:
                    logger.warning(f"⚠ Incremental learning not available: {e}")
            else:
                logger.info(f"⚠ ML enhancement initialized but not enabled for {self.role}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize ML enhancement: {e}")
            self.ml_agent = None
            self.ml_enabled = False
    
    def _init_shared_components(self):
        """
        初始化共享组件
        
        包括：
        - 增强决策引擎（阶段五新增）
        - LLM检测器（使用新的llm_detectors模块）
        - 分析器（TrustScoreManager, TrustScoreCalculator, VotingPatternAnalyzer, GamePhaseAnalyzer）
        - 决策器（VoteDecisionMaker, SheriffElectionDecisionMaker, SheriffVoteDecisionMaker）
        
        每个组件初始化失败时会记录警告，但不会中断整体初始化
        """
        from werewolf.common.utils import CacheManager
        
        # 缓存管理器
        try:
            self.cache_manager = CacheManager()
        except Exception as e:
            logger.warning(f"Failed to initialize cache manager: {e}")
            self.cache_manager = None
        
        # 增强决策引擎（阶段五新增）
        try:
            from werewolf.core.decision_engine import EnhancedDecisionEngine
            
            self.enhanced_decision_engine = EnhancedDecisionEngine(self.ml_agent)
            logger.info("✓ 增强决策引擎已初始化（阶段五优化）")
        except ImportError as e:
            logger.error(f"✗ 无法导入增强决策引擎: {e}")
            self.enhanced_decision_engine = None
        except (ValueError, TypeError) as e:
            logger.error(f"✗ 增强决策引擎初始化参数错误: {e}")
            self.enhanced_decision_engine = None
        except Exception as e:
            logger.error(f"✗ 增强决策引擎初始化失败: {e}", exc_info=True)
            self.enhanced_decision_engine = None
        
        # LLM检测器 - 使用新的llm_detectors模块（替代硬编码规则）
        try:
            from werewolf.core.llm_detectors import create_llm_detectors
            
            # 创建所有LLM检测器
            detectors = create_llm_detectors(self.detection_client, self.detection_model)
            
            self.injection_detector = detectors['injection']
            self.false_quote_detector = detectors['false_quote']
            self.speech_quality_evaluator = detectors['speech_quality']
            self.message_parser = detectors['message_parser']
            
            logger.info("✓ LLM检测器已初始化（舍弃硬编码规则）")
        except ImportError as e:
            logger.error(f"✗ 无法导入LLM检测器: {e}")
            self._init_fallback_detectors()
        except KeyError as e:
            logger.error(f"✗ LLM检测器缺少必要组件: {e}")
            self._init_fallback_detectors()
        except Exception as e:
            logger.error(f"✗ LLM检测器初始化失败: {e}", exc_info=True)
            self._init_fallback_detectors()
    
    def _init_fallback_detectors(self):
        """初始化降级检测器"""
        try:
            from werewolf.villager.detectors import (
                InjectionDetector, FalseQuoteDetector, 
                MessageParser, SpeechQualityEvaluator
            )
            
            self.injection_detector = InjectionDetector(self.config, self.detection_client)
            self.false_quote_detector = FalseQuoteDetector(self.config, self.detection_client)
            self.message_parser = MessageParser(self.config, self.detection_client)
            self.speech_quality_evaluator = SpeechQualityEvaluator(self.config, self.detection_client)
            
            logger.warning("⚠ 使用旧版检测器（降级模式）")
        except Exception as e2:
            logger.error(f"✗ 降级检测器初始化也失败: {e2}")
            self.injection_detector = None
            self.false_quote_detector = None
            self.message_parser = None
            self.speech_quality_evaluator = None
        
        # 分析器 - 使用平民的实现作为默认实现
        try:
            from werewolf.villager.analyzers import (
                TrustScoreManager, TrustScoreCalculator,
                VotingPatternAnalyzer, GamePhaseAnalyzer
            )
            
            self.trust_score_manager = TrustScoreManager(self.config)
            self.trust_score_calculator = TrustScoreCalculator(self.config)
            self.voting_pattern_analyzer = VotingPatternAnalyzer(self.config)
            self.game_phase_analyzer = GamePhaseAnalyzer(self.config)
            
            logger.info("✓ Analyzers initialized")
        except ImportError as e:
            logger.error(f"✗ 无法导入分析器: {e}")
            self.trust_score_manager = None
            self.trust_score_calculator = None
            self.voting_pattern_analyzer = None
            self.game_phase_analyzer = None
        except (ValueError, TypeError) as e:
            logger.error(f"✗ 分析器初始化参数错误: {e}")
            self.trust_score_manager = None
            self.trust_score_calculator = None
            self.voting_pattern_analyzer = None
            self.game_phase_analyzer = None
        except Exception as e:
            logger.error(f"✗ 分析器初始化失败: {e}", exc_info=True)
            self.trust_score_manager = None
            self.trust_score_calculator = None
            self.voting_pattern_analyzer = None
            self.game_phase_analyzer = None
        
        # 决策器 - 使用平民的实现作为默认实现
        try:
            from werewolf.villager.decision_makers import (
                VoteDecisionMaker, SheriffElectionDecisionMaker,
                SheriffVoteDecisionMaker
            )
            
            self.vote_decision_maker = VoteDecisionMaker(
                self.config, self.trust_score_calculator, self.voting_pattern_analyzer
            )
            self.sheriff_election_decision_maker = SheriffElectionDecisionMaker(self.config)
            self.sheriff_vote_decision_maker = SheriffVoteDecisionMaker(
                self.config, self.trust_score_calculator
            )
            
            logger.info("✓ Decision makers initialized")
        except ImportError as e:
            logger.error(f"✗ 无法导入决策器: {e}")
            self.vote_decision_maker = None
            self.sheriff_election_decision_maker = None
            self.sheriff_vote_decision_maker = None
        except (ValueError, TypeError) as e:
            logger.error(f"✗ 决策器初始化参数错误: {e}")
            self.vote_decision_maker = None
            self.sheriff_election_decision_maker = None
            self.sheriff_vote_decision_maker = None
        except Exception as e:
            logger.error(f"✗ 决策器初始化失败: {e}", exc_info=True)
            self.vote_decision_maker = None
            self.sheriff_election_decision_maker = None
            self.sheriff_vote_decision_maker = None
    
    def _init_specific_components(self):
        """
        初始化角色特有组件（钩子方法）
        
        子类应该覆盖此方法来初始化角色特有的组件
        例如：
        - 预言家：CheckDecisionMaker, CheckPriorityCalculator
        - 女巫：PotionManager, SaveDecisionMaker, PoisonDecisionMaker
        - 守卫：ProtectDecisionMaker, ProtectValidator
        - 猎人：ShootDecisionMaker, ThreatAnalyzer, WolfProbCalculator
        - 平民：无特有组件（可以不覆盖）
        """
        pass
    
    # ==================== 共享方法 ====================
    
    def _process_player_message(self, message: str, player_name: str):
        """
        处理玩家消息（共享逻辑）- 使用LLM检测器
        
        包括：
        - 注入检测（LLM驱动）
        - 虚假引用检测（LLM驱动）
        - 消息解析（LLM驱动）
        - 发言质量评估（LLM驱动）
        - 更新信任分数
        
        Args:
            message: 玩家消息
            player_name: 玩家名称
        """
        player_data = self.memory.load_variable("player_data")
        if player_name not in player_data:
            player_data[player_name] = {}
        
        # 1. 注入检测（使用LLM）
        if self.injection_detector:
            try:
                result = self.injection_detector.detect(message)
                
                if result.get('detected', False):
                    injection_type = result.get('type', 'NONE')
                    confidence = result.get('confidence', 0.0)
                    reason = result.get('reason', '')
                    
                    player_data[player_name]["malicious_injection"] = True
                    player_data[player_name]["injection_type"] = injection_type
                    player_data[player_name]["injection_confidence"] = confidence
                    player_data[player_name]["injection_attempts"] = player_data[player_name].get("injection_attempts", 0) + 1
                    
                    # 根据类型计算信任惩罚
                    penalty_map = {
                        'SYSTEM_FAKE': self.config.TRUST_INJECTION_ATTACK_SYSTEM,
                        'STATUS_FAKE': self.config.TRUST_INJECTION_ATTACK_STATUS,
                        'ROLE_FAKE': -30
                    }
                    penalty = penalty_map.get(injection_type, -20)
                    player_data[player_name]["trust_penalty"] = player_data[player_name].get("trust_penalty", 0) + penalty
                    
                    logger.warning(f"[LLM注入检测] {player_name}: {injection_type} (置信度: {confidence:.2f}, 原因: {reason})")
                    
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"LLM注入检测失败 for {player_name}: {e}")
            except Exception as e:
                logger.error(f"LLM注入检测未知错误 for {player_name}: {e}", exc_info=True)
        
        # 2. 虚假引用检测（使用LLM）
        if self.false_quote_detector:
            try:
                history = self.memory.load_history()
                result = self.false_quote_detector.detect(message, history)
                
                if result.get('detected', False):
                    confidence = result.get('confidence', 0.0)
                    
                    if confidence > 0.6:
                        player_data[player_name]["false_quotes"] = player_data[player_name].get("false_quotes", 0) + 1
                        player_data[player_name]["false_quote_confidence"] = confidence
                        player_data[player_name]["trust_penalty"] = player_data[player_name].get("trust_penalty", 0) + self.config.TRUST_FALSE_QUOTATION
                        
                        logger.warning(f"[LLM虚假引用检测] {player_name}: 置信度 {confidence:.2f}")
                        
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"LLM虚假引用检测失败 for {player_name}: {e}")
            except Exception as e:
                logger.error(f"LLM虚假引用检测未知错误 for {player_name}: {e}", exc_info=True)
        
        # 3. 消息解析（使用LLM）
        if self.message_parser:
            try:
                parsed_info = self.message_parser.parse(message, player_name)
                
                # 处理角色声称
                claimed_role = parsed_info.get("claimed_role", "none")
                if claimed_role != "none":
                    player_data[player_name]["claimed_role"] = claimed_role
                    logger.info(f"[LLM消息解析] {player_name} 声称角色: {claimed_role}")
                
                # 处理预言家验证信息
                seer_check = parsed_info.get("seer_check", {})
                if seer_check:
                    checked_player = seer_check.get("player")
                    result = seer_check.get("result")
                    if checked_player and result:
                        seer_checks = self.memory.load_variable("seer_checks")
                        seer_checks[checked_player] = result
                        self.memory.set_variable("seer_checks", seer_checks)
                        logger.info(f"[LLM消息解析] 预言家验证: {checked_player} = {result}")
                
                # 处理支持/怀疑关系
                for supported_player in parsed_info.get("supports", []):
                    if supported_player not in player_data:
                        player_data[supported_player] = {}
                    if "supported_by" not in player_data[supported_player]:
                        player_data[supported_player]["supported_by"] = []
                    if player_name not in player_data[supported_player]["supported_by"]:
                        player_data[supported_player]["supported_by"].append(player_name)
                
                for suspected_player in parsed_info.get("suspects", []):
                    if suspected_player not in player_data:
                        player_data[suspected_player] = {}
                    if "suspected_by" not in player_data[suspected_player]:
                        player_data[suspected_player]["suspected_by"] = []
                    if player_name not in player_data[suspected_player]["suspected_by"]:
                        player_data[suspected_player]["suspected_by"].append(player_name)
                
                # 处理投票意向
                vote_intention = parsed_info.get("vote_intention", "")
                if vote_intention:
                    player_data[player_name]["vote_intention"] = vote_intention
                    logger.info(f"[LLM消息解析] {player_name} 投票意向: {vote_intention}")
                    
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"LLM消息解析失败 for {player_name}: {e}")
            except Exception as e:
                logger.error(f"LLM消息解析未知错误 for {player_name}: {e}", exc_info=True)
        
        # 4. 发言质量评估（使用LLM）
        if self.speech_quality_evaluator and len(message) >= 50:
            try:
                result = self.speech_quality_evaluator.evaluate(message)
                
                overall_score = result.get('overall_score', 50)
                player_data[player_name]["speech_quality"] = overall_score
                player_data[player_name]["llm_analysis"] = {
                    'logic_score': result.get('logic_score', 50),
                    'information_score': result.get('information_score', 50),
                    'persuasion_score': result.get('persuasion_score', 50),
                    'strategy_score': result.get('strategy_score', 50),
                }
                
                if overall_score >= 70:
                    player_data[player_name]["logical_speech"] = True
                    logger.info(f"[LLM质量评估] {player_name}: 高质量发言 ({overall_score}分)")
                elif overall_score < 30:
                    player_data[player_name]["low_quality_speech"] = True
                    logger.info(f"[LLM质量评估] {player_name}: 低质量发言 ({overall_score}分)")
                    
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"LLM发言质量评估失败 for {player_name}: {e}")
            except Exception as e:
                logger.error(f"LLM发言质量评估未知错误 for {player_name}: {e}", exc_info=True)
        
        self.memory.set_variable("player_data", player_data)
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """
        投票决策（共享逻辑 - 阶段五优化版）
        
        使用增强决策引擎：
        1. 复杂决策树（非线性、多维度、阈值判断）
        2. 贝叶斯推理
        3. 动态ML融合（根据置信度和游戏阶段调整）
        
        Args:
            candidates: 候选人列表
            
        Returns:
            投票目标
        """
        if not candidates:
            return ""
        
        context = self._build_context()
        
        # 使用增强决策引擎
        if hasattr(self, 'enhanced_decision_engine') and self.enhanced_decision_engine:
            try:
                # 判断游戏阶段
                current_day = context.get('current_day', 1)
                total_players = context.get('total_players', 12)
                alive_players = context.get('alive_players', total_players)
                
                if current_day <= 2:
                    game_phase = 'early'
                elif alive_players <= 5:
                    game_phase = 'endgame'
                else:
                    game_phase = 'midgame'
                
                # 增强决策
                target, confidence, all_scores = self.enhanced_decision_engine.decide_vote(
                    candidates, context, game_phase
                )
                
                logger.info(f"[ENHANCED DECISION] Target: {target}, Confidence: {confidence:.2f}, Phase: {game_phase}")
                logger.info(f"[ENHANCED DECISION] All scores: {all_scores}")
                
                return target
                
            except Exception as e:
                logger.error(f"Enhanced decision failed: {e}, using fallback")
                return self._fallback_vote_decision(candidates)
        
        # 降级：使用旧决策逻辑
        logger.warning("Enhanced decision engine not available, using legacy decision")
        return self._legacy_vote_decision(candidates, context)
    
    def _legacy_vote_decision(self, candidates: List[str], context: Dict) -> str:
        """旧版投票决策（降级使用）"""
        my_name = context.get("my_name", "")
        
        # 使用决策树决定投票目标
        if self.vote_decision_maker:
            try:
                target, reason, vote_scores = self.vote_decision_maker.decide(candidates, my_name, context)
                logger.info(f"[LEGACY VOTE] Target: {target}, Reason: {reason}")
                return target
            except Exception as e:
                logger.error(f"Legacy vote decision failed: {e}")
        
        return self._fallback_vote_decision(candidates)
    
    def _fallback_vote_decision(self, candidates: List[str]) -> str:
        """
        回退投票决策（当决策器失败时使用）
        
        选择信任分数最低的候选人
        
        Args:
            candidates: 候选人列表
            
        Returns:
            投票目标
        """
        if not candidates:
            logger.warning("候选人列表为空，无法做出投票决策")
            return ""
            
        trust_scores = self.memory.load_variable("trust_scores")
        if not trust_scores:
            logger.warning("信任分数为空，返回第一个候选人")
            return candidates[0]
        
        min_trust = float('inf')
        target = candidates[0]
        for candidate in candidates:
            trust = trust_scores.get(candidate, 50)
            if trust < min_trust:
                min_trust = trust
                target = candidate
        return target
    
    def _build_context(self) -> Dict:
        """
        构建决策上下文
        
        Returns:
            包含所有决策所需信息的上下文字典
        """
        return {
            "player_data": self.memory.load_variable("player_data"),
            "game_state": self.memory.load_variable("game_state"),
            "seer_checks": self.memory.load_variable("seer_checks"),
            "voting_results": self.memory.load_variable("voting_results"),
            "trust_scores": self.memory.load_variable("trust_scores"),
            "voting_history": self.memory.load_variable("voting_history"),
            "speech_history": self.memory.load_variable("speech_history"),
            "my_name": self.memory.load_variable("name"),
        }
    
    def _truncate_output(self, text: str, max_length: int = None) -> str:
        """
        截断输出文本
        
        Args:
            text: 原始文本
            max_length: 最大长度（默认使用配置中的MAX_SPEECH_LENGTH）
            
        Returns:
            截断后的文本
        """
        if max_length is None:
            max_length = self.config.MAX_SPEECH_LENGTH
        
        if len(text) <= max_length:
            return text
        
        # 截断到最大长度
        truncated = text[:max_length]
        
        # 尝试在句子结束处截断
        last_period = max(
            truncated.rfind('。'),
            truncated.rfind('.'),
            truncated.rfind('！'),
            truncated.rfind('!')
        )
        
        if last_period > self.config.MIN_SPEECH_LENGTH:
            return truncated[:last_period + 1]
        else:
            return truncated
    
    def _validate_player_name(self, output: str, valid_choices: List[str]) -> str:
        """
        验证玩家名称
        
        如果输出不在有效选择中，返回第一个有效选择
        
        Args:
            output: LLM输出的玩家名称
            valid_choices: 有效的玩家名称列表
            
        Returns:
            验证后的玩家名称
        """
        if not valid_choices:
            logger.error("有效选择列表为空")
            return ""
            
        if output in valid_choices:
            return output
        
        logger.warning(f"LLM output '{output}' not in valid choices: {valid_choices}")
        return valid_choices[0]
    
    def _extract_player_names(self, text: str) -> List[str]:
        """
        从文本中提取玩家名称
        
        Args:
            text: 文本
            
        Returns:
            玩家名称列表
        """
        import re
        players = re.findall(r"No\.\d+", text)
        return list(set(players))  # 去重

    # ==================== LLM调用方法 ====================
    
    def _llm_analyze(self, prompt: str, temperature: float = 0.1) -> str:
        """
        使用分析模型进行推理分析
        
        用于：消息检测、发言质量评估、行为分析等需要精确推理的任务
        
        Args:
            prompt: 分析提示词
            temperature: 温度参数（分析任务使用低温度，默认0.1）
        
        Returns:
            分析结果文本
        """
        if not self.detection_client:
            logger.warning("分析客户端未初始化，使用主模型")
            return self.llm_caller(prompt)
        
        try:
            response = self.detection_client.chat.completions.create(
                model=self.detection_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            # 降级到主模型
            try:
                return self.llm_caller(prompt)
            except:
                return ""
    
    def _llm_generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        使用生成模型生成发言
        
        用于：生成讨论发言、警长演讲、遗言等需要创造性的任务
        
        Args:
            prompt: 生成提示词
            temperature: 温度参数（生成任务使用高温度，默认0.7）
        
        Returns:
            生成的发言文本
        """
        return self.llm_caller(prompt)  # 使用SDK的llm_caller
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        解析LLM返回的JSON响应
        
        Args:
            text: LLM返回的文本（可能包含JSON）
        
        Returns:
            解析后的字典，如果解析失败返回空字典
        """
        try:
            # 尝试直接解析
            return json.loads(text)
        except:
            pass
        
        try:
            # 提取JSON部分
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
        
        return {}

    # ==================== 游戏结束处理 ====================
    
    def _handle_game_end(self, req):
        """
        处理游戏结束 - 收集数据并触发ML训练
        
        Args:
            req: 请求对象
        """
        self.memory.append_history(req.message)
        
        # 1. 收集游戏数据（使用标准化特征提取）
        logger.info("[GAME END] 开始收集游戏数据用于ML训练")
        game_data = self._collect_game_data_with_features(req.message)
        
        # 2. 保存到数据收集器
        try:
            from game_data_collector import GameDataCollector
            collector = GameDataCollector()
            game_id = self.memory.load_variable("game_id") or f"game_{int(__import__('time').time())}"
            collector.collect_game_data(
                game_id=game_id,
                players_data=game_data
            )
            logger.info(f"✓ 游戏数据已保存: {len(game_data)} 个玩家")
        except ImportError as e:
            logger.error(f"无法导入GameDataCollector: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"保存游戏数据参数错误: {e}")
        except Exception as e:
            logger.error(f"保存游戏数据失败: {e}", exc_info=True)
        
        # 3. 触发增量学习
        try:
            from werewolf.incremental_learning import IncrementalLearningSystem
            if hasattr(self, 'ml_agent') and self.ml_agent:
                learning_system = IncrementalLearningSystem(
                    ml_agent=self.ml_agent,
                    retrain_interval=int(os.getenv('ML_TRAIN_INTERVAL', '10'))
                )
                game_id = self.memory.load_variable("game_id")
                result = learning_system.on_game_end(
                    game_id=game_id,
                    players_data=game_data
                )
                logger.info(f"[ML学习] {result}")
        except ImportError as e:
            logger.error(f"无法导入IncrementalLearningSystem: {e}")
        except (ValueError, TypeError) as e:
            logger.error(f"增量学习参数错误: {e}")
        except Exception as e:
            logger.error(f"增量学习失败: {e}", exc_info=True)
        
        # 4. 触发游戏结束处理（兼容旧系统）
        try:
            from werewolf.game_utils import GameEndTrigger
            GameEndTrigger.trigger_game_end(req, self.memory, self.role)
        except Exception as e:
            logger.debug(f"GameEndTrigger失败: {e}")
    
    def _collect_game_data_with_features(self, result_message: str) -> List[Dict]:
        """
        收集游戏数据（使用标准化特征提取）
        
        Args:
            result_message: 游戏结果消息
        
        Returns:
            玩家数据列表 [{'name': 'No.1', 'role': 'wolf', 'data': {...}}, ...]
        """
        from ml_enhanced.feature_extractor import StandardFeatureExtractor
        
        player_data_dict = self.memory.load_variable("player_data")
        context = self._build_context()
        
        game_data = []
        
        for player_name, data in player_data_dict.items():
            if not isinstance(data, dict):
                continue
            
            try:
                # 提取标准化特征
                features = StandardFeatureExtractor.extract_player_features(
                    player_name, data, context
                )
                
                # 转换为ML格式
                ml_features = StandardFeatureExtractor.features_to_ml_format(features)
                
                # 推断角色
                role = self._infer_player_role(player_name, result_message, context)
                
                game_data.append({
                    'name': player_name,
                    'role': role,
                    'data': ml_features,
                    'features': features  # 保留原始特征用于分析
                })
                
                logger.debug(f"收集玩家数据: {player_name} (角色: {role})")
                
            except Exception as e:
                logger.error(f"提取特征失败 for {player_name}: {e}")
                continue
        
        return game_data
    
    def _infer_player_role(
        self, 
        player_name: str, 
        result_message: str, 
        context: Dict
    ) -> str:
        """
        推断玩家角色
        
        优先级：
        1. 预言家验证结果
        2. 角色声称 + 行为验证
        3. 游戏结果推断
        4. unknown
        
        Args:
            player_name: 玩家名称
            result_message: 游戏结果消息
            context: 游戏上下文
        
        Returns:
            角色名称 (wolf/good/seer/witch/guard/hunter/villager/unknown)
        """
        # 1. 从预言家验证获取
        seer_checks = context.get("seer_checks", {})
        if player_name in seer_checks:
            result = seer_checks[player_name]
            if isinstance(result, dict):
                return "wolf" if result.get("is_wolf") else "good"
            elif isinstance(result, str):
                return "wolf" if "wolf" in result.lower() else "good"
        
        # 2. 从角色声称推断（需要行为验证）
        player_data = context.get("player_data", {}).get(player_name, {})
        
        # 预言家：声称+有验人记录
        if player_data.get("claimed_seer"):
            # 检查是否有验人行为
            if context.get("seer_checks"):
                return "seer"
        
        # 女巫：声称+有用药记录
        if player_data.get("claimed_witch"):
            if player_data.get("potion_used"):
                return "witch"
        
        # 守卫：声称+有守护记录
        if player_data.get("claimed_guard"):
            if player_data.get("protect_history"):
                return "guard"
        
        # 猎人：声称+有开枪记录
        if player_data.get("claimed_hunter"):
            if player_data.get("shot_player"):
                return "hunter"
        
        # 3. 从游戏结果推断
        # 解析result_message，查找角色信息
        if player_name in result_message:
            if "wolf" in result_message.lower():
                return "wolf"
            elif "seer" in result_message.lower():
                return "seer"
            elif "witch" in result_message.lower():
                return "witch"
            elif "guard" in result_message.lower():
                return "guard"
            elif "hunter" in result_message.lower():
                return "hunter"
        
        # 4. 默认返回unknown
        return "unknown"
