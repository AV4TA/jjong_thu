import json
import urllib.request
import re
import datetime

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_kbo_rankings():
    # KBO 공식 홈페이지 기록실 페이지
    url = "https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx"
    html = fetch_html(url)
    
    if not html:
        return []

    rankings = []
    
    # <tbody> 내부만 추출
    tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL)
    if not tbody_match:
        return []
    
    tbody_content = tbody_match.group(1)
    # 각 줄(tr) 추출
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_content, re.DOTALL)
    
    for row in rows:
        # 각 셀(td) 추출
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(tds) >= 8:
            # HTML 태그 제거 및 공백 정리
            clean_data = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
            
            # 랭킹 숫자가 있는 줄만 수집
            if clean_data[0].isdigit():
                rankings.append({
                    "rank": clean_data[0],
                    "teamName": clean_data[1],
                    "games": clean_data[2],
                    "win": clean_data[3],
                    "lose": clean_data[4],
                    "draw": clean_data[5],
                    "wra": clean_data[6],
                    "gameDiff": clean_data[7]
                })
    return rankings

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    today_str = today_kst.strftime("%Y-%m-%d")

    # 순위 데이터 직접 스크래핑
    rankings = fetch_kbo_rankings()

    # (경기 일정 등 기존 로직 유지)
    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "rankings": rankings,
        # ... 경기 일정 등은 기존처럼 유지 ...
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ 직접 파싱 완료: {len(rankings)}개 팀 순위 수집됨.")

if __name__ == "__main__":
    fetch_kt_wiz_data()
