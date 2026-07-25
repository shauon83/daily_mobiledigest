import os
import json
import datetime
import yfinance as yf
import urllib.request
import xml.etree.ElementTree as ET
import requests
import math

api_key = os.environ.get("GEMINI_API_KEY")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def ask_gemini_direct(prompt):
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts":[{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        pass
    return None

def get_stocks():
    tickers = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "Micron": "MU", "TSMC": "TSM", "NVIDIA": "NVDA"}
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
        
        news_items = []
        titles = []
        for item in root.findall('.//item')[:20]:
            title = item.find('title').text
            link = item.find('link').text
            titles.append(title)
            news_items.append({"title": title, "link": link})
        
        prompt = f"다음은 오늘의 주요 뉴스 헤드라인들입니다. 가장 중요한 핵심 이슈들을 분석하여 대표적인 요약문 20개를 작성해줘. 각 요약문은 줄바꿈으로 구분해줘.\n\n헤드라인:\n{chr(10).join(titles)}"
        ai_summary = ask_gemini_direct(prompt)
        
        if not ai_summary:
            return [{"text": "뉴스 요약 데이터 생성 실패", "link": "https://news.google.com"}]
            
        summaries = [line.strip() for line in ai_summary.strip().split('\n') if line.strip()]
        
        result = []
        for i, text in enumerate(summaries[:20]):
            link = news_items[i]["link"] if i < len(news_items) else "https://news.google.com"
            result.append({"text": text, "link": link})
        return result
    except Exception:
        return [{"text": "뉴스 데이터를 불러오지 못했습니다.", "link": "https://google.com"}]

def get_english_opic():
    prompt = "OPIc AL 등급 달성을 위해 유용한 원어민 영어 표현 5개를 선정하고, 각각의 표현, 의미, 간단한 대화문 예시를 번호 매겨서 작성해줘. 마크다운 기호 없이 텍스트로만 깔끔하게 작성해."
    res = ask_gemini_direct(prompt)
    return res if res else "영어 표현 데이터를 불러오지 못했습니다."

def get_japanese_sjpt():
    prompt = "SJPT 레벨 7 이상을 위한 고급 일본어 표현 5개를 선정하고, 한글 발음 표기와 함께 의미, 예문을 번호 매겨서 작성해줘. 마크다운 없이 텍스트로만 작성해."
    res = ask_gemini_direct(prompt)
    return res if res else "일어 표현 데이터를 불러오지 못했습니다."

def get_tech_papers():
    url = "http://export.arxiv.org/api/query?search_query=all:semiconductor+metrology&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending"
    try:
        response = urllib.request.urlopen(url)
        root = ET.fromstring(response.read())
        ns = {'arxiv': 'http://www.w3.org/2005/Atom'}
        
        paper_list = []
        papers_text = []
        for entry in root.findall('arxiv:entry', ns):
            title = entry.find('arxiv:title', ns).text.strip().replace('\n', ' ')
            summary = entry.find('arxiv:summary', ns).text.strip().replace('\n', ' ')
            id_url = entry.find('arxiv:id', ns).text.strip()
            paper_list.append({"title": title, "link": id_url})
            papers_text.append(f"제목: {title}\n초록: {summary[:100]}...")
        
        if not paper_list:
            return {"summary": "최근 논문 검색 결과가 없습니다.", "papers": []}
            
        prompt = f"다음은 반도체 계측(Semiconductor metrology) 관련 최신 논문들입니다. 이를 바탕으로 전반적인 최신 기술 트렌드를 한국어로 4~5문장으로 요약해줘.\n\n{chr(10).join(papers_text[:10])}"
        ai_summary = ask_gemini_direct(prompt)
        
        summary_text = ai_summary if ai_summary else "논문 트렌드 요약 데이터 생성 실패"
        
        return {
            "summary": summary_text,
            "papers": paper_list
        }
    except Exception:
        return {"summary": "논문 데이터를 불러오지 못했습니다.", "papers": []}

def main():
    print("데이터 수집을 시작합니다...")
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    data = {
        "last_updated": kst_now.strftime("%Y-%m-%d %H:%M:%S"),
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
