# -*- coding: utf-8 -*-
"""
预言家代理人工具类模块

提供各种工具函数和辅助类
"""

from typing import Dict, List, Optional
from agent_build_sdk.utils.logger import logger
from .config import SeerConfig
import re


class SpeechTruncator:
    """
    发言截断器
    
    负责将发言截断到指定长度，保持语义完整性
    
    Attributes:
        config: 配置对象
    """
    
    def __init__(self, config: SeerConfig):
        """
        初始化截断器
        
        Args:
            config: 配置对象
        """
        self.config = config
    
    def truncate(self, text: str, max_length: int) -> str:
        """
        截断文本到指定长度
        
        Args:
            text: 原始文本
            max_length: 最大长度
            
        Returns:
            截断后的文本
        """
        if not text or not isinstance(text, str):
            return ""
        
        if len(text) <= max_length:
            return text
        
        # 在句子边界截断
        truncated = text[:max_length]
        last_period = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?'),
            truncated.rfind('。')
        )
        
        if last_period > max_length * 0.8:
            return truncated[:last_period + 1]
        
        return truncated + "..."


class PlayerExtractor:
    """
    玩家提取器
    
    提供玩家名称提取和存活玩家列表生成功能
    """
    
    @staticmethod
    def get_alive_players(speech_history: Dict[str, List[str]], 
                         dead_players: set, 
                         my_name: str) -> List[str]:
        """
        获取存活玩家列表
        
        Args:
            speech_history: 发言历史
            dead_players: 死亡玩家集合
            my_name: 自己的名字
            
        Returns:
            存活玩家列表
        """
        all_players = set(speech_history.keys())
        all_players.add(my_name)
        
        alive = all_players - dead_players
        return sorted(list(alive))
    
    @staticmethod
    def extract_player_names(text: str) -> List[str]:
        """
        从文本中提取玩家名称
        
        Args:
            text: 文本
            
        Returns:
            玩家名称列表
        """
        pattern = r'No\.(\d+)'
        matches = re.findall(pattern, text)
        return [f"No.{m}" for m in matches]


class CheckReasonGenerator:
    """
    检查原因生成器
    
    根据玩家数据生成检查原因说明
    
    Attributes:
        config: 配置对象
    """
    
    def __init__(self, config: SeerConfig):
        """
        初始化生成器
        
        Args:
            config: 配置对象
        """
        self.config = config
    
    def generate(self, player: str, context: Dict) -> str:
        """
        生成检查原因
        
        Args:
            player: 玩家名称
            context: 上下文
            
        Returns:
            检查原因
        """
        reasons = []
        
        player_data = context.get('player_data', {}).get(player, {})
        
        if player_data.get('malicious_injection'):
            reasons.append("injection attack detected")
        
        if player_data.get('false_quotes'):
            reasons.append("false quotation detected")
        
        trust_scores = context.get('trust_scores', {})
        trust = trust_scores.get(player, 50)
        if trust < 20:
            reasons.append(f"very low trust ({trust})")
        
        if not reasons:
            reasons.append("strategic priority")
        
        return ", ".join(reasons)


class LastWordsDetector:
    """
    遗言阶段检测器
    
    检测消息是否属于遗言阶段
    """
    
    @staticmethod
    def is_last_words_phase(message: str) -> bool:
        """
        检测是否是遗言阶段
        
        Args:
            message: 消息
            
        Returns:
            是否是遗言阶段
        """
        if not message or not isinstance(message, str):
            return False
        
        last_words_indicators = [
            "leaves their last words",
            "Last Words:",
            "'s last words",
            "遗言：",
            "遗言:",
            "last words"
        ]
        
        message_lower = message.lower()
        return any(indicator.lower() in message_lower for indicator in last_words_indicators)


