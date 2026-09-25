"""把高分消息丟給 Claude，產出「重點 + 為什麼重要 + 台股供應鏈」的中文快評。"""

from __future__ import annotations

import json
import logging
import os

import anthropic

from .models import Item

log = logging.getLogger(__name__)

MODEL = os.environ.get("RADAR_MODEL", "claude-opus-5")
EFFORT = os.environ.get("RADAR_EFFORT", "medium")

SYSTEM = """你是台股產業研究員，專門從美國科技大廠、AI 公司與供應鏈的新聞中，第一時間抓出對台股有意義的訊號。

寫作風格：台灣口語、直接講重點、像跟懂行的朋友聊天。先講發生什麼事（數字要精確），再講這代表什麼（例如「連雲端廠都要自己掏錢預購記憶體，代表供給真的很緊」），最後講台股誰可能有感。

規則：
- 只根據提供的內容寫事實；推論要明講是推論，不可以編造數字。
- 內容若只是舊聞重發、純股價評論、或跟 AI/半導體/雲端供應鏈無關，relevant 設為 false。
- importance 1-5：5 = 產業級訊號（數十億美元合約、capex 大改、供給吃緊的直接證據）；3 = 值得追蹤；1 = 雜訊。
- 台股標的只挑有明確邏輯的，每檔寫一句理由；沒有就給空陣列。
- 這是研究筆記，不是投資建議。"""

SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "importance": {"type": "integer", "description": "1-5"},
        "headline": {"type": "string", "description": "一行中文標題，含關鍵數字"},
        "key_facts": {"type": "array", "items": {"type": "string"}},
        "why_it_matters": {"type": "string"},
        "tw_supply_chain": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["ticker", "name", "reason"],
                "additionalProperties": False,
            },
        },
        "watch_next": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "relevant",
        "importance",
        "headline",
        "key_facts",
        "why_it_matters",
        "tw_supply_chain",
        "watch_next",
    ],
    "additionalProperties": False,
}


def build_prompt(item: Item, article: str) -> str:
    candidates = "\n".join(
        f"- {theme}: " + "、".join(f"{name} {code}" for code, name in tickers.items())
        for theme, tickers in item.themes.items()
    ) or "（無）"
    body = article or item.summary or "（只有標題）"
    return f"""來源：{item.source}
時間：{item.published.isoformat() if item.published else "未知"}
連結：{item.url}
標題：{item.title}

規則引擎命中的題材與台股候選（僅供參考，可增刪）：
{candidates}

<內容>
{body}
</內容>"""


class Summarizer:
    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()

    def summarize(self, item: Item, article: str) -> dict | None:
        try:
            resp = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                thinking={"type": "adaptive"},
                output_config={
                    "effort": EFFORT,
                    "format": {"type": "json_schema", "schema": SCHEMA},
                },
                system=SYSTEM,
                messages=[{"role": "user", "content": build_prompt(item, article)}],
            )
        except anthropic.RateLimitError:
            log.warning("Claude rate limit，這則改用規則版推播: %s", item.title)
            return None
        except anthropic.APIStatusError as exc:
            log.warning("Claude API 錯誤 %s: %s", exc.status_code, exc.message)
            return None
        except anthropic.APIConnectionError as exc:
            log.warning("連不到 Claude API: %s", exc)
            return None

        if resp.stop_reason == "refusal":
            log.warning("Claude 拒答: %s", item.title)
            return None
        text = next((b.text for b in resp.content if b.type == "text"), "")
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            log.warning("Claude 回傳不是 JSON (stop_reason=%s)", resp.stop_reason)
            return None
        result["importance"] = max(1, min(5, int(result.get("importance", 1))))
        return result
