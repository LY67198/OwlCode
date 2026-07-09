"""agents 模块：Agent 定义、加载、工具过滤、Fork、追踪与后台任务管理。"""

from owlcode.agents.parser import AgentDef, AgentParseError, parse_agent_file
from owlcode.agents.loader import AgentLoader
from owlcode.agents.tool_filter import resolve_agent_tools
from owlcode.agents.fork import build_forked_messages, ForkError
from owlcode.agents.trace import TraceManager, TraceNode
from owlcode.agents.task_manager import TaskManager, BackgroundTask
from owlcode.agents.notification import format_task_notification, inject_task_notifications


__all__ = [
    "AgentDef",
    "AgentParseError",
    "parse_agent_file",
    "AgentLoader",
    "resolve_agent_tools",
    "build_forked_messages",
    "ForkError",
    "TraceManager",
    "TraceNode",
    "TaskManager",
    "BackgroundTask",
    "format_task_notification",
    "inject_task_notifications",
]
