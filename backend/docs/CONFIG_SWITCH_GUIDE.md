# LLM配置快速切换工具

本目录包含用于快速切换LLM配置的批处理脚本。

## 📋 可用脚本

### 1. `show_config.bat` - 查看当前配置
显示当前`.env`文件中的LLM配置。

**使用方法:**
```batch
show_config.bat
```

**输出示例:**
```
========================================
  当前 LLM 配置
========================================

📊 当前配置:
  LLM Provider: openai
  Backend URL:  http://127.0.0.1:1234/v1
  Deep Model:   Qwen/Qwen3-30B-A3B-Instruct-2507
  Quick Model:  Qwen/Qwen3-30B-A3B-Instruct-2507

✓ 当前使用: LM Studio 本地服务器

⚠️  请确保:
  1. LM Studio 服务器已启动
  2. 模型已加载: Qwen/Qwen3-30B-A3B-Instruct-2507

💡 切换到云端服务: switch_to_cloud.bat
```

### 2. `switch_to_local.bat` - 切换到本地服务器
将配置切换为使用LM Studio本地服务器。

**使用方法:**
```batch
switch_to_local.bat
```

**功能:**
- 自动注释掉SiliconFlow配置
- 启用LM Studio配置
- 自动创建配置备份 (`.env.backup`)

**切换后配置:**
```bash
LLM_PROVIDER=openai
BACKEND_URL=http://127.0.0.1:1234/v1
DEEP_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
QUICK_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
```

### 3. `switch_to_cloud.bat` - 切换到云端服务
将配置切换为使用SiliconFlow云端服务。

**使用方法:**
```batch
switch_to_cloud.bat
```

**功能:**
- 自动注释掉LM Studio配置
- 启用SiliconFlow配置
- 自动创建配置备份 (`.env.backup`)

**切换后配置:**
```bash
LLM_PROVIDER=siliconflow
BACKEND_URL=https://api.siliconflow.cn/v1
DEEP_THINK_LLM=Qwen/Qwen3-30B-A3B-Thinking-2507
QUICK_THINK_LLM=Qwen/Qwen3-30B-A3B-Instruct-2507
```

## 🔄 使用流程

### 场景1: 在公司使用本地模型
```batch
# 1. 启动 LM Studio 并加载模型
# 2. 切换配置
switch_to_local.bat

# 3. 验证配置
show_config.bat

# 4. 启动API服务器
uvicorn api.main:app --reload
```

### 场景2: 在家使用云端服务
```batch
# 1. 切换配置
switch_to_cloud.bat

# 2. 验证配置
show_config.bat

# 3. 确保SILICONFLOW_API_KEY已配置
# 4. 启动API服务器
uvicorn api.main:app --reload
```

### 场景3: 临时测试不同配置
```batch
# 1. 查看当前配置
show_config.bat

# 2. 切换到另一个配置
switch_to_cloud.bat  # 或 switch_to_local.bat

# 3. 运行测试
python test_lm_studio.py  # 或其他测试

# 4. 切换回原配置
switch_to_local.bat  # 或 switch_to_cloud.bat
```

## 🔒 安全性

### 配置备份
- 首次运行切换脚本时，会自动创建 `.env.backup`
- 如果配置出错，可以手动恢复: `copy .env.backup .env`

### API密钥保护
- 切换脚本**不会**修改API密钥（如`SILICONFLOW_API_KEY`）
- API密钥始终保持在`.env`文件中
- 确保`.env`文件不要提交到Git（已在`.gitignore`中）

## ⚠️ 注意事项

1. **重启服务**: 切换配置后，需要重启API服务器才能生效
   ```batch
   # Windows: 按 Ctrl+C 停止服务器，然后重新启动
   uvicorn api.main:app --reload
   ```

2. **LM Studio状态**: 使用本地配置前，确保:
   - LM Studio服务器已启动
   - 模型已加载
   - 端口1234未被占用

3. **云端服务状态**: 使用云端配置前，确保:
   - `SILICONFLOW_API_KEY`已配置
   - 网络连接正常
   - API密钥有效且有余额

4. **配置冲突**: 不要同时启用两种配置，否则会使用最后一个`LLM_PROVIDER`的值

## 🛠️ 故障排查

### 问题1: 脚本执行后配置未改变
**原因**: 可能权限不足或文件被占用
**解决**:
```batch
# 1. 以管理员身份运行
# 2. 关闭所有正在编辑.env的程序
# 3. 手动编辑.env文件
```

### 问题2: 切换后服务器报错
**原因**: 配置不匹配
**解决**:
```batch
# 1. 运行 show_config.bat 检查配置
# 2. 确保服务器已重启
# 3. 检查日志错误信息
```

### 问题3: 找不到.env文件
**原因**: 当前目录不对
**解决**:
```batch
# 确保在项目根目录运行脚本
cd "D:\Program Files (x86)\CodeRepos\HiddenGem\reference\TradingAgents-CN"
show_config.bat
```

## 📚 相关文档

- [LM Studio配置指南](./docs/LM_STUDIO_CONFIG.md)
- [Timeout修改记录](./docs/TIMEOUT_CHANGES.md)
- [环境变量示例](./.env.example)

## 🔧 高级用法

### 手动切换
如果脚本不工作，可以手动编辑`.env`文件：

1. 打开 `.env` 文件
2. 找到 LLM 配置部分
3. 注释掉不使用的配置（添加`#`）
4. 取消注释要使用的配置（删除`#`）
5. 保存文件
6. 重启API服务器

### 创建自定义配置
你可以添加自定义配置方案：

```bash
# 🚀 方案3: DeepSeek (自定义)
# LLM_PROVIDER=deepseek
# BACKEND_URL=https://api.deepseek.com
# DEEP_THINK_LLM=deepseek-chat
# QUICK_THINK_LLM=deepseek-chat
```

然后创建对应的切换脚本 `switch_to_deepseek.bat`。

---

**最后更新**: 2025-01-08
**维护者**: Claude Code
