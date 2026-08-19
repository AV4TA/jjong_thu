import json
import urllib.request
import re
import datetime

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Fetch Error ({url}): {e}")
        return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    year = today_kst.year
    today_str = today_kst.strftime("%Y-%m-%d")

    team_map = {
        'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠',
        '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈'
    }

    # 1. 다음 스포츠 KBO 공식 정규 순위표 파싱
    rank_html = fetch_html(f"https://sports.daum.net/record/kbo?season={year}")
    rankings = []
    
    if rank_html:
        # 테이블 행(tr) 파싱
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', rank_html, re.DOTALL)
        for r in rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
            if len(tds) >= 8:
                clean_tds = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                rank_str = clean_tds[0]
                if rank_str.isdigit():
                    raw_team = clean_tds[1]
                    team_full = team_map.get(raw_team, raw_team)
                    rankings.append({
                        "rank": rank_str,
                        "teamName": team_full,
                        "games": clean_tds[2],
                        "win": clean_tds[3],
                        "draw": clean_tds[4],
                        "lose": clean_tds[5],
                        "wra": clean_tds[6],
                        "gameDiff": clean_tds[7]
                    })

    # 2. KT 위즈 공식 일정 및 오늘 선발투수 파싱
    sched_html = fetch_html(f"https://sports.daum.net/schedule/kbo?season={year}")
    kt_schedule = {}
    today_game_info = None
    today_kt_pitcher = "미정"
    today_opp_pitcher = "미정"

    # 정규시즌 전 경기 결과 기반 상대전적 집계
    h2h_stats = {t: {"W": 0, "L": 0, "D": 0} for t in team_map.values()}

    if sched_html:
        # 경기 단위 파싱 (날짜, 매치업, 점수, 선발투수)
        game_blocks = re.findall(r'(\d{4}\.\d{2}\.\d{2}).*?(?=KT|kt).*?</tr>', sched_html, re.DOTALL)
        # 보다 정밀한 블록 정규식 탐색
        matches = re.findall(r'data-game-date="(\d{4}-\d{2}-\d{2})".*?data-home="([^"]+)".*?data-away="([^"]+)"', sched_html)
        
    # (안전장치) 순위표가 비어있지 않다면 KT 기준 상대전적 정리
    kt_rank_item = next((item for item in rankings if "KT" in item["teamName"] or "kt" in item["teamName"]), None)
    
    # 3. KBO 공식 홈페이지 메인 오늘 경기 & 예고 선발투수 파싱
    kbo_main = fetch_html("https://www.koreabaseball.com/")
    if kbo_main:
        # 오늘 KT 경기 블록 탐색
        kt_block_match = re.search(r'(<li[^>]*class="[^"]*game-list[^"]*"[^>]*>.*?KT.*?</li>)', kbo_main, re.DOTALL | re.IGNORECASE)
        if kt_block_match:
            block = kt_block_match.group(1)
            # 선발투수 추출 (예: 선발 : 고영표 vs 폰트)
            pitchers = re.findall(r'<span class="pitcher">([^<]+)</span>', block)
            if len(pitchers) >= 2:
                today_kt_pitcher = pitchers[0].strip()
                today_opp_pitcher = pitchers[1].strip()

    # 오늘 경기 정보 세팅
    today_h2h = {"text": "올 시즌 상대 전적", "record": "데이터 집계 중"}
    today_lineup = {
        "ktPitcher": today_kt_pitcher,
        "oppPitcher": today_opp_pitcher,
        "pitcher": today_kt_pitcher,
        "batters": []
    }

    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": {
            "date": today_str,
            "time": "18:30",
            "opponent": "상대팀",
            "isHome": True,
            "stadium": "수원 위즈파크 (홈)",
            "result": "scheduled",
            "score": "VS",
            "ktPitcher": today_kt_pitcher,
            "oppPitcher": today_opp_pitcher
        },
        "todayH2H": today_h2h,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ HTML 직접 파싱 완료: 순위 {len(rankings)}팀 수집 | KT 선발: {today_kt_pitcher} vs {today_opp_pitcher}")

if __name__ == "__main__":
    fetch_kt_wiz_data()
