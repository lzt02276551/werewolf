"""
通用分析器

提供信任分析、投票分析、狼人概率分析等通用分析功能
"""

from typing import Dict, Any, List, Optional
from werewolf.core.base_components import BaseAnalyzer, BaseTrustManager
from werewolf.core.config import BaseConfig
from werewolf.optimization.utils.safe_math import safe_divide


class TrustAnalyzer(BaseTrustManager):
    """
    信任分析器
    
    管理和分析玩家信任分数
    """
    
    def __init__(self, config: BaseConfig):
        """
        初始化分析器
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
        self.trust_history: Dict[str, List[Dict]] = {}
    
    def initialize_players(self, players: List[str]) -> None:
        """
        初始化玩家信任分数
        
        Args:
            players: 玩家列表
        """
        for player in players:
            self.trust_scores[player] = self.config.trust_score_default
            self.trust_history[player] = []
        
        self.logger.info(f"Initialized trust scores for {len(players)} players")
    
    def update_score(
        self,
        player: str,
        delta: float,
        reason: str = "",
        confidence: float = 1.0
    ) -> float:
        """
        更新玩家信任分数（使用优化的Sigmoid衰减算法）
        
        Args:
            player: 玩家名称
            delta: 分数变化
            reason: 更新原因
            confidence: 置信度(0-1)
            
        Returns:
            更新后的分数
        
        验证需求：AC-1.3.1
        """
        # 导入优化的信任分数更新算法
        from werewolf.optimization.algorithms.trust_score import update_trust_score
        
        if player not in self.trust_scores:
            self.trust_scores[player] = self.config.trust_score_default
            self.trust_history[player] = []
        
        # 应用置信度
        evidence_impact = delta * confidence
        
        # 使用优化的Sigmoid衰减算法更新分数
        old_score = self.trust_scores[player]
        
        # 配置参数
        config = {
            'decay_steepness': 0.1,
            'decay_midpoint': 50.0
        }
        
        new_score = update_trust_score(old_score, evidence_impact, config)
        self.trust_scores[player] = new_score
        
        # 记录历史
        self.trust_history[player].append({
            'old_score': old_score,
            'new_score': new_score,
            'delta': evidence_impact,
            'reason': reason,
            'confidence': confidence
        })
        
        self.logger.debug(
            f"Updated trust score for {player}: "
            f"{old_score:.1f} -> {new_score:.1f} ({reason}) [Sigmoid衰减]"
        )
        
        return new_score
    
    def get_score(self, player: str) -> float:
        """
        获取玩家信任分数
        
        Args:
            player: 玩家名称
            
        Returns:
            信任分数
        """
        return self.trust_scores.get(player, self.config.trust_score_default)
    
    def get_all_scores(self) -> Dict[str, float]:
        """
        获取所有玩家的信任分数
        
        Returns:
            信任分数字典
        """
        return self.trust_scores.copy()
    
    def get_top_trusted(self, n: int = 3) -> List[tuple]:
        """
        获取最受信任的玩家
        
        Args:
            n: 返回数量
            
        Returns:
            (玩家, 分数)元组列表
        """
        sorted_players = sorted(
            self.trust_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_players[:n]
    
    def get_least_trusted(self, n: int = 3) -> List[tuple]:
        """
        获取最不受信任的玩家
        
        Args:
            n: 返回数量
            
        Returns:
            (玩家, 分数)元组列表
        """
        sorted_players = sorted(
            self.trust_scores.items(),
            key=lambda x: x[1]
        )
        return sorted_players[:n]
    
    def _get_default_result(self) -> float:
        """获取默认信任分数"""
        return self.config.trust_score_default


class VotingAnalyzer(BaseAnalyzer):
    """
    投票分析器
    
    分析投票历史和模式
    """
    
    def __init__(self, config: BaseConfig):
        """
        初始化分析器
        
        Args:
            config: 配置对象
        """
        super().__init__(config)
    
    def _do_analyze(
        self,
        vote_history: List[Dict[str, Any]],
        target_player: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析投票历史
        
        Args:
            vote_history: 投票历史
            target_player: 目标玩家(可选)
            
        Returns:
            分析结果
        """
        if not vote_history:
            return {
                'total_votes': 0,
                'vote_patterns': {},
                'consistency_score': 0.0
            }
        
        # 统计投票模式
        vote_patterns = self._analyze_patterns(vote_history)
        
        # 计算一致性
        consistency = self._calculate_consistency(vote_history)
        
        # 如果指定了目标玩家,分析该玩家的投票行为
        player_analysis = None
        if target_player:
            player_analysis = self._analyze_player_votes(vote_history, target_player)
        
        return {
            'total_votes': len(vote_history),
            'vote_patterns': vote_patterns,
            'consistency_score': consistency,
            'player_analysis': player_analysis
        }
    
    def _analyze_patterns(self, vote_history: List[Dict]) -> Dict[str, int]:
        """分析投票模式"""
        patterns = {}
        
        for vote in vote_history:
            voter = vote.get('voter', '')
            target = vote.get('target', '')
            
            if voter and target:
                key = f"{voter}->{target}"
                patterns[key] = patterns.get(key, 0) + 1
        
        return patterns
    
    def _calculate_consistency(self, vote_history: List[Dict]) -> float:
        """计算投票一致性"""
        if len(vote_history) < 2:
            return 1.0
        
        # 简单的一致性计算:检查是否经常改变投票目标
        changes = 0
        prev_target = None
        
        for vote in vote_history:
            target = vote.get('target')
            if prev_target and target != prev_target:
                changes += 1
            prev_target = target
        
        consistency = 1.0 - (changes / len(vote_history))
        return max(0.0, consistency)
    
    def _analyze_player_votes(
        self,
        vote_history: List[Dict],
        player: str
    ) -> Dict[str, Any]:
        """分析特定玩家的投票行为"""
        player_votes = [
            v for v in vote_history
            if v.get('voter') == player
        ]
        
        if not player_votes:
            return {'vote_count': 0, 'targets': []}
        
        targets = [v.get('target') for v in player_votes if v.get('target')]
        
        return {
            'vote_count': len(player_votes),
            'targets': targets,
            'unique_targets': len(set(targets))
        }
    
    def _get_default_result(self) -> Dict[str, Any]:
        """获取默认分析结果"""
        return {
            'total_votes': 0,
            'vote_patterns': {},
            'consistency_score': 0.0
        }


