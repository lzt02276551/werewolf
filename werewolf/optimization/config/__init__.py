"""
配置管理模块

提供配置加载、环境变量覆盖等功能
"""

from .config_loader import load_config, get_config_path

__all__ = ['load_config', 'get_config_path']
