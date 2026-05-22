"""Content Optimizer API — FastAPI + Gemini 2.5 Flash"""
import os, re, json, httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Content Optimizer API")

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ── Request Models ──
class AnalyzeReq(BaseModel):
    text: str
    content_type: str = "blog"

class ChatReq(BaseModel):
    message: str
    history: list[dict] = []
    analysis_context: dict | None = None

# ── Analysis Engine ──
def count_matches(text, patterns):
    return sum(len(re.findall(p, text, re.I)) for p in patterns)

def analyze(text: str, ctype: str):
    lines = [l for l in text.split("\n") if l.strip()]
    words = [w for w in text.split() if w]
    wc = len(words)
    sents = [s.strip() for s in re.split(r'[.!?。]+', text) if len(s.strip()) > 3]
    sc = len(sents)

    stats = count_matches(text, [r'\d+(\.\d+)?%', r'\d{1,3}(,\d{3})+', r'\$\d+', r'\d+배', r'\d+\s*(만|억|조)', r'\d+x'])
    cites = count_matches(text, [r'\(.*?\d{4}.*?\)', r'according to', r'에 따르면', r'연구에 의하면', r'\[[\d,\s]+\]', r'출처\s*:', r'research\s*(by|from|shows|found)'])
    quotes = len(re.findall(r'[""\u201c][^""\u201d]+[""\u201d]|「[^」]+」', text))
    heads = [l for l in lines if re.match(r'^#{1,6}\s', l)]
    qheads = len([h for h in heads if re.search(r'\?|란|어떻게|무엇|왜|언제', h)])
    lists = len([l for l in lines if re.match(r'^\s*[-*•]\s', l) or re.match(r'^\s*\d+[.)]\s', l)])
    schema = len(re.findall(r'schema|FAQ|HowTo|Article|스키마', text, re.I))
    eeat = len(re.findall(r'expert|전문가|PhD|박사|교수|professor|경력|경험|저자|ORCID', text, re.I))
    hashtags = len(re.findall(r'#[^\s#]+', text))
    ctas = len(re.findall(r'구독|팔로우|좋아요|공유|댓글|subscribe|follow|like|share|comment', text, re.I))

    fl = next((l for l in lines if len(l.strip()) > 20 and not l.strip().startswith(('#', '<'))), None)
    ans_first = fl is not None and 30 < len(fl) < 300
    avg_sl = wc / max(sc, 1)
    fluency = 1.0 if 5 < avg_sl < 25 else 0.5

    freq = {}
    for w in words:
        c = re.sub(r'[^a-z가-힣]', '', w.lower())
        if len(c) > 2:
            freq[c] = freq.get(c, 0) + 1
    stuffed = max(freq.values(), default=0) / max(wc, 1) > 0.05 if wc > 0 else False
    hook = bool(re.search(r'\?|!|알고|비밀|충격|꿀팁|방법|이유|진짜', lines[0] if lines else ""))

    is_vid = ctype in ("youtube", "shorts")
    is_short = ctype in ("shorts", "sns")

    # SEO scoring
    if is_vid:
        seo_scores = [70 if heads else 20, 100 if wc > 100 else 60 if wc > 50 else 30, 100 if hashtags >= 3 else 50 if hashtags > 0 else 0, 100 if ctas > 0 else 0, 100 if hook else 20]
    else:
        seo_scores = [100 if len(heads) >= 3 else 50 if heads else 0, 100 if wc > 500 else 60 if wc > 200 else 30, 100 if lists > 3 else 50 if lists > 0 else 0, 20 if stuffed else 100, round(fluency * 100)]

    # AEO scoring
    if is_short:
        aeo_scores = [100 if hook else 0, 80 if wc > 20 else 30, 100 if hashtags >= 3 else 50 if hashtags > 0 else 0]
    else:
        aeo_scores = [100 if ans_first else 0, 100 if qheads > 0 else 0, 100 if schema > 0 else 0, 100 if eeat >= 3 else 50 if eeat > 0 else 0]

    # GEO scoring
    geo_scores = [min(100, stats * 25), min(100, cites * 30), min(100, quotes * 35), round(fluency * (100 if stats > 0 else 50))]

    seo_s = min(100, round(sum(seo_scores) / len(seo_scores)))
    aeo_s = min(100, round(sum(aeo_scores) / len(aeo_scores)))
    geo_s = min(100, round(sum(geo_scores) / len(geo_scores)))
    overall = round(seo_s * 0.3 + aeo_s * 0.3 + geo_s * 0.4)

    # AI citation probability
    bp = min(95, round(
        (20 if stats > 0 else 0) + (18 if cites > 0 else 0) + (12 if quotes > 0 else 0) +
        (15 if ans_first else 0) + (8 if len(heads) >= 3 else 0) + (8 if not stuffed else 0) +
        fluency * 8 + (6 if eeat > 0 else 0)
    ))
    platforms = {
        "ChatGPT": min(95, bp + (5 if quotes > 0 else -10)),
        "Perplexity": min(95, bp + (10 if cites > 0 else -5)),
        "Google AI Overview": min(95, bp + (8 if len(heads) > 2 else -5)),
        "네이버 AI 브리핑": min(95, bp + (8 if eeat > 0 else -8)),
        "Claude": min(95, bp + (8 if stats > 1 else -3)),
    }

    # Suggestions
    suggestions = []
    if stats < 2:
        suggestions.append({"priority": "높음", "text": "구체적 통계 추가", "detail": "통계 추가가 GEO 단일 최고 전략. 최대 40% 가시성 향상. '크게 증가' → '47% 증가'로 교체.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if cites < 1:
        suggestions.append({"priority": "높음", "text": "신뢰 출처 인용", "detail": "출처 인용이 5위 사이트에서 115.1% 가시성 증가. '(저자, 연도)' 패턴으로 학술논문·보고서 인용.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if quotes < 1:
        suggestions.append({"priority": "높음", "text": "전문가 인용문 포함", "detail": "인용문 추가가 상위 3대 GEO 전략. AI가 인용문을 증거로 추출.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if not ans_first and not is_short:
        suggestions.append({"priority": "높음", "text": "Answer-first 요약 배치", "detail": "AEO 핵심 전환. H2 직후 40~60단어로 핵심 답변 제시.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if qheads == 0 and not is_vid:
        suggestions.append({"priority": "중간", "text": "질문형 H2 작성", "detail": "사용자 AI 프롬프트와 동일 형태 헤딩이 인용 확률 증가.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if schema == 0 and not is_short:
        suggestions.append({"priority": "중간", "text": "스키마 마크업 추가", "detail": "FAQPage/HowTo JSON-LD가 리치결과 + AI 정확 추출 지원.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if eeat == 0:
        suggestions.append({"priority": "중간", "text": "E-E-A-T 신호 추가", "detail": "저자명, 직함, ORCID, 경력 명시. AI 신뢰 핵심.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})
    if stuffed:
        suggestions.append({"priority": "높음", "text": "키워드 과다 반복 제거", "detail": "키워드 스터핑이 GEO 9가지 전략 중 최하위.", "paper": "GEO: Generative Engine Optimization (SIGKDD 2024)", "paper_url": "https://arxiv.org/abs/2311.09735"})

    return {
        "overall": overall, "seo": seo_s, "aeo": aeo_s, "geo": geo_s,
        "platforms": platforms, "suggestions": suggestions,
        "meta": {
            "word_count": wc, "stats": stats, "citations": cites, "quotes": quotes,
            "headings": len(heads), "question_headings": qheads, "lists": lists,
            "answer_first": ans_first, "keyword_stuffing": stuffed, "hashtags": hashtags,
            "content_type": ctype
        }
    }


# ── API Routes ──
@app.post("/api/analyze")
async def api_analyze(req: AnalyzeReq):
    if len(req.text.strip()) < 10:
        raise HTTPException(400, "텍스트가 너무 짧습니다 (10자 이상)")
    return analyze(req.text, req.content_type)


@app.post("/api/chat")
async def api_chat(req: ChatReq):
    if not GEMINI_KEY:
        raise HTTPException(500, "GEMINI_API_KEY 환경변수가 설정되지 않았습니다")

    sys_prompt = """You are an SEO/AEO/GEO content optimization expert. Speak Korean.
Key research: Princeton GEO (SIGKDD 2024): Stats=best(+40%), Citations=+115%@rank5, Quotes=top3, Fluency+Stats=best combo(+5.5%), Keyword stuffing=worst.
Naver AI Briefing: 20% expansion, CTR+8%, dwell+22%. AI citations overlap Google SERP only 12% (ChatGPT 8%, Perplexity 28%).
Give specific, actionable advice with research references."""

    if req.analysis_context:
        ctx = req.analysis_context
        sys_prompt += f"\nCurrent analysis: Overall {ctx.get('overall',0)}/100, SEO {ctx.get('seo',0)}, AEO {ctx.get('aeo',0)}, GEO {ctx.get('geo',0)}."
        m = ctx.get("meta", {})
        sys_prompt += f" Stats:{m.get('stats',0)}, Citations:{m.get('citations',0)}, Quotes:{m.get('quotes',0)}, Words:{m.get('word_count',0)}, Type:{m.get('content_type','blog')}."

    contents = [
        {"role": "user", "parts": [{"text": sys_prompt}]},
        {"role": "model", "parts": [{"text": "네, SEO/AEO/GEO 전문가로서 도와드리겠습니다."}]},
    ]
    for msg in req.history:
        contents.append({"role": msg.get("role", "user"), "parts": [{"text": msg.get("text", "")}]})
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                f"{GEMINI_URL}?key={GEMINI_KEY}",
                json={
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.7}
                }
            )
            data = resp.json()
        except Exception as e:
            raise HTTPException(502, f"Gemini API 연결 실패: {str(e)}")

    if "error" in data:
        raise HTTPException(502, f"Gemini API 오류: {data['error'].get('message','')}")

    reply = ""
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        reply += part.get("text", "")

    return {"reply": reply or "응답을 받지 못했습니다."}


@app.get("/api/health")
async def health():
    return {"status": "ok", "gemini_configured": bool(GEMINI_KEY)}


# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
