# -*- coding: utf-8 -*-
"""
猎人代理人性能监控模块

提供性能监控、分析和优化功能
"""

import time
import functools
from typing import Callable, Any, Dict
from collections import defaultdict
from agent_build_sdk.utils.logger import logger


class PerformanceMonitor:
    """
    性能监控器
    
    跟踪方法执行时间、调用次数、性能瓶颈
    """
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'avg_time': 0.0
        })
        self.enabled = True
    
    def record(self, method_name: str, execution_time: float):
        """
        记录方法执行时间
        
        Args:
            method_name: 方法名称
            execution_time: 执行时间（秒）
        """
        if not self.enabled:
            return
        
        metrics = self.metrics[method_name]
        metrics['count'] += 1
        metrics['total_time'] += execution_time
        metrics['min_time'] = min(metrics['min_time'], execution_time)
        metrics['max_time'] = max(metrics['max_time'], execution_time)
        metrics['avg_time'] = metrics['total_time'] / metrics['count']
    
    def get_report(self) -> str:
        """
        生成性能报告
        
        Returns:
            格式化的性能报告
        """
        if not self.metrics:
            return "No performance data collected"
        
        lines = ["=" * 80, "Performance Report", "=" * 80]
        
        # 按平均时间排序
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        
        lines.append(f"{'Method':<40} {'Calls':>8} {'Avg(ms)':>10} {'Min(ms)':>10} {'Max(ms)':>10}")
        lines.append("-" * 80)
        
        for method_name, metrics in sorted_metrics:
            lines.append(
                f"{method_name:<40} "
                f"{metrics['count']:>8} "
                f"{metrics['avg_time']*1000:>10.2f} "
                f"{metrics['min_time']*1000:>10.2f} "
                f"{metrics['max_time']*1000:>10.2f}"
            )
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def reset(self):
        """重置所有统计数据"""
        self.metrics.clear()
    
    def enable(self):
        """启用性能监控"""
        self.enabled = True
    
    def disable(self):
        """禁用性能监控"""
        self.enabled = False


# 全局性能监控器实例
_performance_monitor = PerformanceMonitor()


def monitor_performance(method: Callable) -> Callable:
    """
    性能监控装饰器
    
    自动记录方法执行时间
    
    Args:
        method: 要监控的方法
        
    Returns:
        包装后的方法
    """
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = method(*args, **kwargs)
            return result
        finally:
            execution_time = time.perf_counter() - start_time
            method_name = f"{method.__module__}.{method.__qualname__}"
            _performance_monitor.record(method_name, execution_time)
            
            # 如果执行时间超过100ms，记录警告
            if execution_time > 0.1:
                logger.warning(
                    f"[PERFORMANCE] {method_name} took {execution_time*1000:.2f}ms "
                    f"(threshold: 100ms)"
                )
    
    return wrapper


def get_performance_report() -> str:
    """获取性能报告"""
    return _performance_monitor.get_report()


def reset_performance_metrics():
    """重置性能统计"""
    _performance_monitor.reset()


def enable_performance_monitoring():
    """启用性能监控"""
    _performance_monitor.enable()


def disable_performance_monitoring():
    """禁用性能监控"""
    _performance_monitor.disable()


__all__ = [
    'PerformanceMonitor',
    'monitor_performance',
    'get_performance_report',
    'reset_performance_metrics',
    'enable_performance_monitoring',
    'disable_performance_monitoring'
]

