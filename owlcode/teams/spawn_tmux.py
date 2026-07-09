from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class TmuxPaneInfo:
    """tmux 窗格信息数据类。"""
    pane_id: str
    session: str


class TmuxSpawnError(Exception):
    """tmux 窗格启动异常。"""
    pass


def _run_tmux(*args: str) -> str:
    result = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise TmuxSpawnError(f"tmux {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def build_cli_command(
    team_name: str,
    teammate_name: str,
    worktree_path: str,
    prompt: str,
    agent_type: str = "",
    model: str = "",
    mailbox_dir: str = "",
) -> str:
    """构建启动团队成员的 owlcode CLI 命令字符串。

    包括环境变量设置和工作目录，支持指定 Agent 类型和模型。

    Args:
        team_name: 团队名称。
        teammate_name: 成员名称。
        worktree_path: 工作树路径。
        prompt: 任务提示词。
        agent_type: Agent 类型（可选）。
        model: 模型名称（可选）。
        mailbox_dir: 邮箱目录路径（可选）。

    Returns:
        可在 shell 中执行的 CLI 命令字符串。
    """
    parts = ["owlcode", "-p"]
    parts.extend(["--work-dir", worktree_path])
    if agent_type:
        parts.extend(["--agent-type", agent_type])
    if model:
        parts.extend(["--model", model])
    env_parts = [
        f"OWLCODE_TEAM_NAME={team_name}",
        f"OWLCODE_TEAMMATE_NAME={teammate_name}",
    ]
    if mailbox_dir:
        env_parts.append(f"OWLCODE_MAILBOX_DIR={mailbox_dir}")
    env_prefix = " ".join(env_parts)
    cmd = " ".join(parts)
    full_prompt = prompt.replace("'", "'\\''")
    return f"{env_prefix} {cmd} '{full_prompt}'"


def spawn_tmux_teammate(
    team_name: str,
    teammate_name: str,
    worktree_path: str,
    prompt: str,
    agent_type: str = "",
    model: str = "",
    mailbox_dir: str = "",
) -> TmuxPaneInfo:
    """在 tmux 新窗格/窗口中启动团队成员进程。

    首先尝试在当前 tmux 会话中 split-window，失败则创建 new-window，
    再失败则创建 new-session。最后通过 send-keys 发送 CLI 命令。

    Args:
        team_name: 团队名称（也作为 tmux session 名）。
        teammate_name: 成员名称。
        worktree_path: 工作树路径。
        prompt: 任务提示词。
        agent_type: Agent 类型。
        model: 模型名称。
        mailbox_dir: 邮箱目录路径。

    Returns:
        TmuxPaneInfo 包含 pane_id 和 session 名称。

    Raises:
        TmuxSpawnError: tmux 操作失败。
    """
    window_name = f"{team_name}-{teammate_name}"

    try:
        pane_id = _run_tmux(
            "split-window",
            "-h",
            "-P",
            "-F", "#{pane_id}",
            "-t", f"{team_name}",
        )
    except TmuxSpawnError:
        try:
            _run_tmux("new-window", "-t", f"{team_name}", "-n", window_name, "-P", "-F", "#{pane_id}")
            pane_id = _run_tmux(
                "split-window",
                "-h",
                "-P",
                "-F", "#{pane_id}",
                "-t", f"{team_name}:{window_name}",
            )
        except TmuxSpawnError:
            _run_tmux("new-session", "-d", "-s", team_name, "-n", window_name)
            pane_id = _run_tmux(
                "list-panes",
                "-t", f"{team_name}:{window_name}",
                "-F", "#{pane_id}",
            ).split("\n")[0]

    cli_cmd = build_cli_command(
        team_name=team_name,
        teammate_name=teammate_name,
        worktree_path=worktree_path,
        prompt=prompt,
        agent_type=agent_type,
        model=model,
        mailbox_dir=mailbox_dir,
    )
    _run_tmux("send-keys", "-t", pane_id, cli_cmd, "Enter")

    log.info("Spawned tmux teammate %s in pane %s", teammate_name, pane_id)
    return TmuxPaneInfo(pane_id=pane_id, session=team_name)


def send_keys_to_pane(pane_id: str, keys: str = "") -> None:
    """向指定的 tmux 窗格发送按键。

    Args:
        pane_id: 目标窗格 ID。
        keys: 要发送的按键字符串。
    """
    try:
        _run_tmux("send-keys", "-t", pane_id, keys, "Enter")
    except TmuxSpawnError:
        log.warning("Failed to send keys to tmux pane %s", pane_id)


def kill_pane(pane_id: str) -> None:
    """关闭指定的 tmux 窗格。

    Args:
        pane_id: 目标窗格 ID。
    """
    try:
        _run_tmux("kill-pane", "-t", pane_id)
    except TmuxSpawnError:
        pass
