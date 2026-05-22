# Content Optimizer — SEO · AEO · GEO

Princeton SIGKDD 2024 논문 기반 콘텐츠 최적화 분석기 + Gemini 2.5 Flash AI 상담

## 기능

- **SEO/AEO/GEO 점수 분석** — 글을 붙여넣으면 항목별 점수 산출
- **AI 인용 시뮬레이터** — ChatGPT, Perplexity, Google AI, 네이버 AI, Claude별 인용 확률
- **최적화 제안** — 논문 근거와 링크 포함된 구체적 개선안
- **Gemini AI 상담** — 분석 결과 기반 실시간 AI 조언 (백엔드 프록시)
- **콘텐츠 유형별 분석** — 블로그, 홈페이지, YouTube, Shorts/릴스, SNS

## 구조

```
content-optimizer/
├── main.py              # FastAPI 백엔드
├── requirements.txt     # Python 의존성
├── render.yaml          # Render 배포 설정
├── .gitignore
├── README.md
└── static/
    └── index.html       # 프론트엔드 (단일 파일)
```

## 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
export GEMINI_API_KEY="your-api-key-here"

# 3. 서버 시작
uvicorn main:app --reload --port 8000

# 4. 브라우저에서 http://localhost:8000 접속
```

## Render 배포 (무료)

### 방법 1: render.yaml 자동 배포
1. 이 repo를 GitHub에 push
2. [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. GitHub repo 연결 → `render.yaml` 자동 감지
4. Environment에서 `GEMINI_API_KEY` 값 입력
5. **Apply** → 배포 완료

### 방법 2: 수동 배포
1. Render Dashboard → **New** → **Web Service**
2. GitHub repo 연결
3. 설정:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment** 탭 → `GEMINI_API_KEY` 추가
5. **Deploy** 클릭

### Gemini API 키 발급
1. [Google AI Studio](https://aistudio.google.com/apikey) 접속
2. **Create API Key** 클릭
3. 키 복사 → Render Environment에 붙여넣기

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | 프론트엔드 페이지 |
| `/api/analyze` | POST | 콘텐츠 분석 |
| `/api/chat` | POST | Gemini AI 채팅 |
| `/api/health` | GET | 서버 상태 확인 |

## 참고 논문

- [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735) — ACM SIGKDD 2024
- [What Generative Search Engines Like](https://arxiv.org/abs/2510.11438) — arXiv 2025
- [Beyond Retrieval: Modeling Confidence Decay in GEO](https://arxiv.org/abs/2604.03656) — arXiv 2025

## 라이선스

MIT
