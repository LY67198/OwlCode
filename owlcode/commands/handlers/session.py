"""会话管理的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType
from owlcode.conversation import ConversationManager


async def handle_session(ctx: CommandContext) -> None:
    """管理对话会话：查看、列出、恢复、新建或删除会话。

    支持子命令：
      - (无): 显示当前会话信息
      - list: 列出已保存的会话
      - resume <id|序号>: 恢复指定会话
      - new: 创建新会话
      - delete <id>: 删除指定会话

    Args:
        ctx: 命令执行上下文。
    """
    sm = ctx.session_manager
    if sm is None:
        ctx.ui.add_system_message("\u4f1a\u8bdd\u7ba1\u7406\u5668\u672a\u521d\u59cb\u5316")
        return

    parts = ctx.args.split(None, 1)
    sub = parts[0] if parts else ""

    if sub == "":
        if ctx.session:
            m = ctx.session.meta
            ts = m.last_active.strftime("%Y-%m-%d %H:%M")
            ctx.ui.add_system_message(
                f"\u5f53\u524d\u4f1a\u8bdd: {m.id}\n"
                f"  \u6807\u9898: {m.title or '(\u672a\u547d\u540d)'}\n"
                f"  \u6d88\u606f: {m.message_count} \u6761\n"
                f"  Token: {m.total_tokens:,}\n"
                f"  \u6700\u540e\u6d3b\u8dc3: {ts}"
            )
        else:
            ctx.ui.add_system_message("\u5f53\u524d\u6ca1\u6709\u6d3b\u8dc3\u4f1a\u8bdd")
        return

    if sub == "list":
        metas = sm.list()
        if not metas:
            ctx.ui.add_system_message("\u6ca1\u6709\u5df2\u4fdd\u5b58\u7684\u4f1a\u8bdd\u3002")
            return
        lines: list[str] = ["\u4f1a\u8bdd\u5217\u8868\uff1a"]
        for m in metas[:10]:
            ts = m.last_active.strftime("%Y-%m-%d %H:%M")
            title = m.title or "(\u672a\u547d\u540d)"
            lines.append(f"  {m.id}  {title}  [{m.message_count} msgs, {ts}]")
        ctx.ui.add_system_message("\n".join(lines))

    elif sub == "resume":
        session_id = parts[1].strip() if len(parts) > 1 else ""
        if not session_id:
            metas = sm.list()
            if not metas:
                ctx.ui.add_system_message("\u6ca1\u6709\u5df2\u4fdd\u5b58\u7684\u4f1a\u8bdd\u3002")
                return
            lines: list[str] = ["\u53ef\u6062\u590d\u7684\u4f1a\u8bdd\uff08\u4f7f\u7528 /session resume <id> \u6216 /session resume <\u5e8f\u53f7>\uff09\uff1a"]
            for i, m in enumerate(metas[:15], 1):
                ts = m.last_active.strftime("%Y-%m-%d %H:%M")
                title = m.title or "(\u672a\u547d\u540d)"
                lines.append(f"  {i}. [{m.id[:8]}]  {title}  ({m.message_count} msgs, {ts})")
            ctx.ui.add_system_message("\n".join(lines))
            ctx.config["_resume_candidates"] = [m.id for m in metas[:15]]
            return
        candidates = ctx.config.get("_resume_candidates", [])
        if session_id.isdigit() and candidates:
            idx = int(session_id) - 1
            if 0 <= idx < len(candidates):
                session_id = candidates[idx]
        result = sm.resume(session_id)
        if result is None:
            ctx.ui.add_system_message(f"\u4f1a\u8bdd\u672a\u627e\u5230: {session_id}")
            return
        if ctx.session:
            ctx.session.close()
        ctx.config["set_session"](result.session)
        conv = ConversationManager()
        for msg in result.messages:
            conv.history.append(msg)
        ctx.config["set_conversation"](conv)
        if ctx.agent:
            ctx.agent._loop_count = 0
        await ctx.config["render_restored"](result.messages)
        ctx.ui.add_system_message(
            f"\u4f1a\u8bdd\u5df2\u6062\u590d: {session_id} ({result.session.meta.message_count} msgs)"
        )


    elif sub == "new":
        if ctx.session:
            ctx.session.close()
        new_session = sm.create()
        ctx.config["set_session"](new_session)
        ctx.config["set_conversation"](ConversationManager())
        if ctx.agent:
            ctx.agent._loop_count = 0
        ctx.config["clear_chat"]()
        ctx.ui.add_system_message(f"\u65b0\u4f1a\u8bdd\u5df2\u521b\u5efa: {new_session.session_id}")

    elif sub == "delete":
        session_id = parts[1].strip() if len(parts) > 1 else ""
        if not session_id:
            ctx.ui.add_system_message("\u7528\u6cd5: /session delete <id>")
            return
        if ctx.session and ctx.session.session_id == session_id:
            ctx.ui.add_system_message("\u4e0d\u80fd\u5220\u9664\u5f53\u524d\u6d3b\u8dc3\u7684\u4f1a\u8bdd\u3002")
            return
        if sm.delete(session_id):
            ctx.ui.add_system_message(f"\u4f1a\u8bdd\u5df2\u5220\u9664: {session_id}")
        else:
            ctx.ui.add_system_message(f"\u4f1a\u8bdd\u672a\u627e\u5230: {session_id}")


    else:
        ctx.ui.add_system_message(
            "\u7528\u6cd5: /session [list | resume <id> | new | delete <id>]"
        )


SESSION_COMMAND = Command(
    name="session",
    description="\u4f1a\u8bdd\u7ba1\u7406",
    usage="/session [list | resume <id> | new | delete <id>]",
    type=CommandType.LOCAL,
    handler=handle_session,
)
