import json
import datetime
import urllib.request

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://m.sports.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"API 호출 실패 [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 2026 시즌 전체 일정 (일정 불러온 방식 그대로)
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
                raw_dt = g.get("gameDateTime", "")
                game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]
                is_home = ("KT" in home) or (home_code == "KT")
                opp_raw = away if is_home else home
                opp_name = team_map.get(opp_raw, opp_raw)
                stadium = g.get("stadium", "수원 케이티위즈파크" if is_home else "원정구장")
                
                home_score = g.get("homeTeamScore")
                away_score = g.get("awayTeamScore")
                status = g.get("status", "")
                status_code = g.get("statusCode", "")
                game_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in status or status_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != "":
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

    # 2. 오늘 경기 선발 라인업
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_team = l_data.get("result", {}).get("gameInfo", {}).get("homeTeamCode", "")
            is_kt_home = (home_team == "KT")
            target_lineup = l_data.get("result", {}).get("lineup", {}).get("home" if is_kt_home else "away", {})
            
            pitcher_info = target_lineup.get("starterPitcher", {})
            pitcher_name = pitcher_info.get("name") if isinstance(pitcher_info, dict) else "-"
            
            batters_list = []
            for b in target_lineup.get("batters", []):
                batters_list.append({
                    "order": b.get("order", "-"),
                    "name": b.get("name", "-"),
                    "pos": b.get("pos", "-")
                })

            today_lineup = {
                "pitcher": pitcher_name or "미발표",
                "batters": batters_list
            }

    # 3. KBO 리그 순위 (일정 API와 동일한 sports.naver.com 공식 체계)
    rankings = []
    rank_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/team?season={year}"
    r_data = fetch_json(rank_url)
    if r_data and "result" in r_data:
        r_list = r_data.get("result", {}).get("teamRankList", []) or r_data.get("result", {}).get("list", [])
        for r in r_list:
            rankings.append({
                "rank": r.get("rank") or r.get("ranking", "-"),
                "teamName": r.get("teamName") or r.get("name", "-"),
                "games": r.get("gameCount") or r.get("games", 0),
                "win": r.get("winCount") or r.get("wins", 0),
                "draw": r.get("drawCount") or r.get("draws", 0),
                "lose": r.get("loseCount") or r.get("loses", 0),
                "wra": str(r.get("wra") or r.get("winRate", "0.000")),
                "gameDiff": str(r.get("gameDiff") or r.get("diff", "0.0"))
            })

    # 4. KT Wiz 선수 기록 (Daum 스포츠 JSONP 공식 API - 차단 없고 안정적)
    player_stats = {"batters": [], "pitchers": []}
    
    # 타자 기록
    b_url = f"https://score.sports.media.daum.net/plan/do/kbo/record_team_individual.json?season={year}&team_id=KT&category=hitter"
    b_data = fetch_json(b_url)
    if b_data and "list" in b_data:
        for b in b_data.get("list", [])[:15]:
            player_stats["batters"].append({
                "name": b.get("name", "-"),
                "hra": b.get("hra", "-"),
                "hit": b.get("hit", "-"),
                "hr": b.get("hr", "-"),
                "rbi": b.get("rbi", "-"),
                "ops": b.get("ops", "-")
            })

    # 투수 기록
    p_url = f"https://score.sports.media.daum.net/plan/do/kbo/record_team_individual.json?season={year}&team_id=KT&category=pitcher"
    p_data = fetch_json(p_url)
    if p_data and "list" in p_data:
        for p in p_data.get("list", [])[:15]:
            player_stats["pitchers"].append({
                "name": p.get("name", "-"),
                "era": p.get("era", "-"),
                "win": p.get("w", "-"),
                "lose": p.get("l", "-"),
                "save": p.get("sv", "-"),
                "so": p.get("so", "-")
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

    print(f"완료: 일정 {len(kt_schedule)}개, 순위 {len(rankings)}팀, 타자 {len(player_stats['batters'])}명, 투수 {len(player_stats['pitchers'])}명")

if __name__ == "__main__":
    fetch_kt_wiz_data()
