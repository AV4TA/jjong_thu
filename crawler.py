import json
import datetime
import urllib.request

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://sports.media.daum.net/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"데이터 조회 실패: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 경기 일정 및 순위 로직은 동일
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)
    kt_schedule = {}
    today_game_id = None
    today_game_info = None
    
    # 순위 계산용
    all_teams = ['LG', 'SSG', '두산', 'KIA', '삼성', '롯데', '한화', 'NC', '키움', 'KT']
    standings_calc = {t: {"teamName": "", "games": 0, "win": 0, "draw": 0, "lose": 0} for t in all_teams}

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            # KT 경기 정보 추출
            if "KT" in g.get("homeTeamName", "") or "KT" in g.get("awayTeamName", ""):
                raw_dt = g.get("gameDateTime", "")
                game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]
                if game_date >= f"{year}-03-28":
                    is_home = ("KT" in g.get("homeTeamName", ""))
                    opp = g.get("awayTeamName") if is_home else g.get("homeTeamName")
                    kt_schedule[game_date] = {
                        "date": game_date, "opponent": opp, "score": f"{g.get('homeTeamScore')} : {g.get('awayTeamScore')}",
                        "result": "win" if (is_home and g.get('homeTeamScore') > g.get('awayTeamScore')) or (not is_home and g.get('awayTeamScore') > g.get('homeTeamScore')) else "lose"
                    }
                    if game_date == today_str:
                        today_game_id = g.get("gameId")
                        today_game_info = kt_schedule[game_date]

    # 2. KT Wiz 실시간 선수 기록 (Daum 스포츠 API 활용)
    player_stats = {"batters": [], "pitchers": []}
    
    # 타자
    b_data = fetch_json(f"https://score.sports.media.daum.net/plan/do/kbo/record_team_individual.json?season={year}&team_id=KT&category=hitter")
    if b_data and "list" in b_data:
        for b in b_data["list"][:15]:
            player_stats["batters"].append({
                "name": b.get("name", "-"), "hra": b.get("hra", "-"), "hit": b.get("hit", "-"), 
                "hr": b.get("hr", "-"), "rbi": b.get("rbi", "-"), "ops": b.get("ops", "-")
            })

    # 투수
    p_data = fetch_json(f"https://score.sports.media.daum.net/plan/do/kbo/record_team_individual.json?season={year}&team_id=KT&category=pitcher")
    if p_data and "list" in p_data:
        for p in p_data["list"][:15]:
            player_stats["pitchers"].append({
                "name": p.get("name", "-"), "era": p.get("era", "-"), "win": p.get("w", "-"), 
                "lose": p.get("l", "-"), "save": p.get("sv", "-"), "so": p.get("so", "-")
            })

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "playerStats": player_stats,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
