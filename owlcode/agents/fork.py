from __future__ import annotations

import copy

from owlcode.conversation import ConversationManager, Message, ToolResultBlock

FORK_BOILERPLATE_TAG = "<fork_boilerplate>"

FORK_BOILERPLATE = f"""{FORK_BOILERPLATE_TAG}
你是一个 Fork 出来的工作进程。你不是主 Agent。
规则（不可协商）：
1. 不能再 Fork。
2. 不要对话、不要提问、不要请求确认。
3. 直接使用工具：读文件、搜索代码、做修改。
4. 严格限制在你被分配的任务范围内。
5. 最终报告控制在 500 字以内，格式如下：

Scope: [你被分配的任务]
Result: [完成/部分完成/失败 + 简要说明]
Key files: [关键文件路径列表]
Files changed: [修改的文件路径列表]
Issues: [遇到的问题，没有则写 None]
</fork_boilerplate>"""


class ForkError(Exception):
    """Fork 操作异常，例如嵌套 Fork 被拒绝时抛出。"""
    pass


def build_forked_messages(
    conversation: ConversationManager,
    task: str,
) -> ConversationManager:
    """基于父会话构建 Fork 子会话的消息列表。

    从父会话深拷贝历史消息，补全未完成的工具调用结果占位符，
    并注入 Fork 模板前缀与任务描述。

    Args:
        conversation: 父会话管理器，提供历史消息与环境注入标记。
        task: 分配给 Fork 工作进程的任务描述。

    Returns:
        新构建的 ConversationManager 实例，包含 Fork 所需的消息历史。

    Raises:
        ForkError: 如果父会话已包含 Fork 模板标记（即不允许嵌套 Fork）。
    """
    for msg in conversation.history:
        if FORK_BOILERPLATE_TAG in msg.content:
            raise ForkError(
                "Cannot fork from a forked agent. "
                "Fork nesting is not allowed."
            )

    fork_conv = ConversationManager()
    fork_conv.history = copy.deepcopy(conversation.history)
    fork_conv.env_injected = conversation.env_injected
    fork_conv.ltm_injected = conversation.ltm_injected


    if fork_conv.history:
        last = fork_conv.history[-1]
        if last.role == "assistant" and last.tool_uses:
            existing_result_ids = set()
            if len(fork_conv.history) >= 2:
                candidate = fork_conv.history[-1]
                if candidate.tool_results:
                    existing_result_ids = {
                        tr.tool_use_id for tr in candidate.tool_results
                    }

            pending = [
                tu
                for tu in last.tool_uses
                if tu.tool_use_id not in existing_result_ids
            ]
            if pending:
                placeholders = [
                    ToolResultBlock(
                        tool_use_id=tu.tool_use_id,
                        content="interrupted",
                        is_error=False,
                    )
                    for tu in pending
                ]
                fork_conv.history.append(
                    Message(
                        role="user",
                        content="",
                        tool_results=placeholders,
                    )
                )

    fork_conv.add_user_message(f"{FORK_BOILERPLATE}\n\n你的任务：\n{task}")
    return fork_conv
