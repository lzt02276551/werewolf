# 狼人杀AI系统 - 魔搭平台部署指南

## 部署版本说明

此版本为轻量级部署版本，仅保留系统运行必须的核心组件。

### 包含的功能
✅ 7种角色完整游戏逻辑（村民、狼人、预言家、女巫、守卫、猎人、狼王）
✅ LLM驱动的智能AI玩家
✅ 基础ML增强（sklearn异常检测）
✅ 自动数据收集和模型训练
✅ FastAPI Web界面

### 移除的功能
❌ Golden Path三阶段深度学习（torch/transformers）
❌ XGBoost高级集成学习
❌ 数据可视化工具（matplotlib/seaborn）
❌ 开发和测试工具

## 资源需求

- CPU: 2核
- 内存: 8GB（推荐）/ 4GB（最低）
- 磁盘: 2GB
- 安装大小: 约150MB

## 部署步骤

### 1. 准备文件

确保以下文件存在：
- `Dockerfile` - Docker构建配置
- `requirements-lite.txt` - 轻量级依赖
- `ms_deploy.json` - 魔搭平台配置
- `start.sh` - 启动脚本
- `werewolf/` - 核心代码目录
- `config.py` - 配置文件
- `utils.py` - 工具函数

### 2. 环境变量配置

在 `ms_deploy.json` 中已配置：

```json
{
  "ENABLE_GOLDEN_PATH": "false",     // 禁用深度学习
  "ML_AUTO_TRAIN": "true",           // 启用基础ML训练
  "ML_TRAIN_INTERVAL": "10",         // 每10局训练一次
  "ML_MIN_SAMPLES": "50",            // 最少50个样本开始训练
  "ML_MODEL_DIR": "./ml_models",     // 模型保存目录
  "DATA_DIR": "./game_data",         // 数据保存目录
  "LOG_LEVEL": "INFO"                // 日志级别
}
```

### 3. 本地测试（可选）

```bash
# 构建镜像
docker build -t werewolf-lite .

# 运行容器
docker run -p 7860:7860 \
  -e MODEL_NAME=your_model_name \
  -e DETECTION_MODEL_NAME=your_detection_model \
  werewolf-lite
```

### 4. 魔搭平台部署

1. 将代码推送到Git仓库
2. 在魔搭平台创建新的创空间
3. 选择"从Git导入"
4. 配置环境变量（MODEL_NAME等）
5. 点击部署

## 核心文件说明

### 必需文件
- `werewolf/app.py` - 主应用入口
- `werewolf/*/` - 各角色智能体实现
- `werewolf/core/` - 核心框架
- `werewolf/common/` - 公共组件
- `config.py` - 全局配置
- `utils.py` - 工具函数

### 可选文件（已排除）
- `ml_golden_path/` - 深度学习模块
- `golden_path_integration.py` - Golden Path集成
- `test_*.py` - 测试文件
- `check_*.py` - 检查脚本
- `*.md` - 文档文件（除README.md）

## 性能优化建议

### 内存优化
- 使用轻量级依赖（已配置）
- 禁用Golden Path（已配置）
- 减少训练频率（调整ML_TRAIN_INTERVAL）

### 启动速度优化
- 使用Python 3.10-slim镜像
- 最小化系统依赖
- 预编译Python字节码

### 运行时优化
- 调整ML_MIN_SAMPLES降低训练门槛
- 使用INFO日志级别
- 定期清理旧数据

## 故障排查

### 内存不足
```bash
# 降低资源配置
"resource_configuration": "platform/2v-cpu-4g-mem"

# 禁用ML训练
"ML_AUTO_TRAIN": "false"
```

### 启动失败
```bash
# 检查日志
docker logs <container_id>

# 验证依赖
pip list | grep -E "fastapi|openai|sklearn"
```

### 模型加载失败
```bash
# 确保环境变量正确
echo $MODEL_NAME
echo $DETECTION_MODEL_NAME

# 检查模型目录
ls -la ml_models/
```

## 监控和维护

### 日志查看
```bash
# 应用日志
tail -f /app/logs/app.log

# 系统日志
docker logs -f <container_id>
```

### 数据管理
```bash
# 查看收集的数据
ls -lh game_data/

# 清理旧数据（保留最近100局）
find game_data/ -name "*.json" | sort -r | tail -n +101 | xargs rm
```

### 模型管理
```bash
# 查看模型文件
ls -lh ml_models/

# 备份模型
tar -czf ml_models_backup.tar.gz ml_models/
```

## 升级路径

如果需要更强大的功能，可以升级到完整版：

1. 使用 `requirements.txt` 替代 `requirements-lite.txt`
2. 设置 `ENABLE_GOLDEN_PATH=true`
3. 增加资源配置到 16GB 内存
4. 调整训练参数（ML_MIN_SAMPLES=1800）

## 技术支持

- 问题反馈：提交Issue到Git仓库
- 文档：查看项目README.md
- 社区：魔搭平台讨论区

## 版本信息

- 版本: 1.0.0-lite
- 更新日期: 2024
- 适用平台: 魔搭创空间
- Python版本: 3.10
