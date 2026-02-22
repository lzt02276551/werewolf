# 魔搭平台部署指南

## 问题诊断

你遇到的"Internal Server Error"通常由以下原因引起：

### 1. 环境变量缺失 ✓ 已修复
- 缺少 `MODEL_NAME`（必需）
- 缺少 `OPENAI_API_KEY`（必需）
- 缺少 `OPENAI_BASE_URL`（必需）

### 2. 健康检查失败 ✓ 已修复
- Dockerfile中的健康检查访问了不存在的 `/health` 端点
- 已注释掉健康检查

### 3. 启动脚本问题 ✓ 已改进
- 添加了环境变量验证
- 添加了模块导入测试

## 已修复的文件

1. **ms_deploy.json** - 添加了所有必需的环境变量
2. **Dockerfile** - 注释掉了健康检查
3. **start.sh** - 添加了启动前验证

## 部署步骤

### 1. 提交代码到Git仓库
```bash
git add .
git commit -m "修复魔搭平台部署配置"
git push
```

### 2. 在魔搭平台重新部署
- 进入你的创空间
- 点击"重新构建"或"重新部署"
- 等待构建完成（约3-5分钟）

### 3. 查看日志
如果仍然失败，查看部署日志：
- 点击"日志"标签
- 查找错误信息
- 常见错误：
  - `ModuleNotFoundError`: 缺少依赖包
  - `KeyError`: 环境变量未设置
  - `ConnectionError`: API密钥无效

## 环境变量说明

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| MODEL_NAME | 主对话模型 | deepseek-chat |
| OPENAI_API_KEY | API密钥 | sk-xxx |
| OPENAI_BASE_URL | API地址 | https://api.deepseek.com/v1 |
| DETECTION_MODEL_NAME | 分析模型 | deepseek-reasoner |
| ENABLE_GOLDEN_PATH | 启用高级学习 | false（资源受限时） |
| ML_AUTO_TRAIN | 启用ML训练 | true |

## 资源配置

当前配置：`platform/2v-cpu-16g-mem`
- CPU: 2核
- 内存: 16GB
- 适合轻量级部署

如果需要更多资源，可以修改 `ms_deploy.json` 中的 `resource_configuration`。

## 测试部署

部署成功后，访问：
```
https://你的空间名.modelscope.cn
```

应该看到狼人杀游戏界面，而不是错误页面。

## 常见问题

### Q: 仍然显示Internal Server Error
A: 检查以下几点：
1. 环境变量是否正确设置（特别是API密钥）
2. API密钥是否有效（可以在本地测试）
3. 查看部署日志中的具体错误信息

### Q: 构建超时
A: 
1. 检查网络连接
2. 尝试使用国内镜像源
3. 减少依赖包数量

### Q: 内存不足
A: 
1. 确认使用的是 `requirements-lite.txt`
2. 设置 `ENABLE_GOLDEN_PATH=false`
3. 升级资源配置

## 本地测试

在推送到魔搭之前，可以本地测试Docker镜像：

```bash
# 构建镜像
docker build -t werewolf-game .

# 运行容器
docker run -p 7860:7860 \
  -e MODEL_NAME=deepseek-chat \
  -e OPENAI_API_KEY=你的密钥 \
  -e OPENAI_BASE_URL=https://api.deepseek.com/v1 \
  werewolf-game

# 访问
curl http://localhost:7860
```

## 下一步

如果问题仍然存在，请提供：
1. 完整的部署日志
2. 浏览器控制台的错误信息
3. 网络请求的响应内容
