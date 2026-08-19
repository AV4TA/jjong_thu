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
            return res.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read().decode('utf-8'))
    except:
        return None

def fetch_kbo_rankings():
    # KBO 공식 홈페이지 기록실에서 직접 순위 데이터 추출
    url = "https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx"
    html = fetch_html(url)
    if not html: return []

    rankings = []
    tbody_match = re.search(r'<tbody[^>]*>(.*?)</tbody>', html, re.DOTALL)
    if tbody_match:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL)
        for row in rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(tds) >= 8:
                clean_data = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
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
    year = today_kst.year
    today_str = today_kst.strftime("%Y-%m-%d")

    # 1. 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)
    kt_schedule = {}
    today_game_id = None
    today_game_info = None
    team_map = {'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈'}

    if s_data and "result" in s_data:
        for g in s_data["result"].get("games", []):
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0]
            if "KT" in g.get("homeTeamName", "") or "KT" in g.get("awayTeamName", "") or g.get("homeTeamCode") == "KT" or g.get("awayTeamCode") == "KT":
                is_home = ("KT" in g.get("homeTeamName", "")) or (g.get("homeTeamCode") == "KT")
                opp_raw = g.get("awayTeamName") if is_home else g.get("homeTeamName")
                res_type = "scheduled"
                if g.get("statusCode") in ['RESULT', 'END']:
                    kt_s = int(g.get("homeTeamScore" if is_home else "awayTeamScore", 0))
                    opp_s = int(g.get("awayTeamScore" if is_home else "homeTeamScore", 0))
                    res_type = "win" if kt_s > opp_s else ("lose" if kt_s < opp_s else "draw")
                
                game_obj = {"date": game_date, "opponent": team_map.get(opp_raw, opp_raw), "result": res_type}
                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = game_obj

    # 2. 오늘 라인업
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            target = l_data["result"]["lineup"]["home" if ("KT" in l_data["result"]["gameInfo"]["homeTeamName"]) else "away"]
            today_lineup = {"pitcher": target.get("starterPitcher", {}).get("name", "-"), "batters": [{"name": b.get("name", "-")} for b in target.get("batters", [])]}

    # 3. KBO 직접 파싱한 순위
    rankings = fetch_kbo_rankings()

    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
