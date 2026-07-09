"""代码审查的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType


REVIEW_PROMPT = (
    "\u8bf7\u5ba1\u67e5\u5f53\u524d git diff \u4e2d\u7684\u4ee3\u7801\u53d8\u66f4\u3002\u91cd\u70b9\u5173\u6ce8\uff1a\n"
    "1. \u903b\u8f91\u9519\u8bef\n"
    "2. \u5b89\u5168\u95ee\u9898\n"
    "3. \u6027\u80fd\u95ee\u9898\n"
    "4. \u4ee3\u7801\u98ce\u683c"
)


async def handle_review(ctx: CommandContext) -> None:
    """将代码审查请求发送给模型，可附带额外关注点。

    Args:
        ctx: 命令执行上下文。
    """
    prompt = REVIEW_PROMPT
    if ctx.args:
        prompt += f"\n\n\u989d\u5916\u5173\u6ce8\uff1a{ctx.args}"
    ctx.ui.send_user_message(prompt)


REVIEW_COMMAND = Command(
    name="review",
    description="\u5ba1\u67e5\u4ee3\u7801\u53d8\u66f4",
    usage="/review [\u989d\u5916\u5173\u6ce8\u70b9]",
    type=CommandType.PROMPT,
    handler=handle_review,
)
