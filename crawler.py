import json
import datetime
import urllib.request

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://m.sports.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"조회 실패 [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 전체 시즌 경기 일정
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-01&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)
    
    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")
            home_code = g.get("homeTeamCode", "")
            away_code = g.get("awayTeamCode", "")

            if "KT" in home or "KT" in away or home_code == "KT" or away_code == "KT":
                game_date = g.get("gameDateTime", "").split("T")[0]
                is_home = ("KT" in home) or (home_code == "KT")
                opp_raw = away if is_home else home
                opp_name = team_map.get(opp_raw, opp_raw)
                stadium = g.get("stadium", "수원 케이티위즈파크" if is_home else "원정구장")
                
                home_score = g.get("homeTeamScore")
                away_score = g.get("awayTeamScore")
                status = g.get("status", "")
                status_code = g.get("statusCode", "")
                game_time = g.get("gameDateTime", "").split("T")[1][:5] if "T" in g.get("gameDateTime", "") else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in status or status_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif home_score is not None and away_score is not None:
                    kt_score = int(home_score if is_home else away_score)
                    opp_score = int(away_score if is_home else home_score)
                    score_str = f"KT {kt_score} : {opp_score} {opp_raw}"
                    if kt_score > opp_score:
                        res_type = "win"
                    elif kt_score < opp_score:
                        res_type = "lose"
                    else:
                        res_type = "draw"

                game_obj = {
                    "gameId": g.get("gameId"),
                    "date": game_date,
                    "time": game_time,
                    "opponent": opp_name,
                    "isHome": is_home,
                    "stadium": f"수원 위즈파크 (홈)" if is_home else f"{stadium} (원정)",
                    "result": res_type,
                    "score": score_str
                }

                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = game_obj

    # 2. 오늘 경기 라인업
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_team = l_data.get("result", {}).get("gameInfo", {}).get("homeTeamCode", "")
            is_kt_home = (home_team == "KT")
            target_lineup = l_data.get("result", {}).get("lineup", {}).get("home" if is_kt_home else "away", {})
            
            today_lineup = {
                "pitcher": target_lineup.get("starterPitcher", {}).get("name", "미발표"),
                "batters": [{"order": b.get("order"), "name": b.get("name"), "pos": b.get("pos")} for b in target_lineup.get("batters", [])]
            }

    # 3. KBO 리그 팀 순위 (안정적인 공식 엔드포인트)
    rankings = []
    rank_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/team?season={year}"
    r_data = fetch_json(rank_url)
    if r_data and "result" in r_data:
        rank_list = r_data.get("result", {}).get("teamRankList", []) or r_data.get("result", {}).get("regularSeason", [])
        for r in rank_list:
            rankings.append({
                "rank": r.get("rank") or r.get("ranking"),
                "teamName": r.get("teamName") or r.get("name"),
                "games": r.get("gameCount") or r.get("games", 0),
                "win": r.get("winCount") or r.get("wins", 0),
                "draw": r.get("drawCount") or r.get("draws", 0),
                "lose": r.get("loseCount") or r.get("loses", 0),
                "wra": r.get("wra") or r.get("winRate", "0.000"),
                "gameDiff": r.get("gameDiff") or r.get("diff", "0.0")
            })

    # 4. KT Wiz 타자 / 투수 기록
    player_stats = {"batters": [], "pitchers": []}
    
    # 타자
    b_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/player/hitter?season={year}&teamCode=KT"
    b_data = fetch_json(b_url)
    if b_data and "result" in b_data:
        b_list = b_data.get("result", {}).get("playerRankList", []) or b_data.get("result", {}).get("list", [])
        for b in b_list[:15]:
            player_stats["batters"].append({
                "name": b.get("playerName") or b.get("name"),
                "hra": b.get("hra") or b.get("battingAvg", "-"),
                "hit": b.get("hit") or b.get("hits", "-"),
                "hr": b.get("hr") or b.get("homeRuns", "-"),
                "rbi": b.get("rbi", "-"),
                "ops": b.get("ops", "-")
            })

    # 투수
    p_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/player/pitcher?season={year}&teamCode=KT"
    p_data = fetch_json(p_url)
    if p_data and "result" in p_data:
        p_list = p_data.get("result", {}).get("playerRankList", []) or p_data.get("result", {}).get("list", [])
        for p in p_list[:15]:
            player_stats["pitchers"].append({
                "name": p.get("playerName") or p.get("name"),
                "era": p.get("era") or p.get("earnedRunAvg", "-"),
                "win": p.get("win") or p.get("wins", "-"),
                "lose": p.get("lose") or p.get("loses", "-"),
                "save": p.get("save") or p.get("saves", "-"),
                "so": p.get("kk") or p.get("strikeOuts", "-")
            })

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "playerStats": player_stats,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print("전체 데이터 수집 완료!")

if __name__ == "__main__":
    fetch_kt_wiz_data()
