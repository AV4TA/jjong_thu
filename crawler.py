import json
import datetime
import urllib.request

def fetch_json(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://m.sports.naver.com/'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"API 요청 실패 [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 2026 정규시즌 전체 일정 (3월 28일 개막전부터)
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    # 전체 10개 구단 순위 자동 계산용 딕셔너리
    all_teams = ['LG', 'SSG', '두산', 'KIA', '삼성', '롯데', '한화', 'NC', '키움', 'KT']
    standings_calc = {t: {"teamName": team_map[t], "games": 0, "win": 0, "draw": 0, "lose": 0} for t in all_teams}

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            if game_date < f"{year}-03-28":
                continue

            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")
            home_code = g.get("homeTeamCode", "")
            away_code = g.get("awayTeamCode", "")
            home_score = g.get("homeTeamScore")
            away_score = g.get("awayTeamScore")
            status = g.get("status", "")
            status_code = g.get("statusCode", "")

            # [A] 10개 구단 전체 전적 집계 (순위 산출)
            if home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != "":
                h_team = home_code if home_code in standings_calc else next((k for k in all_teams if k in home), None)
                a_team = away_code if away_code in standings_calc else next((k for k in all_teams if k in away), None)
                
                if h_team and a_team:
                    h_sc = int(home_score)
                    a_sc = int(away_score)
                    standings_calc[h_team]["games"] += 1
                    standings_calc[a_team]["games"] += 1

                    if h_sc > a_sc:
                        standings_calc[h_team]["win"] += 1
                        standings_calc[a_team]["lose"] += 1
                    elif h_sc < a_sc:
                        standings_calc[a_team]["win"] += 1
                        standings_calc[h_team]["lose"] += 1
                    else:
                        standings_calc[h_team]["draw"] += 1
                        standings_calc[a_team]["draw"] += 1

            # [B] kt wiz 일정 필터링
            if "KT" in home or "KT" in away or home_code == "KT" or away_code == "KT":
                is_home = ("KT" in home) or (home_code == "KT")
                opp_raw = away if is_home else home
                opp_name = team_map.get(opp_raw, opp_raw)
                stadium = g.get("stadium", "수원 케이티위즈파크" if is_home else "원정구장")
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

    # 2. 정규시즌 공식 순위 계산 (승률순 -> 다승순 정렬)
    rankings_list = []
    for team_code, data in standings_calc.items():
        total_decided = data["win"] + data["lose"]
        win_rate = (data["win"] / total_decided) if total_decided > 0 else 0.0
        rankings_list.append({
            "teamName": data["teamName"],
            "games": data["games"],
            "win": data["win"],
            "draw": data["draw"],
            "lose": data["lose"],
            "wra_num": win_rate,
            "wra": f"{win_rate:.3f}"
        })

    rankings_list.sort(key=lambda x: (x["wra_num"], x["win"]), reverse=True)

    final_rankings = []
    top_w = rankings_list[0]["win"] if rankings_list else 0
    top_l = rankings_list[0]["lose"] if rankings_list else 0

    for i, r in enumerate(rankings_list):
        diff = ((top_w - r["win"]) + (r["lose"] - top_l)) / 2.0
        final_rankings.append({
            "rank": str(i + 1),
            "teamName": r["teamName"],
            "games": r["games"],
            "win": r["win"],
            "draw": r["draw"],
            "lose": r["lose"],
            "wra": r["wra"],
            "gameDiff": "0.0" if i == 0 else f"{diff:.1f}"
        })

    # 3. 오늘 선발 라인업
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_team = l_data.get("result", {}).get("gameInfo", {}).get("homeTeamCode", "")
            is_kt_home = (home_team == "KT")
            target_lineup = l_data.get("result", {}).get("lineup", {}).get("home" if is_kt_home else "away", {})
            pitcher_name = target_lineup.get("starterPitcher", {}).get("name", "미발표")
            today_lineup = {
                "pitcher": pitcher_name,
                "batters": [{"order": b.get("order", "-"), "name": b.get("name", "-"), "pos": b.get("pos", "-")} for b in target_lineup.get("batters", [])]
            }

    # 4. KT Wiz 현재 시즌 실제 선수단 기록 (네이버 최신 API 자동 수집)
    player_stats = {"batters": [], "pitchers": []}
    
    # 타자
    b_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/player/hitter?season={year}&teamCode=KT"
    b_data = fetch_json(b_url)
    if b_data and "result" in b_data:
        b_list = b_data.get("result", {}).get("playerRankList", []) or b_data.get("result", {}).get("list", [])
        for b in b_list[:15]:
            player_stats["batters"].append({
                "name": b.get("playerName") or b.get("name", "-"),
                "hra": str(b.get("hra") or b.get("battingAvg", "-")),
                "hit": str(b.get("hit") or b.get("hits", "-")),
                "hr": str(b.get("hr") or b.get("homeRuns", "-")),
                "rbi": str(b.get("rbi", "-")),
                "ops": str(b.get("ops", "-"))
            })

    # 투수
    p_url = f"https://api-gw.sports.naver.com/baseball/kbo/ranking/player/pitcher?season={year}&teamCode=KT"
    p_data = fetch_json(p_url)
    if p_data and "result" in p_data:
        p_list = p_data.get("result", {}).get("playerRankList", []) or p_data.get("result", {}).get("list", [])
        for p in p_list[:15]:
            player_stats["pitchers"].append({
                "name": p.get("playerName") or p.get("name", "-"),
                "era": str(p.get("era") or p.get("earnedRunAvg", "-")),
                "win": str(p.get("win") or p.get("wins", "-")),
                "lose": str(p.get("lose") or p.get("loses", "-")),
                "save": str(p.get("save") or p.get("saves", "-")),
                "so": str(p.get("kk") or p.get("strikeOuts", "-"))
            })

    # 최종 JSON 파일 구성 (rankings 누락 방지)
    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": final_rankings,
        "playerStats": player_stats,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"수집 성공: 일정 {len(kt_schedule)}개, 리그 순위 {len(final_rankings)}팀, 타자 {len(player_stats['batters'])}명, 투수 {len(player_stats['pitchers'])}명")

if __name__ == "__main__":
    fetch_kt_wiz_data()
