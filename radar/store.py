"""已推播紀錄，避免同一則新聞重複推。GitHub Actions 會把這個檔 commit 回 repo。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

KEEP_SECONDS = 14 * 24 * 3600


def title_key(title: str) -> str:
    # Google News 標題結尾是「 - 媒體名」，同一則新聞各家轉載只差在這裡
    t = re.sub(r"\s[-–|]\s[^-–|]{1,40}$", "", title)
    return re.sub(r"[\W_]+", "", t.lower())[:80]


class SeenStore:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, float] = {}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    def _keys(self, uid: str, title: str) -> list[str]:
        keys = [f"id:{uid}"]
        tk = title_key(title)
        if tk:
            keys.append(f"t:{tk}")
        return keys

    def seen(self, uid: str, title: str) -> bool:
        return any(k in self.data for k in self._keys(uid, title))

    def add(self, uid: str, title: str) -> None:
        now = time.time()
        for k in self._keys(uid, title):
            self.data[k] = now

    def save(self) -> None:
        cutoff = time.time() - KEEP_SECONDS
        self.data = {k: v for k, v in self.data.items() if v >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8",
        )
