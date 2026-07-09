"""路径沙箱：限制文件系统操作在允许的目录范围内。"""

from __future__ import annotations

import tempfile
from pathlib import Path


class PathSandbox:
    """路径沙箱，确保文件操作不超出项目根目录和临时目录范围。

    支持扩展额外的允许目录。
    """

    def __init__(
        self,
        project_root: str,
        extra_allowed: list[str] | None = None,
    ) -> None:
        """初始化路径沙箱。

        Args:
            project_root: 项目根目录。
            extra_allowed: 额外允许的目录路径列表。
        """
        root = Path(project_root).resolve()
        self._allowed_roots: list[Path] = [root, Path(tempfile.gettempdir()).resolve()]
        if extra_allowed:
            for p in extra_allowed:
                self._allowed_roots.append(Path(p).resolve())

    @property
    def project_root(self) -> Path:
        """项目根目录的 Path 对象。"""
        return self._allowed_roots[0]

    def check(self, path: str) -> tuple[bool, str]:
        """检查指定路径是否在沙箱允许范围内。

        相对路径会基于 project_root 解析，支持 ~ 展开和符号链接解析。

        Args:
            path: 待检查的文件路径。

        Returns:
            (是否允许, 拒绝原因) 元组。允许时返回 (True, "")。
        """
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.project_root / p
        abs_path = p.absolute()

        try:
            real_path = abs_path.resolve(strict=True)
        except OSError:
            ancestor = abs_path
            while not ancestor.exists():
                parent = ancestor.parent
                if parent == ancestor:
                    return False, f"无法解析路径: {path}"
                ancestor = parent
            try:
                resolved_ancestor = ancestor.resolve(strict=True)
            except OSError:
                return False, f"无法解析路径: {path}"
            real_path = resolved_ancestor / abs_path.relative_to(ancestor)

        for root in self._allowed_roots:
            try:
                real_path.relative_to(root)
                return True, ""
            except ValueError:
                continue

        return False, f"路径 {path} 超出沙箱范围"
