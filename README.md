# OwlCode

```
 ┌────┐
 │◉ ◉│   轻量级终端 Coding Agent
 │ ◠ │
 └────┘
```

轻量级终端 Coding Agent，基于 **ReAct** 与 **Plan Mode** 双模式驱动 LLM 自主完成编程任务。交互、引擎、工具、记忆、安全五层分层架构，支持 Anthropic、OpenAI 双协议、MCP 工具扩展、Skill 技能包、跨会话记忆、多 Agent 并行协作。

## 架构

```
┌─────────────────────────────────────────────┐
│                  交互层                       │
│     Textual TUI · 斜杠命令 · 权限弹窗         │
│          Plan Mode · 子代理进度树             │
├─────────────────────────────────────────────┤
│                  引擎层                       │
│     ReAct Loop · Prompt 构建 · 上下文管理     │
│       LLM Client (Anthropic / OpenAI)        │
│        序列化 · 自动压缩 · 恢复               │
├─────────────────────────────────────────────┤
│                  工具层                       │
│     Bash · File R/W · Edit · Grep · Glob     │
│     Deferred Tool · Sub-Agent · MCP Wrapper  │
│     Skill · Task CRUD · Team Create/Delete   │
├─────────────────────────────────────────────┤
│                  记忆层                       │
│     会话持久化 · 自动记忆提取 · 矢量召回       │
│     项目指令加载 · 内容替换 (Prompt Cache)     │
├─────────────────────────────────────────────┤
│                  安全层                       │
│     权限模式 · 危险命令检测 · 路径沙箱         │
│     规则引擎 · Hook 生命周期                  │
└─────────────────────────────────────────────┘
```

## 功能特性

**交互层**
- **Textual TUI** — 终端原生 UI，消息渲染、输入提示、对话历史滚动
- **Plan Mode** — 先设计再编码，计划审批通过后执行
- **15+ 斜杠命令** — `/help`、`/memory`、`/plan`、`/skills`、`/compact` 等
- **子代理进度树** — 实时展示多 Agent 任务状态

**引擎层**
- **ReAct 范式** — Thinking → Tool Call → Observing → Looping
- **Plan Mode** — 计划生成 → 用户审批 → 步骤执行 → 完成验证
- **三协议统一** — Anthropic Messages / OpenAI Responses / OpenAI 兼容 Chat Completions
- **自动上下文管理** — 超窗口自动压缩、会话恢复、Prompt Cache 优化

**工具层**
- **核心工具** — Bash 执行、文件读写、精确编辑、正则搜索、Glob 匹配
- **MCP 集成** — Model Context Protocol 客户端全生命周期管理，外部工具自动注册
- **Skill 技能包** — Markdown + YAML 定义，自定义工具注册，可插拔扩展
- **延迟加载** — `should_defer=True` 工具仅在被搜索时暴露，减少 Token 消耗

**记忆层**
- **跨会话记忆** — 对话自动保存，记忆提取与召回，跨会话上下文注入
- **项目指令** — 自动加载 `OWLCODE.md` / `CLAUDE.md` 作为系统指令
- **内容替换** — ReadFile 结果缓存为 Surrogate ID，保持 Anthropic Prompt Cache 命中

**安全层**
- **四模式权限** — default / acceptEdits / plan / bypassPermissions
- **危险命令检测** — Bash 指令风险识别
- **路径沙箱** — 限制文件访问范围
- **Hook 系统** — pre/post_tool_call、on_message 等生命周期事件

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.11+ | `asyncio` 全链路异步 |
| TUI | Textual 2.8+ | 终端 UI 渲染、CSS 布局 |
| Agent 范式 | ReAct + Plan Mode | 双模式 LLM 驱动 |
| Agent 架构 | Multi-Agent | Lead + Teammate 并行协作 |
| LLM 协议 | Anthropic / OpenAI / Chat Completions | 三协议统一抽象 |
| LLM SDK | Anthropic SDK / OpenAI SDK | 流式对话、Tool Use |
| 工具系统 | Tool Registry + Deferred Tools | 注册表模式 + 延迟发现 |
| 技能系统 | Skill（Markdown + YAML） | 可扩展自定义工具包 |
| MCP | Model Context Protocol | 外部 AI 工具集成 |
| 配置管理 | YAML 多层合并 | 全局 → 项目 → 本地 |
| 会话存储 | JSON 文件系统 | `.owlcode/sessions/` |
| 记忆召回 | 关键词 + 嵌入向量 | 自动提取 + 上下文注入 |
| 子代理 | Agent Fork + Worktree | 异步分派 + Git 隔离 |
| 团队后端 | in-process / tmux / iTerm2 | 三种孵化方式 |
| 安全 | RuleEngine + Sandbox + Detector | 四模式权限体系 |
| 钩子 | Shell Executor + Regex Condition | 生命周期事件 |
| 构建工具 | Hatchling + uv | 构建、安装、依赖管理 |

## 快速开始

### 前置要求

- Python 3.11+
- uv（推荐）

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

### 3. 运行

```bash
owlcode                      # 交互式 TUI
owlcode -p "你好"            # 单次问答
```

## 项目结构

