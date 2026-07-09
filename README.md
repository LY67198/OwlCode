# OwlCode

```
 ┌────┐
 │◉ ◉│   终端 AI 编程助手
 │ ◠ │
 └────┘
```

OwlCode 是一个类 Claude Code 的终端 AI 编程助手，支持多 LLM 提供商，基于 Textual TUI 框架和异步 Python 构建。

## 安装

```bash
git clone https://github.com/LY67198/OwlCode.git
cd OwlCode
uv sync --dev
uv tool install --editable .
```

## 使用

```bash
owlcode                      # 交互式 TUI
owlcode -p "你的问题"         # 单次问答
ANTHROPIC_API_KEY=sk-xxx owlcode -p "hello"   # 直接指定 API key
```

## 配置

创建 `~/.owlcode/config.yaml` 或 `.owlcode/config.yaml`：

```yaml
providers:
  - name: deepseek
    protocol: openai-compat
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: ${OPENAI_API_KEY}

permission_mode: default   # default | acceptEdits | plan | bypassPermissions
```

支持三种协议：`anthropic` / `openai` / `openai-compat`。API key 支持 `${ENV}` 环境变量语法。

配置合并顺序：`~/.owlcode/` → `.owlcode/` → `.owlcode/config.local.yaml`

## 特性

- **多 LLM 提供商** — Anthropic、OpenAI 及所有兼容 Chat Completions API 的第三方提供商
- **Textual TUI** — 终端交互界面，支持权限弹窗、计划模式、会话管理
- **工具系统** — Bash、文件读写、代码编辑、内容搜索、Glob 匹配
- **子代理** — 异步子代理分派，支持隔离工作树
- **团队协作** — 多代理团队，进程内/tmux/iTerm2 等多种后端
- **技能系统** — 可扩展的 Markdown 定义技能，支持自定义工具
- **MCP 集成** — Model Context Protocol 客户端管理
- **会话持久化** — 自动保存/恢复会话，记忆提取与召回
- **Hook 系统** — 生命周期钩子（pre_tool_call、post_tool_call 等）
- **斜杠命令** — 内置 `/help`、`/memory`、`/skills`、`/plan` 等命令

## 项目结构

```
owlcode/
├── agent.py          # 核心代理循环
├── app.py            # Textual TUI
├── client.py         # 多提供商 LLM 客户端
├── config.py         # 配置加载与合并
├── tools/            # 工具注册与实现
├── agents/           # 子代理定义与管理
├── teams/            # 多代理团队
├── skills/           # 技能系统
├── memory/           # 记忆与召回
├── permissions/      # 权限检查
├── hooks/            # 生命周期钩子
├── mcp/              # MCP 客户端
├── commands/         # 斜杠命令
├── context/          # 上下文管理
└── worktree/         # Git 工作树隔离
```

## 开发

```bash
uv sync --dev       # 安装开发依赖
uv run pytest       # 运行全部测试
uv run pytest -v    # 详细输出
```
