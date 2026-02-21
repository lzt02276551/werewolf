"""
增强贝叶斯推理 - 基于证据的概率推理

使用贝叶斯定理结合多个证据进行狼人概率推理
"""

import logging
import numpy as np
from typing import Dict, List
from werewolf.optimization.utils.safe_math import safe_divide

logger = logging.getLogger(__name__)


class BayesianAnalyzer:
    """
    贝叶斯分析器
    
    使用贝叶斯定理结合多个证据：
    - 信任分数
    - 投票准确度
    - 注入攻击
    - 虚假引用
    - 发言质量
    """
    
    def __init__(self, prior_wolf_prob: float = 0.33):
        """
        初始化贝叶斯分析器
        
        Args:
            prior_wolf_prob: 先验狼人概率（默认33%，4/12）
        """
        self.prior_wolf_prob = prior_wolf_prob
        self.prior_good_prob = 1.0 - prior_wolf_prob
        
        logger.info(f"✓ BayesianAnalyzer initialized (prior={prior_wolf_prob:.2%})")
    
    def analyze_player(self, player_data: Dict) -> float:
        """
        分析玩家，返回狼人概率
        
        Args:
            player_data: 玩家数据
            
        Returns:
            狼人概率 (0-1)
        """
        # 收集证据
        evidences = []
        
        # 证据1: 信任分数
        trust_score = player_data.get('trust_score', 50)
        if trust_score < 30:
            # 低信任分数，狼人可能性高
            likelihood_ratio = 3.0
            evidences.append(('low_trust', likelihood_ratio))
        elif trust_score > 70:
            # 高信任分数，好人可能性高
            likelihood_ratio = 0.3
            evidences.append(('high_trust', likelihood_ratio))
        
        # 证据2: 投票准确度
        vote_accuracy = player_data.get('vote_accuracy', 0.5)
        if vote_accuracy < 0.3:
            # 低准确度，狼人可能性高
            likelihood_ratio = 2.5
            evidences.append(('low_vote_accuracy', likelihood_ratio))
        elif vote_accuracy > 0.7:
            # 高准确度，好人可能性高
            likelihood_ratio = 0.4
            evidences.append(('high_vote_accuracy', likelihood_ratio))
        
        # 证据3: 注入攻击
        injection_attempts = player_data.get('injection_attempts', 0)
        if injection_attempts > 0:
            # 有注入攻击，狼人可能性极高
            likelihood_ratio = 5.0 * injection_attempts
            evidences.append(('injection_attack', likelihood_ratio))
        
        # 证据4: 虚假引用
        false_quotation_count = player_data.get('false_quotation_count', 0)
        if false_quotation_count > 0:
            # 有虚假引用，狼人可能性高
            likelihood_ratio = 4.0 * false_quotation_count
            evidences.append(('false_quotation', likelihood_ratio))
        
        # 证据5: 矛盾次数
        contradiction_count = player_data.get('contradiction_count', 0)
        if contradiction_count > 2:
            # 多次矛盾，狼人可能性高
            likelihood_ratio = 2.0
            evidences.append(('contradictions', likelihood_ratio))
        
        # 证据6: 发言质量
        speech_lengths = player_data.get('speech_lengths', [100])
        if speech_lengths:
            avg_length = sum(speech_lengths) / len(speech_lengths)
            if avg_length < 50:
                # 发言太短，可能是狼人
                likelihood_ratio = 1.8
                evidences.append(('short_speech', likelihood_ratio))
            elif avg_length > 200:
                # 发言详细，可能是好人
                likelihood_ratio = 0.6
                evidences.append(('detailed_speech', likelihood_ratio))
        
        # 证据7: 夜间存活率
        night_survival_rate = player_data.get('night_survival_rate', 0.5)
        if night_survival_rate > 0.8:
            # 夜间存活率高，可能是狼人（不会被狼人杀）
            likelihood_ratio = 1.5
            evidences.append(('high_survival', likelihood_ratio))
        
        # 证据8: 孤立分数
        isolation_score = player_data.get('isolation_score', 0.5)
        if isolation_score > 0.7:
            # 孤立度高，可能是狼人
            likelihood_ratio = 1.6
            evidences.append(('isolated', likelihood_ratio))
        
        # 如果没有证据，返回先验概率
        if not evidences:
            return self.prior_wolf_prob
        
        # 使用贝叶斯定理计算后验概率
        posterior_prob = self._calculate_posterior(evidences)
        
        logger.debug(f"Bayesian analysis: {len(evidences)} evidences, posterior={posterior_prob:.3f}")
        
        return posterior_prob
    
    def _calculate_posterior(self, evidences: List[tuple]) -> float:
        """
        计算后验概率
        
        Args:
            evidences: 证据列表 [(name, likelihood_ratio), ...]
            
        Returns:
            后验概率
        """
        # 使用对数空间计算，避免数值下溢
        log_prior_wolf = np.log(self.prior_wolf_prob)
        log_prior_good = np.log(self.prior_good_prob)
        
        # 累积似然比的对数
        log_likelihood_ratio_sum = 0.0
        for name, likelihood_ratio in evidences:
            # 限制似然比范围，避免极端值
            likelihood_ratio = max(0.01, min(100.0, likelihood_ratio))
            log_likelihood_ratio_sum += np.log(likelihood_ratio)
        
        # 计算后验概率的对数
        log_posterior_wolf = log_prior_wolf + log_likelihood_ratio_sum
        log_posterior_good = log_prior_good
        
        # 归一化（使用log-sum-exp技巧避免溢出）
        max_log = max(log_posterior_wolf, log_posterior_good)
        exp_wolf = np.exp(log_posterior_wolf - max_log)
        exp_good = np.exp(log_posterior_good - max_log)
        
        # 使用safe_divide防止除零
        posterior_wolf = safe_divide(exp_wolf, exp_wolf + exp_good, default=self.prior_wolf_prob)
        
        # 确保在有效范围内
        posterior_wolf = max(0.0, min(1.0, posterior_wolf))
        
        return float(posterior_wolf)
