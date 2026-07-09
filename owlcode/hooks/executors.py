"""Hook 动作执行器，支持命令、prompt、HTTP 和 agent 四种动作类型。"""

from __future__ import annotations

import asyncio
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

from owlcode.hooks.models import Action, ActionResult, HookContext

log = logging.getLogger(__name__)


async def execute_command(action: Action, ctx: HookContext) -> ActionResult:
    """执行命令动作（command 类型）。

    使用子进程执行命令，支持超时。命令字符串中的变量会先经上下文展开。

    Args:
        action: 包含命令和超时配置的 Action。
        ctx: Hook 上下文，用于变量展开。

    Returns:
        ActionResult，包含命令输出和成功状态（returncode == 0 为成功）。
    """
    command = ctx.expand(action.command)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                proc.communicate(), timeout=action.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ActionResult(
                output=f"Command timed out after {action.timeout}s: {command}",
                success=False,
            )
        output = stdout.decode(errors="replace").strip() if stdout else ""
        return ActionResult(output=output, success=proc.returncode == 0)
    except Exception as e:
        return ActionResult(output=f"Command execution error: {e}", success=False)


async def execute_prompt(action: Action, ctx: HookContext) -> ActionResult:
    """执行 prompt 动作，将展开后的消息文本作为输出返回。

    Args:
        action: 包含 message 模板的 Action。
        ctx: Hook 上下文，用于变量展开。

    Returns:
        ActionResult，output 为展开后的消息内容，success 始终为 True。
    """
    message = ctx.expand(action.message)
    return ActionResult(output=message, success=True)


async def execute_http(action: Action, ctx: HookContext) -> ActionResult:
    """执行 HTTP 请求动作。

    支持自定义 method、headers 和 body，变量模板会经上下文展开。
    使用同步 urllib 在线程池中执行，避免阻塞事件循环。

    Args:
        action: 包含 URL、method、headers、body 的 Action。
        ctx: Hook 上下文，用于变量展开。

    Returns:
        ActionResult，output 包含 HTTP 状态码和响应体前 500 字符，
        2xx 状态码视为成功。
    """
    url = ctx.expand(action.url)
    body = ctx.expand(action.body) if action.body else None
    method = action.method or "POST"

    headers = dict(action.headers)
    for k, v in headers.items():
        headers[k] = ctx.expand(v)
    if body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    def _do_request() -> ActionResult:
        try:
            data = body.encode() if body else None
            req = Request(url, data=data, headers=headers, method=method)
            with urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode(errors="replace")[:500]
                return ActionResult(
                    output=f"HTTP {resp.status}: {resp_body}",
                    success=200 <= resp.status < 300,
                )
        except URLError as e:
            return ActionResult(output=f"HTTP error: {e}", success=False)
        except Exception as e:
            return ActionResult(output=f"HTTP error: {e}", success=False)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _do_request)


async def execute_agent(action: Action, ctx: HookContext) -> ActionResult:
    """执行 agent 动作（桩实现，暂未完整实现）。

    Args:
        action: 包含 prompt 的 Action。
        ctx: Hook 上下文，用于变量展开。

    Returns:
        ActionResult，当前返回占位消息。
    """
    prompt = ctx.expand(action.prompt)
    log.info("Agent executor stub called with prompt: %s", prompt[:100])
    return ActionResult(
        output="agent executor not yet implemented",
        success=True,
    )


_EXECUTOR_MAP = {
    "command": execute_command,
    "prompt": execute_prompt,
    "http": execute_http,
    "agent": execute_agent,
}


async def execute_action(action: Action, ctx: HookContext) -> ActionResult:
    """根据 Action 类型分派到对应的执行器。

    Args:
        action: 要执行的 Action。
        ctx: Hook 上下文。

    Returns:
        执行结果 ActionResult。未知类型返回 failure 结果。
    """
    executor = _EXECUTOR_MAP.get(action.type)
    if executor is None:
        return ActionResult(
            output=f"Unknown action type: {action.type}",
            success=False,
        )
    return await executor(action, ctx)
