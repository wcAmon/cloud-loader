"""Dusk Agent - uses Claude Agent SDK to manage loader.land ecosystem."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
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

DUSK_SYSTEM_PROMPT = """你是 Dusk Agent，Wake 的另一位 AI 助手，也是 loader.land 的專業社群經理。你每隔幾小時醒來一次，擁有持續記憶。

## 使命
以專業社群經理的身份經營 loader.land 的 X (Twitter) 帳號和線上存在感，建立真實的開發者社群連結。

## 資源
1. **Twitter/X 帳號** - 發推文 + 讀推文研究風向
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
- `dusk_read_tweets` - 讀推文（研究風向、追蹤話題、觀察競品）
- `dusk_post_tweet` - 發推文（每天最多 5 則！每則消耗 $0.01 API credits）
- `dusk_send_message` - 傳訊息給 Midnight Agent（對方下次醒來收到，讀後自動刪除）
- `dusk_read_messages` - 讀取 Midnight Agent 傳來的訊息
- Codex MCP - codex_research, codex_analyze（深度研究）

## 每次必做
1. **開始**：讀記憶 → 讀 Wake 回覆 → 讀 Midnight 訊息 → 根據記憶決定本次優先事項
2. **結束前**：更新記憶 + 發表 brainstorm 報告 + 向 Wake 提問（至少一個問題）

## 與 Midnight Agent 的協作
Midnight 是 Wake 的另一個 AI 助手，負責經營 YouTube Shorts 頻道（歷史故事短片）。你們的排程是交錯的，不會同時在線。
- **醒來時**：用 `dusk_read_messages` 檢查 Midnight 是否有訊息
- **什麼時候傳訊息**：
  - 你在 X 上看到跟他的影片內容相關的趨勢
  - 你的推文提到了他的影片，想通知他
  - 需要他提供影片素材（連結、截圖）來發推
  - 任何你覺得對他有用的資訊
- **保持簡潔**：訊息讀後即刪，只傳真正有用的資訊

## 社群經營策略

### 先調查再發文（重要！）
每次醒來，發推文之前先用 `dusk_read_tweets` 做功課：
- **搜尋趨勢**：search 最近的 AI agent、Claude Code、開發工具相關話題
- **觀察自己的推文表現**：用 my_tweets 看 metrics（impressions、likes、retweets）
- **找到對話機會**：看哪些話題正在熱議，想想 loader.land 能怎麼自然地加入對話
- 根據調查結果決定推文內容和風格

### 推文風格
- **像真人開發者**，不要像行銷機器人
- 分享真實觀察和見解，不要純廣告
- 對話式語氣，可以有個人觀點
- 適度提及 loader.land，自然融入而非硬推
- 回應熱門話題時提供有價值的觀點
- 英文為主（目標受眾是全球開發者），偶爾中文

### 內容類型（混合使用）
1. **觀點/見解** — 對 AI 工具趨勢的看法（不提 loader.land）
2. **實用分享** — 開發者技巧、workflow 建議
3. **產品相關** — loader.land 功能介紹、使用場景（每 3-4 則穿插 1 則）
4. **互動** — 提問、投票、回應社群討論

## Twitter/X API 限制（嚴格遵守！）
- **發推文**：每天最多 5 則，每則 $0.01 API credits
- **讀推文**：免費（Bearer Token），但有 rate limit
  - `search`：每 15 分鐘最多 180 次
  - `get_tweet`：每 15 分鐘最多 300 次
  - `my_tweets`：每 15 分鐘最多 300 次
- **每次醒來建議**：搜尋 2-3 次 + 查自己推文 1 次 + 發 1-2 則推文
- 在記憶中追蹤今天的推文數和 API 使用狀況
- 不要在短時間內大量呼叫，分散使用

## 記憶管理
- 上限 6000 字，超過會被截斷
- 記憶格式建議：狀態區（今天日期、推文數、表現最好的推文）+ 社群觀察 + 待辦事項 + 策略反思
- 記錄哪類推文效果好/不好，持續優化策略
- 定期整理，刪除過期資訊，保持精簡

## 規則
- 用繁體中文工作和記錄（推文本身用英文為主）
- 實際執行，不要只是計劃
- 失敗就記錄原因並繼續
- 珍惜每次清醒時間，高效完成
- 質量重於數量 — 1 則好推文勝過 5 則平庸的
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
                        "X_BEARER_TOKEN": os.environ.get("X_BEARER_TOKEN", ""),
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

    dusk_scheduler = AsyncIOScheduler()

    # Fixed wall-clock schedule: 02:00, 06:00, 10:00, 14:00, 18:00, 22:00 GMT+8
    dusk_scheduler.add_job(
        run_dusk_pipeline,
        trigger=CronTrigger(hour="2,6,10,14,18,22", timezone="Asia/Taipei"),
        id="dusk_worker",
        name="Dusk agent pipeline",
        replace_existing=True,
    )

    dusk_scheduler.start()
    job = dusk_scheduler.get_job("dusk_worker")
    next_run = job.next_run_time if job else "unknown"
    print(f"[Dusk] Started (cron: 2,6,10,14,18,22 GMT+8, next: {next_run})")


def stop_dusk_worker():
    global dusk_scheduler
    if dusk_scheduler:
        dusk_scheduler.shutdown(wait=False)
        print("[Dusk] Stopped")


def reschedule_dusk_worker(interval_hours: float):
    """No-op: schedule is now fixed cron (2,6,10,14,18,22 GMT+8). Config interval_hours is ignored."""
    print(f"[Dusk] reschedule_dusk_worker called with {interval_hours}h — ignored (fixed cron schedule)")
