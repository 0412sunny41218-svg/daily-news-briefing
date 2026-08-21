"""
generate_briefing.py
---------------------
1) data/raw_YYYY-MM-DD.json 을 읽어서 (카테고리는 이미 fetch_news.py에서 태깅됨)
2) Claude API(Haiku)로 기사별 한 줄 요약("무슨 내용인가요?")을 만들고
3) docs/index.html (랜딩페이지) + docs/briefing/YYYY-MM-DD.html (오늘자 전체 브리핑)를 생성한다.

환경변수 ANTHROPIC_API_KEY 필요 (GitHub Actions Secrets로 주입).
비용 절감을 위해 Haiku 모델을 사용한다.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import requests

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST)
TODAY_STR = TODAY.strftime("%Y-%m-%d")
TODAY_LABEL = TODAY.strftime("%Y년 %m월 %d일 (%a)")
WEEKDAY_KR = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금", "Sat": "토", "Sun": "일"}
for en, kr in WEEKDAY_KR.items():
    TODAY_LABEL = TODAY_LABEL.replace(en, kr)

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"

CATEGORY_ORDER = ["정치·시사", "경제", "국제"]
CATEGORY_COLOR = {
    "정치·시사": "#2A3F5C",
    "경제": "#8A6A2F",
    "국제": "#4A5D4E",
}


def load_raw():
    path = f"data/raw_{TODAY_STR}.json"
    if not os.path.exists(path):
        print(f"[에러] {path} 없음. fetch_news.py를 먼저 실행하세요.", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_claude_summaries(items):
    """각 기사에 대해 한 문장 요약을 받아온다."""
    listing = "\n".join(
        f"{i+1}. [{it['category']}/{it['source']}] {it['title']}"
        for i, it in enumerate(items)
    )

    system_prompt = (
        "너는 종합 뉴스 브리핑 편집자야. 아래 기사 제목 목록을 보고, "
        "각 기사가 어떤 내용인지 한국어 2~3문장(80~100자 내외)으로 쉽게 풀어써줘. "
        "무슨 일이 있었는지(배경/현황)와 왜 눈여겨볼만한지를 함께 담아줘. "
        "제목을 그대로 반복하지 마. "
        "반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 없이 순수 JSON 배열만:\n"
        '[{"index": 1, "summary": "..."}, {"index": 2, "summary": "..."}]'
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 3000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": listing}],
        },
        timeout=120,
    )
    if resp.status_code >= 400:
        print(f"[API 에러 상세] status={resp.status_code} body={resp.text}", file=sys.stderr)
    resp.raise_for_status()
    data = resp.json()
    text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
    text = re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip()
    summaries = json.loads(text)

    summary_map = {s["index"]: s["summary"] for s in summaries}
    for i, it in enumerate(items):
        it["summary"] = summary_map.get(i + 1, it["title"])
    return items


CSS = """
:root{
  --paper:#EDEDE8;
  --card:#FFFFFF;
  --card-alt:#F1F0EC;
  --ink:#232323;
  --ink-soft:#4A4A45;
  --mono:#6B6B65;
  --rule:#DCDBD2;
}
*{box-sizing:border-box;}
body{
  margin:0;background:var(--paper);color:var(--ink);
  font-family:'Pretendard',-apple-system,sans-serif;line-height:1.6;
}
.wrap{max-width:720px;margin:0 auto;padding:40px 20px 80px;}
.eyebrow{font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:1.5px;color:var(--mono);margin-bottom:8px;}
h1{font-family:'Noto Serif KR',serif;font-size:26px;font-weight:700;margin:0 0 6px;letter-spacing:-0.3px;}
.subtitle{font-family:'Pretendard';font-size:13px;color:var(--mono);margin-bottom:20px;}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px;}
.chip{
  font-family:'Pretendard';font-size:12.5px;font-weight:500;color:var(--ink);
  background:#DDDCD3;padding:6px 14px;border-radius:20px;cursor:pointer;border:none;
}
.chip.active{color:#fff;}
.section-head{display:flex;align-items:center;gap:7px;margin:22px 0 10px;}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
.section-head .cat{font-family:'Pretendard';font-size:14.5px;font-weight:500;}
.section-head .count{font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--mono);}
.card{
  background:var(--card);border:1px solid var(--rule);border-radius:10px;
  padding:16px 18px;margin-bottom:12px;
}
.card .source{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--mono);margin-bottom:6px;}
.card h3{font-family:'Noto Serif KR',serif;font-size:16px;font-weight:700;margin:0 0 10px;line-height:1.4;}
.card .summarybox{background:var(--card-alt);border-radius:8px;padding:10px 12px;margin-bottom:10px;}
.card .summarybox .label{font-family:'Pretendard';font-weight:500;font-size:11px;margin-bottom:4px;}
.card .summarybox .text{font-family:'Pretendard';font-size:13px;color:var(--ink-soft);}
.card a.origin{font-family:'Pretendard';font-size:12px;text-decoration:none;font-weight:500;}
footer{
  margin-top:50px;padding-top:18px;border-top:1px solid var(--rule);
  font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--mono);
  display:flex;flex-direction:column;gap:4px;
}
/* 랜딩페이지 전용 */
.hero{background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:26px 24px;margin-bottom:32px;}
.hero h2{font-family:'Noto Serif KR',serif;font-size:21px;font-weight:700;line-height:1.5;margin:0 0 18px;}
.cta{
  display:flex;align-items:center;justify-content:space-between;
  background:var(--ink);color:#fff;border-radius:10px;padding:14px 18px;
  text-decoration:none;font-family:'Pretendard';font-weight:500;font-size:14.5px;
}
.recent-title{font-family:'Pretendard';font-weight:500;font-size:14px;color:var(--mono);margin:0 0 12px;}
.recent-item{
  display:flex;justify-content:space-between;align-items:center;
  background:var(--card);border:1px solid var(--rule);border-radius:10px;
  padding:14px 16px;margin-bottom:10px;text-decoration:none;color:var(--ink);
}
.recent-item .rdate{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--mono);margin-bottom:3px;}
.recent-item .rtitle{font-family:'Noto Serif KR',serif;font-size:15px;font-weight:700;margin-bottom:4px;}
.recent-item .rcounts{font-family:'Pretendard';font-size:12px;color:var(--mono);}
"""

DAILY_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>오늘의 국내외 브리핑 · {date_label}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">TODAY BRIEFING</div>
  <h1>{date_label}</h1>
  <div class="subtitle">최근 24시간 이내 발행된 기사만 모았어요</div>

  <div class="chips" id="chips">
    <button class="chip active" data-cat="all" style="background:#232323;color:#fff;">전체</button>
    {chip_buttons}
  </div>

  {sections}

  <footer>
    <span>정치·경제·국제 뉴스 자동 브리핑</span>
    <span>Claude AI 요약 · 매일 자동 생성</span>
    <span><a href="../index.html" style="color:inherit">← 처음으로</a></span>
  </footer>
</div>
<script>
const chips = document.querySelectorAll('.chip');
const sections = document.querySelectorAll('[data-section]');
chips.forEach(chip => {{
  chip.addEventListener('click', () => {{
    chips.forEach(c => {{ c.classList.remove('active'); c.style.color='#232323'; c.style.background='#DDDCD3'; }});
    chip.classList.add('active'); chip.style.color='#fff'; chip.style.background = chip.dataset.color || '#232323';
    const cat = chip.dataset.cat;
    sections.forEach(sec => {{
      sec.style.display = (cat === 'all' || sec.dataset.section === cat) ? '' : 'none';
    }});
  }});
}});
</script>
</body>
</html>
"""