class WolfProbabilityAnalyzer(BaseAnalyzer):
    """
    狼人概率分析器
    
    分析玩家是狼人的概率
    """
    
    def __init__(self, config: BaseConfig, trust_analyzer: TrustAnalyzer):
        """
        初始化分析器
        
        Args:
            config: 配置对象
            trust_analyzer: 信任分析器
        """
        super().__init__(config)
        self.trust_analyzer = trust_analyzer
    
    def _do_analyze(
        self,
        player: str,
        context: Dict[str, Any]
    ) -> float:
        """
        分析玩家是狼人的概率
        
        Args:
            player: 玩家名称
            context: 上下文信息
            
        Returns:
            狼人概率(0-1)
        """
        # 基于信任分数计算
        trust_score = self.trust_analyzer.get_score(player)
        
        # 信任分数越低,狼人概率越高
        # 将信任分数(0-100)转换为概率(0-1)，使用safe_divide
        base_probability = 1.0 - safe_divide(trust_score, 100.0, default=0.5)
        
        # 考虑其他因素
        adjustments = self._calculate_adjustments(player, context)
        
        # 综合概率
        final_probability = base_probability * (1.0 + adjustments)
        
        # 限制在0-1范围内
        return max(0.0, min(1.0, final_probability))
    
    def _calculate_adjustments(
        self,
        player: str,
        context: Dict[str, Any]
    ) -> float:
        """
        计算概率调整因子
        
        Args:
            player: 玩家名称
            context: 上下文信息
            
        Returns:
            调整因子(-1到1)
        """
        adjustment = 0.0
        
        # 检查是否有注入行为
        if context.get('has_injection', {}).get(player, False):
            adjustment += 0.3
        
        # 检查投票行为
        vote_consistency = context.get('vote_consistency', {}).get(player, 0.5)
        if vote_consistency < 0.3:
            adjustment += 0.2
        
        # 检查发言质量
        speech_quality = context.get('speech_quality', {}).get(player, 0.5)
        if speech_quality < 0.3:
            adjustment += 0.1
        
        return adjustment
    
    def analyze_all_players(
        self,
        players: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        分析所有玩家的狼人概率
        
        Args:
            players: 玩家列表
            context: 上下文信息
            
        Returns:
            玩家->概率字典
        """
        probabilities = {}
        
        for player in players:
            probabilities[player] = self.analyze(player, context)
        
        return probabilities
    
    def get_top_suspects(
        self,
        players: List[str],
        context: Dict[str, Any],
        n: int = 3
    ) -> List[tuple]:
        """
        获取最可疑的玩家
        
        Args:
            players: 玩家列表
            context: 上下文信息
            n: 返回数量
            
        Returns:
            (玩家, 概率)元组列表
        """
        probabilities = self.analyze_all_players(players, context)
        sorted_players = sorted(
            probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_players[:n]
    
    def _get_default_result(self) -> float:
        """获取默认概率"""
        return 0.5
