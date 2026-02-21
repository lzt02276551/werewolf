"""
配置加载器

从YAML文件加载配置，支持环境变量覆盖
验证需求: AC-2.3.1, AC-2.3.2, AC-2.3.3
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..models.config import OptimizationConfig

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """配置错误异常"""
    pass


def get_config_path(config_name: str = "scoring_weights.yaml") -> Path:
    """
    获取配置文件路径
    
    参数:
        config_name: 配置文件名
    
    返回:
        配置文件路径
    """
    # 优先从环境变量获取配置目录
    config_dir = os.getenv('WEREWOLF_CONFIG_DIR')
    
    if config_dir:
        config_path = Path(config_dir) / config_name
    else:
        # 默认使用项目根目录下的config目录
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / config_name
    
    return config_path


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """
    加载YAML配置文件
    
    参数:
        config_path: 配置文件路径
    
    返回:
        配置字典
    
    异常:
        ConfigurationError: 配置文件不存在或格式错误
    """
    if not config_path.exists():
        raise ConfigurationError(f"配置文件不存在: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config or {}
    except yaml.YAMLError as e:
        raise ConfigurationError(f"配置文件格式错误: {e}")


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用环境变量覆盖
    
    环境变量格式: WEREWOLF_<section>_<key>=value
    例如: WEREWOLF_CACHE_ENABLED=false
    
    参数:
        config: 原始配置字典
    
    返回:
        应用环境变量后的配置字典
    
    验证需求: AC-2.3.3
    """
    # 扫描环境变量
    for key, value in os.environ.items():
        if not key.startswith('WEREWOLF_'):
            continue
        
        # 解析环境变量名
        parts = key[9:].lower().split('_', 1)  # 去掉 WEREWOLF_ 前缀
        if len(parts) != 2:
            continue
        
        section, param = parts
        
        # 应用覆盖
        if section in config:
            # 尝试转换类型
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # 保持字符串
            
            config[section][param] = value
            logger.info(f"环境变量覆盖配置: {section}.{param} = {value}")
    
    return config


def load_config(
    config_path: Optional[Path] = None,
    use_env_overrides: bool = True
) -> OptimizationConfig:
    """
    加载优化配置
    
    参数:
        config_path: 配置文件路径（可选，默认使用标准路径）
        use_env_overrides: 是否应用环境变量覆盖
    
    返回:
        验证后的配置对象
    
    异常:
        ConfigurationError: 配置加载或验证失败
    
    验证需求: AC-2.3.1, AC-2.3.2, AC-2.3.3
    """
    try:
        # 确定配置文件路径
        if config_path is None:
            config_path = get_config_path()
        
        # 加载YAML配置
        if config_path.exists():
            config_dict = load_yaml_config(config_path)
            logger.info(f"已加载配置文件: {config_path}")
        else:
            logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
            return OptimizationConfig.default()
        
        # 应用环境变量覆盖
        if use_env_overrides:
            config_dict = apply_env_overrides(config_dict)
        
        # 验证配置
        validated_config = OptimizationConfig(**config_dict)
        return validated_config
        
    except FileNotFoundError:
        logger.warning("配置文件不存在，使用默认配置")
        return OptimizationConfig.default()
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        raise ConfigurationError(f"无法加载配置: {e}")
