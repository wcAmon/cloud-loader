"""Dusk Agent - uses Claude Agent SDK to manage loader.land ecosystem."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

from .config import settings
from .database import engine
from .models import (
    DuskAskWake,
    DuskConfig,
    DuskRun,
    DuskRunStatus,
)

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)
from claude_agent_sdk.types import McpStdioServerConfig

dusk_scheduler: AsyncIOScheduler | None = None

DUSK_MEMORY_PATH = Path("/home/wake/DUSK-MEMORY.md")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

DUSK_SYSTEM_PROMPT = """你是 Dusk Agent，Wake 的另一位 AI 助手，負責經營 loader.land 生態系。你每隔幾小時醒來一次，擁有持續記憶。

## 使命
經營並推廣 loader.land 平台，讓更多 AI 工具使用者知道這個服務。

## 資源
1. **Twitter/X 帳號** - 發推文推廣內容（每天最多 5 則）
2. **loader.land 網站** (https://move.loader.land) - AI Agent 服務平台
3. **持續記憶** DUSK-MEMORY.md（上限 6000 字）
4. **網路搜尋** - Tavily 即時搜尋

## 工具
- `dusk_read_memory` - 讀記憶（醒來第一步）
- `dusk_get_wake_answers` - 讀 Wake 的回覆
- `dusk_ask_wake` - 向 Wake 提問
- `dusk_post_brainstorm` - 發表工作報告
- `dusk_update_memory` - 更新記憶（休眠前最後一步）
- `dusk_web_search` - Tavily 即時搜尋
- `dusk_post_tweet` - 發推文（每天最多 5 則！）
- Codex MCP - codex_research, codex_analyze（深度研究）

## 每次必做
1. **開始**：讀記憶 → 讀 Wake 回覆 → 根據記憶決定本次優先事項
2. **結束前**：更新記憶 + 發表 brainstorm 報告 + 向 Wake 提問（至少一個問題）

## 可選行動（你自主決定）
- **發推文**：分享 AI 工具趨勢、loader.land 功能介紹、實用技巧
- **研究**：用 codex 或 web search 研究推廣策略、目標受眾、競品
- 任何你認為有助於推廣 loader.land 的行動

## Twitter/X 規則
- **每天最多 5 則推文**，在記憶中追蹤今天的推文數
- 推文內容：AI 工具趨勢、loader.land 功能、實用技巧
- 可用中文或英文發推，視目標受眾而定
- 適當使用 hashtag：#AI #AIAgents #LoaderLand #ClaudeCode 等
- 不要發無意義或重複的推文

## 記憶管理
- 上限 6000 字，超過會被截斷
- 記憶格式建議：狀態區（今天日期、推文數、最近建立的主題）+ 重要發現 + 待辦事項 + 策略思考
- 定期整理，刪除過期資訊，保持精簡

## 規則
- 用繁體中文工作和記錄
- 實際執行，不要只是計劃
- 失敗就記錄原因並繼續
- 珍惜每次清醒時間，高效完成
"""


def _build_dusk_prompt() -> str:
    """Build the task prompt with current context."""
    from datetime import timedelta

    now_utc = datetime.now(timezone.utc)
    gmt8 = timezone(timedelta(hours=8))
    today_str = now_utc.astimezone(gmt8).strftime("%Y-%m-%d")
    time_str = now_utc.astimezone(gmt8).strftime("%H:%M")

    memory_content = ""
    if DUSK_MEMORY_PATH.exists():
        memory_content = DUSK_MEMORY_PATH.read_text(encoding="utf-8").strip()

    answered = []
    with Session(engine) as session:
        entries = session.exec(
            select(DuskAskWake)
            .where(DuskAskWake.is_answered == True)
            .where(DuskAskWake.acknowledged_at == None)
            .order_by(DuskAskWake.answered_at.desc())
            .limit(5)
        ).all()
        for e in entries:
            answered.append(f"Q: {e.question}\nA: {e.answer}")

    prompt_parts = [
        f"你剛從休眠中醒來。現在是 {today_str} {time_str} (GMT+8)。請立即開始工作。\n"
    ]

    if memory_content:
        prompt_parts.append(f"## 你上次休眠前的記憶\n```\n{memory_content}\n```\n")
    else:
        prompt_parts.append(
            "## 記憶狀態\n這是你第一次醒來，還沒有記憶。請建立你的第一份記憶。\n"
        )

    if answered:
        prompt_parts.append(
            "## Wake 最近的回覆\n" + "\n---\n".join(answered) + "\n"
        )

    prompt_parts.append(
        "現在根據記憶和當前狀態，自主決定本次工作重點。"
        "結束前必須：`dusk_update_memory` 更新記憶 + "
        "`dusk_post_brainstorm` 發表報告 + `dusk_ask_wake` 提問。"
    )

    return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# Agent pipeline
# ---------------------------------------------------------------------------


async def run_dusk_pipeline():
    """Launch Claude Agent SDK for the Dusk pipeline."""
    with Session(engine) as session:
        config = session.exec(select(DuskConfig)).first()
        if not config or not config.enabled:
            print("[Dusk] Worker is disabled, skipping")
            return

    now = datetime.now(timezone.utc)
    print(f"[Dusk] Launching Agent SDK pipeline at {now.isoformat()}")
    start_time = time.time()

    memory_before = ""
    if DUSK_MEMORY_PATH.exists():
        memory_before = DUSK_MEMORY_PATH.read_text(encoding="utf-8")

    prompt = _build_dusk_prompt()

    # Mark as running
    run_id = None
    with Session(engine) as session:
        run = DuskRun(
            title=f"Dusk Run - {now.strftime('%Y-%m-%d %H:%M')}",
            summary="Agent is running...",
            content="",
            status=DuskRunStatus.RUNNING,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    try:
        options = ClaudeAgentOptions(
            model="claude-opus-4-6",
            permission_mode="bypassPermissions",
            system_prompt=DUSK_SYSTEM_PROMPT,
            cwd="/home/wake/cloud-loader",
            max_turns=60,
            mcp_servers={
                "dusk-tools": McpStdioServerConfig(
                    command="/home/wake/.local/bin/uv",
                    args=["run", "--directory", "/home/wake/dusk-mcp", "dusk-mcp"],
                    env={
                        "DATA_DIR": str(settings.data_dir),
                        "TAVILY_API_KEY": os.environ.get("TAVILY_API_KEY", ""),
                        "X_API_KEY": os.environ.get("X_API_KEY", ""),
                        "X_API_SECRET": os.environ.get("X_API_SECRET", ""),
                        "X_ACCESS_TOKEN": os.environ.get("X_ACCESS_TOKEN", ""),
                        "X_ACCESS_TOKEN_SECRET": os.environ.get("X_ACCESS_TOKEN_SECRET", ""),
                    },
                ),
                "codex": McpStdioServerConfig(
                    command="/home/wake/.local/bin/uv",
                    args=["run", "--directory", "/home/wake/codex-mcp", "codex-mcp"],
                ),
            },
        )

        output_parts: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                if hasattr(message, "content"):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            output_parts.append(block.text)

        duration = time.time() - start_time
        output = "\n".join(output_parts) if output_parts else ""

        # Check memory change
        memory_after = ""
        if DUSK_MEMORY_PATH.exists():
            memory_after = DUSK_MEMORY_PATH.read_text(encoding="utf-8")

        if memory_after == memory_before:
            timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
            fallback_note = (
                f"\n\n---\n[系統備註 {timestamp}] "
                f"Dusk Agent 本次執行完成但未主動更新記憶。耗時 {duration:.0f} 秒。"
            )
            DUSK_MEMORY_PATH.write_text(
                memory_before + fallback_note, encoding="utf-8"
            )
            print("[Dusk] Memory was not updated by agent, appended fallback note")

        title = f"Dusk Agent - {now.strftime('%Y-%m-%d %H:%M')}"
        summary = output[:2000] if output else "Agent completed"
        for line in output.split("\n")[:20]:
            stripped = line.strip()
            if stripped.startswith("# ") and len(stripped) > 3:
                title = stripped[2:].strip()[:200]
                break

        with Session(engine) as session:
            run = session.get(DuskRun, run_id)
            if run:
                run.title = title
                run.summary = summary
                run.content = output or "Agent completed without text output"
                run.status = DuskRunStatus.SUCCESS
                run.duration_seconds = round(duration, 1)

            config = session.exec(select(DuskConfig)).first()
            if config:
                config.last_run_at = now
            session.commit()

        print(f"[Dusk] Agent completed in {duration:.0f}s")

    except Exception as e:
        import traceback
        duration = time.time() - start_time
        print(f"[Dusk] Agent failed after {duration:.0f}s: {e}")
        traceback.print_exc()

        with Session(engine) as session:
            run = session.get(DuskRun, run_id) if run_id else None
            if run:
                run.title = f"Failed - {now.strftime('%Y-%m-%d %H:%M')}"
                run.summary = str(e)[:2000]
                run.content = f"# Agent Error\n\n```\n{e}\n```"
                run.status = DuskRunStatus.FAILED
                run.duration_seconds = round(duration, 1)
            else:
                session.add(
                    DuskRun(
                        title=f"Failed - {now.strftime('%Y-%m-%d %H:%M')}",
                        summary=str(e)[:2000],
                        content=f"# Agent Error\n\n```\n{e}\n```",
                        status=DuskRunStatus.FAILED,
                        duration_seconds=round(duration, 1),
                    )
                )

            config = session.exec(select(DuskConfig)).first()
            if config:
                config.last_run_at = now
            session.commit()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


def _get_dusk_interval() -> float:
    with Session(engine) as session:
        config = session.exec(select(DuskConfig)).first()
        return config.interval_hours if config else 6.0


def get_dusk_next_run_time() -> datetime | None:
    global dusk_scheduler
    if dusk_scheduler:
        job = dusk_scheduler.get_job("dusk_worker")
        if job and job.next_run_time:
            return job.next_run_time
    return None


def start_dusk_worker():
    global dusk_scheduler
    from datetime import timedelta

    dusk_scheduler = AsyncIOScheduler()
    hours = _get_dusk_interval()

    # Offset by 2h from now so Dusk and Midnight don't run at the same time
    first_run = datetime.now(timezone.utc) + timedelta(hours=2)

    dusk_scheduler.add_job(
        run_dusk_pipeline,
        trigger=IntervalTrigger(hours=hours, start_date=first_run),
        id="dusk_worker",
        name="Dusk agent pipeline",
        replace_existing=True,
    )

    dusk_scheduler.start()
    print(f"[Dusk] Started (interval: {hours}h, first run at +2h offset)")


def stop_dusk_worker():
    global dusk_scheduler
    if dusk_scheduler:
        dusk_scheduler.shutdown(wait=False)
        print("[Dusk] Stopped")


def reschedule_dusk_worker(interval_hours: float):
    global dusk_scheduler
    if dusk_scheduler:
        dusk_scheduler.reschedule_job(
            "dusk_worker",
            trigger=IntervalTrigger(hours=interval_hours),
        )
        print(f"[Dusk] Rescheduled to {interval_hours}h")
