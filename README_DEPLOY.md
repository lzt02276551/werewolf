# 🚀 魔搭平台部署 - 快速开始

## ⚡ 一键部署

### Windows用户
```cmd
quick_deploy.bat
```

### Linux/Mac用户
```bash
chmod +x quick_deploy.sh
./quick_deploy.sh
```

## 📋 部署前准备

### 1. 获取API密钥
访问 [DeepSeek平台](https://platform.deepseek.com/) 获取API密钥

### 2. 运行检查
```bash
python check_deploy_readiness.py
```

应该看到: `✓ 所有检查通过!`

### 3. 配置魔搭平台环境变量

**方案A: 单模型模式 (推荐新手)**

只需配置3个变量:

| 变量名 | 值 |
|--------|-----|
| `MODEL_NAME` | `deepseek-chat` |
| `OPENAI_API_KEY` | `sk-你的密钥` |
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` |

**方案B: 双模型模式 (推荐生产)**

需要配置6个变量:

| 变量名 | 值 |
|--------|-----|
| `MODEL_NAME` | `deepseek-chat` |
| `OPENAI_API_KEY` | `sk-你的密钥` |
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` |
| `DETECTION_MODEL_NAME` | `deepseek-reasoner` |
| `DETECTION_API_KEY` | `sk-你的密钥` (可以相同) |
| `DETECTION_BASE_URL` | `https://api.deepseek.com/v1` |

💡 **提示**: 两个密钥可以使用相同的值!

## 📚 详细文档

- 📖 [魔搭部署指南.md](魔搭部署指南.md) - 完整部署说明
- 🔄 [部署配置对比.md](部署配置对比.md) - 单模型vs双模型对比
- 🎯 [魔搭平台单模型部署说明.md](魔搭平台单模型部署说明.md) - 单模型详解
- ✅ [部署前最终检查.md](部署前最终检查.md) - 检查清单
- 📊 [部署总结.md](部署总结.md) - 已完成工作总结

## 🔧 手动部署

如果不使用自动脚本:

```bash
# 1. 检查
python check_deploy_readiness.py

# 2. 提交
git add .
git commit -m "准备部署到魔搭平台"
git push origin main

# 3. 在魔搭平台点击"重新构建"
```

## ❓ 遇到问题?

1. 查看 [魔搭部署指南.md](魔搭部署指南.md) 的故障排查部分
2. 检查魔搭平台的部署日志
3. 确认环境变量设置正确

## ✅ 部署成功标志

- ✓ 应用状态显示"运行中"
- ✓ 可以访问创空间URL
- ✓ 游戏界面正常显示
- ✓ AI玩家可以正常对话

## 🎮 支持的角色

- 🐺 狼人 / 👑 狼王
- 👨 村民 / 🔮 预言家
- 🧙 女巫 / 🛡️ 守卫 / 🏹 猎人

---

**准备好了? 开始部署吧! 🚀**
