from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolUseBlock:
    """表示助手消息中的一次工具调用请求。"""

    tool_use_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass
class ToolResultBlock:
    """表示工具调用的返回结果。"""

    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class ThinkingBlock:
    """表示助手思考块（Anthropic extended thinking）。"""

    thinking: str
    signature: str


@dataclass
class Message:
    """对话中的一条消息，包含角色、文本内容和可选的工具调用/结果/思考块。"""

    role: str  # "user" | "assistant"
    content: str
    tool_uses: list[ToolUseBlock] = field(default_factory=list)
    tool_results: list[ToolResultBlock] = field(default_factory=list)
    thinking_blocks: list[ThinkingBlock] = field(default_factory=list)


# 估算最后一次 API 用量锚点之后追加的消息 token 开销时使用的字符/token 比率。
# 与 context.manager 中的恢复状态启发值保持一致，全代码库统一使用同一比率。
_CHARS_PER_TOKEN = 3.5


def _message_chars(m: Message) -> int:
    n = len(m.content)
    for tb in m.thinking_blocks:
        n += len(tb.thinking)
    for tu in m.tool_uses:
        n += len(tu.tool_name) + len(json.dumps(tu.arguments, ensure_ascii=False))
    for tr in m.tool_results:
        n += len(tr.content)
    return n


def estimate_tokens(messages: list[Message]) -> int:
    """基于字符数对一组消息做 token 估算。

    刻意做得粗略——它只覆盖那些尚未锚定到真实 API 用量数值的消息，这部分的
    精确度本就无关紧要。统计内容包括消息正文、thinking、工具调用参数以及
    工具结果内容。
    """
    total = sum(_message_chars(m) for m in messages)
    return int(total / _CHARS_PER_TOKEN)


