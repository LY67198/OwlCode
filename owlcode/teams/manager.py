from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlcode.teams.backend_detect import BackendDetectionError, detect_backend
from owlcode.teams.mailbox import Mailbox, create_message
from owlcode.teams.models import (
    AgentTeam,
    BackendType,
    TeammateInfo,
    resolve_team_dir,
    unique_team_name,
)
from owlcode.teams.progress import TeammateProgress
from owlcode.teams.registry import AgentNameRegistry
from owlcode.teams.shared_task import SharedTaskStore
from owlcode.teams.spawn_inprocess import InProcessTeammateHandle

if TYPE_CHECKING:
    from owlcode.agent import Agent

log = logging.getLogger(__name__)


class TeamError(Exception):
    """团队管理相关异常。"""
    pass


class TeamManager:
    """团队管理器，负责团队的创建、成员注册、后端检测与生命周期管理。

    管理团队配置持久化、任务共享存储、邮件、进程内句柄和终端窗格映射。
    """

    def __init__(self, worktree_manager: Any = None, trace_manager: Any = None) -> None:
        """初始化团队管理器。

        Args:
            worktree_manager: 可选的工作树管理器引用。
            trace_manager: 可选的追踪管理器引用。
        """
        self._teams: dict[str, AgentTeam] = {}
        self._task_stores: dict[str, SharedTaskStore] = {}
        self._mailboxes: dict[str, Mailbox] = {}
        self._inprocess_handles: dict[str, InProcessTeammateHandle] = {}
        self._pane_ids: dict[str, str] = {}  # agent_id -> pane_id (tmux/iterm2)
        self._detected_backend: BackendType | None = None
        self._worktree_manager = worktree_manager
        self._trace_manager = trace_manager
        self._teammate_team_map: dict[str, str] = {}  # agent_id -> team_name

    def detect_backend(
        self,
        teammate_mode: str = "",
        is_interactive: bool = True,
    ) -> BackendType:
        """检测后端类型（惰性检测，结果缓存）。

        Args:
            teammate_mode: 团队成员模式。
            is_interactive: 是否为交互模式。

        Returns:
            检测到的 BackendType。
        """
        if self._detected_backend is None:
            self._detected_backend = detect_backend(teammate_mode, is_interactive)
        return self._detected_backend


    def create_team(
        self,
        name: str,
        lead_agent_id: str,
        description: str = "",
        teammate_mode: str = "",
        is_interactive: bool = True,
    ) -> AgentTeam:
        """创建新团队。

        创建团队目录、配置文件、共享任务存储和邮箱。

        Args:
            name: 团队名称。
            lead_agent_id: 团队领导 Agent ID。
            description: 团队描述。
            teammate_mode: 成员运行模式。
            is_interactive: 是否交互模式。

        Returns:
            新创建的 AgentTeam 实例。
        """
        backend = self.detect_backend(teammate_mode, is_interactive)
        slug = unique_team_name(name)
        team_dir = resolve_team_dir(slug)
        team_dir.mkdir(parents=True, exist_ok=True)

        config_path = str(team_dir / "config.json")
        team = AgentTeam(
            name=slug,
            lead_agent_id=lead_agent_id,
            config_path=config_path,
            description=description,
        )
        team.save()

        task_store = SharedTaskStore(team_dir / "tasks.json")
        task_store.init_empty()

        mailbox_dir = team_dir / "mailbox"
        mailbox_dir.mkdir(parents=True, exist_ok=True)
        mailbox = Mailbox(mailbox_dir)

        self._teams[slug] = team
        self._task_stores[slug] = task_store
        self._mailboxes[slug] = mailbox

        log.info("Created team '%s' at %s (backend=%s)", slug, team_dir, backend.value)
        return team


    def get_team(self, name: str) -> AgentTeam | None:
        """获取团队对象，优先从内存缓存取，其次从磁盘加载。

        Args:
            name: 团队名称。

        Returns:
            AgentTeam 实例，不存在则返回 None。
        """
        if name in self._teams:
            return self._teams[name]
        team_dir = resolve_team_dir(name)
        config_path = team_dir / "config.json"
        if config_path.exists():
            team = AgentTeam.load(str(config_path))
            self._teams[name] = team
            return team
        return None

    def get_task_store(self, team_name: str) -> SharedTaskStore | None:
        """获取团队的共享任务存储。

        Args:
            team_name: 团队名称。

        Returns:
            SharedTaskStore 实例，不存在则返回 None。
        """
        if team_name in self._task_stores:
            return self._task_stores[team_name]
        team_dir = resolve_team_dir(team_name)
        tasks_path = team_dir / "tasks.json"
        if tasks_path.exists():
            store = SharedTaskStore(tasks_path)
            self._task_stores[team_name] = store
            return store
        return None

    def get_mailbox(self, team_name: str) -> Mailbox | None:
        """获取团队的邮箱。

        Args:
            team_name: 团队名称。

        Returns:
            Mailbox 实例，不存在则返回 None。
        """
        if team_name in self._mailboxes:
            return self._mailboxes[team_name]
        team_dir = resolve_team_dir(team_name)
        mailbox_dir = team_dir / "mailbox"
        if mailbox_dir.exists():
            mailbox = Mailbox(mailbox_dir)
            self._mailboxes[team_name] = mailbox
            return mailbox
        return None

    def register_member(
        self,
        team_name: str,
        member: TeammateInfo,
    ) -> None:
        """在团队中注册新成员。

        Args:
            team_name: 团队名称。
            member: 成员信息。

        Raises:
            TeamError: 团队不存在。
        """
        team = self.get_team(team_name)
        if team is None:
            raise TeamError(f"Team '{team_name}' not found")
        team.add_member(member)
        team.save()

        AgentNameRegistry.instance().register(member.name, member.agent_id)
        self._teammate_team_map[member.agent_id] = team_name
        log.info("Registered member '%s' (agent=%s) in team '%s'", member.name, member.agent_id, team_name)

    def set_member_idle(self, team_name: str, member_name: str) -> None:
        """将团队成员标记为空闲状态。

        Args:
            team_name: 团队名称。
            member_name: 成员名称。
        """
        team = self.get_team(team_name)
        if team is None:
            return
        team.set_member_active(member_name, False)
        team.save()

        mailbox = self.get_mailbox(team_name)
        if mailbox:
            msg = create_message(
                from_agent=member_name,
                to_agent=team.lead_agent_id,
                content=f"Teammate '{member_name}' is now idle (run_to_completion finished).",
                summary=f"{member_name} idle",
                message_type="text",
            )
            mailbox.write(team.lead_agent_id, msg)

    def register_inprocess_handle(self, agent_id: str, handle: InProcessTeammateHandle) -> None:
        """注册进程内成员的执行句柄。

        Args:
            agent_id: Agent ID。
            handle: 进程内执行句柄。
        """
        self._inprocess_handles[agent_id] = handle

    def register_pane_id(self, agent_id: str, pane_id: str) -> None:
        """注册终端窗格 ID 与 Agent 的映射。

        Args:
            agent_id: Agent ID。
            pane_id: 终端窗格 ID。
        """
        self._pane_ids[agent_id] = pane_id


    def get_pane_id(self, agent_id: str) -> str | None:
        """获取 Agent 对应的终端窗格 ID。

        Args:
            agent_id: Agent ID。

        Returns:
            窗格 ID 字符串，不存在则返回 None。
        """
        return self._pane_ids.get(agent_id)

    def delete_team(self, team_name: str) -> None:
        """删除团队及其所有资源。

        包括取消活跃成员、清理窗口/窗格、删除工作树和邮箱目录。

        Args:
            team_name: 团队名称。

        Raises:
            TeamError: 团队不存在或仍有活跃成员。
        """
        team = self.get_team(team_name)
        if team is None:
            raise TeamError(f"Team '{team_name}' not found")

        active = [m for m in team.members if m.is_active is not False]
        if active:
            names = ", ".join(m.name for m in active)
            raise TeamError(f"Cannot delete team: active members: {names}")

        for member in list(team.members):
            AgentNameRegistry.instance().unregister(member.name)

            handle = self._inprocess_handles.pop(member.agent_id, None)
            if handle and not handle.done:
                handle.cancel()

            pane_id = self._pane_ids.pop(member.agent_id, None)
            if pane_id:
                self._kill_pane(pane_id, member.backend_type)

            if member.worktree_path:
                self._cleanup_worktree(member.worktree_path)

            if self._trace_manager:
                self._trace_manager.remove(member.agent_id)

        mailbox = self.get_mailbox(team_name)
        if mailbox:
            mailbox.cleanup_all()

        team_dir = resolve_team_dir(team_name)
        self._remove_dir(team_dir)

        self._teams.pop(team_name, None)
        self._task_stores.pop(team_name, None)
        self._mailboxes.pop(team_name, None)

        log.info("Deleted team '%s'", team_name)

    def get_team_for_teammate(self, agent_id: str) -> str | None:
        """根据 Agent ID 查找所属团队名称。

        Args:
            agent_id: Agent ID。

        Returns:
            团队名称，未找到则返回 None。
        """
        if agent_id in self._teammate_team_map:
            return self._teammate_team_map[agent_id]
        for name, team in self._teams.items():
            for m in team.members:
                if m.agent_id == agent_id:
                    return name
        return None


    def drain_lead_mailbox(self) -> list[str]:
        """消费所有团队 lead 邮箱中的消息，格式化为通知。

        Returns:
            格式化的团队通知字符串列表。
        """
        notes: list[str] = []
        for team_name in list(self._teams.keys()):
            team = self.get_team(team_name)
            if team is None:
                continue
            mailbox = self.get_mailbox(team_name)
            if mailbox is None:
                continue
            msgs = mailbox.consume(team.lead_agent_id)
            if not msgs:
                continue
            parts = [f'<team-notification team="{team_name}">']
            for m in msgs:
                parts.append(f"from={m.from_agent}: {m.content}")
            parts.append("</team-notification>")
            notes.append("\n".join(parts))
        return notes

    def get_all_teammate_progress(self) -> list[TeammateProgress]:
        """Collect progress objects attached to every registered teammate."""
        results: list[TeammateProgress] = []
        for team in self._teams.values():
            for member in team.members:
                if hasattr(member, "progress") and member.progress is not None:
                    results.append(member.progress)
        return results

    def on_teammate_completed(self, agent_id: str) -> None:
        """成员任务完成时的回调处理。

        Args:
            agent_id: 完成任务的 Agent ID。
        """
        team_name = self.get_team_for_teammate(agent_id)
        if team_name is None:
            return
        team = self.get_team(team_name)
        if team is None:
            return
        member = next((m for m in team.members if m.agent_id == agent_id), None)
        if member:
            self.set_member_idle(team_name, member.name)


    def _kill_pane(self, pane_id: str, backend_type: str) -> None:
        try:
            if backend_type == BackendType.TMUX.value:
                from owlcode.teams.spawn_tmux import kill_pane
                kill_pane(pane_id)
        except Exception as e:
            log.warning("Failed to kill pane %s: %s", pane_id, e)

    def _cleanup_worktree(self, worktree_path: str) -> None:
        import subprocess
        try:
            subprocess.run(
                ["git", "worktree", "remove", worktree_path, "--force"],
                capture_output=True, timeout=10,
            )
        except Exception as e:
            log.warning("git worktree remove failed for %s: %s", worktree_path, e)
            import shutil
            try:
                if Path(worktree_path).exists():
                    shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                pass

    def _remove_dir(self, path: Path) -> None:
        import shutil
        try:
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            log.warning("Failed to remove directory %s: %s", path, e)
