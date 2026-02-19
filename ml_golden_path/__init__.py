"""
ML Golden Path - 三阶段渐进式学习系统
Three-Stage Progressive Learning System for Werewolf AI

阶段一：无监督/自监督学习 (Stage 1: Unsupervised Learning)
- WerewolfLM: 狼人杀专业语言模型
- 掩码语言模型 (MLM)
- 对比学习 (Contrastive Learning)

阶段二：监督学习 (Stage 2: Supervised Learning)
- IdentityDetector: 超级身份识别模型
- 多任务学习 (Multi-task Learning)
- 注意力机制 (Attention Mechanism)

阶段三：强化学习 (Stage 3: Reinforcement Learning)
- RLAgent: 强化学习智能体
- PPO算法 (Proximal Policy Optimization)
- 模仿学习 (Imitation Learning)
"""

import logging

logger = logging.getLogger(__name__)

# 版本信息
__version__ = '1.0.0'
__author__ = 'Werewolf AI Team'

# 尝试导入各阶段模块（优雅降级）
try:
    from .stage1_unsupervised import (
        WerewolfLM,
        WerewolfSpeechDataset,
        Stage1Trainer,
        prepare_unsupervised_data
    )
    STAGE1_AVAILABLE = True
    logger.info("✓ Stage 1 (Unsupervised Learning) modules loaded")
except ImportError as e:
    STAGE1_AVAILABLE = False
    logger.warning(f"⚠ Stage 1 modules not available: {e}")
    WerewolfLM = None
    WerewolfSpeechDataset = None
    Stage1Trainer = None
    prepare_unsupervised_data = None

try:
    from .stage2_supervised import (
        IdentityDetector,
        LabeledGameDataset,
        Stage2Trainer,
        prepare_labeled_data
    )
    STAGE2_AVAILABLE = True
    logger.info("✓ Stage 2 (Supervised Learning) modules loaded")
except ImportError as e:
    STAGE2_AVAILABLE = False
    logger.warning(f"⚠ Stage 2 modules not available: {e}")
    IdentityDetector = None
    LabeledGameDataset = None
    Stage2Trainer = None
    prepare_labeled_data = None

try:
    from .stage3_reinforcement import (
        RLAgent,
        WerewolfEnv,
        PPOTrainer,
        ImitationLearner,
        PolicyNetwork,
        ValueNetwork
    )
    STAGE3_AVAILABLE = True
    logger.info("✓ Stage 3 (Reinforcement Learning) modules loaded")
except ImportError as e:
    STAGE3_AVAILABLE = False
    logger.warning(f"⚠ Stage 3 modules not available: {e}")
    RLAgent = None
    WerewolfEnv = None
    PPOTrainer = None
    ImitationLearner = None
    PolicyNetwork = None
    ValueNetwork = None

# 导出所有公共接口
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    
    # 可用性标志
    'STAGE1_AVAILABLE',
    'STAGE2_AVAILABLE',
    'STAGE3_AVAILABLE',
    
    # Stage 1
    'WerewolfLM',
    'WerewolfSpeechDataset',
    'Stage1Trainer',
    'prepare_unsupervised_data',
    
    # Stage 2
    'IdentityDetector',
    'LabeledGameDataset',
    'Stage2Trainer',
    'prepare_labeled_data',
    
    # Stage 3
    'RLAgent',
    'WerewolfEnv',
    'PPOTrainer',
    'ImitationLearner',
    'PolicyNetwork',
    'ValueNetwork',
]


def get_available_stages():
    """
    获取可用的训练阶段
    
    Returns:
        dict: 各阶段的可用性状态
    """
    return {
        'stage1': STAGE1_AVAILABLE,
        'stage2': STAGE2_AVAILABLE,
        'stage3': STAGE3_AVAILABLE
    }


def check_dependencies():
    """
    检查依赖项是否完整
    
    Returns:
        dict: 依赖检查结果
    """
    results = {
        'torch': False,
        'transformers': False,
        'all_stages_available': False
    }
    
    try:
        import torch
        results['torch'] = True
    except ImportError:
        pass
    
    try:
        import transformers
        results['transformers'] = True
    except ImportError:
        pass
    
    results['all_stages_available'] = (
        STAGE1_AVAILABLE and 
        STAGE2_AVAILABLE and 
        STAGE3_AVAILABLE
    )
    
    return results


def print_status():
    """打印模块状态信息"""
    print("=" * 60)
    print("ML Golden Path - Module Status")
    print("=" * 60)
    print(f"Version: {__version__}")
    print()
    print("Stage Availability:")
    print(f"  Stage 1 (Unsupervised): {'✓ Available' if STAGE1_AVAILABLE else '✗ Not Available'}")
    print(f"  Stage 2 (Supervised):   {'✓ Available' if STAGE2_AVAILABLE else '✗ Not Available'}")
    print(f"  Stage 3 (Reinforcement):{'✓ Available' if STAGE3_AVAILABLE else '✗ Not Available'}")
    print()
    
    deps = check_dependencies()
    print("Dependencies:")
    print(f"  PyTorch:      {'✓ Installed' if deps['torch'] else '✗ Not Installed'}")
    print(f"  Transformers: {'✓ Installed' if deps['transformers'] else '✗ Not Installed'}")
    print()
    
    if deps['all_stages_available']:
        print("✓ All stages are ready for training!")
    else:
        print("⚠ Some stages are not available. Install missing dependencies:")
        if not deps['torch']:
            print("  pip install torch")
        if not deps['transformers']:
            print("  pip install transformers")
    print("=" * 60)


# 模块加载时的初始化
if __name__ != '__main__':
    # 静默加载，只在调试时输出
    logger.debug(f"ML Golden Path v{__version__} initialized")
    logger.debug(f"Available stages: {sum([STAGE1_AVAILABLE, STAGE2_AVAILABLE, STAGE3_AVAILABLE])}/3")
