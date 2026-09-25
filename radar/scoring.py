"""關鍵字打分：先用便宜的規則把雜訊濾掉，只有高分的才送去給 Claude。"""

from __future__ import annotations

import re
from functools import lru_cache

from .models import Item

AMOUNT_RE = re.compile(
    r"(?:US)?\$\s?\d[\d,]*(?:\.\d+)?\s?(?:billion|bn|million|trillion|[BMT]\b)"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:億|兆)(?:美元|美金|元|台幣|新台幣)?",
    re.IGNORECASE,
)


@lru_cache(maxsize=None)
def _pattern(word: str) -> re.Pattern[str]:
    w = word.lower()
    if w.isascii():
        # 英文用字邊界，避免 edge 命中 knowledge、cpu 命中 cpus 以外的奇怪字
        return re.compile(r"(?<![a-z0-9])" + re.escape(w) + r"s?(?![a-z0-9])")
    return re.compile(re.escape(w))


def _matches(text: str, words: list[str]) -> list[str]:
    return [w for w in words if _pattern(str(w)).search(text)]


def score_item(item: Item, cfg: dict) -> Item:
    text = item.text.lower()

    hits: dict[str, list[str]] = {}
    score = 0
    for group, spec in cfg.get("keyword_groups", {}).items():
        found = _matches(text, spec["words"])
        if found:
            hits[group] = found
            score += int(spec.get("weight", 1))

    amounts = [m.group(0).strip() for m in AMOUNT_RE.finditer(item.text)]
    if amounts:
        score += int(cfg.get("amount_bonus", 0))

    for combo in cfg.get("combo_bonus", []):
        if all(g in hits for g in combo["groups"]):
            score += int(combo["bonus"])

    themes = {}
    for name, spec in cfg.get("themes", {}).items():
        if _matches(text, spec["words"]):
            themes[name] = {str(k): v for k, v in spec["tickers"].items()}

    item.score = score
    item.hits = hits
    item.amounts = list(dict.fromkeys(amounts))
    item.themes = themes
    return item
