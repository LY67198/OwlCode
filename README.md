# OwlCode

```
 ┌────┐
 │◉ ◉│   终端 AI 编程助手
 │ ◠ │
 └────┘
```

基于 Textual TUI + 异步 Python 的跨平台终端 AI 编程助手，支持多 LLM 提供商、工具调用、子代理协作、技能系统和 MCP 服务器集成。类 Claude Code 的本地替代方案。

## 功能特性

- **多 LLM 提供商** — 同时支持 Anthropic、OpenAI、及所有兼容 Chat Completions 的第三方接口（DeepSeek、vLLM、Ollama 等）
- **Textual TUI** — 终端交互界面，支持权限弹窗、计划模式、子代理进度树、对话历史滚动
- **工具系统** — Bash 执行、文件读写、代码编辑、Grep/Glob 搜索，支持延迟工具加载减少 Token 消耗
- **子代理与团队** — 异步子代理分派，多代理协作（进程内/tmux/iTerm2），共享任务队列与邮箱通信
- **技能系统** — Markdown 定义 + YAML 元数据的前端技能，支持自定义工具注册与斜杠命令
- **MCP 集成** — Model Context Protocol 客户端全生命周期管理，自动注册 MCP 工具到注册表
- **会话持久化** — 对话记录自动保存、会话恢复、自动记忆提取与召回
- **权限控制** — 四种模式（default / acceptEdits / plan / bypassPermissions），危险命令检测、路径沙箱
- **Hook 系统** — pre/post 工具调用、消息发送等生命周期钩子，Shell 执行器
- **斜杠命令** — `/help`、`/memory`、`/plan`、`/skills`、`/compact`、`/review` 等 15+ 内置命令

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.11+ | `asyncio` 全链路异步 |
| TUI 框架 | Textual 2.8+ | 终端 UI 渲染、事件处理、CSS 布局 |
| Agent 范式 | ReAct（Reasoning + Acting） | 思考 → 工具调用 → 观察 → 循环 |
| Agent 架构 | Multi-Agent | Lead + Teammate 多代理协作 |
| LLM 协议 | Anthropic Messages / OpenAI Responses / Chat Completions | 三协议统一抽象 |
| LLM SDK | Anthropic SDK / OpenAI SDK | 多提供商流式对话、Tool Use |
| 工具系统 | Tool Registry + Deferred Tools | 注册表模式 + 延迟加载减少 Token |
| 技能系统 | Skill（Markdown + YAML Frontmatter） | 可扩展的自定义工具与斜杠命令 |
| MCP | Model Context Protocol | 外部 AI 客户端工具集成 |
| 序列化 | 自定义转换器 | Message ↔ 提供商特定格式 |
| 配置管理 | YAML 多层合并 | `~/.owlcode/` → `.owlcode/` → `config.local.yaml` |
| 会话存储 | JSON 文件系统 | `.owlcode/sessions/` 会话持久化 |
| 记忆召回 | 关键词匹配 + 嵌入向量 | 自动提取 + 上下文注入 |
| Prompt 缓存 | Content Replacement + Surrogate ID | 替换可变内容保持 Cache Hit |
| 子代理 | Agent Fork + Worktree 隔离 | 异步分派 + Git 工作树隔离 |
| 团队后端 | in-process / tmux / iTerm2 | 三种进程孵化方式 |
| 权限控制 | RuleEngine + PathSandbox + DangerousDetector | 四模式权限体系 |
| Hooks | Shell Executor + Regex Condition | 生命周期事件钩子 |
| 构建工具 | Hatchling + uv | 构建、安装、依赖管理 |

## 快速开始

### 前置要求

- Python 3.11+
- uv（推荐）或 pip

### 1. 安装

```bash
git clone https://github.com/LY67198/OwlCode.git
cd OwlCode
uv sync --dev
uv tool install --editable .
```

### 2. 配置

创建 `~/.owlcode/config.yaml`：

```yaml
providers:
  - name: deepseek
    protocol: openai-compat
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: ${OPENAI_API_KEY}

permission_mode: default
```

配置合并顺序：`~/.owlcode/config.yaml` → `.owlcode/config.yaml` → `.owlcode/config.local.yaml`