```
owlcode/
├── __main__.py              # CLI 入口
├── agent.py                 # 引擎层 — ReAct + Plan Mode 核心循环
├── app.py                   # 交互层 — Textual TUI
├── client.py                # 引擎层 — 多协议 LLM 客户端
├── config.py                # 引擎层 — 配置加载与合并
├── prompts.py               # 引擎层 — 系统提示词构建
├── conversation.py          # 引擎层 — 对话消息管理
├── serialization.py         # 引擎层 — Message ↔ 提供商格式
├── validator.py             # 引擎层 — 配置校验
├── tools/                   # 工具层
│   ├── __init__.py          # ToolRegistry 注册表
│   ├── bash.py              # Bash 执行
│   ├── edit_file.py         # 精确编辑
│   ├── write_file.py        # 文件写入
│   ├── read_file.py         # 文件读取
│   ├── glob.py              # 文件匹配
│   ├── grep.py              # 正则搜索
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
│   ├── exit_plan_mode.py    # Plan Mode 退出
│   ├── team_create.py       # 团队创建
│   ├── team_delete.py       # 团队删除
│   └── impl/tool_search.py  # 工具搜索（延迟发现）
├── agents/                  # 引擎层 — Multi-Agent
│   ├── loader.py            # 代理加载
│   ├── fork.py              # Agent Fork
│   ├── task_manager.py      # 异步任务管理
│   ├── trace.py             # 调用链追踪
│   ├── tool_filter.py       # 工具过滤器
│   └── builtins/            # 内置子代理（explore/plan/verification）
├── teams/                   # 引擎层 — 团队协作
│   ├── manager.py           # 团队管理
│   ├── coordinator.py       # 协调器
│   ├── spawn_inprocess.py   # 进程内孵化
│   ├── spawn_tmux.py        # tmux 多窗格
│   ├── spawn_iterm2.py      # iTerm2 多标签
│   ├── mailbox.py           # 代理邮箱
│   ├── progress.py          # 进度追踪
│   └── shared_task.py       # 共享任务队列
├── skills/                  # 工具层 — Skill 技能包
│   ├── loader.py            # 技能加载
│   ├── executor.py          # 技能执行
│   ├── directory.py         # 自定义工具注册
│   └── builtins/            # 内置技能（commit/review/test）
├── memory/                  # 记忆层
│   ├── session.py           # 会话持久化
│   ├── auto_memory.py       # 自动记忆提取
│   ├── recall.py            # 矢量召回
│   └── instructions.py      # 项目指令加载
├── permissions/             # 安全层
│   ├── checker.py           # 权限检查器
│   ├── dangerous.py         # 危险命令检测
│   ├── sandbox.py           # 路径沙箱
│   ├── rules.py             # 规则引擎
│   └── modes.py             # 权限模式定义
├── hooks/                   # 安全层 — Hook 系统
├── mcp/                     # 工具层 — MCP 集成
├── commands/                # 交互层 — 斜杠命令
├── context/                 # 引擎层 — 上下文管理
└── worktree/                # 安全层 — Git 工作树隔离
```

## 配置详解

```yaml
# 提供商
providers:
  - name: deepseek
    protocol: openai-compat         # anthropic | openai | openai-compat
    base_url: https://api.deepseek.com/v1
    model: deepseek-chat
    api_key: ${OPENAI_API_KEY}      # 支持 ${ENV} 语法

permission_mode: default            # default | acceptEdits | plan | bypassPermissions

# MCP 服务器（可选）
mcp_servers:
  - name: filesystem
    command: npx
    args: ["-y", "@anthropic-ai/mcp-server-filesystem", "."]

# Hook 事件（可选）
hooks:
  - event: pre_tool_call
    condition: tool_name == "Bash" && contains_rm
    action:
      type: shell
      command: "echo 'Dangerous: {{tool_call}}'"

# 工作树（可选）
worktree:
  symlink_directories: [node_modules, .venv]
  stale_cutoff_hours: 24

# Multi-Agent（可选）
teammate_mode: in-process
enable_coordinator_mode: false
```

## 工具清单

| 工具名 | 功能 | 所属 |
|--------|------|------|
| `Bash` | Shell 命令执行 | 核心 |
| `ReadFile` / `WriteFile` / `EditFile` | 文件读写编辑 | 核心 |
| `Glob` / `Grep` | 文件匹配 / 内容搜索 | 核心 |
| `AgentTool` | 子代理分派 | Multi-Agent |
| `TeamCreate` / `TeamDelete` | 团队管理 | Multi-Agent |
| `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` | 任务 CRUD | 任务 |
| `LoadSkill` | Skill 技能加载 | Skill |
| `EnterWorktree` / `ExitWorktree` | 工作树隔离 | 安全 |
| `ExitPlanMode` | Plan Mode 审批退出 | Plan |
| `AskUser` | 用户询问 | 交互 |
| `SendMessage` | 团队消息 | Multi-Agent |
| `ToolSearch` | 延迟工具发现 | 工具 |

## 权限模式

| 模式 | 行为 |
|------|------|
| `default` | 编辑操作弹窗确认 |
| `acceptEdits` | 编辑操作自动允许 |
| `plan` | Plan Mode — 计划审批后执行 |
| `bypassPermissions` | 跳过所有检查 |

## 斜杠命令

| 命令 | 功能 | 所属层 |
|------|------|--------|
| `/help` | 帮助信息 | 交互 |
| `/plan` | Plan Mode | 引擎 |
| `/memory` | 记忆管理 | 记忆 |
| `/skills` | 技能列表 | 工具 |
| `/compact` | 手动压缩 | 引擎 |
| `/review` | 代码审查 | 引擎 |
| `/rewind` | 回退对话 | 记忆 |
| `/session` | 会话管理 | 记忆 |
| `/status` | 系统状态 | 引擎 |
| `/tasks` | 任务列表 | 工具 |
| `/trace` | 调用追踪 | 引擎 |
| `/worktree` | 工作树管理 | 安全 |
| `/mcp` | MCP 状态 | 工具 |
| `/clear` | 清屏 | 交互 |

## 开发

```bash
uv sync --dev       # 安装开发依赖
uv run pytest       # 运行全部测试
uv run pytest -v    # 详细输出
```
