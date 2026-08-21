# 오늘의 국내외 브리핑

정치·시사 / 경제 / 국제 뉴스를 매일 아침 자동으로 수집·요약해서
정적 웹사이트로 발행하는 파이프라인입니다.

작동 방식: 구글 뉴스 RSS 검색(최근 24시간) → Claude API(Haiku)로 한 줄 요약 →
정적 HTML 생성(랜딩페이지 + 일일 브리핑) → GitHub Actions가 매일 자동 실행 →
GitHub Pages로 배포

---

## 1. GitHub 저장소 만들기

1. GitHub에서 새 저장소 생성 (예: `daily-news-briefing`), Public으로 설정
2. 이 폴더 전체를 저장소에 push (marketing-briefing 때와 같은 방식: GitHub Desktop으로 Clone → 파일 복사 → Commit → Push)

## 2. Claude API 키 등록 (Secrets)

marketing-briefing 저장소에서 썼던 것과 **같은 키 값**을 이 저장소에도 등록해야 해요.
(저장소마다 따로 등록해야 하고, 자동으로 공유되지 않아요)

1. 저장소 페이지 → **Settings → Secrets and variables → Actions**
2. **New repository secret** 클릭
3. Name: `ANTHROPIC_API_KEY`, Value: 기존에 쓰던 API 키 붙여넣기

## 3. GitHub Pages 켜기

1. 저장소 **Settings → Pages**
2. Source: `Deploy from a branch`
3. Branch: `main`, 폴더: `/docs` 선택 → Save

## 4. 자동 실행 확인

- 기본: 매일 한국시간 오전 7시 자동 실행
- 지금 바로 테스트: Actions 탭 → `Daily News Briefing` → **Run workflow**

---

## 커스터마이징 포인트

| 바꾸고 싶은 것 | 어디를 수정 |
|---|---|
| 검색 키워드 | `scripts/fetch_news.py` 의 `CATEGORY_KEYWORDS` |
| 카테고리당 기사 수 | `scripts/fetch_news.py` 의 `MAX_PER_CATEGORY` |
| 요약 스타일/톤 | `scripts/generate_briefing.py` 의 `system_prompt` |
| 디자인(색상, 폰트) | `scripts/generate_briefing.py` 의 `CSS` |
| 실행 시간 | `.github/workflows/daily-briefing.yml` 의 `cron` |
| 사용 모델 | `scripts/generate_briefing.py` 의 `MODEL` (현재 Haiku, 비용 절감용) |

## 폴더 구조

```
daily-news-briefing/
├── scripts/
│   ├── fetch_news.py         # 뉴스 수집
│   └── generate_briefing.py  # 요약 + 사이트 생성
├── data/                     # 수집된 원본 데이터 (자동 생성)
├── docs/                     # GitHub Pages로 배포되는 사이트
│   ├── index.html            # 랜딩페이지 (최근 브리핑 목록)
│   └── briefing/              # 날짜별 전체 브리핑 페이지
├── .github/workflows/
│   └── daily-briefing.yml
└── requirements.txt
```
