import os
import json
import datetime
import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET
import requests
import math

api_key = os.environ.get("GEMINI_API_KEY")

# 야후 파이낸스 우회 세션
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

# 라이브러리 우회: REST API 직접 호출 함수
def ask_gemini_direct(prompt):
    if not api_key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts":[{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"API 에러: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"AI 통신 실패: {e}")
        return None

def get_stocks():
    tickers = {
        "삼성전자": "005930.KS", 
        "SK하이닉스": "000660.KS", 
        "Micron": "MU", 
        "TSMC": "TSM", 
        "NVIDIA": "NVDA"
    }
    stock_data = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="5d")
            if not hist.empty:
                closes = [x for x in hist['Close'].tolist() if not math.isnan(x)]
                if len(closes) > 0:
                    today_price = closes[-1]
                    prev_price = closes[-2] if len(closes) > 1 else closes[-1]
                    change_pct = ((today_price - prev_price) / prev_price) * 100 if prev_price != 0 else 0
                    
                    stock_data[name] = {
                        "price": round(today_price, 2),
                        "change_pct": round(change_pct, 2),
                        "trend_5d": [round(x, 2) for x in closes]
                    }
        except Exception:
            continue
    return stock_data

def get_exchange_rates():
    tickers = {"USD/KRW": "USDKRW=X", "JPY/KRW": "JPYKRW=X", "EUR/KRW": "EURKRW=X"}
    rate_data = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="2d")
            if not hist.empty:
                closes = [x for x in hist['Close'].tolist() if not math.isnan(x)]
                if closes:
                    rate_data[name] = round(closes[-1], 2)
        except Exception:
            continue
    return rate_data

def get_news_summary():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req)
        root = ET.fromstring(response.read())
        titles = [item.find('title').text for item in root.findall('.//item')[:10]]
        
        prompt = f"다음은 오늘의 주요 뉴스 헤드라인입니다. 가장 중요한 핵심 이슈 5가지를 뽑아서 1줄씩 요약해주세요.\n\n헤드라인:\n{chr(10).join(titles)}"
        ai_summary = ask_gemini_direct(prompt)
        
        if ai_summary:
            return [line.strip() for line in ai_summary.strip().split('\n') if line.strip()]
        else:
            # 안전장치: AI 실패 시 원본 헤드라인 5개 제공
            return [f"📰 {t}" for t in titles[:5]]
    except Exception as e:
        return ["뉴스 데이터를 불러오지 못했습니다."]

def get_english_opic():
    prompt = "OPIc AL 등급 달성을 위해 유용한 '오늘의 원어민 영어 표현' 1개를 선정하고, 그 의미와 2~3줄의 상황별 대화문 예시를 작성해줘. 마크다운 기호 없이 텍스트로만 깔끔하게 작성해."
    res = ask_gemini_direct(prompt)
    if res:
        return res
    # 안전장치: 고정 표현 반환
    return "💡 오늘의 표현: I haven't gotten around to it yet.\n의미: 아직 거기까지 신경 쓸 겨를이 없었어요.\n(AI 연결 지연으로 기본 표현이 제공되었습니다.)"

def get_japanese_sjpt():
    prompt = "SJPT 레벨 7 이상을 위한 '오늘의 고급 일본어 표현' 1개를 선정하고, 한글 발음 표기와 함께 의미, 예문을 작성해줘. 마크다운 없이 텍스트로만 작성해."
    res = ask_gemini_direct(prompt)
    if res:
        return res
    # 안전장치: 고정 표현 반환
    return "💡 오늘의 표현: 差し支えなければ (사시츠카에 나케레바)\n의미: 지장이 없으시다면, 괜찮으시다면\n(AI 연결 지연으로 기본 표현이 제공되었습니다.)"

def get_tech_papers():
    url = "http://export.arxiv.org/api/query?search_query=all:semiconductor+metrology&start=0&max_results=3&sortBy=submittedDate&sortOrder=descending"
    try:
        response = urllib.request.urlopen(url)
        root = ET.fromstring(response.read())
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        papers = []
        for entry in root.findall('arxiv:entry', ns):
            title = entry.find('arxiv:title', ns).text.strip()
            summary = entry.find('arxiv:summary', ns).text.strip()
            papers.append(f"제목: {title}\n초록: {summary[:200]}...")
        
        if not papers:
            return "최근 논문 검색 결과가 없습니다."
            
        prompt = f"다음은 반도체 계측(Semiconductor metrology) 관련 최신 논문 3편입니다. 이를 바탕으로 최신 기술 트렌드를 한국어로 3~4문장으로 요약해줘.\n\n{chr(10).join(papers)}"
        ai_summary = ask_gemini_direct(prompt)
        
        if ai_summary:
            return ai_summary
        else:
            # 안전장치: 원본 논문 제목 제공
            return "🔬 최신 논문 리스트 (AI 요약 지연 중):\n\n" + "\n".join([p.split('\n')[0] for p in papers])
            
    except Exception as e:
        return "논문 데이터를 불러오지 못했습니다."

def main():
    print("데이터 수집을 시작합니다...")
    data = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stocks": get_stocks(),
        "exchange_rates": get_exchange_rates(),
        "news": get_news_summary(),
        "english_opic": get_english_opic(),
        "japanese_sjpt": get_japanese_sjpt(),
        "tech_papers": get_tech_papers()
    }
    
    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("데이터 저장 완료: public/data.json")

if __name__ == "__main__":
    main()
