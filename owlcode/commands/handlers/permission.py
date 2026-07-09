"""权限管理的命令处理器。"""

from __future__ import annotations

from owlcode.commands.registry import Command, CommandContext, CommandType
from owlcode.permissions import PermissionMode


_MODE_NAMES = {m.value: m for m in PermissionMode}


async def handle_permission(ctx: CommandContext) -> None:
    """管理权限模式与规则。

    支持子命令：
      - (无): 显示当前权限状态
      - mode <模式>: 切换权限模式
      - rules: 列出所有权限规则
      - add <规则> <allow|deny>: 添加本地规则
      - reset: 清空本地规则

    Args:
        ctx: 命令执行上下文。
    """
    if ctx.agent is None:
        ctx.ui.add_system_message("Agent \u672a\u521d\u59cb\u5316")
        return

    parts = ctx.args.split(None, 1)
    sub = parts[0] if parts else ""

    if sub == "":
        mode = ctx.agent.permission_mode
        checker = ctx.agent.permission_checker
        rule_count = 0
        if checker and checker.rule_engine:
            tiers = checker.rule_engine._load_tiers()
            rule_count = sum(len(t) for t in tiers)
        ctx.ui.add_system_message(
            f"\u6743\u9650\u72b6\u6001\n"
            f"  \u5f53\u524d\u6a21\u5f0f: {mode.value}\n"
            f"  \u89c4\u5219\u6570\u91cf: {rule_count}"
        )

    elif sub == "mode":
        mode_str = parts[1].strip() if len(parts) > 1 else ""
        if not mode_str:
            modes = ", ".join(_MODE_NAMES.keys())
            ctx.ui.add_system_message(f"\u7528\u6cd5: /permission mode <\u6a21\u5f0f>\n\u53ef\u9009: {modes}")
            return
        mode = _MODE_NAMES.get(mode_str)
        if mode is None:
            modes = ", ".join(_MODE_NAMES.keys())
            ctx.ui.add_system_message(f"\u672a\u77e5\u6a21\u5f0f: {mode_str}\n\u53ef\u9009: {modes}")
            return
        ctx.agent.set_permission_mode(mode)
        ctx.ui.refresh_status()
        ctx.ui.add_system_message(f"\u6743\u9650\u6a21\u5f0f\u5df2\u5207\u6362\u4e3a: {mode.value}")

    elif sub == "rules":
        checker = ctx.agent.permission_checker
        if not checker or not checker.rule_engine:
            ctx.ui.add_system_message("\u89c4\u5219\u5f15\u64ce\u672a\u521d\u59cb\u5316")
            return
        tiers = checker.rule_engine._load_tiers()
        names = ["\u7528\u6237\u7ea7", "\u9879\u76ee\u7ea7", "\u672c\u5730\u7ea7"]
        lines: list[str] = ["\u6743\u9650\u89c4\u5219\uff1a"]
        for name, rules in zip(names, tiers):
            if rules:
                lines.append(f"  [{name}]")
                for r in rules:
                    lines.append(f"    {r.tool_name}({r.pattern}) \u2192 {r.effect}")
            else:
                lines.append(f"  [{name}] (\u65e0\u89c4\u5219)")
        ctx.ui.add_system_message("\n".join(lines))

    elif sub == "add":
        rule_str = parts[1].strip() if len(parts) > 1 else ""
        if not rule_str:
            ctx.ui.add_system_message("\u7528\u6cd5: /permission add <\u89c4\u5219> <\u6548\u679c>")
            return
        from owlcode.permissions.rules import Rule, parse_rule
        rule_parts = rule_str.rsplit(None, 1)
        if len(rule_parts) < 2 or rule_parts[1] not in ("allow", "deny"):
            ctx.ui.add_system_message(
                "\u7528\u6cd5: /permission add <Tool(pattern)> <allow|deny>\n"
                "\u793a\u4f8b: /permission add Bash(git*) allow"
            )
            return
        try:
            rule = parse_rule(rule_parts[0], rule_parts[1])
        except ValueError as e:
            ctx.ui.add_system_message(str(e))
            return
        checker = ctx.agent.permission_checker
        if checker and checker.rule_engine:
            checker.rule_engine.append_local_rule(rule)
            ctx.ui.add_system_message(f"\u89c4\u5219\u5df2\u6dfb\u52a0: {rule.tool_name}({rule.pattern}) \u2192 {rule.effect}")
        else:
            ctx.ui.add_system_message("\u89c4\u5219\u5f15\u64ce\u672a\u521d\u59cb\u5316")


    elif sub == "reset":
        checker = ctx.agent.permission_checker
        if checker and checker.rule_engine and checker.rule_engine._local_path:
            path = checker.rule_engine._local_path
            if path.exists():
                path.write_text("", encoding="utf-8")
            ctx.ui.add_system_message("\u672c\u5730\u89c4\u5219\u5df2\u6e05\u7a7a")
        else:
            ctx.ui.add_system_message("\u65e0\u672c\u5730\u89c4\u5219\u6587\u4ef6")

    else:
        ctx.ui.add_system_message(
            "\u7528\u6cd5: /permission [mode <\u6a21\u5f0f> | rules | add <\u89c4\u5219> <\u6548\u679c> | reset]"
        )


PERMISSION_COMMAND = Command(
    name="permission",
    description="\u6743\u9650\u7ba1\u7406",
    usage="/permission [mode <\u6a21\u5f0f> | rules | add <\u89c4\u5219> | reset]",
    type=CommandType.LOCAL,
    handler=handle_permission,
)
