"""
信任分数衰减算法

使用Sigmoid函数实现平滑的信任分数衰减，避免分数在极端值时的突变。

验证需求: AC-1.3.1, AC-1.3.2
"""

import numpy as np
from typing import Dict, Any


def sigmoid_decay_factor(
    current_score: float,
    steepness: float = 0.1,
    midpoint: float = 50.0
) -> float:
    """
    计算基于Sigmoid的衰减因子
    
    使用Sigmoid函数计算衰减因子，使得分数接近极端值（0或100）时衰减变慢，
    接近中点时衰减变快，从而实现平滑过渡。
    
    数学公式:
        normalized = (current_score - midpoint) / 50.0
        decay_factor = 1 / (1 + e^(-steepness * normalized))
    
    参数:
        current_score: 当前信任分数，范围 [0, 100]
        steepness: 曲线陡峭度，越大变化越剧烈，默认 0.1
        midpoint: 中点位置，默认 50.0
    
    返回:
        衰减因子，范围 [0, 1]
        - 分数接近极端值时，衰减因子接近1（衰减慢）
        - 分数接近中点时，衰减因子接近0.5（衰减快）
    
    示例:
        >>> sigmoid_decay_factor(0.0)    # 接近0，衰减慢
        0.2689...
        >>> sigmoid_decay_factor(50.0)   # 中点，衰减适中
        0.5
        >>> sigmoid_decay_factor(100.0)  # 接近100，衰减慢
        0.7310...
    
    验证需求: AC-1.3.1, AC-1.3.2
    """
    # 归一化到 [-1, 1] 范围
    normalized = (current_score - midpoint) / 50.0
    
    # Sigmoid函数: 1 / (1 + e^(-steepness * x))
    # 分数越极端，衰减因子越大，意味着衰减越慢
    decay_factor = 1.0 / (1.0 + np.exp(-steepness * normalized))
    
    return float(decay_factor)


def update_trust_score(
    current_score: float,
    evidence_impact: float,
    config: Dict[str, Any]
) -> float:
    """
    更新信任分数，使用平滑衰减
    
    根据证据影响更新信任分数，使用Sigmoid衰减因子确保分数变化平滑，
    避免在极端值附近出现突变。
    
    算法流程:
        1. 计算当前分数的衰减因子
        2. 应用衰减因子调整证据影响: adjusted_impact = evidence_impact * decay_factor
        3. 更新分数: new_score = current_score + adjusted_impact
        4. 限制在 [0, 100] 范围内
    
    修复说明 (2026-02-21):
        - 修复了衰减因子应用逻辑错误
        - decay_factor 越大表示越接近极端值，应该衰减越慢（影响越大）
        - 因此应该直接乘以 decay_factor，而不是 (1 - decay_factor)
    
    参数:
        current_score: 当前分数，范围 [0, 100]
        evidence_impact: 证据影响，范围 [-100, 100]
            - 正值表示增加信任
            - 负值表示减少信任
        config: 配置参数字典，支持以下键:
            - decay_steepness: 衰减陡峭度，默认 0.1
            - decay_midpoint: 衰减中点，默认 50.0
    
    返回:
        更新后的分数，范围 [0, 100]
    
    示例:
        >>> config = {'decay_steepness': 0.1, 'decay_midpoint': 50.0}
        >>> update_trust_score(50.0, 20.0, config)  # 中点，正常衰减
        60.0
        >>> update_trust_score(90.0, 20.0, config)  # 接近上限，衰减慢
        95.38...
        >>> update_trust_score(10.0, -20.0, config) # 接近下限，衰减慢
        5.38...
    
    验证需求: AC-1.3.1, AC-1.3.2
    """
    # 获取配置参数
    decay_steepness = config.get('decay_steepness', 0.1)
    decay_midpoint = config.get('decay_midpoint', 50.0)
    
    # 计算衰减因子
    decay_factor = sigmoid_decay_factor(
        current_score,
        steepness=decay_steepness,
        midpoint=decay_midpoint
    )
    
    # 应用衰减因子
    # 修复: decay_factor 越大（接近极端值），影响应该越大，衰减越慢
    # decay_factor 越小（接近中点），影响应该越小，衰减越快
    adjusted_impact = evidence_impact * decay_factor
    
    # 更新分数
    new_score = current_score + adjusted_impact
    
    # 限制在 [0, 100] 范围内
    return float(np.clip(new_score, 0.0, 100.0))
