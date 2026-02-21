"""
安全数学计算工具

提供安全的数学运算函数，避免除零错误等常见问题
"""

import logging
from typing import Union

logger = logging.getLogger(__name__)


def safe_divide(
    numerator: Union[int, float],
    denominator: Union[int, float],
    default: float = 0.0,
    epsilon: float = 1e-10
) -> float:
    """
    安全除法，避免除零错误
    
    当分母的绝对值小于epsilon阈值时，返回默认值而不是执行除法。
    这样可以处理浮点数精度问题，避免程序崩溃。
    
    参数:
        numerator: 分子，可以是整数或浮点数
        denominator: 分母，可以是整数或浮点数
        default: 分母为零时的默认返回值，默认为0.0
        epsilon: 判断分母是否为零的阈值，默认为1e-10
    
    返回:
        float: 除法结果或默认值
    
    示例:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
        >>> safe_divide(10, 0, default=1.0)
        1.0
        >>> safe_divide(10, 1e-12)  # 分母接近零
        0.0
        >>> safe_divide(10, 1e-12, default=-1.0)
        -1.0
    
    需求:
        - AC-1.1.1: 所有除法操作都使用safe_divide函数
        - AC-1.1.3: 日志记录异常情况但不中断执行
    """
    if abs(denominator) < epsilon:
        logger.warning(
            f"除法操作中分母接近零: numerator={numerator}, "
            f"denominator={denominator}, 返回默认值={default}"
        )
        return default
    
    return numerator / denominator
