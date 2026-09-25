# 產業雷達 radar

目標：像 Akamai × Anthropic 116 億美元大單、「capex 加 17 億美元預購記憶體」這類消息一出來，就先推到手機，附上重點整理和台股相關族群。

## 運作流程

```
抓來源（每 10 分鐘） → 去重 → 關鍵字打分 → 高分才送 Claude 摘要 → 推播 Telegram / Discord → 寫進當日日報
```

| 來源 | 抓什麼 |
|---|---|
| Google News RSS | 用關鍵字組合搜「AI 大單」「capex + 記憶體」「DRAM 缺貨」等，中英文都有 |
| SEC 8-K | Akamai、微軟、Google、Amazon、Meta、Oracle、輝達、美光、Dell、SMCI、Cloudflare、Jabil、CoreWeave 的重大事件公告 |
| 證交所上市重大訊息 | 台灣上市公司每日重大訊息（資本支出、大單公告） |
| 任意 RSS | 在 `config.yaml` 加 `type: rss` 就能擴充 |

**打分**（`config.yaml` → `keyword_groups`）：AI 買家、大單、capex、預購／缺貨、記憶體、算力、認股權證、上修財測，各群組有權重；出現金額（`$11.6 billion`、`116億美元`）再加分，「AI 買家 + 大單」「capex + 預購」這類組合額外加分。以 Akamai 這則新聞為例，拿到 25 分，門檻是 6。

**Claude 摘要**（有設 `ANTHROPIC_API_KEY` 才會啟用）：抓原文後請 Claude 用台灣口語寫出重點數字、這代表什麼、台股誰有感，並給 1–5 的重要性評分。判定不相關或重要性低於 3 的直接略過，推播品質更好。沒設 key 就推規則版：標題、金額、命中的族群。

## 設定（GitHub Actions，免開電腦）

1. 在 repo 的 **Settings → Secrets and variables → Actions** 新增：
   - `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`：找 @BotFather 建 bot 拿 token，對 bot 說一句話後開 `https://api.telegram.org/bot<token>/getUpdates` 找 chat id
   - `DISCORD_WEBHOOK_URL`（選用）：Discord 頻道設定 → 整合 → Webhook
   - `ANTHROPIC_API_KEY`（選用但建議）：開啟 Claude 摘要
   - Variables 裡的 `SEC_USER_AGENT`：填 `你的名字 你的email`（SEC 規定要附聯絡方式）
2. 把這個分支合併到預設分支（GitHub 排程只會在預設分支上執行）。
3. 到 **Actions → 產業雷達 → Run workflow**，勾選 `bootstrap` 跑一次，把現有新聞標記為已讀，避免第一次就被舊聞洗版。
4. 之後每 10 分鐘自動掃一次。已讀紀錄存在 `radar/state/seen.json`，每日日報在 `radar/digest/`。

## 本機執行

```bash
pip install -r radar/requirements.txt
python -m radar --dry-run --no-llm     # 只印出來看，不推播
python -m radar --loop 180             # 本機常駐，每 3 分鐘掃一次（比 Actions 更即時）
python -m pytest -q tests
```

## 調整

- **太吵**：調高 `alert_threshold`／`min_importance`，或刪掉太泛的關鍵字。
- **漏抓**：在 `sources` 加 Google News 查詢或公司 IR 的 RSS，在 `keyword_groups` 補字。
- **加台股族群**：在 `themes` 加題材關鍵字和股票代號。
- **換模型或思考強度**：環境變數 `RADAR_MODEL`（預設 `claude-opus-5`）、`RADAR_EFFORT`（預設 `medium`）。

## 限制

- GitHub 排程最短 5 分鐘，尖峰時段常延遲；要更即時就在本機或 VPS 用 `--loop`。
- Google News 本身比原始新聞稿晚幾分鐘到十幾分鐘；SEC 8-K 通常是最早的一手來源。
- 台股重大訊息目前只抓上市（證交所）；上櫃（櫃買中心）還沒接。
- 推播內容是研究筆記，不是投資建議。