### 3. 运行

```bash
owlcode                      # 交互式 TUI
owlcode -p "你好"            # 单次问答
ANTHROPIC_API_KEY=sk-xxx owlcode -p "hello"   # 直接指定 Key
```

## 项目结构

```
owlcode/
├── __main__.py              # CLI 入口
├── agent.py                 # 核心代理循环
├── app.py                   # Textual TUI 应用
├── client.py                # 多提供商 LLM 客户端
├── config.py                # 配置加载与合并
├── prompts.py               # 系统提示词构建
├── conversation.py          # 对话消息管理
├── serialization.py         # 消息格式序列化
├── validator.py             # 配置校验
├── tools/                   # 工具注册与实现
│   ├── __init__.py          # ToolRegistry 注册表
│   ├── bash.py              # Bash 执行
│   ├── edit_file.py         # 文件编辑
│   ├── write_file.py        # 文件写入
│   ├── read_file.py         # 文件读取
│   ├── glob.py              # 文件匹配
│   ├── grep.py              # 内容搜索
│   ├── agent_tool.py        # 子代理分派
│   ├── task_create.py       # 任务创建
│   ├── task_update.py       # 任务更新
│   ├── task_list.py         # 任务列表
│   ├── task_get.py          # 任务查询
│   ├── load_skill.py        # 技能加载
│   ├── ask_user.py          # 用户询问
│   ├── send_message.py      # 团队消息
│   ├── enter_worktree.py    # 工作树进入
│   ├── exit_worktree.py     # 工作树退出
│   ├── exit_plan_mode.py    # 计划模式退出
│   ├── team_create.py       # 团队创建
│   ├── team_delete.py       # 团队删除
│   └── impl/tool_search.py  # 工具搜索
├── agents/                  # 子代理
│   ├── loader.py            # 代理加载器
│   ├── fork.py              # 代理分支
│   ├── task_manager.py      # 任务管理器
│   ├── trace.py             # 调用链追踪
│   ├── tool_filter.py       # 工具过滤器
│   └── builtins/            # 内置子代理（explore/plan/verification）
├── teams/                   # 多代理团队
│   ├── manager.py           # 团队管理
│   ├── coordinator.py       # 协调器
│   ├── spawn_inprocess.py   # 进程内孵化
│   ├── spawn_tmux.py        # tmux 孵化
│   ├── spawn_iterm2.py      # iTerm2 孵化
│   ├── mailbox.py           # 代理邮箱
│   ├── progress.py          # 进度追踪
│   └── shared_task.py       # 共享任务队列
├── skills/                  # 技能系统
│   ├── loader.py            # 技能加载
│   ├── executor.py          # 技能执行
│   ├── directory.py         # 工具注册
│   └── builtins/            # 内置技能（commit/review/test/backend-interview）
├── memory/                  # 记忆系统
│   ├── session.py           # 会话持久化
│   ├── auto_memory.py       # 自动记忆提取
│   ├── recall.py            # 记忆召回
│   └── instructions.py      # 项目指令加载
├── permissions/             # 权限控制
│   ├── checker.py           # 权限检查器
│   ├── dangerous.py         # 危险命令检测
│   ├── sandbox.py           # 路径沙箱
│   ├── rules.py             # 规则引擎
│   └── modes.py             # 权限模式
├── hooks/                   # 生命周期钩子
│   ├── engine.py            # 钩子引擎
│   ├── loader.py            # 钩子加载
│   ├── executors.py         # 动作执行器
│   └── conditions.py        # 条件匹配
├── commands/                # 斜杠命令
│   └── handlers/            # 命令处理器（help/memory/plan/review 等）
├── mcp/                     # MCP 客户端
│   ├── client.py            # 进程间通信
│   ├── manager.py           # 生命周期管理
│   └── tool_wrapper.py      # 工具包装
├── context/                 # 上下文管理
│   └── manager.py           # 自动压缩、内容替换、恢复
└── worktree/                # Git 工作树隔离
    ├── manager.py           # 工作树管理
    ├── setup.py             # 创建后配置
    ├── cleanup.py           # 过期清理
    └── changes.py           # 变更检测
```

