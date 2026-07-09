from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from owlcode.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from owlcode.agent import Agent
    from owlcode.skills.directory import register_skill_tools
    from owlcode.skills.loader import SkillLoader


class LoadSkillParams(BaseModel):
    name: str = Field(description="The name of the skill to load")


class LoadSkill(Tool):
    """按名称加载并激活技能。

    加载后技能的 SOP 会固定到环境上下文中，若技能带有专用工具也会一并注册。
    """

    name = "LoadSkill"
    description = (
        "Load and activate a skill by name. "
        "The skill's SOP will be pinned to the environment context "
        "and any specialized tools will be registered."
    )
    params_model = LoadSkillParams
    category = "read"
    is_concurrency_safe = False
    is_system_tool = True


    def __init__(self) -> None:
        self._loader: SkillLoader | None = None
        self._agent: Agent | None = None


    def set_loader(self, loader: SkillLoader) -> None:
        """设置技能加载器。

        Args:
            loader: SkillLoader 实例。
        """
        self._loader = loader

    def set_agent(self, agent: Agent) -> None:
        """设置要激活技能的 Agent 实例。

        Args:
            agent: Agent 实例。
        """
        self._agent = agent


    async def execute(self, params: BaseModel) -> ToolResult:
        """加载并激活指定技能。

        Args:
            params: 包含 name（技能名称）的 LoadSkillParams。

        Returns:
            ToolResult，激活成功返回确认信息及注册的专用工具数量，
            技能不存在或初始化未完成时 is_error 为 True。
        """
        assert isinstance(params, LoadSkillParams)

        if self._loader is None or self._agent is None:
            return ToolResult(
                output="Error: LoadSkill not properly initialized",
                is_error=True,
            )

        skill = self._loader.get(params.name)
        if skill is None:
            available = ", ".join(n for n, _ in self._loader.get_catalog())
            return ToolResult(
                output=f"Error: unknown skill '{params.name}'. Available skills: {available}",
                is_error=True,
            )

        self._agent.activate_skill(skill.name, skill.prompt_body)

        tool_count = 0
        if skill.is_directory and skill.source_path is not None:
            from owlcode.skills.directory import register_skill_tools
            skill_dir = skill.source_path.parent
            tool_count = register_skill_tools(skill_dir, self._agent.registry)

        parts = [f"Skill '{skill.name}' activated. SOP pinned to environment context."]
        if tool_count > 0:
            parts.append(f"{tool_count} specialized tool(s) registered.")
        return ToolResult(output=" ".join(parts))
