"""技能加载器：从项目、用户目录和内置资源中加载技能定义。"""

from __future__ import annotations

import importlib.resources
import logging
from pathlib import Path

from owlcode.skills.parser import SkillDef, SkillParseError, parse_frontmatter, parse_skill_file

log = logging.getLogger(__name__)

PROJECT_SKILLS_DIR = ".owlcode/skills"
USER_SKILLS_DIR = "~/.owlcode/skills"


class SkillLoader:
    """技能加载器，负责从多个来源加载并缓存技能定义。

    加载优先级：项目 > 用户 > 内置。同名技能以先加载的为准。
    """

    def __init__(self, work_dir: str) -> None:
        self._work_dir = work_dir
        self._project_dir = Path(work_dir) / PROJECT_SKILLS_DIR
        self._user_dir = Path(USER_SKILLS_DIR).expanduser()
        self._skills: dict[str, SkillDef] = {}
        self._cache: dict[str, SkillDef] = {}

    def load_all(self) -> dict[str, SkillDef]:
        """加载所有可用的技能定义。

        Returns:
            以技能名称为键、SkillDef 为值的字典。
        """
        seen: dict[str, SkillDef] = {}

        for skill in self._scan_directory(self._project_dir, "project"):
            if skill.name not in seen:
                seen[skill.name] = skill

        for skill in self._scan_directory(self._user_dir, "user"):
            if skill.name not in seen:
                seen[skill.name] = skill

        for skill in self._load_builtins():
            if skill.name not in seen:
                seen[skill.name] = skill

        self._skills = seen
        self._cache = {k: v for k, v in seen.items()}
        return seen

    def _scan_directory(self, path: Path, source: str) -> list[SkillDef]:
        """扫描指定目录，解析其中所有技能文件。

        Args:
            path: 待扫描的目录路径。
            source: 技能来源标签（如 "project"、"user"）。

        Returns:
            解析出的 SkillDef 列表。
        """
        results: list[SkillDef] = []
        if not path.is_dir():
            return results

        for entry in sorted(path.iterdir()):
            try:
                if entry.is_file() and entry.suffix == ".md":
                    skill = parse_skill_file(entry)
                    skill.source_path = entry
                    results.append(skill)
                elif entry.is_dir():
                    skill_md = entry / "SKILL.md"
                    if skill_md.is_file():
                        skill = parse_skill_file(skill_md)
                        skill.source_path = skill_md
                        skill.is_directory = True
                        results.append(skill)
            except SkillParseError as e:
                log.warning("Skipping %s skill '%s': %s", source, entry.name, e)

        return results

    def _load_builtins(self) -> list[SkillDef]:
        """从包内 builtins 目录加载内置技能。

        Returns:
            内置技能的 SkillDef 列表。
        """
        results: list[SkillDef] = []
        builtins_pkg = importlib.resources.files("owlcode.skills.builtins")

        for resource in builtins_pkg.iterdir():
            skill_md = resource / "SKILL.md" if resource.is_dir() else None
            if skill_md is None or not skill_md.is_file():
                continue
            try:
                raw = skill_md.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(raw)
                from owlcode.skills.parser import _validate_meta
                _validate_meta(meta, f"builtin:{resource.name}")
                source = None
                try:
                    source = Path(str(skill_md))
                except Exception:
                    pass
                skill = SkillDef(
                    name=meta["name"],
                    description=meta["description"],
                    prompt_body=body,
                    allowed_tools=meta.get("allowedTools", []),
                    mode=meta.get("mode", "inline"),
                    model=meta.get("model"),
                    context=meta.get("context", "full"),
                    source_path=source,
                    is_directory=True,
                )
                results.append(skill)
            except (SkillParseError, Exception) as e:
                log.warning("Skipping builtin skill '%s': %s", resource.name, e)

        return results

    def get(self, name: str) -> SkillDef | None:
        """按名称获取技能定义，支持热重载。

        如果技能有源文件路径，会尝试重新解析文件以获取最新内容；
        解析失败时回退到缓存版本。

        Args:
            name: 技能名称。

        Returns:
            对应的 SkillDef，未找到时返回 None。
        """
        skill = self._skills.get(name)
        if skill is None:
            return None

        if skill.source_path is not None:
            try:
                fresh = parse_skill_file(skill.source_path)
                fresh.is_directory = skill.is_directory
                self._skills[name] = fresh
                self._cache[name] = fresh
                return fresh
            except SkillParseError as e:
                log.warning(
                    "Hot-reload failed for skill '%s', using cached version: %s",
                    name, e,
                )
                return self._cache.get(name, skill)

        return skill

    def get_catalog(self) -> list[tuple[str, str]]:
        """获取所有技能的目录列表。

        Returns:
            (名称, 描述) 元组的列表。
        """
        return [(s.name, s.description) for s in self._skills.values()]

    def reload(self) -> dict[str, SkillDef]:
        """重新加载所有技能。

        Returns:
            重新加载后的技能字典。
        """
        return self.load_all()

    def get_source_label(self, name: str) -> str:
        """获取指定技能的来源标签。

        Args:
            name: 技能名称。

        Returns:
            来源字符串：project、user、builtin 或 unknown。
        """
        skill = self._skills.get(name)
        if skill is None:
            return "unknown"
        if skill.source_path is None:
            return "builtin"
        path_str = str(skill.source_path)
        if path_str.startswith(str(self._project_dir)):
            return "project"
        if path_str.startswith(str(self._user_dir)):
            return "user"
        return "builtin"