SECTION_TEMPLATE = """
<div data-section="{category}">
  <div class="section-head">
    <span class="dot" style="background:{color}"></span>
    <span class="cat">{category}</span>
    <span class="count">{count}건</span>
  </div>
  {cards}
</div>
"""

CARD_TEMPLATE = """
<div class="card">
  <div class="source">{source}</div>
  <h3><a href="{link}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none;">{headline}</a></h3>
  <div class="summarybox">
    <div class="label" style="color:{color}">무슨 내용인가요?</div>
    <div class="text">{summary}</div>
  </div>
  <a class="origin" href="{link}" target="_blank" rel="noopener" style="color:{color}">원문에서 확인 ↗</a>
</div>
"""

LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>오늘의 국내외 브리핑</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">TODAY BRIEFING</div>
  <h1 style="margin-bottom:20px;">오늘의 국내외 브리핑</h1>

  <div class="hero">
    <h2>정치·경제·국제 소식을<br>매일 아침 모아드려요</h2>
    <a class="cta" href="briefing/{today}.html">
      <span>오늘({today_short}) 브리핑 읽기</span>
      <span>→</span>
    </a>
  </div>

  <div class="recent-title">최근 업데이트</div>
  {recent_items}

  <footer>
    <span>정치·경제·국제 뉴스 자동 브리핑</span>
    <span>Claude AI 요약 · 매일 자동 생성 · 최근 24시간 이내 발행 기사만 수록</span>
  </footer>
