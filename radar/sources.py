"""各種來源的抓取器。每個抓取器回傳 list[Item]，失敗時只記 log 不中斷整輪。"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import quote_plus

import feedparser
import requests

from .models import Item

log = logging.getLogger(__name__)

# SEC 要求 User-Agent 帶聯絡方式：https://www.sec.gov/os/accessing-edgar-data
SEC_UA = os.environ.get("SEC_USER_AGENT", "tw-strong-radar admin@example.com")
DEFAULT_UA = "Mozilla/5.0 (compatible; tw-strong-radar/1.0)"
TIMEOUT = 20
TPE = timezone(timedelta(hours=8))

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(_TAG_RE.sub(" ", s or ""))).strip()


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _get(url: str, ua: str = DEFAULT_UA) -> requests.Response:
    resp = requests.get(url, headers={"User-Agent": ua}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def parse_feed(content: bytes | str, source_name: str) -> list[Item]:
    feed = feedparser.parse(content)
    items = []
    for e in feed.entries:
        items.append(
            Item(
                source=source_name,
                title=strip_html(e.get("title", "")),
                url=e.get("link", ""),
                summary=strip_html(e.get("summary", "")),
                published=_entry_time(e),
                raw_id=e.get("id", "") or e.get("link", ""),
            )
        )
    return items


def fetch_rss(src: dict) -> list[Item]:
    return parse_feed(_get(src["url"]).content, src["name"])


def google_news_url(query: str, lang: str = "en") -> str:
    if lang.lower().startswith("zh"):
        region = "hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    else:
        region = "hl=en-US&gl=US&ceid=US:en"
    # when:2d 限制兩天內，避免撈到舊聞
    return f"https://news.google.com/rss/search?q={quote_plus(query + ' when:2d')}&{region}"


def fetch_google_news(src: dict) -> list[Item]:
    url = google_news_url(src["query"], src.get("lang", "en"))
    return parse_feed(_get(url).content, src["name"])


def fetch_sec_8k(src: dict) -> list[Item]:
    items: list[Item] = []
    for ticker, cik in src["ciks"].items():
        url = (
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&CIK={int(cik):010d}&type=8-K&dateb=&owner=include&count=10&output=atom"
        )
        try:
            parsed = parse_feed(_get(url, SEC_UA).content, f"{src['name']} {ticker}")
        except requests.RequestException as exc:
            log.warning("SEC %s 抓取失敗: %s", ticker, exc)
            continue
        for it in parsed:
            it.title = f"[{ticker} 8-K] {it.title}"
        items.extend(parsed)
    return items


def parse_twse_material(rows: list[dict], source_name: str) -> list[Item]:
    items = []
    for row in rows:
        # 證交所欄位名稱偶爾帶空白，統一先 strip
        r = {str(k).strip(): (str(v).strip() if v is not None else "") for k, v in row.items()}
        code = r.get("公司代號", "")
        name = r.get("公司名稱", "")
        subject = r.get("主旨", "")
        detail = r.get("說明", "")
        date = r.get("發言日期", "")
        tm = r.get("發言時間", "")
        items.append(
            Item(
                source=source_name,
                title=f"[{code} {name}] {subject}",
                url=f"https://mops.twse.com.tw/mops/#/web/t05st01?companyId={code}",
                summary=detail,
                published=_roc_datetime(date, tm),
                raw_id=f"twse:{code}:{date}:{tm}:{subject[:40]}",
            )
        )
    return items


def _roc_datetime(date: str, tm: str) -> datetime | None:
    """民國日期 1150925 + 時間 143012 → UTC datetime。"""
    try:
        y, m, d = int(date[:-4]) + 1911, int(date[-4:-2]), int(date[-2:])
        tm = tm.zfill(6)
        hh, mm, ss = int(tm[:2]), int(tm[2:4]), int(tm[4:6])
        return datetime(y, m, d, hh, mm, ss, tzinfo=TPE).astimezone(timezone.utc)
    except (ValueError, IndexError):
        return None


def fetch_twse_material(src: dict) -> list[Item]:
    return parse_twse_material(_get(src["url"]).json(), src["name"])


FETCHERS = {
    "rss": fetch_rss,
    "google_news": fetch_google_news,
    "sec_8k": fetch_sec_8k,
    "twse_material": fetch_twse_material,
}


def fetch_all(cfg: dict) -> list[Item]:
    items: list[Item] = []
    for src in cfg.get("sources", []):
        fetcher = FETCHERS.get(src["type"])
        if not fetcher:
            log.warning("未知來源類型: %s", src["type"])
            continue
        try:
            got = fetcher(src)
            log.info("%s: %d 則", src["name"], len(got))
            items.extend(got)
        except (requests.RequestException, ValueError) as exc:
            log.warning("%s 抓取失敗: %s", src["name"], exc)
    return items


def fetch_article_text(url: str, limit: int = 40000) -> str:
    """抓原文給 Claude 看。抓不到就回空字串，改用標題+摘要。"""
    if not url:
        return ""
    ua = SEC_UA if "sec.gov" in url else DEFAULT_UA
    try:
        resp = _get(url, ua)
    except requests.RequestException:
        return ""
    if "html" not in resp.headers.get("content-type", "html"):
        return ""
    text = strip_html(re.sub(r"(?is)<(script|style).*?</\1>", " ", resp.text))
    if len(text) > limit:
        text = text[:limit] + "\n[內容過長，已截斷]"
    return text
