"""Skill 技能包管理的命令处理器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlcode.commands.registry import Command, CommandContext, CommandType

if TYPE_CHECKING:
    from owlcode.skills.loader import SkillLoader


async def handle_skill(ctx: CommandContext) -> None:
    """管理 Skill 技能包：列出、查看详情或重新加载。

    支持子命令：
      - list: 列出所有已加载的 Skill
      - info <name>: 查看指定 Skill 的详细信息
      - reload: 重新加载所有 Skill

    Args:
        ctx: 命令执行上下文。
    """
    parts = ctx.args.strip().split(maxsplit=1)
    subcmd = parts[0] if parts else "list"
    sub_args = parts[1] if len(parts) > 1 else ""

    loader: SkillLoader | None = ctx.config.get("skill_loader")
    if loader is None:
        ctx.ui.add_system_message("Skill \u7cfb\u7edf\u672a\u521d\u59cb\u5316")
        return

    if subcmd == "list":
        _handle_list(ctx, loader)
    elif subcmd == "info":
        _handle_info(ctx, loader, sub_args)
    elif subcmd == "reload":
        await _handle_reload(ctx, loader)
    else:
        ctx.ui.add_system_message(
            f"\u672a\u77e5\u5b50\u547d\u4ee4\uff1a{subcmd}\n\u7528\u6cd5\uff1a/skill list | /skill info <name> | /skill reload"
        )


def _handle_list(ctx: CommandContext, loader: SkillLoader) -> None:
    catalog = loader.get_catalog()
    if not catalog:
        ctx.ui.add_system_message("\u6ca1\u6709\u5df2\u52a0\u8f7d\u7684 Skill")
        return

    lines = ["\u5df2\u52a0\u8f7d\u7684 Skill\uff1a"]
    for name, desc in catalog:
        source = loader.get_source_label(name)
        lines.append(f"  {name:<20} {desc}  [{source}]")
    ctx.ui.add_system_message("\n".join(lines))


def _handle_info(ctx: CommandContext, loader: SkillLoader, name: str) -> None:
    if not name:
        ctx.ui.add_system_message("\u7528\u6cd5\uff1a/skill info <name>")
        return

    skill = loader.get(name)
    if skill is None:
        ctx.ui.add_system_message(f"\u672a\u627e\u5230 Skill\uff1a{name}")
        return

    source = loader.get_source_label(name)
    lines = [
        f"Skill: {skill.name}",
        f"Description: {skill.description}",
        f"Mode: {skill.mode}",
        f"Context: {skill.context}",
        f"Model: {skill.model or '(default)'}",
        f"AllowedTools: {', '.join(skill.allowed_tools) or '(all)'}",
        f"Source: {source}",
        f"Path: {skill.source_path or '(builtin)'}",
        f"Directory: {skill.is_directory}",
    ]
    ctx.ui.add_system_message("\n".join(lines))


async def _handle_reload(ctx: CommandContext, loader: SkillLoader) -> None:
    """重新加载所有 Skill 并重新注册对应的命令。

    Args:
        ctx: 命令执行上下文。
        loader: Skill 加载器实例。
    """
    skills = loader.reload()

    registry = ctx.config.get("registry")
    if registry is not None:
        from owlcode.commands.handlers.skill_register import register_skill_commands
        register_skill_commands(registry, loader, ctx.config.get("skill_executor"))

    ctx.ui.add_system_message(f"\u5df2\u91cd\u65b0\u52a0\u8f7d {len(skills)} \u4e2a Skill")


SKILL_COMMAND = Command(
    name="skill",
    description="\u7ba1\u7406 Skill \u6280\u80fd\u5305",
    usage="/skill list | /skill info <name> | /skill reload",
    type=CommandType.LOCAL,
    handler=handle_skill,
    aliases=["skills"],
)
