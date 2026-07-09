from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlcode.tools import ToolRegistry

if TYPE_CHECKING:
    from owlcode.agents.parser import AgentDef
    from owlcode.teams.manager import TeamManager

ALL_AGENT_DISALLOWED_TOOLS: frozenset[str] = frozenset({
    "TaskOutput",
    "ExitPlanMode",
    "EnterPlanMode",
    "Agent",
    "AskUserQuestion",
    "TaskStop",
    "Workflow",
})

CUSTOM_AGENT_DISALLOWED_TOOLS: frozenset[str] = frozenset({
    "TaskOutput",
    "ExitPlanMode",
    "EnterPlanMode",
    "Agent",
    "AskUserQuestion",
    "TaskStop",
    "Workflow",
})

ASYNC_AGENT_ALLOWED_TOOLS: frozenset[str] = frozenset({
    "ReadFile",
    "WebSearch",
    "TodoWrite",
    "Grep",
    "WebFetch",
    "Glob",
    "Bash",
    "EditFile",
    "WriteFile",
    "NotebookEdit",
    "Skill",
    "LoadSkill",
    "SyntheticOutput",
    "ToolSearch",
    "EnterWorktree",
    "ExitWorktree",
})

TEAMMATE_COORDINATION_TOOLS: frozenset[str] = frozenset({
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskUpdate",
    "SendMessage",
})

IN_PROCESS_TEAMMATE_ALLOWED_TOOLS: frozenset[str] = (
    ASYNC_AGENT_ALLOWED_TOOLS | TEAMMATE_COORDINATION_TOOLS | frozenset({
        "CronCreate",
        "CronDelete",
        "CronList",
    })
)

COORDINATOR_MODE_ALLOWED_TOOLS: frozenset[str] = frozenset({
    "Agent",
    "TaskStop",
    "SendMessage",
    "SyntheticOutput",
    "TeamCreate",
    "TeamDelete",
})


def _is_mcp_tool(name: str) -> bool:
    return name.startswith("mcp__")


def resolve_agent_tools(
    parent_registry: ToolRegistry,
    definition: AgentDef,
    is_background: bool = False,
) -> ToolRegistry:
    """根据全局规则和 Agent 定义过滤工具列表。

    过滤层级：
    0. MCP 工具始终放行
    1. 全局禁用工具
    2. 自定义 Agent 额外限制
    3. 后台任务白名单
    4. Agent 定义中的 disallowed_tools / tools

    Args:
        parent_registry: 父级工具注册表。
        definition: Agent 定义（含 tools 和 disallowed_tools）。
        is_background: 是否为后台任务。

    Returns:
        过滤后的 ToolRegistry。
    """
    all_tools = {t.name: t for t in parent_registry.list_tools()}

    # 第 0 层：MCP 工具始终放行，先分离出来再做后续过滤
    mcp_tools = {name: tool for name, tool in all_tools.items() if _is_mcp_tool(name)}
    all_tools = {name: tool for name, tool in all_tools.items() if not _is_mcp_tool(name)}

    # 第 1 层：全局禁用工具
    for name in ALL_AGENT_DISALLOWED_TOOLS:
        all_tools.pop(name, None)

    # 第 2 层：自定义 agent 额外限制
    if definition.source in ("project", "user", "plugin"):
        for name in CUSTOM_AGENT_DISALLOWED_TOOLS:
            all_tools.pop(name, None)

    # 第 3 层：后台任务白名单
    if is_background:
        all_tools = {
            name: tool
            for name, tool in all_tools.items()
            if name in ASYNC_AGENT_ALLOWED_TOOLS
        }

    # 第 4 层：按 agent 定义中的禁用/允许列表过滤
    if definition.disallowed_tools:
        for name in definition.disallowed_tools:
            all_tools.pop(name, None)

    if definition.tools:
        allowed_set = set(definition.tools)
        all_tools = {
            name: tool
            for name, tool in all_tools.items()
            if name in allowed_set
        }

    filtered = ToolRegistry()
    for tool in mcp_tools.values():
        filtered.register(tool)
    for tool in all_tools.values():
        filtered.register(tool)
    return filtered


def build_teammate_tools(
    parent_registry: ToolRegistry,
    team_manager: TeamManager,
    team_name: str,
    agent_id: str,
    agent_name: str,
    backend_type: str,
    definition: AgentDef | None = None,
) -> ToolRegistry:
    """为团队成员构建工具注册表，注入协作工具。

    根据后端类型（in-process 或其他）决定允许的工具范围，并注入
    TaskCreate、TaskGet、TaskList、TaskUpdate、SendMessage 等协作工具。

    Args:
        parent_registry: 父级工具注册表。
        team_manager: 团队管理器实例。
        team_name: 团队名称。
        agent_id: Agent 的唯一 ID。
        agent_name: Agent 名称。
        backend_type: 后端类型（in-process / tmux / iterm2）。
        definition: 可选的 Agent 定义，用于进一步限制工具。

    Returns:
        包含协作工具的 ToolRegistry。
    """
    from owlcode.teams.models import BackendType
    from owlcode.tools.send_message import SendMessageTool
    from owlcode.tools.task_create import TaskCreateTool
    from owlcode.tools.task_get import TaskGetTool
    from owlcode.tools.task_list import TaskListTool
    from owlcode.tools.task_update import TaskUpdateTool

    if backend_type == BackendType.IN_PROCESS.value:
        all_tools = {t.name: t for t in parent_registry.list_tools()}
        filtered = {
            name: tool
            for name, tool in all_tools.items()
            if name in IN_PROCESS_TEAMMATE_ALLOWED_TOOLS
        }
    else:
        filtered = {t.name: t for t in parent_registry.list_tools()}
        filtered.pop("TeamCreate", None)
        filtered.pop("TeamDelete", None)

    # 应用 agent 定义中的工具限制
    if definition is not None:
        if definition.disallowed_tools:
            for name in definition.disallowed_tools:
                filtered.pop(name, None)
        if definition.tools:
            allowed_set = set(definition.tools) | TEAMMATE_COORDINATION_TOOLS
            filtered = {
                name: tool
                for name, tool in filtered.items()
                if name in allowed_set
            }

    coordination_tools = [
        TaskCreateTool(team_manager, team_name, agent_name),
        TaskGetTool(team_manager, team_name),
        TaskListTool(team_manager, team_name),
        TaskUpdateTool(team_manager, team_name),
        SendMessageTool(team_manager, team_name, agent_id, agent_name),
    ]

    registry = ToolRegistry()
    for tool in filtered.values():
        registry.register(tool)
    for tool in coordination_tools:
        registry.register(tool)

    return registry


def apply_coordinator_filter(registry: ToolRegistry) -> ToolRegistry:
    """对工具注册表应用协调器模式过滤，只保留协调器允许的工具。

    Args:
        registry: 原始工具注册表。

    Returns:
        仅包含协调器模式允许工具的 ToolRegistry。
    """
    all_tools = {t.name: t for t in registry.list_tools()}
    filtered = ToolRegistry()
    for name, tool in all_tools.items():
        if name in COORDINATOR_MODE_ALLOWED_TOOLS:
            filtered.register(tool)
    return filtered