@dataclass
class ConversationManager:
    """对话管理器，维护消息历史、用量追踪和环境注入状态。

    通过 record_usage_anchor 锚定 API 报告的真实用量，之后仅对增量消息
    做字符估算，兼顾精度与性能。
    """

    history: list[Message] = field(default_factory=list)
    env_injected: bool = field(default=False, init=False)
    ltm_injected: bool = field(default=False, init=False)
    # API 报告的每轮真实 prompt 大小，保留用于向后兼容。
    # 现在与 baseline_tokens 一致（input + cache_read + cache_creation + output）。
    last_input_tokens: int = field(default=0, init=False)
    # 真实用量锚点。baseline_tokens 是上一轮 API 计费的完整 prompt+output 大小；
    # anchor_count 是记录该数值时的消息数量。两者配合让 current_tokens() 在
    # anchor_count 以内信任 API 数据，只对之后追加的消息做字符估算。
    # baseline_tokens == 0 表示"尚无锚点"（冷启动），此时退化为纯字符估算。
    baseline_tokens: int = field(default=0, init=False)
    anchor_count: int = field(default=0, init=False)

    def record_usage_anchor(
        self,
        input_tokens: int,
        output_tokens: int = 0,
        cache_read: int = 0,
        cache_creation: int = 0,
    ) -> None:
        """根据一次 API 响应钉下一个真实用量锚点。

        baseline = input + cache_read + cache_creation + output。各家服务商
        返回的 input_tokens 已经排除了命中缓存的 token，所以这三个 input 分量
        是相加关系，合起来才是真正的 prompt 大小；之所以再加上 output，是因为
        assistant 的回复此刻已成为历史的一部分。anchor_count 对齐到当前的消息
        数量，这样后续新追加的消息就成了唯一需要估算的部分。
        """
        self.baseline_tokens = (
            input_tokens + cache_read + cache_creation + output_tokens
        )
        self.anchor_count = len(self.history)
        # 保持旧字段同步，兼容仍在使用它的读取方。
        self.last_input_tokens = self.baseline_tokens

    def current_tokens(self) -> int:
        """对当前对话中的 token 数量做出最佳估算。

        有锚点时：baseline（真实用量）+ 仅对锚点之后追加的那些消息做字符估算。
        没有锚点时（冷启动，或刚经历一次压缩重置）：对整个历史做字符估算，
        这样在第一次 API 响应到来之前阈值检查依然能正常工作。
        """
        if self.baseline_tokens <= 0:
            return estimate_tokens(self.history)
        tail = self.history[self.anchor_count:]
        return self.baseline_tokens + estimate_tokens(tail)

    def add_user_message(self, content: str) -> None:
        """追加一条用户消息到对话历史。

        Args:
            content: 用户消息的文本内容。
        """
        self.history.append(Message(role="user", content=content))

    def add_assistant_message(
        self,
        content: str,
        tool_uses: list[ToolUseBlock] | None = None,
        thinking_blocks: list[ThinkingBlock] | None = None,
    ) -> None:
        """追加一条助手消息到对话历史。

        Args:
            content: 助手消息的文本内容。
            tool_uses: 可选的工具调用列表。
            thinking_blocks: 可选的思考块列表。
        """
        self.history.append(
            Message(
                role="assistant",
                content=content,
                tool_uses=tool_uses or [],
                thinking_blocks=thinking_blocks or [],
            )
        )

    def add_system_reminder(self, content: str) -> None:
        """以 system-reminder 包裹的 user 消息形式追加系统提醒。

        Args:
            content: 提醒内容文本。
        """
        self.history.append(
            Message(
                role="user",
                content=f"<system-reminder>\n{content}\n</system-reminder>",
            )
        )

    def add_tool_results_message(self, tool_results: list[ToolResultBlock]) -> None:
        """追加一条包含工具结果列表的 user 消息。

        Args:
            tool_results: ToolResultBlock 列表。
        """
        self.history.append(
            Message(role="user", content="", tool_results=tool_results)
        )

    def inject_environment(self, context: str) -> None:
        """在对话开头注入环境上下文（仅首次调用生效）。

        Args:
            context: 环境上下文字符串。
        """
        if not self.env_injected:
            self.history.insert(0, Message(role="user", content=context))
            self.env_injected = True

    def inject_long_term_memory(
        self, instructions: str, memories: str
    ) -> None:
        """在对话开头注入长期记忆（指令和记忆，仅首次调用生效）。

        Args:
            instructions: 项目指令内容。
            memories: 自动记忆内容。
        """
        if self.ltm_injected:
            return
        sections: list[str] = []
        if instructions:
            sections.append(
                "# owlcodeMd\n"
                "Codebase and user instructions are shown below. "
                "Be sure to adhere to these instructions. "
                "IMPORTANT: These instructions OVERRIDE any default behavior "
                "and you MUST follow them exactly as written.\n\n" + instructions
            )
        if memories:
            sections.append("# autoMemory\n" + memories)
        if not sections:
            return
        from datetime import date

        sections.append(f"# currentDate\nToday's date is {date.today().isoformat()}.")
        body = "\n\n".join(sections)
        wrapped = (
            "<system-reminder>\n"
            "As you answer the user's questions, you can use the following context:\n"
            + body
            + "\n\n      IMPORTANT: this context may or may not be relevant to your tasks."
            " You should not respond to this context unless it is highly relevant to your task.\n"
            "</system-reminder>"
        )
        pos = 1 if self.env_injected else 0
        self.history.insert(pos, Message(role="user", content=wrapped))
        self.ltm_injected = True

    def replace_history(self, new_messages: list[Message]) -> None:
        """完全替换对话历史（通常在压缩后调用），并重置注入和用量状态。

        Args:
            new_messages: 替换后的消息列表。
        """
        self.history = new_messages
        self.env_injected = False
        self.ltm_injected = False
        # 旧的用量锚点描述的是压缩前的对话记录，这里清除它，
        # 使 current_tokens() 退化为字符估算，直到下次 API 响应
        # 基于摘要后的历史重新建立锚点。
        self.baseline_tokens = 0
        self.anchor_count = 0
        self.last_input_tokens = 0

    def get_messages(self) -> list[Message]:
        """返回当前对话历史的副本。

        Returns:
            消息列表的浅拷贝。
        """
        return list(self.history)
