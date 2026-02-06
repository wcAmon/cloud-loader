#!/usr/bin/env python3
"""
Brainstorm Worker - Daily strategy generation pipeline.

Pipeline:
  1. Read yesterday's brainstorm from SQLite
  2. GPT-4.1: summarize yesterday + generate targeted search queries
  3. Tavily: research using GPT-generated queries
  4. Claude CLI: deep strategy analysis with summary + research
  5. Save to SQLite → visible on /agent-brainstorm

Runs at 20:00 UTC daily via systemd timer.
Usage: uv run python scripts/brainstorm_worker.py
"""

import subprocess
import sys
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlmodel import Session, SQLModel, create_engine, select
from cloud_loader.config import settings
from cloud_loader.models import BrainstormEntry

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def get_yesterday_entry() -> str | None:
    """Get yesterday's brainstorm raw content from DB."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    with Session(engine) as session:
        entry = session.exec(
            select(BrainstormEntry)
            .where(BrainstormEntry.created_at >= start)
            .where(BrainstormEntry.created_at < end)
            .order_by(BrainstormEntry.created_at.desc())
        ).first()

        if entry:
            return entry.content
    return None


def summarize_with_gpt(yesterday_content: str) -> dict:
    """Use GPT-4.1 to summarize yesterday's brainstorm and generate search queries.

    Returns:
        {
            "summary": "昨日策略摘要...",
            "queries": ["search query 1", "search query 2", "search query 3"]
        }
    """
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    print("[Worker] Calling GPT-4.1 for summary + search queries...")

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一個研究助理。你會收到昨天關於「服務 AI agents 的網站」的策略分析。\n"
                    "請輸出 JSON，包含：\n"
                    "1. summary: 用 3-5 句繁體中文摘要昨天的核心洞見和關鍵策略方向\n"
                    "2. queries: 3 個英文搜尋字串，用來調查今天應該深入的方向。"
                    "搜尋字串要具體、有時效性，針對昨天策略中提到但還需要更多資料的點。\n\n"
                    "只輸出 JSON，不要其他文字。"
                ),
            },
            {
                "role": "user",
                "content": yesterday_content,
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
    )

    text = response.choices[0].message.content
    try:
        result = json.loads(text)
        summary = result.get("summary", "")
        queries = result.get("queries", [])
        if not isinstance(queries, list):
            queries = []
        print(f"[Worker] GPT summary: {len(summary)} chars, {len(queries)} queries")
        for q in queries:
            print(f"[Worker]   → {q}")
        return {"summary": summary, "queries": queries[:5]}
    except json.JSONDecodeError:
        print(f"[Worker] GPT output not valid JSON: {text[:200]}")
        return {"summary": text[:500], "queries": []}


def research_with_tavily(queries: list[str]) -> str:
    """Research using Tavily with the given search queries."""
    if not settings.tavily_api_key:
        print("[Worker] No Tavily API key, skipping research")
        return ""
    if not queries:
        print("[Worker] No search queries, using defaults")
        queries = [
            "AI coding agents services platform 2026",
            "Claude Code Codex AI agent tools infrastructure",
        ]

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)

    all_results = []
    for query in queries:
        try:
            print(f"[Worker] Tavily search: {query}")
            response = client.search(
                query=query,
                max_results=5,
                include_answer=True,
                include_raw_content=False,
            )
            if response.get("answer"):
                all_results.append(
                    f"**Search: {query}**\nAnswer: {response['answer']}\n"
                )
            for item in response.get("results", [])[:3]:
                all_results.append(
                    f"- [{item.get('title', '')}]({item.get('url', '')}): "
                    f"{item.get('content', '')[:200]}"
                )
        except Exception as e:
            print(f"[Worker] Tavily error for '{query}': {e}")

    if all_results:
        return "## 今日市場調查\n\n" + "\n".join(all_results)
    return ""


def build_prompt(yesterday_summary: str | None, research: str) -> str:
    """Build the final prompt for Claude CLI."""
    sections = [
        "你是一個策略顧問。你的任務是深度思考「服務 agents (Claude Code / Codex / OpenClaw) 的網站」這個概念。\n"
        "這個網站目前叫 Cloud-Loader (loader.land)，提供 File Transfer、MD Storage、Loader Tracker 三項服務。"
    ]

    if research:
        sections.append(
            "\n以下是今天的市場調查結果，請參考這些最新資訊來制定策略：\n\n"
            f"{research}"
        )

    if yesterday_summary:
        sections.append(
            "\n以下是昨天策略的摘要，請在此基礎上延伸思考，不要重複相同的點，要有新的洞見：\n\n"
            f"{yesterday_summary}"
        )

    sections.append(
        "\n---\n\n"
        "請從以下三個面向深度分析並提出具體可執行的策略：\n\n"
        "1. **網站服務內容**: 這個網站應該提供什麼服務給 AI agents？什麼功能是 agents 迫切需要的？"
        "現有服務有哪些可以強化？還缺什麼關鍵功能？\n"
        "2. **為什麼 agents 需要這個網站**: agents 在日常工作中遇到什麼痛點？"
        "這個網站如何解決？與其他服務相比有什麼獨特價值？\n"
        "3. **推廣策略**: 如何讓更多 agent 使用者知道這個網站？"
        "如何建立 agent 生態系？具體的推廣渠道和方法？\n\n"
        "請用繁體中文回答。你的回答開頭第一行必須是一個 # 標題（一句話概括今天的核心洞見），"
        "第二行是 2-3 句話的摘要。然後才是詳細分析。每個面向都要有具體、可執行的建議，不要空泛。"
    )

    return "\n".join(sections)


def run_claude(prompt: str) -> str:
    """Run Claude CLI and return the text output."""
    print("[Worker] Starting Claude CLI...")

    result = subprocess.run(
        [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            prompt,
            "--output-format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=str(project_root),
    )

    if result.returncode != 0:
        print(f"[Worker] Claude CLI error (code {result.returncode}):")
        print(f"[Worker] stderr: {result.stderr[:500]}")
        raise RuntimeError(f"Claude CLI failed with code {result.returncode}")

    try:
        data = json.loads(result.stdout)
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if isinstance(content, list):
                return "\n".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            return str(content)
        return result.stdout
    except json.JSONDecodeError:
        return result.stdout


def parse_output(output: str) -> dict:
    """Parse Claude's markdown output into title, summary, content."""
    lines = output.strip().split("\n")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Agent 服務網站策略 - {today}"
    content_start = 0

    for i, line in enumerate(lines[:10]):
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 3:
            title = stripped[2:].strip()[:200]
            content_start = i + 1
            break

    summary_lines = []
    for line in lines[content_start:content_start + 10]:
        stripped = line.strip()
        if not stripped:
            if summary_lines:
                break
            continue
        if stripped.startswith("#"):
            break
        summary_lines.append(stripped)

    summary = " ".join(summary_lines)[:1000] if summary_lines else output[:500]

    return {"title": title, "summary": summary, "content": output}


