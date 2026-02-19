# -*- coding: utf-8 -*-
"""
平民代理人模块（重构版）
模块化架构，应用面向对象设计原则
"""

from .villager_agent import VillagerAgent
from .config import VillagerConfig

__all__ = ['VillagerAgent', 'VillagerConfig']

