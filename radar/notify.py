"""推播：Telegram、Discord，外加每天一份 markdown 日報寫進 repo。"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .models import Item

log = logging.getLogger(__name__)
TPE = timezone(timedelta(hours=8))
STARS = {5: "🔴🔴🔴", 4: "🔴🔴", 3: "🟠", 2: "⚪", 1: "⚪"}


def format_alert(item: Item, analysis: dict | None) -> str:
    when = item.published.astimezone(TPE).strftime("%m/%d %H:%M") if item.published else ""
    lines: list[str] = []
    if analysis:
        lines.append(f"{STARS.get(analysis['importance'], '')} {analysis['headline']}")
        lines += [f"• {f}" for f in analysis["key_facts"]]
        lines.append(f"\n💡 {analysis['why_it_matters']}")
        if analysis["tw_supply_chain"]:
            lines.append("\n🇹🇼 台股觀察")
            lines += [
                f"• {s['name']} {s['ticker']}：{s['reason']}" for s in analysis["tw_supply_chain"]
            ]
        if analysis["watch_next"]:
            lines.append("\n👀 後續追蹤：" + "；".join(analysis["watch_next"]))
    else:
        lines.append(f"📡 {item.title}")
        if item.amounts:
            lines.append("💰 " + "、".join(item.amounts[:5]))
        if item.summary:
            lines.append(item.summary[:300])
        if item.themes:
            lines.append("\n🇹🇼 相關族群")
            for theme, tickers in item.themes.items():
                lines.append(
                    f"• {theme}：" + "、".join(f"{n} {c}" for c, n in tickers.items())
                )
    hit_words = sorted({w for ws in item.hits.values() for w in ws})
    lines.append(f"\n[{item.source}] {when}  分數 {item.score}（{', '.join(hit_words)}）")
    lines.append(item.url)
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True},
            timeout=20,
        ).raise_for_status()
    except requests.RequestException as exc:
        log.warning("Telegram 推播失敗: %s", exc)


def send_discord(text: str) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"content": text[:1990]}, timeout=20).raise_for_status()
    except requests.RequestException as exc:
        log.warning("Discord 推播失敗: %s", exc)


def append_digest(digest_dir: Path, text: str) -> None:
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    digest_dir.mkdir(parents=True, exist_ok=True)
    path = digest_dir / f"{today}.md"
    header = "" if path.exists() else f"# 產業雷達 {today}\n\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(header + text + "\n\n---\n\n")


def dispatch(text: str, digest_dir: Path | None, dry_run: bool) -> None:
    print(text + "\n" + "-" * 60)
    if dry_run:
        return
    send_telegram(text)
    send_discord(text)
    if digest_dir:
        append_digest(digest_dir, text)
