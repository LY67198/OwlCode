"""斜杠命令自动补全弹出层组件。"""

from __future__ import annotations

from textual.message import Message as TMessage
from textual.widgets import Static


class CompletionPopup(Static):
    """斜杠命令的自动补全弹出层，以高亮可选项列表的方式显示候选项。"""

    DEFAULT_CSS = """
    CompletionPopup {
        height: auto;
        max-height: 8;
        display: none;
        padding: 0 1;
    }
    """

    class Selected(TMessage):
        """用户选定某个补全项后发出的消息。"""

        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._displays: list[str] = []
        self._values: list[str] = []
        self._cursor: int = 0

    def show_pairs(self, pairs: list[tuple[str, str]]) -> None:
        """以 (display_text, value) 对的形式显示候选项。"""
        self._displays = [d for d, _ in pairs]
        self._values = [v for _, v in pairs]
        self._cursor = 0
        self._refresh_content()
        self.display = True

    def show(self, items: list[str]) -> None:
        """显示候选项列表，每个候选项的显示文本与取值相同。

        Args:
            items: 候选项字符串列表。
        """
        self.show_pairs([(i, i) for i in items])

    def hide(self) -> None:
        """隐藏弹出层并清空所有候选项。"""
        self.display = False
        self._displays = []
        self._values = []
        self._cursor = 0

    @property
    def is_visible(self) -> bool:
        """返回弹出层当前是否可见。"""
        return bool(self.display)

    def move_up(self) -> None:
        """将高亮光标向上移动一项。"""
        if self._displays and self._cursor > 0:
            self._cursor -= 1
            self._refresh_content()

    def move_down(self) -> None:
        """将高亮光标向下移动一项。"""
        if self._displays and self._cursor < len(self._displays) - 1:
            self._cursor += 1
            self._refresh_content()

    def get_selected(self) -> str | None:
        """返回当前高亮项的值。

        Returns:
            当前选中项的值字符串，无候选项时返回 None。
        """
        if not self._values:
            return None
        return self._values[self._cursor]

    def _refresh_content(self) -> None:
        lines = []
        for i, display in enumerate(self._displays):
            if i == self._cursor:
                lines.append(f"[bold reverse] {display} [/]")
            else:
                lines.append(f"  [dim]{display}[/]")
        self.update("\n".join(lines))

    def on_click(self) -> None:
        """处理点击事件：获取当前选中值并发出 Selected 消息后隐藏。"""
        selected = self.get_selected()
        if selected:
            self.post_message(self.Selected(selected))
            self.hide()
