"""Skill 命令动态注册器，将 Skill 目录中的技能包注册为斜杠命令。"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from owlcode.commands.registry import Command, CommandContext, CommandRegistry, CommandType

if TYPE_CHECKING:
    from owlcode.skills.executor import SkillExecutor
    from owlcode.skills.loader import SkillLoader

log = logging.getLogger(__name__)

_REGISTERED_SKILL_NAMES: set[str] = set()


def register_skill_commands(
    registry: CommandRegistry,
    loader: SkillLoader,
    executor: SkillExecutor | None = None,
) -> None:
    """根据 Skill 目录动态注册斜杠命令。

    先清除先前注册的 Skill 命令，然后遍历 loader 中的 Skill 目录，
    为每个 Skill 创建对应的 Command 并注册到 registry 中。

    Args:
        registry: 目标命令注册表。
        loader: Skill 加载器，提供 Skill 目录信息。
        executor: 可选的 Skill 执行器，未提供时从上下文中获取。
    """
    for name in list(_REGISTERED_SKILL_NAMES):
        if registry.find(name) is not None:
            registry._commands.pop(name, None)
            registry._alias_map = {
                k: v for k, v in registry._alias_map.items() if v != name
            }
        _REGISTERED_SKILL_NAMES.discard(name)

    for skill_name, skill_desc in loader.get_catalog():
        if registry.find(skill_name) is not None:
            continue

        s_name = skill_name
        s_desc = skill_desc


        def make_handler(name: str) -> callable:


            async def handler(ctx: CommandContext) -> None:
                exe = ctx.config.get("skill_executor") if executor is None else executor
                if exe is None:
                    ctx.ui.add_system_message("Skill \u6267\u884c\u5668\u672a\u521d\u59cb\u5316")
                    return

                skill_loader: SkillLoader | None = ctx.config.get("skill_loader")
                if skill_loader is None:
                    ctx.ui.add_system_message("Skill \u52a0\u8f7d\u5668\u672a\u521d\u59cb\u5316")
                    return

                skill = skill_loader.get(name)
                if skill is None:
                    ctx.ui.add_system_message(f"\u672a\u627e\u5230 Skill\uff1a{name}")
                    return

                if skill.mode == "fork":
                    ctx.ui.add_system_message(f"\u23f3 Running {name} skill...")


                    async def _run_fork() -> None:
                        try:
                            result = await exe.execute_fork(skill, ctx.args)
                            ctx.ui.add_system_message(
                                f"[{name} skill result]\n{result}"
                            )
                        except Exception as e:
                            ctx.ui.add_system_message(
                                f"Skill {name} failed: {e}"
                            )

                    asyncio.create_task(_run_fork())
                else:
                    exe.execute_inline(skill, ctx.args)
                    tools_info = ""
                    if skill.allowed_tools:
                        tools_info = f" \u00b7 {len(skill.allowed_tools)} tools allowed"
                    ctx.ui.add_system_message(
                        f"skill({name})\nSuccessfully loaded skill{tools_info}"
                    )
                    trigger = ctx.args if ctx.args else f"/{name}"
                    ctx.ui.send_user_message(trigger)

            return handler

        cmd = Command(
            name=s_name,
            description=f"{s_desc} [skill]",
            usage=f"/{s_name} [args]",
            type=CommandType.PROMPT,
            handler=make_handler(s_name),
        )

        try:
            registry.register_sync(cmd)
            _REGISTERED_SKILL_NAMES.add(s_name)
        except ValueError as e:
            log.warning("Cannot register skill command '%s': %s", s_name, e)