## 配置详解

```yaml
# 提供商（必填）
providers:
  - name: deepseek
    protocol: openai-compat         # anthropic | openai | openai-compat
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: sk-xxx                 # 或 ${OPENAI_API_KEY}
    context_window: 128000          # 可选，自动从 /models 获取
    max_output_tokens: 4096         # 可选

# 权限模式（可选）
permission_mode: default            # default | acceptEdits | plan | bypassPermissions

# MCP 服务器（可选）
mcp_servers:
  - name: filesystem
    command: npx
    args: ["-y", "@anthropic-ai/mcp-server-filesystem", "."]

# 钩子（可选）
hooks:
  - event: pre_tool_call
    condition: tool_name == "Bash" && contains_rm
    action:
      type: shell
      command: "echo 'Dangerous: {{tool_call}}'"

# 工作树（可选）
worktree:
  symlink_directories: [node_modules, .venv]
  stale_cleanup_interval: 3600
  stale_cutoff_hours: 24

# 团队模式（可选）
teammate_mode: in-process            # 空 | in-process
enable_coordinator_mode: false
```

## 工具清单

| 工具名 | 功能 | 延迟加载 |
|--------|------|----------|
| `Bash` | Shell 命令执行 | 否 |
| `ReadFile` | 文件读取 | 否 |
| `WriteFile` | 文件写入 | 否 |
| `EditFile` | 精确字符串替换 | 否 |
| `Glob` | 文件名匹配 | 否 |
| `Grep` | 内容正则搜索 | 否 |
| `AgentTool` | 子代理分派 | 否 |
| `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` | 任务管理 | 否 |
| `LoadSkill` | 技能加载 | 否 |
| `AskUser` | 用户询问 | 否 |
| `SendMessage` | 团队消息 | 否 |
| `EnterWorktree` / `ExitWorktree` | 工作树隔离 | 否 |
| `ExitPlanMode` | 计划模式退出 | 否 |
| `TeamCreate` / `TeamDelete` | 团队管理 | 否 |
| `ToolSearch` | 延迟工具发现 | 是 |

## 权限模式

| 模式 | 行为 |
|------|------|
| `default` | 编辑类操作弹窗确认 |
| `acceptEdits` | 编辑操作自动允许 |
| `plan` | 计划模式，需审批后才执行 |
| `bypassPermissions` | 跳过所有权限检查 |

## 斜杠命令

| 命令 | 功能 |
|------|------|
| `/help` | 帮助信息 |
| `/memory` | 记忆管理 |
| `/plan` | 计划模式 |
| `/skills` | 技能列表 |
| `/compact` | 手动压缩对话 |
| `/review` | 代码审查 |
| `/rewind` | 回退对话 |
| `/session` | 会话管理 |
| `/status` | 系统状态 |
| `/tasks` | 任务列表 |
| `/trace` | 调用追踪 |
| `/worktree` | 工作树管理 |
| `/mcp` | MCP 状态 |
| `/clear` | 清屏 |
| `/skill register` | 注册技能 |

## 亮点设计

### 三协议统一抽象

`LLMClient` ABC → `AnthropicClient`（Messages API）/ `OpenAIClient`（Responses API）/ `OpenAICompatClient`（Chat Completions），工厂方法 `create_client(config)` 自动选择，`resolve_context_window()` 从 `/v1/models` 端点自动拉取上下文窗口。

### 内容替换（Prompt Cache 保持）

首次读取文件时缓存内容，后续对话用稳定 Surrogate ID 替换，让 Anthropic 的 prompt caching 持续命中，大幅降低 Token 消耗。

### 多代理团队

Lead + Teammate 模式，支持 in-process、tmux 多窗格、iTerm2 多标签三种后端。共享任务队列 + 代理邮箱通信 + 实时进度树展示。

### 延迟工具发现

标记 `should_defer=True` 的工具不暴露给模型，通过 `ToolSearch` 工具在模型需要时动态发现，减少每次请求的 Tool Schema 体积。

## 开发

```bash
uv sync --dev       # 安装开发依赖
uv run pytest       # 运行全部测试
uv run pytest -v    # 详细输出
```
