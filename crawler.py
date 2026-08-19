import json
import datetime
import urllib.request

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://m.sports.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    year = today_kst.year
    today_str = today_kst.strftime("%Y-%m-%d")
    
    # 📌 3월 28일 정규시즌 시작일
    regular_season_start = f"{year}-03-28"

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', 
        '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    def get_team_name(code_or_name):
        return team_map.get(code_or_name, code_or_name or "알수없음")

    kbo_teams = [
        'kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈',
        '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈'
    ]
    stats = {t: {"W": 0, "L": 0, "D": 0, "G": 0} for t in kbo_teams}

    # 1. 3월 28일부터 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={regular_season_start}&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            # 🚫 3월 28일 이전 및 시범경기 제외
            if game_date < regular_season_start or "시범" in str(g.get("categoryName", "")) or str(g.get("leagueType", "")) == "DEMONSTRATION":
                continue

            home_raw = g.get("homeTeamName") or g.get("homeTeamCode", "")
            away_raw = g.get("awayTeamName") or g.get("awayTeamCode", "")
            home = get_team_name(home_raw)
            away = get_team_name(away_raw)

            home_score = g.get("homeTeamScore")
            away_score = g.get("awayTeamScore")
            status = str(g.get("status", ""))
            status_code = str(g.get("statusCode", ""))

            # 💡 [핵심] 실제로 '완전히 종료된 경기'만 엄격하게 판정
            is_canceled = ("취소" in status or status_code in ["CANCEL", "POSTPONE"])
            is_really_finished = (status_code in ['RESULT', 'END'] or "종료" in status) and not is_canceled
            has_valid_scores = (home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != "")

            # 🏆 정규시즌 공식 경기만 순위 계산에 누적
            if is_really_finished and has_valid_scores:
                try:
                    h_score = int(home_score)
                    a_score = int(away_score)

                    if home in stats and away in stats:
                        stats[home]["G"] += 1
                        stats[away]["G"] += 1
                        if h_score > a_score:
                            stats[home]["W"] += 1
                            stats[away]["L"] += 1
                        elif h_score < a_score:
                            stats[home]["L"] += 1
                            stats[away]["W"] += 1
                        else:
                            # 공식 종료된 경기에서만 무승부 인정
                            stats[home]["D"] += 1
                            stats[away]["D"] += 1
                except Exception:
                    pass

            # KT 위즈 경기 분기
            is_kt_home = (home == 'kt wiz' or "KT" in str(home_raw))
            is_kt_away = (away == 'kt wiz' or "KT" in str(away_raw))

            if is_kt_home or is_kt_away:
                opp_name = away if is_kt_home else home
                stadium = "수원 위즈파크 (홈)" if is_kt_home else f"{g.get('stadium', '원정구장')} (원정)"
                game_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if is_canceled:
                    res_type = "canceled"
                    score_str = "취소"
                elif is_really_finished and has_valid_scores:
                    try:
                        kt_score = int(home_score if is_kt_home else away_score)
                        opp_score = int(away_score if is_kt_home else home_score)
                        score_str = f"KT {kt_score} : {opp_score} {opp_name.split(' ')[0]}"
                        if kt_score > opp_score:
                            res_type = "win"
                        elif kt_score < opp_score:
                            res_type = "lose"
                        else:
                            res_type = "draw"
                    except Exception:
                        pass

                game_obj = {
                    "gameId": g.get("gameId"),
                    "date": game_date,
                    "time": game_time,
                    "opponent": opp_name,
                    "isHome": is_kt_home,
                    "stadium": stadium,
                    "result": res_type,
                    "score": score_str
                }

                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = game_obj

    # 2. 📊 순위 직접 계산 (승률 = 승 / (승 + 패))
    def calc_wra(w, l):
        tot = w + l
        return (w / tot) if tot > 0 else 0.0

    sorted_teams = sorted(
        stats.items(),
        key=lambda x: (calc_wra(x[1]["W"], x[1]["L"]), x[1]["W"]),
        reverse=True
    )

    rankings = []
    top_w = sorted_teams[0][1]["W"] if sorted_teams else 0
    top_l = sorted_teams[0][1]["L"] if sorted_teams else 0

    for i, (team, s) in enumerate(sorted_teams):
        wra = calc_wra(s["W"], s["L"])
        diff = ((top_w - s["W"]) + (s["L"] - top_l)) / 2.0
        diff_str = "0.0" if i == 0 or diff <= 0 else f"{diff:.1f}".rstrip('0').rstrip('.') if f"{diff:.1f}".endswith('.0') else f"{diff:.1f}"

        rankings.append({
            "rank": str(i + 1),
            "teamName": team,
            "games": str(s["G"]),
            "win": str(s["W"]),
            "draw": str(s["D"]),
            "lose": str(s["L"]),
            "wra": f"{wra:.3f}",
            "gameDiff": diff_str
        })

    # 3. 오늘 라인업
    today_lineup = {"pitcher": "-", "batters": []}
    if today_game_id:
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_team_code = l_data.get("result", {}).get("gameInfo", {}).get("homeTeamCode", "")
            is_kt_h = (home_team_code == "KT")
            target_lineup = l_data.get("result", {}).get("lineup", {}).get("home" if is_kt_h else "away", {})
            pitcher_name = target_lineup.get("starterPitcher", {}).get("name", "미발표")
            today_lineup = {
                "pitcher": pitcher_name,
                "batters": [{"order": b.get("order", "-"), "name": b.get("name", "-"), "pos": b.get("pos", "-")} for b in target_lineup.get("batters", [])]
            }

    # 4. JSON 파일 저장
    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ 정규시즌 정상 종료 경기만 순위 계산 완료 ({len(rankings)}팀)")

if __name__ == "__main__":
    fetch_kt_wiz_data()
