import os
import json
import datetime
import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET
import google.generativeai as genai
import requests

# 1. Gemini API 설정 (최신 무료 모델인 2.5-flash로 업데이트)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 야후 파이낸스 접속 차단 우회를 위한 브라우저 위장 세션 설정
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def get_stocks():
    # 삼성전자, SK하이닉스, 마이크론, TSMC, 엔비디아
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
            # session을 추가하여 봇이 아닌 척 데이터를 요청
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="5d")
            if not hist.empty:
                closes = hist['Close'].tolist()
                today_price = closes[-1]
                prev_price = closes[-2] if len(closes) > 1 else closes[-1]
                change_pct = ((today_price - prev_price) / prev_price) * 100
                stock_data[name] = {
                    "price": round(today_price, 2),
                    "change_pct": round(change_pct, 2),
                    "trend_5d": [round(x, 2) for x in closes]
                }
        except Exception as e:
            print(f"{name} 주식 데이터 로드 실패: {e}")
            continue
    return stock_data

def get_exchange_rates():
    tickers = {"USD/KRW": "USDKRW=X", "JPY/KRW": "JPYKRW=X", "EUR/KRW": "EURKRW=X"}
    rate_data = {}
    for name, ticker in tickers.items():
        try:
            # 여기에도 session 추가
            t = yf.Ticker(ticker, session=session)
            hist = t.history(period="2d")
            if not hist.empty:
                rate_data[name] = round(hist['Close'].tolist()[-1], 2)
        except Exception:
            continue
    return rate_data

def get_news_summary():
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(url)
        response = urllib.request.urlopen(req)
        root = ET.fromstring(response.read())
        titles = [item.find('title').text for item in root.findall('.//item')[:20]]
        
        prompt = f"다음은 오늘의 주요 뉴스 헤드라인입니다. 가장 중요한 핵심 이슈 5가지를 뽑아서 1줄씩 요약해주세요.\n\n헤드라인:\n{chr(10).join(titles)}"
        res = model.generate_content(prompt)
        return [line.strip() for line in res.text.strip().split('\n') if line.strip()]
    except Exception as e:
        return [f"뉴스 요약 실패: {e}"]

def get_english_opic():
    prompt = "OPIc AL 등급 달성을 위해 유용한 '오늘의 원어민 영어 표현' 1개를 선정하고, 그 의미와 2~3줄의 상황별 대화문 예시를 작성해줘. 마크다운 기호 없이 텍스트로만 깔끔하게 작성해."
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"영어 표현 요약 실패: {e}"

def get_japanese_sjpt():
    prompt = "SJPT 레벨 7 이상을 위한 '오늘의 고급 일본어 표현' 1개를 선정하고, 한글 발음 표기와 함께 의미, 예문을 작성해줘. 마크다운 없이 텍스트로만 작성해."
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"일어 표현 요약 실패: {e}"

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
            papers.append(f"제목: {title}\n초록: {summary}")
        
        if not papers:
            return "최근 논문 검색 결과가 없습니다."
            
        prompt = f"다음은 반도체 계측(Semiconductor metrology) 관련 최신 논문 3편입니다. 이를 바탕으로 최신 기술 트렌드를 한국어로 3~4문장으로 요약해줘.\n\n{chr(10).join(papers)}"
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"논문 요약 실패: {e}"

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
