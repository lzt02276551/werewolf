"""
贝叶斯推理引擎

实现改进的贝叶斯推理算法，支持证据分组和相关性处理。
使用几何平均处理相关证据，避免过度惩罚。
使用对数空间计算，避免数值溢出。

验证需求: AC-2.2.1, AC-2.2.2, AC-2.2.3
修复日期: 2026-02-21 - 增强数值稳定性
"""

from enum import Enum
from typing import List, Dict, Any
import logging
import numpy as np

from ..utils.safe_math import safe_divide

logger = logging.getLogger(__name__)


class EvidenceType(Enum):
    """
    证据类型枚举
    
    用于区分独立证据和相关证据，以便采用不同的组合策略。
    """
    INDEPENDENT = "independent"  # 独立证据：可以直接相乘
    CORRELATED = "correlated"    # 相关证据：需要使用几何平均


class Evidence:
    """
    证据数据结构
    
    表示一个证据及其对假设的支持程度（似然比）。
    
    属性:
        name: 证据名称，用于标识和日志记录
        likelihood_ratio: 似然比 LR = P(证据|假设为真) / P(证据|假设为假)
        evidence_type: 证据类型（独立或相关）
    
    示例:
        >>> # 独立证据：被预言家查验为狼人
        >>> evidence1 = Evidence("seer_check", 10.0, EvidenceType.INDEPENDENT)
        >>> 
        >>> # 相关证据：发言中的注入攻击
        >>> evidence2 = Evidence("injection_attack", 3.0, EvidenceType.CORRELATED)
    
    验证需求: AC-2.2.1
    """
    
    def __init__(
        self,
        name: str,
        likelihood_ratio: float,
        evidence_type: EvidenceType = EvidenceType.INDEPENDENT
    ):
        """
        初始化证据
        
        参数:
            name: 证据名称
            likelihood_ratio: 似然比，应该 > 0
            evidence_type: 证据类型，默认为独立证据
        """
        self.name = name
        self.likelihood_ratio = likelihood_ratio
        self.evidence_type = evidence_type
    
    def __repr__(self) -> str:
        return (
            f"Evidence(name='{self.name}', "
            f"likelihood_ratio={self.likelihood_ratio:.2f}, "
            f"evidence_type={self.evidence_type.value})"
        )


