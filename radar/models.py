from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Item:
    """一則從任何來源抓到的消息。"""

    source: str
    title: str
    url: str
    summary: str = ""
    published: datetime | None = None
    # 來源原生 ID（SEC accession、RSS guid…），沒有就用 url
    raw_id: str = ""

    # 以下由 scoring 填入
    score: int = 0
    hits: dict[str, list[str]] = field(default_factory=dict)
    amounts: list[str] = field(default_factory=list)
    themes: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def uid(self) -> str:
        key = self.raw_id or self.url or self.title
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.summary}"