class AnalysisFormatter:
    """
    分析结果格式化器
    
    提供各种分析结果的格式化输出功能
    """
    
    @staticmethod
    def format_trust_summary(trust_scores: Dict[str, int]) -> str:
        """
        格式化信任分数摘要
        
        Args:
            trust_scores: 信任分数字典
            
        Returns:
            格式化的摘要
        """
        if not trust_scores:
            return "\n\n=== Trust Scores ===\nNo trust data available.\n"
        
        sorted_scores = sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)
        
        lines = ["\n\n=== Trust Scores ==="]
        for player, score in sorted_scores:
            if score >= 70:
                level = "HIGH"
            elif score >= 40:
                level = "MEDIUM"
            elif score >= 0:
                level = "LOW"
            else:
                level = "VERY LOW"
            
            lines.append(f"{player}: {score} ({level})")
        
        return "\n".join(lines) + "\n"
    
    @staticmethod
    def format_check_results(checked_players: Dict[str, Dict]) -> str:
        """
        格式化检查结果
        
        Args:
            checked_players: 检查结果字典
            
        Returns:
            格式化的结果
        """
        if not checked_players:
            return "\n\n=== Check Results ===\nNo checks performed yet.\n"
        
        lines = ["\n\n=== Check Results ==="]
        for player, data in checked_players.items():
            is_wolf = data.get('is_wolf', False)
            night = data.get('night', 0)
            result = "WOLF" if is_wolf else "GOOD"
            lines.append(f"Night {night}: {player} → {result}")
        
        return "\n".join(lines) + "\n"
    
    @staticmethod
    def format_suspect_analysis(trust_scores: Dict[str, int], 
                                player_data: Dict[str, Dict],
                                checked_players: Dict[str, Dict],
                                my_name: str) -> str:
        """
        格式化嫌疑分析
        
        Args:
            trust_scores: 信任分数
            player_data: 玩家数据
            checked_players: 检查结果
            my_name: 自己的名字
            
        Returns:
            格式化的分析
        """
        suspects = []
        
        for player, score in trust_scores.items():
            if player == my_name:
                continue
            
            if player in checked_players:
                continue
            
            if score < 30:
                reasons = []
                data = player_data.get(player, {})
                
                if data.get('malicious_injection'):
                    reasons.append("injection attack")
                if data.get('false_quotes'):
                    reasons.append("false quotes")
                if data.get('contradictions'):
                    reasons.append("contradictions")
                
                reason_str = ", ".join(reasons) if reasons else "low trust"
                suspects.append(f"{player} (trust: {score}, {reason_str})")
        
        if not suspects:
            return "\n\n=== Suspect Analysis ===\nNo strong suspects identified.\n"
        
        lines = ["\n\n=== Suspect Analysis ==="]
        lines.extend(suspects)
        
        return "\n".join(lines) + "\n"


class VotingAnalysisFormatter:
    """
    投票分析格式化器
    
    提供投票模式分析的格式化输出功能
    """
    
    @staticmethod
    def format_voting_patterns(voting_history: Dict[str, List[str]],
                              voting_results: Dict[str, List]) -> str:
        """
        格式化投票模式分析
        
        Args:
            voting_history: 投票历史
            voting_results: 投票结果
            
        Returns:
            格式化的分析
        """
        if not voting_history:
            return "\n\n=== Voting Patterns ===\nNo voting data available.\n"
        
        lines = ["\n\n=== Voting Patterns ==="]
        
        for player, votes in voting_history.items():
            if not votes:
                continue
            
            results = voting_results.get(player, [])
            if results:
                correct = sum(1 for _, was_wolf in results if was_wolf)
                total = len(results)
                accuracy = correct / total if total > 0 else 0
                
                lines.append(
                    f"{player}: {len(votes)} votes, "
                    f"accuracy: {accuracy:.1%} ({correct}/{total})"
                )
            else:
                lines.append(f"{player}: {len(votes)} votes, accuracy: unknown")
        
        return "\n".join(lines) + "\n"