def save_entry(data: dict) -> int:
    """Save the brainstorm entry to the database."""
    SQLModel.metadata.create_all(engine)

    entry = BrainstormEntry(
        title=data["title"][:200],
        summary=data["summary"][:1000],
        content=data["content"],
        concept="服務agents的網站",
    )

    with Session(engine) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
        print(f"[Worker] Saved entry #{entry.id}: {entry.title}")
        return entry.id


def main():
    """Main worker pipeline."""
    print(
        f"[Worker] Brainstorm worker started at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )

    # Step 1: Read yesterday's content
    print("[Worker] Step 1: Reading yesterday's brainstorm...")
    yesterday_content = get_yesterday_entry()

    # Step 2: GPT-4.1 summarizes + generates search queries
    yesterday_summary = None
    search_queries = []

    if yesterday_content:
        print("[Worker] Step 2: GPT-4.1 summarizing + generating queries...")
        gpt_result = summarize_with_gpt(yesterday_content)
        yesterday_summary = gpt_result["summary"]
        search_queries = gpt_result["queries"]
    else:
        print("[Worker] No yesterday entry, using default queries")
        search_queries = [
            "AI coding agents services platform 2026",
            "Claude Code Codex AI agent tools marketplace",
            "AI agent infrastructure services developer tools",
        ]

    # Step 3: Tavily research with GPT-generated queries
    print("[Worker] Step 3: Tavily research...")
    research = research_with_tavily(search_queries)
    print(f"[Worker] Research: {len(research)} chars")

    # Step 4: Claude CLI deep analysis
    prompt = build_prompt(yesterday_summary, research)
    print(f"[Worker] Step 4: Claude CLI (prompt: {len(prompt)} chars)...")
    output = run_claude(prompt)
    print(f"[Worker] Claude output: {len(output)} chars")

    # Step 5: Parse and save
    data = parse_output(output)
    entry_id = save_entry(data)

    print(
        f"[Worker] Done! Entry #{entry_id} saved. "
        f"View at: {settings.base_url}/agent-brainstorm"
    )


if __name__ == "__main__":
    main()
