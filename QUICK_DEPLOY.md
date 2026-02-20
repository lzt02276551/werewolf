# 快速部署指南

## 一键部署到魔搭平台

### 前置准备

1. 确保你有魔搭平台账号
2. 准备好OpenAI API密钥或兼容的模型服务

### 部署步骤

#### 步骤1: 检查部署就绪状态

```bash
python check_deploy_ready.py
```

应该看到 "✅ 所有检查通过！"

#### 步骤2: 推送代码到Git仓库

```bash
git add .
git commit -m "准备部署到魔搭平台"
git push origin main
```

#### 步骤3: 在魔搭平台创建创空间

1. 访问 https://modelscope.cn/studios
2. 点击"创建创空间"
3. 选择"从Git导入"
4. 输入你的Git仓库地址
5. 选择分支（通常是main）

#### 步骤4: 配置环境变量

在魔搭平台的"设置"页面添加以下环境变量：

**必需变量：**
```
MODEL_NAME=qwen-plus  # 或你使用的模型名称
```

**可选变量（已在ms_deploy.json中配置）：**
```
DETECTION_MODEL_NAME=qwen-plus  # 分析模型，默认同MODEL_NAME
ENABLE_GOLDEN_PATH=false        # 已配置
ML_AUTO_TRAIN=true              # 已配置
ML_TRAIN_INTERVAL=10            # 已配置
ML_MIN_SAMPLES=50               # 已配置
LOG_LEVEL=INFO                  # 已配置
```

**如果使用自定义OpenAI服务：**
```
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://your-api-endpoint.com/v1
```

#### 步骤5: 启动部署

1. 点击"部署"按钮
2. 等待构建完成（约3-5分钟）
3. 部署成功后会显示访问地址

#### 步骤6: 验证部署

访问创空间地址，应该能看到狼人杀游戏界面。

## 资源配置说明

当前配置：`platform/2v-cpu-8g-mem`（2核CPU + 8GB内存）

### 如果遇到资源不足

编辑 `ms_deploy.json`：

```json
{
  "resource_configuration": "platform/2v-cpu-4g-mem"  // 降低到4GB
}
```

或禁用ML训练：

```json
{
  "environment_variables": [
    {"name": "ML_AUTO_TRAIN", "value": "false"}
  ]
}
```

## 常见问题

### Q: 构建失败，提示依赖安装错误

A: 检查 `requirements-lite.txt` 是否正确，确保没有包含 torch/transformers

### Q: 启动后无法访问

A: 检查端口配置，确保使用7860端口（魔搭平台要求）

### Q: 模型调用失败

A: 检查 MODEL_NAME 环境变量是否正确设置

### Q: 内存不足

A: 降低资源配置或禁用ML训练

## 性能优化建议

### 降低内存使用
```json
{
  "ML_AUTO_TRAIN": "false",           // 禁用训练
  "ML_MIN_SAMPLES": "100"             // 提高训练门槛
}
```

### 提高响应速度
```json
{
  "LOG_LEVEL": "WARNING",             // 减少日志
  "ML_TRAIN_INTERVAL": "20"           // 降低训练频率
}
```

## 监控和维护

### 查看日志
在魔搭平台的"日志"页面查看实时日志

### 重启服务
在"设置"页面点击"重启"

### 更新代码
1. 推送新代码到Git仓库
2. 在魔搭平台点击"重新部署"

## 成本估算

- 免费额度：通常包含一定的计算资源
- 付费资源：根据实际使用的CPU/内存计费
- 建议：开发测试阶段使用最小配置

## 下一步

部署成功后，你可以：

1. 邀请朋友一起玩狼人杀
2. 观察AI的表现
3. 查看ML训练效果（如果启用）
4. 根据需要调整配置

## 技术支持

- 文档：查看 DEPLOY_README.md
- 问题：提交Issue到Git仓库
- 社区：魔搭平台讨论区
