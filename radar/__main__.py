"""產業雷達：python -m radar [--dry-run] [--no-llm] [--loop 300] [--bootstrap]"""

from __future__ import annotations

import argparse
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .models import Item
from .notify import dispatch, format_alert
from .scoring import score_item
from .sources import fetch_all, fetch_article_text
from .store import SeenStore

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("radar")


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def select_new(items: list[Item], cfg: dict, store: SeenStore) -> list[Item]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=cfg.get("max_age_hours", 48))
    fresh: list[Item] = []
    batch_seen: set[str] = set()
    for it in items:
        if it.published and it.published < cutoff:
            continue
        if store.seen(it.uid, it.title) or it.uid in batch_seen:
            continue
        batch_seen.add(it.uid)
        score_item(it, cfg)
        if it.score >= cfg.get("alert_threshold", 6):
            fresh.append(it)
    fresh.sort(key=lambda i: i.score, reverse=True)
    return fresh


def run_once(args, cfg: dict) -> int:
    store = SeenStore(Path(args.state))
    items = fetch_all(cfg)
    hits = select_new(items, cfg, store)
    log.info("共抓到 %d 則，%d 則過門檻", len(items), len(hits))

    if args.bootstrap:
        for it in items:
            store.add(it.uid, it.title)
        store.save()
        log.info("bootstrap：已把目前 %d 則標記為已讀，不推播", len(items))
        return 0

    use_llm = not args.no_llm and bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    summarizer = None
    if use_llm:
        from .summarize import Summarizer

        summarizer = Summarizer()

    llm_budget = cfg.get("max_llm_per_run", 8)
    sent = 0
    for it in hits:
        # 同一輪裡轉載的同一則新聞，標題去重後可能已經處理過
        if store.seen(it.uid, it.title):
            continue
        analysis = None
        if summarizer and llm_budget > 0 and it.score >= cfg.get("llm_threshold", 6):
            llm_budget -= 1
            analysis = summarizer.summarize(it, fetch_article_text(it.url))
            if analysis and not analysis["relevant"]:
                log.info("Claude 判定不相關，略過: %s", it.title)
                store.add(it.uid, it.title)
                continue
            if analysis and analysis["importance"] < cfg.get("min_importance", 3):
                log.info("重要性 %d 太低，略過: %s", analysis["importance"], it.title)
                store.add(it.uid, it.title)
                continue
        dispatch(format_alert(it, analysis), None if args.no_digest else Path(args.digest), args.dry_run)
        if not args.dry_run:
            store.add(it.uid, it.title)
        sent += 1

    if not args.dry_run:
        store.save()
    log.info("本輪推播 %d 則", sent)
    return sent


def main() -> None:
    p = argparse.ArgumentParser(prog="radar", description="即時產業雷達")
    p.add_argument("--config", default=str(ROOT / "config.yaml"))
    p.add_argument("--state", default=str(ROOT / "state" / "seen.json"))
    p.add_argument("--digest", default=str(ROOT / "digest"))
    p.add_argument("--dry-run", action="store_true", help="只印出，不推播、不記錄已讀")
    p.add_argument("--no-llm", action="store_true", help="不呼叫 Claude，只用規則版")
    p.add_argument("--no-digest", action="store_true", help="不寫每日 markdown 日報")
    p.add_argument("--bootstrap", action="store_true", help="第一次使用：把現有新聞標為已讀")
    p.add_argument("--loop", type=int, default=0, help="每 N 秒跑一次（本機常駐用）")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(Path(args.config))

    while True:
        run_once(args, cfg)
        if args.loop <= 0:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
