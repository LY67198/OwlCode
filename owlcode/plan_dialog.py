from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Static


class PlanChoice(str, Enum):
    """Plan 审批中的用户选择：YOLO 模式、手动审批或反馈。"""

    YOLO = "yolo"
    MANUAL = "manual"
    FEEDBACK = "feedback"


_OPTIONS = [
    ("Yes, enter YOLO mode (auto-approve all)", PlanChoice.YOLO),
    ("Yes, manually approve edits", PlanChoice.MANUAL),
    ("Tell OwlCode what to change", PlanChoice.FEEDBACK),
]


class InlinePlanWidget(Vertical, can_focus=True):
    """内联的计划审批组件，格式与 Go 版 TUI 保持一致。"""

    BINDINGS = [
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("enter", "select", "Select", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("shift+tab", "approve_with_feedback", "Approve+Feedback", priority=True),
    ]

    class Responded(Message):
        """用户对 Plan 审批弹窗做出应答后发出的消息。"""

        def __init__(self, choice: PlanChoice, feedback: str = "") -> None:
            super().__init__()
            self.choice = choice
            self.feedback = feedback

    def __init__(self, **kwargs) -> None:
        """初始化 Plan 审批组件。"""
        super().__init__(id="plan-inline", **kwargs)
        self._cursor = 0
        self._input = ""

    def compose(self) -> ComposeResult:
        yield Static(self._build_content(), id="plan-content")

    def on_mount(self) -> None:
        """挂载后自动获取焦点。"""
        self.focus()

    def _build_content(self) -> str:
        lines = [
            "\n [bold #875fff]OwlCode has written up a plan and is ready to execute. "
            "Would you like to proceed?[/bold #875fff]\n"
        ]
        for i, (label, _choice) in enumerate(_OPTIONS):
            if i == self._cursor:
                lines.append(f" [bold cyan]❯[/bold cyan] {i + 1}. [bold]{label}[/bold]")
            else:
                lines.append(f"   {i + 1}. [dim]{label}[/dim]")

        if self._cursor == 2:
            display = self._input if self._input else "[dim]Type feedback here...[/dim]"
            lines.append(f"      {display}█")
            lines.append("      [dim]shift+tab to approve with this feedback[/dim]")

        return "\n".join(lines)

    def _refresh(self) -> None:
        """刷新渲染内容。"""
        self.query_one("#plan-content", Static).update(self._build_content())

    def action_cursor_up(self) -> None:
        """光标上移。"""
        if self._cursor > 0:
            self._cursor -= 1
            self._refresh()

    def action_cursor_down(self) -> None:
        """光标下移。"""
        if self._cursor < 2:
            self._cursor += 1
            self._refresh()

    def action_select(self) -> None:
        """确认选择。"""
        if self._cursor == 2 and self._input:
            self.post_message(self.Responded(PlanChoice.FEEDBACK, self._input))
        elif self._cursor == 0:
            self.post_message(self.Responded(PlanChoice.YOLO))
        elif self._cursor == 1:
            self.post_message(self.Responded(PlanChoice.MANUAL))

    def action_cancel(self) -> None:
        """取消操作，默认等同于手动审批。"""
        self.post_message(self.Responded(PlanChoice.MANUAL))

    def action_approve_with_feedback(self) -> None:
        """当光标在反馈输入框且已有内容时，提交反馈。"""
        if self._cursor == 2 and self._input:
            self.post_message(self.Responded(PlanChoice.FEEDBACK, self._input))

    def on_key(self, event) -> None:
        """处理键盘输入，仅在反馈模式下接受自由文本输入。"""
        if self._cursor != 2:
            return
        key = event.key
        if key == "backspace":
            if self._input:
                self._input = self._input[:-1]
                self._refresh()
            event.stop()
        elif len(key) == 1 and key.isprintable():
            self._input += key
            self._refresh()
            event.stop()
