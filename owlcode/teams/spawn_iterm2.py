from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class ITermPaneInfo:
    """iTerm2 窗格信息数据类。"""
    session_id: str


class ITermSpawnError(Exception):
    """iTerm2 窗格启动异常。"""
    pass


def _run_it2(*args: str) -> str:
    result = subprocess.run(
        ["it2", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise ITermSpawnError(f"it2 {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def spawn_iterm2_teammate(
    team_name: str,
    teammate_name: str,
    worktree_path: str,
    prompt: str,
    agent_type: str = "",
    model: str = "",
    mailbox_dir: str = "",
) -> ITermPaneInfo:
    """在 iTerm2 新窗格中启动团队成员进程。

    构建 owlcode CLI 命令，通过 iTerm2 的 split-pane 功能启动。

    Args:
        team_name: 团队名称。
        teammate_name: 成员名称。
        worktree_path: 工作树路径。
        prompt: 任务提示词。
        agent_type: Agent 类型。
        model: 模型名称。
        mailbox_dir: 邮箱目录路径。

    Returns:
        ITermPaneInfo 包含 session_id。

    Raises:
        ITermSpawnError: 启动窗格失败。
    """
    from owlcode.teams.spawn_tmux import build_cli_command

    cli_cmd = build_cli_command(
        team_name=team_name,
        teammate_name=teammate_name,
        worktree_path=worktree_path,
        prompt=prompt,
        agent_type=agent_type,
        model=model,
        mailbox_dir=mailbox_dir,
    )

    try:
        session_id = _run_it2("split-pane", "--command", f"/bin/zsh -c '{cli_cmd}'")
    except ITermSpawnError as e:
        raise ITermSpawnError(f"Failed to spawn iTerm2 pane for {teammate_name}: {e}") from e

    log.info("Spawned iTerm2 teammate %s in session %s", teammate_name, session_id)
    return ITermPaneInfo(session_id=session_id)
