from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import yaml

from radar.__main__ import select_new
from radar.models import Item
from radar.notify import format_alert
from radar.scoring import score_item
from radar.sources import parse_feed, parse_twse_material
from radar.store import SeenStore, title_key
from radar.summarize import Summarizer, build_prompt

CFG = yaml.safe_load((Path(__file__).parents[1] / "radar" / "config.yaml").read_text("utf-8"))

AKAMAI_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
<item>
  <title>Anthropic signs $11.6 billion cloud deal with Akamai, gets warrant for up to 5% stake - Reuters</title>
  <link>https://example.com/akamai</link>
  <guid>g1</guid>
  <pubDate>{now}</pubDate>
  <description>&lt;p&gt;Akamai expects an increase of about $1.7 billion in 2026 capex to secure and pre-purchase components, including memory, for CPU workloads.&lt;/p&gt;</description>
</item>
<item>
  <title>Anthropic signs $11.6 billion cloud deal with Akamai, gets warrant for up to 5% stake - Yahoo Finance</title>
  <link>https://example.com/akamai-yahoo</link>
  <guid>g2</guid>
  <pubDate>{now}</pubDate>
  <description>same story</description>
</item>
<item>
  <title>Local bakery opens new store</title>
  <link>https://example.com/bakery</link>
  <guid>g3</guid>
  <pubDate>{now}</pubDate>
  <description>Knowledge of baking; hedge funds not involved.</description>
</item>
</channel></rss>"""


def _feed():
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return parse_feed(AKAMAI_RSS.format(now=now), "test")


def test_parse_feed_strips_html():
    items = _feed()
    assert len(items) == 3
    assert "<p>" not in items[0].summary
    assert items[0].published is not None


def test_akamai_deal_scores_high_and_maps_tw_themes():
    it = score_item(_feed()[0], CFG)
    assert it.score >= CFG["alert_threshold"]
    assert {"ai_buyer", "capex", "supply_lock", "memory", "equity_link"} <= set(it.hits)
    assert "$11.6 billion" in it.amounts and "$1.7 billion" in it.amounts
    assert "2408" in it.themes["DRAM"]
    assert "伺服器 ODM" in it.themes


def test_noise_scores_low_and_word_boundaries():
    it = score_item(_feed()[2], CFG)
    assert it.score < CFG["alert_threshold"]
    assert "compute" not in it.hits  # knowledge/hedge 不該命中 edge


def test_chinese_amount_and_keywords():
    it = score_item(
        Item(source="t", title="Akamai 與 Anthropic 簽 116億美元長約，資本支出增 17億美元預購記憶體", url="u"),
        CFG,
    )
    assert "116億美元" in it.amounts
    assert {"ai_buyer", "big_deal", "capex", "supply_lock", "memory"} <= set(it.hits)


def test_select_new_dedupes_syndicated_titles(tmp_path):
    store = SeenStore(tmp_path / "seen.json")
    fresh = select_new(_feed(), CFG, store)
    assert [i.url for i in fresh][:1] == ["https://example.com/akamai"]
    store.add(fresh[0].uid, fresh[0].title)
    # 另一家轉載同標題 → 視為已讀
    assert store.seen(fresh[1].uid, fresh[1].title)
    store.save()
    assert SeenStore(tmp_path / "seen.json").seen(fresh[0].uid, fresh[0].title)


def test_title_key_drops_publisher():
    assert title_key("Big deal - Reuters") == title_key("Big deal - Bloomberg")


def test_twse_material_parsing():
    rows = [
        {
            "出表日期": "1150925",
            "發言日期": "1150925",
            "發言時間": "143012",
            "公司代號": "2408",
            "公司名稱": "南亞科",
            "主旨 ": "公告本公司董事會決議資本支出案",
            "說明": "增加 DRAM 產能資本支出新台幣 300億元",
        }
    ]
    [it] = parse_twse_material(rows, "上市重大訊息")
    assert it.title == "[2408 南亞科] 公告本公司董事會決議資本支出案"
    assert it.published == datetime(2026, 9, 25, 6, 30, 12, tzinfo=timezone.utc)
    score_item(it, CFG)
    assert "capex" in it.hits and "300億元" in it.amounts


def test_format_alert_rule_and_llm_versions():
    it = score_item(_feed()[0], CFG)
    rule = format_alert(it, None)
    assert "南亞科 2408" in rule and it.url in rule
    llm = format_alert(
        it,
        {
            "importance": 5,
            "headline": "Akamai 拿下 Anthropic 116 億美元 7 年約",
            "key_facts": ["2026 capex +17 億美元預購記憶體"],
            "why_it_matters": "雲端廠自己掏錢鎖記憶體，供給偏緊",
            "tw_supply_chain": [{"ticker": "2408", "name": "南亞科", "reason": "DRAM 報價受惠"}],
            "watch_next": ["DDR5 合約價"],
        },
    )
    assert llm.startswith("🔴🔴🔴") and "南亞科 2408：DRAM 報價受惠" in llm


class _FakeMessages:
    def __init__(self, text, stop_reason="end_turn"):
        self.text, self.stop_reason, self.kwargs = text, stop_reason, None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="text", text=self.text)],
        )


def _fake_client(msgs):
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs))


def test_summarizer_request_and_parse():
    msgs = _FakeMessages(
        '{"relevant": true, "importance": 9, "headline": "h", "key_facts": [], '
        '"why_it_matters": "w", "tw_supply_chain": [], "watch_next": []}'
    )
    it = score_item(_feed()[0], CFG)
    out = Summarizer(_fake_client(msgs)).summarize(it, "article body")
    assert out["importance"] == 5  # clamp 到 1-5
    kw = msgs.kwargs
    assert kw["fallbacks"] == "default"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert "article body" in kw["messages"][0]["content"]


def test_summarizer_refusal_returns_none():
    msgs = _FakeMessages("", stop_reason="refusal")
    it = score_item(_feed()[0], CFG)
    assert Summarizer(_fake_client(msgs)).summarize(it, "") is None


def test_build_prompt_lists_candidates():
    it = score_item(_feed()[0], CFG)
    assert "南亞科 2408" in build_prompt(it, "")