class BayesianInference:
    """
    贝叶斯推理引擎
    
    实现改进的贝叶斯推理算法，考虑证据之间的相关性。
    
    算法原理:
        1. 独立证据：直接相乘似然比
        2. 相关证据：使用几何平均避免过度惩罚
        3. 组合似然比：independent_lr × correlated_lr
        4. 计算后验概率：posterior = (prior_odds × combined_lr) / (1 + prior_odds × combined_lr)
    
    配置参数:
        prior_probability: 先验概率，默认 0.25（假设4个玩家中1个是狼人）
    
    示例:
        >>> config = {'prior_probability': 0.25}
        >>> bayesian = BayesianInference(config)
        >>> 
        >>> evidences = [
        ...     Evidence("seer_check", 10.0, EvidenceType.INDEPENDENT),
        ...     Evidence("injection_attack", 3.0, EvidenceType.CORRELATED),
        ...     Evidence("false_reference", 2.5, EvidenceType.CORRELATED)
        ... ]
        >>> 
        >>> posterior = bayesian.calculate_posterior(evidences)
        >>> print(f"后验概率: {posterior:.2%}")
    
    验证需求: AC-2.2.1, AC-2.2.2, AC-2.2.3
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化贝叶斯推理引擎
        
        参数:
            config: 配置字典，支持以下键:
                - prior_probability: 先验概率，默认 0.25
        """
        self.config = config
        self.prior_probability = config.get('prior_probability', 0.25)
        
        # 验证先验概率在有效范围内
        if not (0.0 < self.prior_probability < 1.0):
            logger.warning(
                f"先验概率 {self.prior_probability} 不在 (0, 1) 范围内，"
                f"使用默认值 0.25"
            )
            self.prior_probability = 0.25
    
    def calculate_posterior(self, evidences: List[Evidence]) -> float:
        """
        计算后验概率，考虑证据相关性
        
        算法步骤:
            1. 将证据分为独立证据和相关证据两组
            2. 独立证据：直接相乘似然比
            3. 相关证据：使用几何平均 (LR1 × LR2 × ... × LRn)^(1/n)
            4. 组合似然比：independent_lr × correlated_lr
            5. 计算后验概率：posterior = (prior_odds × combined_lr) / (1 + prior_odds × combined_lr)
        
        参数:
            evidences: 证据列表
        
        返回:
            后验概率，范围 [0, 1]
        
        示例:
            >>> bayesian = BayesianInference({'prior_probability': 0.25})
            >>> evidences = [
            ...     Evidence("e1", 4.0, EvidenceType.INDEPENDENT),
            ...     Evidence("e2", 9.0, EvidenceType.CORRELATED),
            ...     Evidence("e3", 4.0, EvidenceType.CORRELATED)
            ... ]
            >>> posterior = bayesian.calculate_posterior(evidences)
            >>> # 独立: 4.0
            >>> # 相关: (9.0 × 4.0)^0.5 = 6.0
            >>> # 组合: 4.0 × 6.0 = 24.0
            >>> # 后验: (0.333 × 24.0) / (1 + 0.333 × 24.0) ≈ 0.889
        
        验证需求: AC-2.2.2, AC-2.2.3
        """
        if not evidences:
            logger.info("没有证据，返回先验概率")
            return self.prior_probability
        
        # 分组证据
        independent_evidences = [
            e for e in evidences 
            if e.evidence_type == EvidenceType.INDEPENDENT
        ]
        correlated_evidences = [
            e for e in evidences 
            if e.evidence_type == EvidenceType.CORRELATED
        ]
        
        logger.debug(
            f"证据分组: {len(independent_evidences)} 个独立证据, "
            f"{len(correlated_evidences)} 个相关证据"
        )
        
        # 独立证据：直接相乘（使用对数空间避免溢出）
        independent_lr = 1.0
        if independent_evidences:
            # 使用对数空间计算，避免数值溢出
            log_lr = sum(np.log(max(e.likelihood_ratio, 1e-10)) 
                         for e in independent_evidences)
            # 限制最大值避免溢出
            independent_lr = np.exp(min(log_lr, 100.0))
            logger.debug(f"独立证据LR: {independent_lr:.2f}")
        
        # 相关证据：使用几何平均（对数空间计算）
        correlated_lr = 1.0
        if correlated_evidences:
            # 几何平均 = exp(mean(log(x)))，避免直接计算 product^(1/n)
            log_lrs = [np.log(max(e.likelihood_ratio, 1e-10)) 
                       for e in correlated_evidences]
            mean_log_lr = np.mean(log_lrs)
            # 限制最大值避免溢出
            correlated_lr = np.exp(min(mean_log_lr, 100.0))
            logger.debug(f"相关证据几何平均LR: {correlated_lr:.2f}")
        
        # 组合似然比（限制最大值）
        combined_lr = independent_lr * correlated_lr
        combined_lr = min(combined_lr, 1e6)  # 限制最大值
        logger.debug(
            f"组合似然比: {independent_lr:.2f} × {correlated_lr:.2f} = {combined_lr:.2f}"
        )
        
        # 计算后验概率
        # prior_odds = P(H) / P(¬H) = P(H) / (1 - P(H))
        prior_odds = safe_divide(
            self.prior_probability,
            1.0 - self.prior_probability,
            default=1.0
        )
        
        # posterior_odds = prior_odds × combined_lr
        posterior_odds = prior_odds * combined_lr
        
        # posterior_prob = posterior_odds / (1 + posterior_odds)
        posterior_prob = safe_divide(
            posterior_odds,
            1.0 + posterior_odds,
            default=0.5
        )
        
        # 限制在合理范围内，避免极端值
        posterior_prob = float(np.clip(posterior_prob, 0.001, 0.999))
        
        logger.info(
            f"贝叶斯推理: 先验={self.prior_probability:.2%}, "
            f"似然比={combined_lr:.2f}, 后验={posterior_prob:.2%}"
        )
        
        return posterior_prob
    
    def compute_likelihood_ratio(
        self,
        p_evidence_given_hypothesis: float,
        p_evidence_given_not_hypothesis: float
    ) -> float:
        """
        计算似然比
        
        似然比 (Likelihood Ratio) 衡量证据对假设的支持程度:
            LR = P(证据|假设为真) / P(证据|假设为假)
        
        - LR > 1: 证据支持假设
        - LR = 1: 证据不提供信息
        - LR < 1: 证据反对假设
        
        参数:
            p_evidence_given_hypothesis: P(证据|假设为真)
            p_evidence_given_not_hypothesis: P(证据|假设为假)
        
        返回:
            似然比，当分母接近零时返回默认值 1.0
        
        示例:
            >>> bayesian = BayesianInference({'prior_probability': 0.25})
            >>> # 狼人有80%概率表现出某行为，村民只有20%
            >>> lr = bayesian.compute_likelihood_ratio(0.8, 0.2)
            >>> print(f"似然比: {lr}")  # 4.0
            >>> 
            >>> # 分母接近零的情况
            >>> lr = bayesian.compute_likelihood_ratio(0.5, 1e-12)
            >>> print(f"似然比: {lr}")  # 1.0 (默认值)
        
        验证需求: AC-2.2.3
        """
        lr = safe_divide(
            p_evidence_given_hypothesis,
            p_evidence_given_not_hypothesis,
            default=1.0,
            epsilon=1e-10
        )
        
        if lr == 1.0 and abs(p_evidence_given_not_hypothesis) < 1e-10:
            logger.warning(
                f"计算似然比时分母接近零: "
                f"P(E|H)={p_evidence_given_hypothesis}, "
                f"P(E|¬H)={p_evidence_given_not_hypothesis}, "
                f"返回默认值 1.0"
            )
        
        return lr
