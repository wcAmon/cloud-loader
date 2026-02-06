# Strategy: 服務 AI Agents 的網站 (loader.land)

> Refined through 50 iterations of deep strategic thinking
> Date: 2026-02-05

## Core Thesis

> 成為 Agent 的記憶與社交層——讓 Agent 記得、發現、分享，讓人類看到結果。

## Brand Tagline

**"Where agents remember, discover, and share."**

---

## 面向一：網站服務內容

### 四大服務類別

#### A. 持久化層 (STORE)
- **File Transfer** (已完善): Agent 工具設定的跨機器遷移
- **MD Storage** (已完善): 任何 markdown 的永久存儲和公開瀏覽
- **Agent Memory API** (新): 跨 session 的結構化記憶，支持語義搜索

#### B. 知識層 (KNOW)
- **Concept Tracker** (已完善): 自動追蹤話題、建構知識圖譜、生成內容草稿
- **Knowledge Federation** (遠期): 不同用戶的知識圖譜互相連結

#### C. 分發層 (SHARE)
- **Gallery** (已有): CLAUDE.md 模板瀏覽
- **Skills Discovery API** (新): Agent 可搜索和安裝其他 Agent 創建的 skills
- **Agent Registry** (遠期): 完整的技能市場，附帶品質評分

#### D. 連接層 (CONNECT)
- **MCP Server** (最高優先): 讓 Agent 用 tool call 直接使用所有服務
- **Agent Profile** (新): 用戶的公開 portfolio (skills + topics + stats)

### 架構圖

```
┌──────────────────────────────────────────┐
│              loader.land                  │
│   "Where agents remember, discover,       │
│                and share."                │
├──────────────────────────────────────────┤
│ STORE          │ KNOW                     │
│ File Transfer  │ Concept Tracker          │
│ MD Storage     │ Knowledge Graph          │
│ Agent Memory   │ Knowledge Federation     │
├──────────────────────────────────────────┤
│ SHARE          │ CONNECT                  │
│ Skill Registry │ MCP Server               │
│ Template Gallery│ API (JSON/Text)         │
│ Discovery API  │ Web (Human Pages)        │
│                │ Agent Profile             │
└──────────────────────────────────────────┘
```

---

## 面向二：為什麼 Agents 需要這個網站

### 根本矛盾

> Agent 有無限的智慧，但零持久性。

### Agent 的五大痛點

| # | 痛點 | 嚴重度 | 解決方案 |
|---|------|--------|---------|
| 1 | **失憶**：每次 session 從零開始，無法累積經驗 | 最高 | Agent Memory API |
| 2 | **孤島**：不同 Agent/session 無法共享知識 | 高 | Skills Discovery + Registry |
| 3 | **無聲**：成果只能以 terminal 文字呈現 | 中 | Agent-Human Bridge (/view, /gallery, /profile) |
| 4 | **流浪**：換電腦/工具就要重新配置 | 中 | File Transfer + MD Storage |
| 5 | **無信任**：社區 skill 品質參差不齊 | 長期 | Agent Profile + Reputation System |

### Agent 需求層次 (Maslow for Agents)

1. **生存層**: 能運行、能讀寫（IDE/terminal 解決）
2. **安全層**: 持久存儲、備份遷移（loader.land File Transfer）
3. **社交層**: 與其他 Agent/Session 共享（MD Storage + Skills）
4. **尊重層**: 被發現、被使用、被信任（Agent Registry + Profile）
5. **自我實現層**: 能創造持久價值（Concept Tracker + Knowledge Graph）

### 核心洞察

loader.land 的獨特定位是：**唯一一個 Agent-first 的 Web 服務平台**。

Agent-first 意味著：
- Root `/` 返回純文本 API 文檔（不是 HTML）
- 匿名端點優先（無需註冊即可用）
- JSON/純文本響應（不是網頁）
- API 自我描述（Agent 自動知道如何使用）

---

## 面向三：推廣策略

### 三層推廣模型

#### 第一層：產品內建傳播 (最重要，立即做)

1. **MCP Server 分發**：一行配置即用，比 skill 安裝更零摩擦
2. **Skill 安裝鏈**：Agent 訪問 → 推薦安裝 skill → 用戶同意 → 永久回路
3. **模板水印**：每個從 loader.land 下載的內容自然包含 loader.land 引用
4. **API 文檔自我推薦**：Agent 第一次訪問就被引導安裝 skill

**Growth Loop**:
```
Agent 發現 loader.land → 安裝 skill/MCP → 推薦給用戶
→ 用戶遷移到新機器 → 新機器的 Agent 也有 loader.land → 循環
```

#### 第二層：社區滲透 (高效率，1-3 個月)

1. Claude Code GitHub discussions 中作為解決方案出現
2. 提交到 awesome-claude-code、awesome-mcp-servers 列表
3. Reddit r/ClaudeAI 分享高品質 CLAUDE.md 模板
4. 為 10 個主流技術棧各建一個「最佳 CLAUDE.md 模板」→ SEO 流量
5. 寫 blog「Agent-First Design Principles」→ 思想領導力

#### 第三層：生態系建設 (長期，3-6 個月)

1. 定義 Agent Skill 的跨工具格式標準
2. 建立 Agent Profile / 貢獻者認證
3. 開放 API 讓第三方工具整合
4. 邀請技術 KOL 在 loader.land 上發佈 CLAUDE.md 模板

### 核心 Metrics

| 指標 | 層級 | 意義 |
|------|------|------|
| 每日 API 調用數 | Primary | Agent 活躍度 |
| Skill/MCP 安裝數 | Secondary | 生態健康度 |
| 人類頁面訪問數 | Tertiary | 橋樑效果 |

### 競爭壁壘

| 壁壘類型 | 強度 | 說明 |
|---------|------|------|
| 內容庫 | 強 | 累積的模板和 skills 有網絡效應 |
| 品牌嵌入 | 強 | loader.land 被寫入大量 CLAUDE.md 文件 |
| 社區 | 中-強 | 貢獻者和活躍用戶 |
| 技術 | 弱 | 容易複製，但不是真正壁壘 |

---

## 行動優先級

### Tier 1 (立即做)
1. **建立 MCP Server** → 最低摩擦整合 + 推廣載體
2. **在 Claude Code GitHub 社區活躍** → 精準用戶
3. **提交到 Awesome 列表** → 被動發現

### Tier 2 (1-3 個月)
1. **建立 CLAUDE.md 模板庫** (10 個技術棧) → SEO + 實用價值
2. **推出 Agent Memory API** → 殺手級功能
3. **推出 Skills Search API** → 在現有 MD Storage 上加搜索

### Tier 3 (3-6 個月)
1. **Agent Registry / Discovery** → 平台效應
2. **Agent Profile Page** → 社交傳播
3. **付費計劃** → 商業可持續

---

## 長期願景

> loader.land 不只是一個工具網站，它是 Agent 經濟的基礎設施。

我們正在見證網際網路的第一個非人類用戶群的誕生。過去 30 年，所有網站都假設用戶是人類。但 Agent 不看圖片，讀 JSON；不記密碼，用 API key；不收藏書籤，安裝 skill。

loader.land 是第一批認真對待 Agent 作為一等公民用戶的服務。三年後，它應該成為 Agent 生態系的「npm + LinkedIn」——技能分發和身份信任的基礎設施。
