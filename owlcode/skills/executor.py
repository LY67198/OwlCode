"""技能执行器：支持 inline 和 fork 两种模式运行技能。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator

from owlcode.conversation import ConversationManager, Message
from owlcode.skills.parser import SkillDef, substitute_arguments
from owlcode.tools import ToolRegistry

if TYPE_CHECKING:
    from owlcode.agent import Agent, AgentEvent
    from owlcode.client import LLMClient

log = logging.getLogger(__name__)

SYSTEM_TOOL_NAMES = frozenset({"LoadSkill"})

FORK_RECENT_COUNT = 5


class SkillDependencyError(Exception):
    """技能依赖的工具未找到时抛出的异常。"""
    pass


def filter_tool_registry(
    registry: ToolRegistry, allowed: list[str]
) -> ToolRegistry:
    """根据允许的工具列表筛选注册表，并保留系统工具。

    Args:
        registry: 原始工具注册表。
        allowed: 允许使用的工具名称列表。若为空则返回原注册表。

    Returns:
        筛选后的新 ToolRegistry。

    Raises:
        SkillDependencyError: 当 allowed 中的某个工具在注册表中不存在时抛出。
    """
    if not allowed:
        return registry

    filtered = ToolRegistry()
    for name in allowed:
        tool = registry.get(name)
        if tool is None:
            raise SkillDependencyError(
                f"Skill requires tool '{name}' but it is not registered"
            )
        filtered.register(tool)

    for tool in registry.list_tools():
        if getattr(tool, "is_system_tool", False) and filtered.get(tool.name) is None:
            filtered.register(tool)

    return filtered


class SkillExecutor:
    """技能执行器，根据技能的模式（inline / fork）来运行技能。"""

    def __init__(
        self,
        agent: Agent,
        client: LLMClient,
        protocol: str,
    ) -> None:
        self.agent = agent
        self.client = client
        self.protocol = protocol

    def execute_inline(self, skill: SkillDef, args: str) -> None:
        """以内联模式执行技能，直接将 prompt 注入当前 agent 会话。

        Args:
            skill: 待执行的技能定义。
            args: 替换 $ARGUMENTS 占位符的参数。
        """
        prompt = substitute_arguments(skill.prompt_body, args)
        self.agent.activate_skill(skill.name, prompt)
        if getattr(self.agent, "recovery_state", None) is not None:
            self.agent.recovery_state.record_skill_invocation(skill.name, prompt)

    async def execute_fork(
        self, skill: SkillDef, args: str
    ) -> str:
        """以 fork 模式执行技能，创建新的 agent 并在隔离会话中运行。

        Args:
            skill: 待执行的技能定义。
            args: 替换 $ARGUMENTS 占位符的参数。

        Returns:
            fork 会话中 agent 产生的文本结果。
        """
        prompt = substitute_arguments(skill.prompt_body, args)
        if getattr(self.agent, "recovery_state", None) is not None:
            self.agent.recovery_state.record_skill_invocation(
                skill.name, skill.prompt_body
            )

        fork_conv = ConversationManager()

        context_messages = self._build_fork_context(skill.context)
        for msg in context_messages:
            if msg.role == "user":
                fork_conv.add_user_message(msg.content)
            else:
                fork_conv.add_assistant_message(msg.content)

        fork_conv.add_user_message(prompt)

        # Register skill-specific tools (from tool.json) before filtering,
        # otherwise filter_tool_registry will fail for custom tools like
        # parse_resume that are listed in allowed_tools but not yet loaded.
        if skill.is_directory and skill.source_path is not None:
            from owlcode.skills.directory import register_skill_tools
            skill_dir = skill.source_path.parent
            register_skill_tools(skill_dir, self.agent.registry)

        try:
            filtered_registry = filter_tool_registry(
                self.agent.registry, skill.allowed_tools
            )
        except SkillDependencyError as e:
            return f"Skill execution failed: {e}"

        from owlcode.agent import Agent as AgentClass, StreamText, LoopComplete, ErrorEvent

        fork_agent = AgentClass(
            client=self.client,
            registry=filtered_registry,
            protocol=self.protocol,
            work_dir=self.agent.work_dir,
            max_iterations=self.agent.max_iterations,
            permission_checker=None,
            context_window=self.agent.context_window,
        )

        result_parts: list[str] = []
        async for event in fork_agent.run(fork_conv):
            if isinstance(event, StreamText):
                result_parts.append(event.text)
            elif isinstance(event, ErrorEvent):
                result_parts.append(f"\n[Error: {event.message}]")
            elif isinstance(event, LoopComplete):
                break

        return "".join(result_parts)

    def _build_fork_context(self, mode: str) -> list[Message]:
        """根据上下文模式构建 fork 会话的上下文消息列表。

        支持三种模式：none（无上下文）、recent（最近几条对话）、full（全部对话摘要）。

        Args:
            mode: 上下文模式，可选 "none"、"recent"、"full"。

        Returns:
            上下文消息列表。
        """
        if mode == "none":
            return []

        history = self.agent._conversation.history if hasattr(self.agent, '_conversation') else []
        if not history:
            main_history = []
        else:
            main_history = history

        if mode == "recent":
            content_messages = [
                m for m in main_history
                if m.content and not m.tool_results
            ]
            return content_messages[-FORK_RECENT_COUNT:]

        if mode == "full":
            content_messages = [
                m for m in main_history
                if m.content and not m.tool_results
            ]
            if not content_messages:
                return []
            summary_parts = []
            for m in content_messages:
                prefix = "User" if m.role == "user" else "Assistant"
                text = m.content[:200]
                if len(m.content) > 200:
                    text += "..."
                summary_parts.append(f"{prefix}: {text}")
            summary = "## Previous conversation summary\n\n" + "\n\n".join(summary_parts)
            return [Message(role="user", content=summary)]

        return []
