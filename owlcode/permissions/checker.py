"""权限检查器：多层级安全策略决策引擎。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from owlcode.permissions.dangerous import DangerousCommandDetector, is_safe_command
from owlcode.permissions.modes import DecisionEffect, PermissionMode, mode_decide
from owlcode.permissions.rules import RuleEngine, extract_content
from owlcode.permissions.sandbox import PathSandbox
from owlcode.tools.base import Tool

_PLAN_MODE_ALLOWED_TOOLS = frozenset({"Agent", "ToolSearch", "AskUserQuestion", "ExitPlanMode"})


@dataclass
class Decision:
    """权限检查决策结果，包含放行/拒绝/询问以及原因说明。"""

    effect: DecisionEffect
    reason: str


class PermissionChecker:
    """多层级权限检查器，按优先级逐层过滤工具调用。

    检查层级（由高到低）：
    Layer 0: Plan 模式例外放行
    Layer 1: 安全只读命令自动放行 / 危险命令黑名单拦截
    Layer 2: 路径沙箱拦截
    Layer 3: 规则引擎匹配
    Layer 4: 权限模式兜底判定
    Layer 5: 人工确认（HITL）
    """

    def __init__(
        self,
        detector: DangerousCommandDetector,
        sandbox: PathSandbox,
        rule_engine: RuleEngine,
        mode: PermissionMode = PermissionMode.DEFAULT,
    ) -> None:
        """初始化权限检查器。

        Args:
            detector: 危险命令检测器。
            sandbox: 路径沙箱。
            rule_engine: 规则引擎。
            mode: 权限模式，默认 DEFAULT。
        """
        self.detector = detector
        self.sandbox = sandbox
        self.rule_engine = rule_engine
        self.mode = mode
        self.plan_file_path: str = ""

    def check(self, tool: Tool, arguments: dict[str, Any]) -> Decision:
        """对一次工具调用执行多层级权限检查。

        Args:
            tool: 要检查的工具对象。
            arguments: 工具调用参数。

        Returns:
            Decision，包含 effect（allow/deny/ask）和 reason。
        """
        content = extract_content(tool.name, arguments)

        # Layer 0: Plan 模式例外放行
        if self.mode == PermissionMode.PLAN:
            if tool.name in _PLAN_MODE_ALLOWED_TOOLS:
                return Decision(effect="allow", reason="Plan mode: allowed tool")
            if tool.name in ("WriteFile", "EditFile") and content:
                if self._is_plan_file(content):
                    return Decision(effect="allow", reason="Plan mode: plan file write")

        # Layer 1: 安全的只读命令（自动放行）
        if tool.category == "command" and is_safe_command(content or ""):
            return Decision(effect="allow", reason="Safe read-only command")

        # Layer 1b: 危险命令黑名单（仅 Bash）
        if tool.category == "command":
            hit, reason = self.detector.detect(content)
            if hit:
                return Decision(effect="deny", reason=f"危险命令拦截: {reason}")

        # Layer 2: 路径沙箱（仅文件类工具）
        if tool.category in ("read", "write") and content:
            ok, reason = self.sandbox.check(content)
            if not ok:
                return Decision(effect="deny", reason=f"路径沙箱拦截: {reason}")

        # Layer 3: 规则引擎匹配
        rule_result = self.rule_engine.evaluate(tool.name, content)
        if rule_result == "allow":
            return Decision(effect="allow", reason="权限规则放行")
        if rule_result == "deny":
            return Decision(effect="deny", reason="权限规则拒绝")

        # Layer 4: 权限模式兜底判定
        effect = mode_decide(self.mode, tool.category)
        if effect == "allow":
            return Decision(effect="allow", reason=f"权限模式 {self.mode.value} 放行")
        if effect == "deny":
            return Decision(effect="deny", reason=f"权限模式 {self.mode.value} 拒绝")

        # Layer 5: 触发人工确认（HITL）
        return Decision(effect="ask", reason="需要用户确认")

    def _is_plan_file(self, target_path: str) -> bool:
        """判断目标路径是否为 Plan 模式计划文件。

        匹配策略：绝对路径相同、文件名相同、或路径包含 .owlcode/plans/。

        Args:
            target_path: 待检查的文件路径。

        Returns:
            是计划文件返回 True。
        """
        if not self.plan_file_path or not target_path:
            return ".owlcode/plans/" in target_path
        try:
            abs_target = os.path.abspath(target_path)
            abs_plan = os.path.abspath(self.plan_file_path)
            if abs_target == abs_plan:
                return True
        except Exception:
            pass
        if os.path.basename(target_path) == os.path.basename(self.plan_file_path):
            return True
        return ".owlcode/plans/" in target_path
