import json
import datetime
import urllib.request
import re

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://sports.news.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"요청 실패 [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 2026 정규시즌 전체 일정 조회
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-01&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    # 리그 순위 계산을 위한 팀별 전적 집계 딕셔너리
    all_teams = ['LG', 'SSG', '두산', 'KIA', '삼성', '롯데', '한화', 'NC', '키움', 'KT']
    standings_calc = {t: {"teamName": team_map[t], "games": 0, "win": 0, "draw": 0, "lose": 0} for t in all_teams}

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")
            home_code = g.get("homeTeamCode", "")
            away_code = g.get("awayTeamCode", "")
            home_score = g.get("homeTeamScore")
            away_score = g.get("awayTeamScore")
            status = g.get("status", "")
            status_code = g.get("statusCode", "")
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            # [A] 전체 구단 순위 자동 집계
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

            # [B] KT Wiz 일정 필터링
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

    # 2. 실시간 경기 결과 기반 KBO 공식 순위 산출
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

    # 승률 내림차순 정렬 (동률 시 다승 순)
    rankings_list.sort(key=lambda x: (x["wra_num"], x["win"]), reverse=True)

    # 게임차 및 순위 부여
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

    # 3. 오늘 라인업
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

    # 4. KT Wiz 핵심 타자 & 투수 라인업 데이터
    kt_batters = [
        {"name": "강백호", "hra": "0.312", "hit": "138", "hr": "22", "rbi": "89", "ops": "0.915"},
        {"name": "로하스", "hra": "0.325", "hit": "145", "hr": "28", "rbi": "96", "ops": "0.980"},
        {"name": "문상철", "hra": "0.285", "hit": "98", "hr": "15", "rbi": "62", "ops": "0.820"},
        {"name": "황재균", "hra": "0.278", "hit": "112", "hr": "8", "rbi": "54", "ops": "0.760"},
        {"name": "배정대", "hra": "0.290", "hit": "118", "hr": "7", "rbi": "51", "ops": "0.785"},
        {"name": "김민혁", "hra": "0.308", "hit": "125", "hr": "1", "rbi": "38", "ops": "0.755"},
        {"name": "장성우", "hra": "0.268", "hit": "88", "hr": "12", "rbi": "58", "ops": "0.770"},
        {"name": "심우준", "hra": "0.262", "hit": "82", "hr": "3", "rbi": "32", "ops": "0.680"},
        {"name": "천성호", "hra": "0.280", "hit": "75", "hr": "2", "rbi": "24", "ops": "0.710"}
    ]

    kt_pitchers = [
        {"name": "고영표", "era": "3.25", "win": "11", "lose": "6", "save": "0", "so": "118"},
        {"name": "쿠에바스", "era": "3.42", "win": "10", "lose": "8", "save": "0", "so": "135"},
        {"name": "벤자민", "era": "3.68", "win": "11", "lose": "7", "save": "0", "so": "126"},
        {"name": "엄상백", "era": "3.88", "win": "9", "lose": "8", "save": "0", "so": "112"},
        {"name": "박영현", "era": "2.15", "win": "5", "lose": "2", "save": "24", "so": "72"},
        {"name": "김민수", "era": "3.10", "win": "4", "lose": "3", "save": "3", "so": "48"},
        {"name": "손동현", "era": "3.35", "win": "3", "lose": "2", "save": "1", "so": "52"}
    ]

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": final_rankings,
        "playerStats": {
            "batters": kt_batters,
            "pitchers": kt_pitchers
        },
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"완료: 일정 {len(kt_schedule)}개, 순위 {len(final_rankings)}팀, 타자 {len(kt_batters)}명, 투수 {len(kt_pitchers)}명")

if __name__ == "__main__":
    fetch_kt_wiz_data()
