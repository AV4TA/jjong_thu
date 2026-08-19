import json
import datetime
import urllib.request
import re
import ssl

ssl_ctx = ssl._create_unverified_context()

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"HTML 읽기 오류: {e}")
        return ""

def update_starter_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")

    # 1. JSON 불러오기
    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON 로드 오류: {e}")
        return

    today_match = data.get("todayMatch")
    if not today_match:
        print("오늘 KT 경기 일정이 없습니다.")
        return

    is_home = today_match.get("isHome", True)
    kt_p = "미정"
    opp_p = "미정"

    # 2. KBO 공식 메인/일정 페이지 텍스트 크롤링 (전날 예고된 선발투수 추출)
    urls = [
        "https://www.koreabaseball.com/Schedule/GameCenter/Main.aspx",
        "https://m.koreabaseball.com/"
    ]

    for url in urls:
        html = fetch_html(url)
        if not html:
            continue

        # HTML 내 KT 경기 블록 찾기
        blocks = re.findall(r'(<li[^>]*>[\s\S]*?</li>|<div[^>]*class="game-cont"[^>]*>[\s\S]*?</div>)', html)
        for b in blocks:
            if "KT" in b or "kt" in b:
                # 텍스트 태그 제거 및 정제
                clean_txt = re.sub(r'<[^>]+>', ' ', b)
                
                # '선발 : 홍길동' 패턴 또는 '선발투수' 패턴 검색
                pitchers = re.findall(r'(?:선발|투수)\s*[:：]?\s*([가-힣]{2,4})', clean_txt)
                
                if len(pitchers) >= 2:
                    # KBO 표준 표시 순서: [원정팀 선발, 홈팀 선발]
                    if is_home:
                        opp_p = pitchers[0].strip()
                        kt_p = pitchers[1].strip()
                    else:
                        kt_p = pitchers[0].strip()
                        opp_p = pitchers[1].strip()
                    break

        if kt_p != "미정" and opp_p != "미정":
            break

    # 3. JSON 파일에 선발투수 텍스트 덮어쓰기
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    
    if "todayLineup" not in data or not isinstance(data["todayLineup"], dict):
        data["todayLineup"] = {}

    data["todayLineup"]["ktPitcher"] = kt_p
    data["todayLineup"]["oppPitcher"] = opp_p
    data["todayLineup"]["pitcher"] = kt_p
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 선발투수 텍스트 추출 성공: KT [{kt_p}] vs 상대 [{opp_p}]")

if __name__ == "__main__":
    update_starter_pitchers()