</div>
</body>
</html>
"""

RECENT_ITEM_TEMPLATE = """
<a class="recent-item" href="briefing/{date}.html">
  <div>
    <div class="rdate">{date_label}</div>
    <div class="rtitle">{date} 브리핑</div>
    <div class="rcounts">{counts}</div>
  </div>
  <span>›</span>
</a>
"""


def render_daily_html(articles):
    grouped = {}
    for a in articles:
        grouped.setdefault(a["category"], []).append(a)

    chip_buttons = "".join(
        f'<button class="chip" data-cat="{cat}" data-color="{CATEGORY_COLOR[cat]}">{cat}</button>'
        for cat in CATEGORY_ORDER if cat in grouped
    )

    sections_html = ""
    for cat in CATEGORY_ORDER:
        if cat not in grouped:
            continue
        color = CATEGORY_COLOR[cat]
        cards = "".join(
            CARD_TEMPLATE.format(
                source=a["source"] or "출처 미상",
                link=a["link"],
                headline=a["title"],
                summary=a["summary"],
                color=color,
            )
            for a in grouped[cat]
        )
        sections_html += SECTION_TEMPLATE.format(
            category=cat, color=color, count=len(grouped[cat]), cards=cards
        )

    return DAILY_TEMPLATE.format(
        date_label=TODAY_LABEL, css=CSS, chip_buttons=chip_buttons, sections=sections_html
    )


def build_counts_str(articles):
    grouped = {}
    for a in articles:
        grouped.setdefault(a["category"], 0)
        grouped[a["category"]] += 1
    return " · ".join(f"{cat} {grouped[cat]}건" for cat in CATEGORY_ORDER if cat in grouped)


def update_landing_page(current_counts_str):
    briefing_dir = "docs/briefing"
    os.makedirs(briefing_dir, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(briefing_dir) if re.match(r"\d{4}-\d{2}-\d{2}\.html", f)],
        reverse=True,
    )[:10]

    recent_html = ""
    for f in files:
        date = f.replace(".html", "")
        dt = datetime.strptime(date, "%Y-%m-%d")
        label = dt.strftime("%Y년 %m월 %d일")
        weekday = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
        label = f"{label} ({weekday})"
        counts = current_counts_str if date == TODAY_STR else "지난 브리핑"
        recent_html += RECENT_ITEM_TEMPLATE.format(date=date, date_label=label, counts=counts)

    today_short = TODAY.strftime("%m월 %d일")
    html = LANDING_TEMPLATE.format(
        css=CSS, today=TODAY_STR, today_short=today_short, recent_items=recent_html
    )
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)


def main():
    if not API_KEY:
        print("[에러] ANTHROPIC_API_KEY 환경변수가 없습니다.", file=sys.stderr)
        sys.exit(1)

    raw_items = load_raw()
    if not raw_items:
        print("[경고] 수집된 기사가 없습니다.")
        sys.exit(0)

    print(f"[요약중] Claude API 호출 ({len(raw_items)}건)")
    articles = call_claude_summaries(raw_items)
    print("[완료] 요약 생성됨")

    daily_html = render_daily_html(articles)
    os.makedirs("docs/briefing", exist_ok=True)
    with open(f"docs/briefing/{TODAY_STR}.html", "w", encoding="utf-8") as f:
        f.write(daily_html)

    counts_str = build_counts_str(articles)
    update_landing_page(counts_str)

    print("[저장] docs/index.html, docs/briefing/*.html")


if __name__ == "__main__":
    main()
