from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path

from owlcode.agents.parser import AgentDef, AgentParseError, parse_agent_file

log = logging.getLogger(__name__)

PROJECT_AGENTS_DIR = ".owlcode/agents"
USER_AGENTS_DIR = "~/.owlcode/agents"


class AgentLoader:
    """加载并管理 Agent 定义，支持项目级、用户级、内置三级来源。

    支持按优先级合并（项目 > 用户 > 内置），并提供文件热重载能力。
    """

    def __init__(
        self,
        work_dir: str,
        enable_verification: bool = False,
    ) -> None:
        """初始化 AgentLoader。

        Args:
            work_dir: 当前工作目录路径。
            enable_verification: 是否启用 Verification 类型的内置 Agent。
        """
        self._work_dir = work_dir
        self._enable_verification = enable_verification
        self._agents: dict[str, AgentDef] = {}


    def _scan_directory(self, path: Path, source: str) -> list[AgentDef]:
        """扫描指定目录下所有 .md 文件，解析为 AgentDef 列表。

        Args:
            path: 待扫描的目录路径。
            source: 来源标记，如 "project"、"user"。

        Returns:
            解析成功的 AgentDef 列表。
        """
        results: list[AgentDef] = []
        if not path.is_dir():
            return results

        for entry in sorted(path.iterdir()):
            if not entry.is_file() or entry.suffix != ".md":
                continue
            try:
                agent_def = parse_agent_file(entry)
                agent_def.source = source
                agent_def.file_path = entry
                results.append(agent_def)
            except AgentParseError as e:
                log.warning("Skipping agent file %s: %s", entry, e)
        return results


    def _load_builtins(self) -> list[AgentDef]:
        """加载内置 Agent 定义（从 owlcode.agents.builtins 包中）。

        直接读取包内 .md 资源文件，解析 frontmatter 后构建 AgentDef。
        若未启用 Verification，则跳过对应类型的内置 Agent。

        Returns:
            内置 AgentDef 列表。
        """
        results: list[AgentDef] = []
        try:
            builtins_pkg = importlib.resources.files("owlcode.agents.builtins")
        except (ModuleNotFoundError, TypeError):
            log.warning("Could not load built-in agents package")
            return results

        for item in builtins_pkg.iterdir():
            if not item.name.endswith(".md"):
                continue
            try:
                raw = item.read_text(encoding="utf-8")
                from owlcode.agents.parser import parse_frontmatter, _validate_agent_meta

                meta, body = parse_frontmatter(raw)
                _validate_agent_meta(meta, item.name)

                agent_def = AgentDef(
                    agent_type=meta["name"],
                    when_to_use=meta["description"],
                    system_prompt=body,
                    tools=meta.get("tools", []),
                    disallowed_tools=meta.get("disallowedTools", []),
                    model=str(meta.get("model", "inherit")),
                    max_turns=meta.get("maxTurns", 50),
                    permission_mode=str(meta.get("permissionMode", "default")),
                    background=bool(meta.get("background", False)),
                    file_path=None,
                    source="builtin",
                )

                if (
                    agent_def.agent_type == "Verification"
                    and not self._enable_verification
                ):
                    continue

                results.append(agent_def)
            except (AgentParseError, Exception) as e:
                log.warning("Skipping built-in agent %s: %s", item.name, e)

        return results

    def load_all(self) -> dict[str, AgentDef]:
        """按优先级加载全部 Agent：项目级 > 用户级 > 内置。

        同名 Agent 以最高优先级来源为准。

        Returns:
            agent_type -> AgentDef 的字典。
        """
        seen: dict[str, AgentDef] = {}

        # 优先级 1：项目级（最高）
        project_path = Path(self._work_dir) / PROJECT_AGENTS_DIR
        for agent_def in self._scan_directory(project_path, "project"):
            if agent_def.agent_type not in seen:
                seen[agent_def.agent_type] = agent_def

        # 优先级 2：用户级
        user_path = Path(USER_AGENTS_DIR).expanduser()
        for agent_def in self._scan_directory(user_path, "user"):
            if agent_def.agent_type not in seen:
                seen[agent_def.agent_type] = agent_def

        # 优先级 3：内置
        for agent_def in self._load_builtins():
            if agent_def.agent_type not in seen:
                seen[agent_def.agent_type] = agent_def

        # 优先级 4：插件（保留，未实现）

        self._agents = seen
        return seen


    def get(self, agent_type: str) -> AgentDef | None:
        """获取指定类型的 AgentDef，如果文件源存在则热重载。

        Args:
            agent_type: Agent 类型名称。

        Returns:
            对应的 AgentDef；未找到则返回 None。
        """
        cached = self._agents.get(agent_type)
        if cached is None:
            return None

        # 从文件热重载
        if cached.file_path is not None and cached.file_path.exists():
            try:
                reloaded = parse_agent_file(cached.file_path)
                reloaded.source = cached.source
                self._agents[agent_type] = reloaded
                return reloaded
            except AgentParseError as e:
                log.warning(
                    "Hot reload failed for %s, using cached: %s",
                    agent_type,
                    e,
                )
        return cached


    def list_agents(self) -> list[tuple[str, str]]:
        """列出所有已加载的 Agent 类型及其描述。

        Returns:
            (agent_type, when_to_use) 元组列表。
        """
        return [
            (ad.agent_type, ad.when_to_use) for ad in self._agents.values()
        ]

    def register_plugin_source(self, path: Path) -> None:
        """注册插件来源路径（保留接口，当前未实现）。

        Args:
            path: 插件目录路径。
        """
        pass
