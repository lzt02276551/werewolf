import os
import logging

from agent_build_sdk.builder import AgentBuilder
from seer.seer_agent import SeerAgent
from villager.villager_agent import VillagerAgent
from witch.witch_agent import WitchAgent
from wolf.wolf_agent import WolfAgent
from guard.guard_agent import GuardAgent
from hunter.hunter_agent import HunterAgent
from wolf_king.wolf_king_agent import WolfKingAgent
from agent_build_sdk.model.roles import ROLE_VILLAGER, ROLE_WOLF, ROLE_SEER, ROLE_WITCH, ROLE_HUNTER, ROLE_GUARD, ROLE_WOLF_KING
from agent_build_sdk.sdk.werewolf_agent import WerewolfAgent

# 游戏结束处理器
from game_end_handler import set_learning_system

# 黄金路径学习系统（向后兼容增量学习）
try:
    import sys
    # 获取项目根目录（werewolf的父目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from golden_path_integration import GoldenPathLearningSystem
    GOLDEN_PATH_AVAILABLE = True
except ImportError as e:
    GOLDEN_PATH_AVAILABLE = False
    logging.warning(f"Golden Path learning system not available: {e}")

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化黄金路径学习系统（默认启用）
    learning_system = None
    ml_auto_train = os.getenv('ML_AUTO_TRAIN', 'true').lower() == 'true'  # 默认启用
    enable_golden_path = os.getenv('ENABLE_GOLDEN_PATH', 'true').lower() == 'true'  # 默认启用黄金路径
    
    if GOLDEN_PATH_AVAILABLE and ml_auto_train:
        try:
            learning_system = GoldenPathLearningSystem(
                model_dir=os.getenv('ML_MODEL_DIR', './ml_models'),
                data_dir=os.getenv('DATA_DIR', './game_data'),
                retrain_interval=int(os.getenv('ML_TRAIN_INTERVAL', '10')),
                min_samples=int(os.getenv('ML_MIN_SAMPLES', '50')),
                enable_golden_path=enable_golden_path  # 黄金路径开关
            )
            logging.info("=" * 60)
            if enable_golden_path:
                logging.info("✓ 黄金路径学习系统已启用 (三阶段渐进式学习)")
                logging.info(f"  当前阶段: Stage {learning_system.current_stage}")
                logging.info("  阶段一: 无监督学习 (语言模型)")
                logging.info("  阶段二: 监督学习 (身份识别) - 需要官方公布身份")
                logging.info("  阶段三: 强化学习 (策略优化) - 自我对弈")
            else:
                logging.info("✓ 增量学习系统已启用 (兼容模式)")
            logging.info("=" * 60)
            learning_system.print_statistics()
        except Exception as e:
            logging.error(f"✗ Failed to initialize learning system: {e}")
            learning_system = None
    elif not GOLDEN_PATH_AVAILABLE:
        logging.warning("⚠ Golden Path learning system not available")
    else:
        logging.info("ℹ Learning system disabled by ML_AUTO_TRAIN=false")
    
    # 初始化狼人杀智能体
    name = 'spy'
    agent = WerewolfAgent(name, model_name=os.getenv('MODEL_NAME'))
    
    # Register basic role
    agent.register_role_agent(ROLE_VILLAGER, VillagerAgent(model_name=os.getenv('MODEL_NAME')))
    
    # Wolf agent with dual-model architecture
    detection_model = os.getenv('DETECTION_MODEL_NAME', os.getenv('MODEL_NAME'))
    agent.register_role_agent(ROLE_WOLF, WolfAgent(
        model_name=os.getenv('MODEL_NAME'),
        analysis_model_name=detection_model
    ))
    
    agent.register_role_agent(ROLE_SEER, SeerAgent(model_name=os.getenv('MODEL_NAME')))
    # Witch agent with dual-model architecture
    agent.register_role_agent(ROLE_WITCH, WitchAgent(
        model_name=os.getenv('MODEL_NAME'),
        analysis_model_name=detection_model
    ))
    
    # Register new characters (12-player game)
    agent.register_role_agent(ROLE_GUARD, GuardAgent(model_name=os.getenv('MODEL_NAME')))
    agent.register_role_agent(ROLE_HUNTER, HunterAgent(model_name=os.getenv('MODEL_NAME')))
    
    # Wolf King agent with dual-model architecture
    agent.register_role_agent(ROLE_WOLF_KING, WolfKingAgent(
        model_name=os.getenv('MODEL_NAME'),
        analysis_model_name=detection_model
    ))
    
    # 如果启用增量学习，将其传递给游戏结束处理器
    if learning_system:
        # 设置全局学习系统
        set_learning_system(learning_system)
        
        # 将learning_system存储到agent（供角色智能体访问）
        agent.learning_system = learning_system
        
        logging.info("=" * 60)
        if enable_golden_path:
            logging.info("✓ 黄金路径学习系统已集成")
            logging.info("=" * 60)
            logging.info("  ✅ 游戏结束时会自动收集数据")
            logging.info(f"  ✅ 每{learning_system.retrain_interval}局会自动重训练模型")
            logging.info(f"  ✅ 当前阶段: Stage {learning_system.current_stage}")
            logging.info("  ✅ AI会通过三阶段学习变得空前强大！")
            logging.info("  ✅ 无需手动操作，完全自动化！")
        else:
            logging.info("✓ 增量学习系统已集成 (兼容模式)")
            logging.info("=" * 60)
            logging.info("  ✅ 游戏结束时会自动收集数据")
            logging.info(f"  ✅ 每{learning_system.retrain_interval}局会自动重训练模型")
            logging.info("  ✅ ML会随着对局越来越强！")
            logging.info("  ✅ 无需手动操作，完全自动化！")
        logging.info("=" * 60)
    
    agent_builder = AgentBuilder(name, agent=agent)
    agent_builder.start()