# OwlCode

终端 AI 编程助手，支持多 LLM 提供商（Anthropic、OpenAI、OpenAI 兼容接口），基于 Textual TUI 框架和异步 Python 构建。

## 安装

```bash
# 克隆仓库
git clone https://github.com/LY67198/OwlCode.git
cd OwlCode

# 安装依赖
uv sync --dev

# 全局安装
uv tool install --editable .
```

## 使用

```bash
# 交互式 TUI
owlcode

# 单次问答
owlcode -p "你的问题"
```

## 配置

在 `~/.owlcode/config.yaml` 或项目目录下 `.owlcode/config.yaml` 创建配置：

```yaml
providers:
  - name: deepseek
    protocol: openai-compat
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: ${OPENAI_API_KEY}

permission_mode: default
```

## 特性

- 多 LLM 提供商支持（Anthropic / OpenAI / 兼容接口）
- Textual TUI 交互式界面
- 完整的工具系统（Bash、文件读写、搜索等）
- 子代理与团队协作
- 技能系统（可扩展）
- MCP 服务器集成
- 会话持久化与恢复
- Hook 生命周期系统
