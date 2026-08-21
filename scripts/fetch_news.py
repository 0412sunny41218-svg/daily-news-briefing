"""
fetch_news.py
--------------
구글 뉴스 RSS(검색 기반)로 정치·시사 / 경제 / 국제 뉴스를 수집한다.
최근 24시간(when:1d) 이내 발행된 기사만 가져온다.

출력: data/raw_YYYY-MM-DD.json
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import feedparser
import requests

# ── 카테고리별 검색 키워드 ─────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "정치·시사": ["국내 정치", "정부 정책", "사회 이슈"],
    "경제": ["경제 지표", "산업 동향", "기업 실적"],
    "국제": ["국제 정세", "미중 관계", "국제 경제"],
}

MAX_PER_CATEGORY = 4  # 카테고리당 최종 기사 수

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).strftime("%Y-%m-%d")

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyBriefingBot/1.0)"}


def build_rss_url(keyword: str) -> str:
    q = quote(keyword)
    return f"https://news.google.com/rss/search?q={q}+when:1d&hl=ko&gl=KR&ceid=KR:ko"


def fetch_keyword(keyword: str, max_items: int = 6):
    url = build_rss_url(keyword)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)

    items = []
    for entry in parsed.entries[:max_items]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        source = ""
        if "source" in entry and hasattr(entry.source, "title"):
            source = entry.source.title
        if not title or not link:
            continue
        items.append({"title": title, "link": link, "source": source, "keyword": keyword})
    return items


def dedupe(items):
    seen = set()
    result = []
    for item in items:
        key = item["title"][:30]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def main():
    all_items = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        category_items = []
        for kw in keywords:
            try:
                print(f"[수집중] {category} / {kw}")
                items = fetch_keyword(kw)
                for it in items:
                    it["category"] = category
                category_items.extend(items)
                time.sleep(1)
            except Exception as e:
                print(f"[경고] '{kw}' 수집 실패: {e}", file=sys.stderr)

        category_items = dedupe(category_items)[:MAX_PER_CATEGORY]
        all_items.extend(category_items)
        print(f"[완료] {category}: {len(category_items)}건")

    os.makedirs("data", exist_ok=True)
    out_path = f"data/raw_{TODAY}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"[저장] {out_path} (총 {len(all_items)}건)")


if __name__ == "__main__":
    main()
