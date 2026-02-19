"""
数据验证工具类 - 企业级数据验证

遵循企业级标准:
1. 单一职责原则 - 每个验证器只负责一类验证
2. 开闭原则 - 通过继承扩展,不修改现有代码
3. 统一的错误处理和日志记录
4. 完整的类型提示
5. 详细的文档字符串

设计模式:
- 策略模式: 不同的验证策略
- 工厂模式: 创建验证器实例
"""
from typing import Any, List, Dict, Set, Optional, Tuple, Union
from agent_build_sdk.utils.logger import logger


class ValidationResult:
    """
    验证结果封装类
    
    提供统一的验证结果接口
    """
    
    def __init__(self, is_valid: bool, value: Any = None, error_message: str = ""):
        """
        初始化验证结果
        
        Args:
            is_valid: 是否有效
            value: 验证后的值(可能经过清理或转换)
            error_message: 错误信息
        """
        self.is_valid = is_valid
        self.value = value
        self.error_message = error_message
    
    def __bool__(self) -> bool:
        """支持布尔判断"""
        return self.is_valid
    
    def __repr__(self) -> str:
        return f"ValidationResult(valid={self.is_valid}, value={self.value}, error='{self.error_message}')"


class DataValidator:
    """
    数据验证器
    
    提供统一的数据验证接口，减少重复代码
    """
    
    @staticmethod
    def validate_player_name(player: Any, context: str = "") -> bool:
        """
        验证玩家名称
        
        Args:
            player: 玩家名称
            context: 上下文信息（用于日志）
        
        Returns:
            True if valid, False otherwise
        """
        if not player or not isinstance(player, str):
            if context:
                logger.warning(f"[{context}] Invalid player name: {player}")
            return False
        return True
    
    @staticmethod
    def validate_trust_score(score: Any, context: str = "") -> bool:
        """
        验证信任分数
        
        Args:
            score: 信任分数
            context: 上下文信息
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(score, (int, float)):
            if context:
                logger.warning(f"[{context}] Invalid trust score type: {type(score)}")
            return False
        
        if not (0 <= score <= 100):
            if context:
                logger.warning(f"[{context}] Trust score out of range: {score}")
            return False
        
        return True
    
    @staticmethod
    def validate_probability(prob: Any, context: str = "") -> bool:
        """
        验证概率值
        
        Args:
            prob: 概率值
            context: 上下文信息
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(prob, (int, float)):
            if context:
                logger.warning(f"[{context}] Invalid probability type: {type(prob)}")
            return False
        
        if not (0 <= prob <= 1):
            if context:
                logger.warning(f"[{context}] Probability out of range: {prob}")
            return False
        
        return True
    
    @staticmethod
    def validate_dict(data: Any, context: str = "") -> bool:
        """
        验证字典类型
        
        Args:
            data: 数据
            context: 上下文信息
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            if context:
                logger.warning(f"[{context}] Invalid dict type: {type(data)}")
            return False
        return True
    
    @staticmethod
    def validate_list(data: Any, context: str = "", min_length: int = 0) -> bool:
        """
        验证列表类型
        
        Args:
            data: 数据
            context: 上下文信息
            min_length: 最小长度
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, list):
            if context:
                logger.warning(f"[{context}] Invalid list type: {type(data)}")
            return False
        
        if len(data) < min_length:
            if context:
                logger.warning(f"[{context}] List too short: {len(data)} < {min_length}")
            return False
        
        return True
    
    @staticmethod
    def validate_set(data: Any, context: str = "") -> bool:
        """
        验证集合类型
        
        Args:
            data: 数据
            context: 上下文信息
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, set):
            if context:
                logger.warning(f"[{context}] Invalid set type: {type(data)}")
            return False
        return True
    
    @staticmethod
    def validate_confidence(confidence: Any, context: str = "") -> float:
        """
        验证并规范化置信度
        
        Args:
            confidence: 置信度值
            context: 上下文信息
        
        Returns:
            规范化后的置信度（0.0-1.0）
        """
        if not isinstance(confidence, (int, float)):
            if context:
                logger.warning(f"[{context}] Invalid confidence type: {type(confidence)}, using 1.0")
            return 1.0
        
        return max(0.0, min(1.0, float(confidence)))
    
    @staticmethod
    def validate_and_clamp_score(score: Any, min_val: float, max_val: float, 
                                 default: float, context: str = "") -> float:
        """
        验证并限制分数范围
        
        Args:
            score: 分数值
            min_val: 最小值
            max_val: 最大值
            default: 默认值
            context: 上下文信息
        
        Returns:
            限制后的分数
        """
        if not isinstance(score, (int, float)):
            if context:
                logger.warning(f"[{context}] Invalid score type: {type(score)}, using default {default}")
            return default
        
        if not (min_val <= score <= max_val):
            if context:
                logger.warning(f"[{context}] Score {score} out of range [{min_val}, {max_val}], clamping")
            return max(min_val, min(max_val, float(score)))
        
        return float(score)


class MemoryValidator:
    """
    记忆系统数据验证器
    
    专门用于验证从记忆系统加载的数据
    """
    
    @staticmethod
    def safe_load_dict(memory, var_name: str, default: Optional[Dict] = None) -> Dict:
        """
        安全加载字典变量
        
        Args:
            memory: 记忆系统
            var_name: 变量名
            default: 默认值
        
        Returns:
            字典数据
        """
        if default is None:
            default = {}
        
        try:
            data = memory.load_variable(var_name)
            if not isinstance(data, dict):
                logger.warning(f"[MemoryValidator] {var_name} is not dict: {type(data)}, using default")
                memory.set_variable(var_name, default)
                return default
            return data
        except (KeyError, AttributeError):
            logger.debug(f"[MemoryValidator] {var_name} not found, using default")
            memory.set_variable(var_name, default)
            return default
    
    @staticmethod
    def safe_load_list(memory, var_name: str, default: Optional[List] = None) -> List:
        """
        安全加载列表变量
        
        Args:
            memory: 记忆系统
            var_name: 变量名
            default: 默认值
        
        Returns:
            列表数据
        """
        if default is None:
            default = []
        
        try:
            data = memory.load_variable(var_name)
            if not isinstance(data, list):
                logger.warning(f"[MemoryValidator] {var_name} is not list: {type(data)}, using default")
                memory.set_variable(var_name, default)
                return default
            return data
        except (KeyError, AttributeError):
            logger.debug(f"[MemoryValidator] {var_name} not found, using default")
            memory.set_variable(var_name, default)
            return default
    
    @staticmethod
    def safe_load_set(memory, var_name: str, default: Optional[Set] = None) -> Set:
        """
        安全加载集合变量
        
        Args:
            memory: 记忆系统
            var_name: 变量名
            default: 默认值
        
        Returns:
            集合数据
        """
        if default is None:
            default = set()
        
        try:
            data = memory.load_variable(var_name)
            if not isinstance(data, set):
                logger.warning(f"[MemoryValidator] {var_name} is not set: {type(data)}, using default")
                memory.set_variable(var_name, default)
                return default
            return data
        except (KeyError, AttributeError):
            logger.debug(f"[MemoryValidator] {var_name} not found, using default")
            memory.set_variable(var_name, default)
            return default
    
    @staticmethod
    def safe_load_int(memory, var_name: str, default: int = 0) -> int:
        """
        安全加载整数变量
        
        Args:
            memory: 记忆系统
            var_name: 变量名
            default: 默认值
        
        Returns:
            整数数据
        """
        try:
            data = memory.load_variable(var_name)
            if not isinstance(data, int):
                logger.warning(f"[MemoryValidator] {var_name} is not int: {type(data)}, using default")
                return default
            return data
        except (KeyError, AttributeError):
            logger.debug(f"[MemoryValidator] {var_name} not found, using default")
            return default
    
    @staticmethod
    def safe_load_str(memory, var_name: str, default: str = "") -> str:
        """
        安全加载字符串变量
        
        Args:
            memory: 记忆系统
            var_name: 变量名
            default: 默认值
        
        Returns:
            字符串数据
        """
        try:
            data = memory.load_variable(var_name)
            if not isinstance(data, str):
                logger.warning(f"[MemoryValidator] {var_name} is not str: {type(data)}, using default")
                return default
            return data
        except (KeyError, AttributeError):
            logger.debug(f"[MemoryValidator] {var_name} not found, using default")
            return default


class VotingDataValidator:
    """
    投票数据验证器
    
    专门用于验证投票相关数据
    """
    
    @staticmethod
    def validate_voting_results(voting_results: Dict) -> Tuple[bool, Dict]:
        """
        验证投票结果数据结构
        
        Args:
            voting_results: 投票结果字典
        
        Returns:
            (是否有效, 清理后的数据)
        """
        if not isinstance(voting_results, dict):
            logger.warning(f"[VotingValidator] Invalid voting_results type: {type(voting_results)}")
            return False, {}
        
        cleaned = {}
        
        for voter, results in voting_results.items():
            if not isinstance(voter, str):
                logger.warning(f"[VotingValidator] Invalid voter type: {type(voter)}")
                continue
            
            if not isinstance(results, list):
                logger.warning(f"[VotingValidator] Invalid results type for {voter}: {type(results)}")
                continue
            
            valid_results = []
            for result in results:
                if isinstance(result, tuple) and len(result) >= 2:
                    target, was_wolf = result[0], result[1]
                    if isinstance(target, str) and isinstance(was_wolf, bool):
                        valid_results.append((target, was_wolf))
            
            if valid_results:
                cleaned[voter] = valid_results
        
        return True, cleaned
    
    @staticmethod
    def validate_voting_history(voting_history: Dict) -> Tuple[bool, Dict]:
        """
        验证投票历史数据结构
        
        Args:
            voting_history: 投票历史字典
        
        Returns:
            (是否有效, 清理后的数据)
        """
        if not isinstance(voting_history, dict):
            logger.warning(f"[VotingValidator] Invalid voting_history type: {type(voting_history)}")
            return False, {}
        
        cleaned = {}
        
        for voter, targets in voting_history.items():
            if not isinstance(voter, str):
                logger.warning(f"[VotingValidator] Invalid voter type: {type(voter)}")
                continue
            
            if not isinstance(targets, list):
                logger.warning(f"[VotingValidator] Invalid targets type for {voter}: {type(targets)}")
                continue
            
            valid_targets = [t for t in targets if t and isinstance(t, str)]
            
            if valid_targets:
                cleaned[voter] = valid_targets
        
        return True, cleaned
