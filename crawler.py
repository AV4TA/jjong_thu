import json
import urllib.request
import datetime

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

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    year = today_kst.year
    today_str = today_kst.strftime("%Y-%m-%d")

    # 1. 팀명 매핑 및 초기 데이터 세팅
    team_map = {
        'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SS': '삼성 라이온즈', 'OB': '두산 베어스',
        'HT': 'KIA 타이거즈', 'HH': '한화 이글스', 'NC': 'NC 다이노스', 'LT': '롯데 자이언츠',
        'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'
    }
    
    # KBO 전체 팀 목록
    kbo_teams = ['kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈', '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈']
    stats = {team: {"W": 0, "L": 0, "D": 0, "G": 0} for team in kbo_teams}

    # 2. 일정 수집 (네이버 API)
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)
    
    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    if s_data and "result" in s_data:
        for g in s_data["result"].get("games", []):
            home_code = g.get("homeTeamCode")
            away_code = g.get("awayTeamCode")
            home_name = team_map.get(home_code, home_code)
            away_name = team_map.get(away_code, away_code)
            
            # 경기 결과 통계 누적
            if g.get("statusCode") in ['RESULT', 'END']:
                h_score = int(g.get("homeTeamScore", 0))
                a_score = int(g.get("awayTeamScore", 0))
                
                # 통계 반영
                stats[home_name]["G"] += 1
                stats[away_name]["G"] += 1
                if h_score > a_score:
                    stats[home_name]["W"] += 1
                    stats[away_name]["L"] += 1
                elif h_score < a_score:
                    stats[home_name]["L"] += 1
                    stats[away_name]["W"] += 1
                else:
                    stats[home_name]["D"] += 1
                    stats[away_name]["D"] += 1

            # KT 위즈 정보 수집
            if home_code == "KT" or away_code == "KT":
                raw_dt = g.get("gameDateTime", "")
                game_date = raw_dt.split("T")[0]
                is_home = (home_code == "KT")
                res_type = "scheduled"
                if g.get("statusCode") in ['RESULT', 'END']:
                    kt_s = h_score if is_home else a_score
                    opp_s = a_score if is_home else h_score
                    res_type = "win" if kt_s > opp_s else ("lose" if kt_s < opp_s else "draw")
                
                game_obj = {"date": game_date, "opponent": away_name if is_home else home_name, "result": res_type}
                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = game_obj

    # 3. 순위 정렬 계산 (승률 = 승/(승+패+무))
    sorted_teams = sorted(
        stats.items(), 
        key=lambda x: (x[1]["W"] / x[1]["G"] if x[1]["G"] > 0 else 0, x[1]["W"]), 
        reverse=True
    )
    
    rankings = []
    for i, (team, s) in enumerate(sorted_teams):
        win_rate = (s["W"] / s["G"]) if s["G"] > 0 else 0
        rankings.append({
            "rank": str(i + 1),
            "teamName": team,
            "games": str(s["G"]),
            "win": str(s["W"]),
            "lose": str(s["L"]),
            "draw": str(s["D"]),
            "wra": f"{win_rate:.3f}",
            "gameDiff": "-"
        })

    # 4. 라인업 수집
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_team = l_data["result"]["gameInfo"]["homeTeamCode"]
            target = l_data["result"]["lineup"]["home" if (home_team == "KT") else "away"]
            today_lineup = {"pitcher": target.get("starterPitcher", {}).get("name", "-"), "batters": [{"name": b.get("name", "-")} for b in target.get("batters", [])]}

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
