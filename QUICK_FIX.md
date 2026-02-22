# 🚀 快速修复指南

## ✅ 问题已找到！

### 错误原因
```
FileNotFoundError: [Errno 2] No such file or directory: 'README.md'
```

**根本原因：** Dockerfile 没有复制 README.md 文件，但 agent_build_sdk 在访问根路径时需要读取它。

### 已修复
- ✅ Dockerfile 已更新，添加了 `COPY README.md ./`
- ✅ 应用本身运行正常（所有Agent都成功初始化）
- ✅ 服务器成功启动在端口 7860

---

## 🔧 立即修复（2步）

### 第1步：提交更新的代码

```bash
git add Dockerfile
git commit -m "修复：添加README.md到Docker镜像"
git push
```

### 第2步：在魔搭平台重新部署

进入你的创空间，点击"重新构建"或"重新部署"

---

## 📋 完整环境变量列表

### 必需（缺一不可）
```bash
MODEL_NAME=deepseek-chat
OPENAI_API_KEY=sk-6320c699e7004706be3af12cde1eb3a6
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

### 推荐（提升性能）
```bash
DETECTION_MODEL_NAME=deepseek-reasoner
DETECTION_API_KEY=sk-6320c699e7004706be3af12cde1eb3a6
DETECTION_BASE_URL=https://api.deepseek.com/v1
```

### 可选（功能开关）
```bash
ENABLE_GOLDEN_PATH=false
ML_AUTO_TRAIN=true
ML_TRAIN_INTERVAL=10
ML_MIN_SAMPLES=50
```

---

## 🔍 如何查看运行日志

1. 进入魔搭创空间
2. 点击顶部的"日志"标签
3. 选择"运行日志"或"容器日志"
4. 查看最新的日志输出

---

## ⚠️ 常见错误

### 错误1：MODEL_NAME未设置
```
✗ 错误: MODEL_NAME 环境变量未设置
```
**解决**：在平台添加 `MODEL_NAME=deepseek-chat`

### 错误2：API密钥无效
```
AuthenticationError: Invalid API key
```
**解决**：检查API密钥是否正确，账户是否有余额

### 错误3：模块导入失败
```
✗ 错误: 无法导入werewolf模块
```
**解决**：重新构建镜像，确保werewolf目录被正确复制

---

## 📞 还是不行？

如果按照上述步骤操作后仍然失败：

1. **复制完整的运行日志**
2. **截图错误页面**
3. **检查API密钥余额**
4. **尝试使用其他模型**（如 `gpt-3.5-turbo`）

---

## ✨ 成功标志

部署成功后，访问你的创空间URL，应该看到：
- 狼人杀游戏界面
- 或者 FastAPI 文档页面（/docs）
- **不再是** "Internal Server Error"

---

## 📝 更新记录

- 添加了启动前诊断脚本
- 增强了环境变量检查
- 改进了错误提示信息
- 添加了详细的日志输出

现在重新部署，日志会更详细，更容易定位问题！
