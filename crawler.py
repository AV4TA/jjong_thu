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
    # 💡 한국 표준시(KST: UTC + 9시간)
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    year = today_kst.year
    today_str = today_kst.strftime("%Y-%m-%d")
    start_date = f"{year}-03-28"  # 📌 정규시즌 시작일 (시범경기 완전 제외)

    team_map = {
        'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠',
        '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈',
        'SS': '삼성 라이온즈', 'OB': '두산 베어스', 'HT': 'KIA 타이거즈',
        'HH': '한화 이글스', 'LT': '롯데 자이언츠', 'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'
    }

    def get_team_name(code_or_name):
        return team_map.get(code_or_name, code_or_name or "알수없음")

    # 10개 구단 정규시즌 통계 초기화
    kbo_teams = [
        'kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈',
        '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈'
    ]
    stats = {t: {"W": 0, "L": 0, "D": 0, "G": 0} for t in kbo_teams}

    # 1. 정규시즌 전 경기 일정 수집 (네이버 API)
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={start_date}&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            # 3월 28일 이전 및 시범경기 제외
            if game_date < start_date or "시범" in str(g.get("categoryName", "")) or str(g.get("leagueType", "")) == "DEMONSTRATION":
                continue

            home_raw = g.get("homeTeamName") or g.get("homeTeamCode", "")
            away_raw = g.get("awayTeamName") or g.get("awayTeamCode", "")
            home = get_team_name(home_raw)
            away = get_team_name(away_raw)

            home_score = g.get("homeTeamScore")
            away_score = g.get("awayTeamScore")
            status = g.get("status", "")
            status_code = g.get("statusCode", "")

            has_score = (home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != "")
            is_finished = (status_code in ['RESULT', 'END'] or has_score) and ("취소" not in status and status_code != "CANCEL")

            # 🏆 10개 구단 정규시즌 승/무/패 직접 집계
            if is_finished:
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
                            stats[home]["D"] += 1
                            stats[away]["D"] += 1
                except Exception:
                    pass

            # KT 위즈 경기 분기
            is_kt_home = (home == 'kt wiz' or "KT" in str(home_raw))
            is_kt_away = (away == 'kt wiz' or "KT" in str(away_raw))

            if is_kt_home or is_kt_away:
                is_home = is_kt_home
                opp_name = away if is_home else home
                stadium = "수원 위즈파크 (홈)" if is_home else f"{g.get('stadium', '원정구장')} (원정)"
                game_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in status or status_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif is_finished:
                    try:
                        kt_score = int(home_score if is_home else away_score)
                        opp_score = int(away_score if is_home else home_score)
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
                    "isHome": is_home,
                    "stadium": stadium,
                    "result": res_type,
                    "score": score_str
                }

                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = game_obj

    # 2. 📊 KBO 공식 룰 순위 & 게임차 직접 계산 (승률 = 승 / (승 + 패))
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

    print(f"✅ 수집 완료 ({today_str} 기준): 오늘 경기 {'있음' if today_game_info else '없음/휴식일'} | 정규시즌 순위 10개 구단 직접 계산 완료")

if __name__ == "__main__":
    fetch_kt_wiz_data()
