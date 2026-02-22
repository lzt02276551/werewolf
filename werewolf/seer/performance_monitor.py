# -*- coding: utf-8 -*-
"""
预言家性能监控模块（企业级五星标准）

提供性能监控、统计分析和优化建议功能
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time
import json
from pathlib import Path
from agent_build_sdk.utils.logger import logger


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    
    def update(self, elapsed_time: float):
        """更新指标"""
        self.count += 1
        self.total_time += elapsed_time
        self.min_time = min(self.min_time, elapsed_time)
        self.max_time = max(self.max_time, elapsed_time)
        self.avg_time = self.total_time / self.count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'operation': self.operation,
            'count': self.count,
            'total_time_ms': round(self.total_time * 1000, 2),
            'min_time_ms': round(self.min_time * 1000, 2),
            'max_time_ms': round(self.max_time * 1000, 2),
            'avg_time_ms': round(self.avg_time * 1000, 2)
        }


class PerformanceMonitor:
    """
    性能监控器（企业级五星标准）
    
    功能：
    - 操作耗时监控
    - 缓存命中率统计
    - 性能瓶颈识别
    - 优化建议生成
    """
    
    def __init__(self):
        """初始化监控器"""
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.cache_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'hits': 0, 'misses': 0})
        self.start_times: Dict[str, float] = {}
        self.enabled = True
    
    def start_operation(self, operation: str) -> str:
        """
        开始监控操作
        
        Args:
            operation: 操作名称
            
        Returns:
            操作ID（用于结束监控）
        """
        if not self.enabled:
            return operation
        
        operation_id = f"{operation}_{id(self)}"
        self.start_times[operation_id] = time.time()
        return operation_id
    
    def end_operation(self, operation_id: str):
        """
        结束监控操作
        
        Args:
            operation_id: 操作ID
        """
        if not self.enabled or operation_id not in self.start_times:
            return
        
        elapsed = time.time() - self.start_times[operation_id]
        del self.start_times[operation_id]
        
        # 提取操作名称
        operation = operation_id.rsplit('_', 1)[0]
        
        # 更新指标
        if operation not in self.metrics:
            self.metrics[operation] = PerformanceMetrics(operation)
        
        self.metrics[operation].update(elapsed)
        
        # 记录慢操作
        if elapsed > 0.1:  # 超过100ms
            logger.warning(f"[PERF] 慢操作: {operation} 耗时 {elapsed*1000:.2f}ms")
    
    def record_cache_hit(self, cache_name: str):
        """记录缓存命中"""
        if self.enabled:
            self.cache_stats[cache_name]['hits'] += 1
    
    def record_cache_miss(self, cache_name: str):
        """记录缓存未命中"""
        if self.enabled:
            self.cache_stats[cache_name]['misses'] += 1
    
    def get_cache_hit_rate(self, cache_name: str) -> float:
        """
        获取缓存命中率
        
        Args:
            cache_name: 缓存名称
            
        Returns:
            命中率 (0.0-1.0)
        """
        stats = self.cache_stats[cache_name]
        total = stats['hits'] + stats['misses']
        if total == 0:
            return 0.0
        return stats['hits'] / total
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Returns:
            性能摘要字典
        """
        summary = {
            'operations': {},
            'cache_stats': {},
            'bottlenecks': [],
            'recommendations': []
        }
        
        # 操作统计
        for operation, metrics in self.metrics.items():
            summary['operations'][operation] = metrics.to_dict()
        
        # 缓存统计
        for cache_name, stats in self.cache_stats.items():
            total = stats['hits'] + stats['misses']
            hit_rate = stats['hits'] / total if total > 0 else 0.0
            summary['cache_stats'][cache_name] = {
                'hits': stats['hits'],
                'misses': stats['misses'],
                'hit_rate': round(hit_rate, 3)
            }
        
        # 识别瓶颈
        for operation, metrics in self.metrics.items():
            if metrics.avg_time > 0.05:  # 平均超过50ms
                summary['bottlenecks'].append({
                    'operation': operation,
                    'avg_time_ms': round(metrics.avg_time * 1000, 2),
                    'count': metrics.count
                })
        
        # 生成优化建议
        summary['recommendations'] = self._generate_recommendations()
        
        return summary
    
    def _generate_recommendations(self) -> List[str]:
        """
        生成优化建议
        
        Returns:
            建议列表
        """
        recommendations = []
        
        # 检查缓存命中率
        for cache_name, stats in self.cache_stats.items():
            hit_rate = self.get_cache_hit_rate(cache_name)
            if hit_rate < 0.5 and stats['hits'] + stats['misses'] > 10:
                recommendations.append(
                    f"缓存 '{cache_name}' 命中率较低 ({hit_rate:.1%})，"
                    f"建议优化缓存键生成逻辑或增加缓存容量"
                )
        
        # 检查慢操作
        for operation, metrics in self.metrics.items():
            if metrics.avg_time > 0.1:  # 平均超过100ms
                recommendations.append(
                    f"操作 '{operation}' 平均耗时较长 ({metrics.avg_time*1000:.2f}ms)，"
                    f"建议优化算法或添加缓存"
                )
        
        return recommendations
    
    def save_report(self, filepath: str = "./performance_report.json"):
        """
        保存性能报告
        
        Args:
            filepath: 报告文件路径
        """
        try:
            summary = self.get_summary()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[PERF] 性能报告已保存: {filepath}")
        except Exception as e:
            logger.error(f"[PERF] 保存性能报告失败: {e}")
    
    def reset(self):
        """重置所有统计数据"""
        self.metrics.clear()
        self.cache_stats.clear()
        self.start_times.clear()
        logger.info("[PERF] 性能监控器已重置")
    
    def print_summary(self):
        """打印性能摘要"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print("性能监控摘要")
        print("=" * 60)
        
        # 操作统计
        if summary['operations']:
            print("\n【操作统计】")
            for op, metrics in summary['operations'].items():
                print(f"  {op}:")
                print(f"    调用次数: {metrics['count']}")
                print(f"    平均耗时: {metrics['avg_time_ms']:.2f}ms")
                print(f"    最小耗时: {metrics['min_time_ms']:.2f}ms")
                print(f"    最大耗时: {metrics['max_time_ms']:.2f}ms")
        
        # 缓存统计
        if summary['cache_stats']:
            print("\n【缓存统计】")
            for cache, stats in summary['cache_stats'].items():
                print(f"  {cache}:")
                print(f"    命中: {stats['hits']}, 未命中: {stats['misses']}")
                print(f"    命中率: {stats['hit_rate']:.1%}")
        
        # 瓶颈
        if summary['bottlenecks']:
            print("\n【性能瓶颈】")
            for bottleneck in summary['bottlenecks']:
                print(f"  {bottleneck['operation']}: "
                      f"{bottleneck['avg_time_ms']:.2f}ms "
                      f"(调用{bottleneck['count']}次)")
        
        # 优化建议
        if summary['recommendations']:
            print("\n【优化建议】")
            for i, rec in enumerate(summary['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("=" * 60 + "\n")


# 全局性能监控器实例
_global_monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return _global_monitor


def monitor_operation(operation: str):
    """
    操作监控装饰器
    
    用法：
    @monitor_operation("check_decision")
    def decide(self, candidates, context):
        ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            op_id = monitor.start_operation(operation)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                monitor.end_operation(op_id)
        return wrapper
    return decorator


__all__ = [
    'PerformanceMetrics',
    'PerformanceMonitor',
    'get_monitor',
    'monitor_operation'
]
