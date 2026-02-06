# Agent Brainstorm Worker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a daily brainstorm worker that uses Claude CLI + ralph-loop to think about "服務agents的網站" concept, then stores strategies in a timeline page at `/agent-brainstorm`.

**Architecture:** New `BrainstormEntry` SQLModel table stores daily brainstorm outputs. A Jinja2 timeline page at `/agent-brainstorm` displays entries with pagination. A standalone worker script runs via systemd timer at 20:00 UTC daily, invoking `claude --dangerously-skip-permissions` with ralph-loop to generate strategy content.

**Tech Stack:** SQLModel/SQLite, Jinja2/Tailwind, systemd timer, Claude CLI

---

### Task 1: Add BrainstormEntry database model
### Task 2: Create `/agent-brainstorm` route with pagination
### Task 3: Create brainstorm.html Jinja2 template (timeline + pagination)
### Task 4: Add brainstorm link in human.html feature grid
### Task 5: Create worker script (reads yesterday, runs claude + ralph-loop, saves to DB)
### Task 6: Create systemd timer for daily 20:00 UTC
### Task 7: Test run the worker
