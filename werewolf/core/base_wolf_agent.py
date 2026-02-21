# -*- coding: utf-8 -*-
"""
BaseWolfAgent - 狼人阵营基类

提供所有狼人角色的共享功能：
- 双模型架构（分析模型 + 生成模型）
- LLM检测系统（检测好人的指令注入）
- 队友智商评估
- 威胁等级分析
- 可突破值计算
- 卖队友战术决策
- ML增强

子类只需实现角色特有功能
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import json
import re
from agent_build_sdk.sdk.role_agent import BasicRoleAgent
from agent_build_sdk.utils.logger import logger
from werewolf.core.base_wolf_config import BaseWolfConfig

# ML Enhancement Integration
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ml_agent import LightweightMLAgent
    ML_AGENT_AVAILABLE = True
except ImportError as e:
    ML_AGENT_AVAILABLE = False
    logger.warning(f"ML agent not available: {e}")


class BaseWolfAgent(BasicRoleAgent):
    """
    狼人阵营基类
    
    所有狼人角色（狼人、狼王）都应该继承此类
    
    职责:
    1. 提供共享的双模型架构
    2. 提供共享的LLM检测系统（检测好人注入）
    3. 提供共享的队友智商评估
    4. 提供共享的威胁等级分析
    5. 提供共享的击杀和投票决策
    6. 提供共享的卖队友战术
    
    子类职责:
    1. 覆盖 _init_memory_variables() 添加角色特有的内存变量
    2. 实现 _init_specific_components() 初始化角色特有组件
    3. 实现角色特有的技能方法（如狼王的开枪）
    
    Attributes:
        config: 配置对象
        analysis_client: 分析专用LLM客户端
        analysis_model_name: 分析模型名称
        generation_model_name: 生成模型名称
        ml_agent: ML代理
        ml_enabled: ML是否启用
        injection_detector: 注入检测器（检测好人注入）
        speech_quality_evaluator: 发言质量评估器
    """
    
    # 常量定义
    DEFAULT_INTELLIGENCE_SCORE = 50
    DEFAULT_THREAT_LEVEL = 50
    DEFAULT_BREAKTHROUGH_VALUE = 50
    
    def __init__(self, role: str, model_name: str, analysis_model_name: str = None):
        """
        初始化狼人基类
        
        Args:
            role: 角色名称（如ROLE_WOLF, ROLE_WOLF_KING等）
            model_name: LLM模型名称（用于生成发言）
            analysis_model_name: 分析模型名称（用于分析消息），如果为None则从环境变量读取
        """
        super().__init__(role, model_name=model_name)
        
        # 双模型架构
        self.generation_model_name = model_name
        self.analysis_model_name = (
            analysis_model_name or 
            os.getenv('DETECTION_MODEL_NAME') or 
            model_name
        )
        
        # 配置（子类可以覆盖为角色特有配置）
        self.config = BaseWolfConfig()
        
        # 初始化内存变量（子类可以覆盖扩展）
        self._init_memory_variables()
        
        # 初始化双模型架构
        self.analysis_client = self._init_analysis_client()
        
        # 初始化ML增强
        self.ml_agent = None
        self.ml_enabled = False
        self._init_ml_enhancement()
        
        # 初始化共享组件
        self._init_shared_components()
        
        # 初始化角色特有组件（钩子方法，由子类实现）
        self._init_specific_components()
        
        logger.info(f"✓ {role} agent initialized with BaseWolfAgent")
        logger.info(f"  - Analysis model: {self.analysis_model_name}")
        logger.info(f"  - Generation model: {self.generation_model_name}")
    
    # ==================== 初始化方法 ====================
    
    def _init_memory_variables(self):
        """
        初始化内存变量
        
        子类可以覆盖此方法来添加角色特有的内存变量
        覆盖时应该先调用 super()._init_memory_variables()
        """
        memory_vars = {
            "teammates": [],
            "teammate_intelligence": {},
            "threat_levels": {},
            "breakthrough_values": {},
            "identified_roles": {},
            "voting_history": {},
            "voting_results": {},
            "speech_quality": {},
            "injection_attempts": {},
            "wolves_eliminated": 0,
            "good_players_eliminated": 0,
            "current_night": 0,
            "current_day": 0,
            "game_data_collected": [],
            "game_result": None,
        }
        
        for key, value in memory_vars.items():
            self.memory.set_variable(key, value)
    
    def _init_analysis_client(self) -> Optional[Any]:
        """
        初始化分析客户端
        
        Returns:
            分析客户端，如果初始化失败则返回None
        """
        # 如果分析模型与生成模型相同，不需要独立客户端
        if self.analysis_model_name == self.generation_model_name:
            logger.info("Analysis model same as generation model, using shared client")
            return None
        
        try:
            from openai import OpenAI
            
            # 获取检测模型的API配置
            detection_api_key = os.getenv('DETECTION_API_KEY') or os.getenv('OPENAI_API_KEY')
            detection_base_url = os.getenv('DETECTION_BASE_URL') or os.getenv('OPENAI_BASE_URL')
            
            if detection_api_key and detection_base_url:
                analysis_client = OpenAI(
                    api_key=detection_api_key,
                    base_url=detection_base_url
                )
                logger.info(f"✓ Analysis LLM client initialized")
                return analysis_client
            else:
                logger.warning("Detection API not configured, using shared client")
                return None
        except Exception as e:
            logger.warning(f"Failed to initialize analysis client: {e}")
            return None
    
    def _init_ml_enhancement(self):
        """
        初始化ML增强系统
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
        - LLM检测器（检测好人的指令注入）
        - 发言质量评估器
        """
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
        
        try:
            from werewolf.core.llm_detectors import create_llm_detectors
            
            # 创建LLM检测器
            detectors = create_llm_detectors(self.analysis_client, self.analysis_model_name)
            
            self.injection_detector = detectors['injection']
            self.speech_quality_evaluator = detectors['speech_quality']
            
            logger.info("✓ LLM检测器已初始化（检测好人注入）")
        except ImportError as e:
            logger.error(f"✗ 无法导入LLM检测器: {e}")
            self.injection_detector = None
            self.speech_quality_evaluator = None
        except KeyError as e:
            logger.error(f"✗ LLM检测器缺少必要组件: {e}")
            self.injection_detector = None
            self.speech_quality_evaluator = None
        except Exception as e:
            logger.error(f"✗ LLM检测器初始化失败: {e}", exc_info=True)
            self.injection_detector = None
            self.speech_quality_evaluator = None
    
    def _init_specific_components(self):
        """
        初始化角色特有组件（钩子方法）
        
        子类应该覆盖此方法来初始化角色特有的组件
        """
        pass
    
    # ==================== 共享方法 ====================
    
    def _process_player_message(self, message: str, player_name: str):
        """
        处理玩家消息（共享逻辑）- 使用LLM检测器
        
        包括：
        - 注入检测（检测好人试图操控狼人）
        - 发言质量评估
        - 队友智商评估 / 好人威胁评估
        
        Args:
            message: 玩家消息
            player_name: 玩家名称
        """
        if not message or not player_name:
            return
        
        teammates = self.memory.load_variable("teammates") or []
        
        # 1. 注入检测（检测好人试图操控狼人）
        if self.injection_detector:
            try:
                result = self.injection_detector.detect(message)
                
                if result.get('detected', False):
                    injection_type = result.get('type', 'NONE')
                    confidence = result.get('confidence', 0.0)
                    reason = result.get('reason', '')
                    
                    # 记录注入尝试
                    injection_attempts = self.memory.load_variable("injection_attempts") or {}
                    if player_name not in injection_attempts:
                        injection_attempts[player_name] = []
                    injection_attempts[player_name].append({
                        'type': injection_type,
                        'confidence': confidence,
                        'reason': reason
                    })
                    self.memory.set_variable("injection_attempts", injection_attempts)
                    
                    logger.warning(f"[LLM注入检测] {player_name}: {injection_type} (置信度: {confidence:.2f})")
                    
            except Exception as e:
                logger.error(f"LLM注入检测失败 for {player_name}: {e}")
        
        # 2. 发言质量评估
        quality = self._analyze_speech_quality(message)
        speech_quality = self.memory.load_variable("speech_quality") or {}
        speech_quality[player_name] = quality
        self.memory.set_variable("speech_quality", speech_quality)
        
        # 3. 根据是否是队友进行不同的评估
        if player_name in teammates:
            self._evaluate_teammate_intelligence(player_name, message, quality)
        else:
            self._evaluate_good_player(player_name, message, quality)
    
    def _analyze_speech_quality(self, message: str) -> int:
        """
        分析发言质量 - 使用LLM分析模型
        
        Args:
            message: 发言内容
            
        Returns:
            质量分数 (0-100)
        """
        # 使用LLM发言质量评估器
        if self.speech_quality_evaluator:
            try:
                result = self.speech_quality_evaluator.evaluate(message)
                overall_score = result.get('overall_score', 50)
                return overall_score
            except Exception as e:
                logger.debug(f"LLM质量评估失败: {e}")
        
        # 后备方案：简化的启发式评估
        quality = self.DEFAULT_INTELLIGENCE_SCORE
        length = len(message)
        
        if 100 <= length <= 300:
            quality += 10
        elif length < 50:
            quality -= 10
        
        return max(0, min(100, quality))
    
    def _evaluate_teammate_intelligence(self, teammate: str, message: str, quality: int):
        """
        评估队友智商
        
        Args:
            teammate: 队友名称
            message: 发言内容
            quality: 发言质量分数
        """
        intelligence = self.memory.load_variable("teammate_intelligence") or {}
        
        # 初始化智商分数
        if teammate not in intelligence:
            intelligence[teammate] = self.DEFAULT_INTELLIGENCE_SCORE
        
        # 根据发言质量调整智商
        if quality >= 70:
            delta = 5
        elif quality < 30:
            delta = -5
        else:
            delta = 0
        
        if delta != 0:
            current = intelligence[teammate]
            new_score = max(0, min(100, current + delta))
            intelligence[teammate] = new_score
            self.memory.set_variable("teammate_intelligence", intelligence)
            
            logger.debug(f"[TEAMMATE] {teammate} intelligence: {current} -> {new_score} (quality: {quality})")
    
    def _evaluate_good_player(self, player: str, message: str, quality: int):
        """
        评估好人玩家
        
        根据发言质量调整威胁等级和可突破值
        
        Args:
            player: 玩家名称
            message: 发言内容
            quality: 发言质量分数
        """
        threat_levels = self.memory.load_variable("threat_levels") or {}
        breakthrough_values = self.memory.load_variable("breakthrough_values") or {}
        
        # 初始化分数
        if player not in threat_levels:
            threat_levels[player] = self.DEFAULT_THREAT_LEVEL
        if player not in breakthrough_values:
            breakthrough_values[player] = self.DEFAULT_BREAKTHROUGH_VALUE
        
        # 根据发言质量调整
        if quality >= 70:
            # 高质量发言：威胁增加，可突破值降低
            threat_levels[player] = min(100, threat_levels[player] + 5)
            breakthrough_values[player] = max(0, breakthrough_values[player] - 5)
        elif quality < 30:
            # 低质量发言：威胁降低，可突破值增加
            threat_levels[player] = max(0, threat_levels[player] - 5)
            breakthrough_values[player] = min(100, breakthrough_values[player] + 5)
        
        self.memory.set_variable("threat_levels", threat_levels)
        self.memory.set_variable("breakthrough_values", breakthrough_values)
    
    def _should_betray_teammate(self, teammate: str) -> Tuple[bool, str]:
        """
        判断是否应该卖队友
        
        策略：
        1. 队友智商极低（< BETRAY_TEAMMATE_THRESHOLD）
        2. 卖队友可以获得信任
        3. 游戏后期需要保护自己
        
        Args:
            teammate: 队友名称
            
        Returns:
            (是否卖队友, 原因)
        """
        # 检查配置是否启用卖队友策略
        if not getattr(self.config, 'BETRAY_ENABLED', True):
            return (False, "卖队友策略未启用")
        
        intelligence = self.memory.load_variable("teammate_intelligence") or {}
        teammate_iq = intelligence.get(teammate, self.DEFAULT_INTELLIGENCE_SCORE)
        
        # 策略1：队友智商极低
        if teammate_iq < self.config.BETRAY_TEAMMATE_THRESHOLD:
            return (True, f"队友智商极低({teammate_iq})，卖掉可获得信任")
        
        # 策略2：游戏后期，队友已暴露
        identified_roles = self.memory.load_variable("identified_roles") or {}
        if identified_roles.get(teammate) == "wolf":
            current_day = self.memory.load_variable("current_day") or 0
            if current_day >= 4:
                return (True, f"队友已暴露且游戏后期(Day {current_day})，卖掉保护自己")
        
        return (False, "队友表现正常，不卖")
    
    def _make_kill_decision(self, candidates: List[str]) -> str:
        """
        击杀决策（共享逻辑）
        
        策略：
        1. 优先击杀高威胁神职（预言家、女巫）
        2. 考虑可突破值
        3. ML增强预测
        
        Args:
            candidates: 候选人列表
            
        Returns:
            目标玩家名称
        """
        if not candidates:
            return ""
        
        teammates = self.memory.load_variable("teammates") or []
        # 过滤掉队友
        non_teammates = [c for c in candidates if c not in teammates]
        
        if not non_teammates:
            return candidates[0] if candidates else ""
        
        # 计算每个候选人的击杀分数
        scores = {}
        threat_levels = self.memory.load_variable("threat_levels") or {}
        breakthrough_values = self.memory.load_variable("breakthrough_values") or {}
        identified_roles = self.memory.load_variable("identified_roles") or {}
        
        for candidate in non_teammates:
            base_threat = threat_levels.get(candidate, self.DEFAULT_THREAT_LEVEL)
            breakthrough = breakthrough_values.get(candidate, self.DEFAULT_BREAKTHROUGH_VALUE)
            role = identified_roles.get(candidate, "unknown")
            
            # 角色威胁加成
            role_bonus = self._get_role_threat_bonus(role)
            
            # 综合分数（确保数值有效）
            try:
                score = float(base_threat) + float(role_bonus) - (float(breakthrough) * 0.3)
            except (ValueError, TypeError) as e:
                logger.warning(f"计算击杀分数失败 for {candidate}: {e}, 使用默认值")
                score = 50.0
            
            scores[candidate] = score
        
        if not scores:
            return non_teammates[0] if non_teammates else ""
        
        # 选择最高分
        target = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(f"[KILL] Target: {target}, Score: {scores[target]:.1f}")
        
        return target
    
    def _get_role_threat_bonus(self, role: str) -> int:
        """
        获取角色威胁加成
        
        Args:
            role: 角色类型
            
        Returns:
            威胁加成分数
        """
        role_bonuses = {
            "seer": 40,
            "likely_seer": 35,
            "witch": 35,
            "guard": 30,
            "strong_villager": 20,
            "hunter": 10,
        }
        return role_bonuses.get(role, 0)
    
    def _make_vote_decision(self, candidates: List[str]) -> str:
        """
        投票决策（共享逻辑）
        
        策略：
        1. 检查是否应该卖队友
        2. 否则投威胁最低的好人
        3. 保护队友
        
        Args:
            candidates: 候选人列表
            
        Returns:
            投票目标
        """
        if not candidates:
            return ""
        
        teammates = self.memory.load_variable("teammates") or []
        
        # 检查是否有队友在候选人中
        teammate_candidates = [c for c in candidates if c in teammates]
        
        if teammate_candidates:
            # 检查是否应该卖队友
            for teammate in teammate_candidates:
                should_betray, reason = self._should_betray_teammate(teammate)
                if should_betray:
                    logger.info(f"[VOTE] 卖队友: {teammate}, 原因: {reason}")
                    return teammate
        
        # 否则投威胁最低的好人
        non_teammates = [c for c in candidates if c not in teammates]
        if not non_teammates:
            return candidates[0]
        
        threat_levels = self.memory.load_variable("threat_levels") or {}
        scores = {}
        for c in non_teammates:
            try:
                scores[c] = float(threat_levels.get(c, self.DEFAULT_THREAT_LEVEL))
            except (ValueError, TypeError) as e:
                logger.warning(f"威胁等级转换失败 for {c}: {e}, 使用默认值")
                scores[c] = float(self.DEFAULT_THREAT_LEVEL)
        
        if not scores:
            return non_teammates[0]
        
        target = min(scores.items(), key=lambda x: x[1])[0]
        
        logger.info(f"[VOTE] Target: {target}, Threat: {scores[target]}")
        return target
    
    def _extract_teammates(self, history: List[str]) -> List[str]:
        """
        从历史消息中提取队友信息
        
        Args:
            history: 历史消息列表
            
        Returns:
            队友名称列表
        """
        teammates = []
        
        # 只检查前20条消息（游戏开始时的信息）
        for msg in history[:20]:
            if "Your teammates are" in msg or "你的队友是" in msg:
                # 提取队友编号
                matches = re.findall(r'No\.(\d+)', msg)
                teammates = [f"No.{m}" for m in matches]
                logger.info(f"Extracted teammates: {teammates}")
                break
        
        return teammates
    
    # ==================== 工具方法 ====================
    
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
        
        return text[:max_length - 3] + "..."
    
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
        
        cleaned = output.strip()
        
        # 尝试在输出中找到有效选项
        for choice in valid_choices:
            if choice in cleaned:
                return choice
        
        logger.warning(f"Invalid player name: {output}, using fallback: {valid_choices[0]}")
        return valid_choices[0]
    
    def _llm_analyze(self, prompt: str, temperature: float = 0.1) -> str:
        """
        使用分析模型进行推理分析
        
        Args:
            prompt: 分析提示词
            temperature: 温度参数
        
        Returns:
            分析结果文本
        """
        if not self.analysis_client:
            return self.llm_caller(prompt)
        
        try:
            response = self.analysis_client.chat.completions.create(
                model=self.analysis_model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return self.llm_caller(prompt)
    
    def _llm_generate(self, prompt: str, temperature: float = 0.7) -> str:
        """
        使用生成模型生成发言
        
        Args:
            prompt: 生成提示词
            temperature: 温度参数
        
        Returns:
            生成的发言文本
        """
        return self.llm_caller(prompt)
