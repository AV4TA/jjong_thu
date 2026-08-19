import json
import urllib.request
import datetime

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://m.sports.naver.com/',
            'Accept': 'application/json, text/plain, */*'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst_tz)
    year = today_kst.year
    start_date = f"{year}-03-28"  # 정규시즌 시작일 (시범경기 완전 제외)
    today_str = today_kst.strftime("%Y-%m-%d")

    team_map = {
        'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠',
        '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈',
        'SS': '삼성 라이온즈', 'OB': '두산 베어스', 'HT': 'KIA 타이거즈',
        'HH': '한화 이글스', 'LT': '롯데 자이언츠', 'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'
    }

    def get_team_name(code_or_name):
        return team_map.get(code_or_name, code_or_name or "알수없음")

    kbo_teams = [
        'kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈',
        '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈'
    ]
    stats = {t: {"W": 0, "L": 0, "D": 0, "G": 0} for t in kbo_teams}

    # 1. 정규시즌 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={start_date}&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_raw = None
    today_game_info = None

    # 상대팀별 KT 전적 집계용 딕셔너리 {'한화 이글스': {'W': 0, 'L': 0, 'D': 0}}
    h2h_stats = {t: {"W": 0, "L": 0, "D": 0} for t in kbo_teams}

    if s_data and "result" in s_data:
        games = s_data.get("result", {}).get("games", [])
        for g in games:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            # 3월 28일 이전(시범경기) 제외
            if game_date < start_date:
                continue

            home_raw = g.get("homeTeamName") or g.get("homeTeamCode", "")
            away_raw = g.get("awayTeamName") or g.get("awayTeamCode", "")
            home_team = get_team_name(home_raw)
            away_team = get_team_name(away_raw)

            home_score_val = g.get("homeTeamScore")
            away_score_val = g.get("awayTeamScore")
            status_code = g.get("statusCode", "")
            status_text = g.get("status", "")

            has_score = (home_score_val is not None and away_score_val is not None and str(home_score_val) != "" and str(away_score_val) != "")
            is_finished = status_code in ['RESULT', 'END'] or has_score

            # 전체 리그 순위 계산용 통계 누적
            if is_finished and "취소" not in status_text and status_code != "CANCEL":
                try:
                    h_score = int(home_score_val)
                    a_score = int(away_score_val)
                    if home_team in stats and away_team in stats:
                        stats[home_team]["G"] += 1
                        stats[away_team]["G"] += 1
                        if h_score > a_score:
                            stats[home_team]["W"] += 1
                            stats[away_team]["L"] += 1
                        elif h_score < a_score:
                            stats[home_team]["L"] += 1
                            stats[away_team]["W"] += 1
                        else:
                            stats[home_team]["D"] += 1
                            stats[away_team]["D"] += 1
                except Exception:
                    pass

            # KT 위즈 경기 처리
            is_kt_home = (home_team == 'kt wiz' or "KT" in str(home_raw))
            is_kt_away = (away_team == 'kt wiz' or "KT" in str(away_raw))

            if is_kt_home or is_kt_away:
                opp_team = away_team if is_kt_home else home_team
                stadium = "수원 위즈파크 (홈)" if is_kt_home else f"{g.get('stadium', '원정구장')} (원정)"
                game_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in status_text or status_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif is_finished:
                    try:
                        kt_s = int(home_score_val if is_kt_home else away_score_val)
                        opp_s = int(away_score_val if is_kt_home else home_score_val)
                        score_str = f"KT {kt_s} : {opp_s} {opp_team.split(' ')[0]}"
                        if kt_s > opp_s:
                            res_type = "win"
                            if opp_team in h2h_stats: h2h_stats[opp_team]["W"] += 1
                        elif kt_s < opp_s:
                            res_type = "lose"
                            if opp_team in h2h_stats: h2h_stats[opp_team]["L"] += 1
                        else:
                            res_type = "draw"
                            if opp_team in h2h_stats: h2h_stats[opp_team]["D"] += 1
                    except Exception:
                        pass

                # 선발투수 파싱 (일정 기본값 추출)
                kt_pitcher = g.get("homeStarterPitcherName") if is_kt_home else g.get("awayStarterPitcherName")
                opp_pitcher = g.get("awayStarterPitcherName") if is_kt_home else g.get("homeStarterPitcherName")

                game_obj = {
                    "gameId": g.get("gameId"),
                    "date": game_date,
                    "time": game_time,
                    "opponent": opp_team,
                    "isHome": is_kt_home,
                    "stadium": stadium,
                    "result": res_type,
                    "score": score_str,
                    "ktPitcher": kt_pitcher or "미정",
                    "oppPitcher": opp_pitcher or "미정"
                }

                kt_schedule[game_date] = game_obj
                if game_date == today_str:
                    today_game_raw = g
                    today_game_info = game_obj

    # 2. 오늘 경기 상대 전적 계산
    today_h2h = {"text": "올 시즌 첫 맞대결", "record": "0승 0패"}
    if today_game_info:
        opp_name = today_game_info["opponent"]
        if opp_name in h2h_stats:
            rec = h2h_stats[opp_name]
            total_h2h_g = rec["W"] + rec["L"] + rec["D"]
            if total_h2h_g > 0:
                d_str = f"{rec['D']}무 " if rec["D"] > 0 else ""
                today_h2h = {
                    "text": f"올시즌 {total_h2h_g}전 {rec['W']}승 {d_str}{rec['L']}패",
                    "record": f"{rec['W']}승 {d_str}{rec['L']}패",
                    "wins": rec["W"],
                    "loses": rec["L"],
                    "draws": rec["D"]
                }

    # 3. 오늘 상세 라인업 보강
    today_lineup = {
        "ktPitcher": today_game_info.get("ktPitcher", "미정") if today_game_info else "미정",
        "oppPitcher": today_game_info.get("oppPitcher", "미정") if today_game_info else "미정",
        "pitcher": today_game_info.get("ktPitcher", "미정") if today_game_info else "미정",
        "batters": []
    }

    if today_game_raw and today_game_raw.get("gameId"):
        g_id = today_game_raw.get("gameId")
        l_url = f"https://api-gw.sports.naver.com/schedule/games/{g_id}/relay"
        l_data = fetch_json(l_url)
        if l_data and "result" in l_data:
            home_code = l_data.get("result", {}).get("gameInfo", {}).get("homeTeamCode", "")
            is_kt_h = (home_code == "KT")
            lineup_root = l_data.get("result", {}).get("lineup", {})
            kt_lineup = lineup_root.get("home" if is_kt_h else "away", {})
            opp_lineup = lineup_root.get("away" if is_kt_h else "home", {})

            # 릴레이 데이터에 선발투수가 있으면 갱신
            p_kt = kt_lineup.get("starterPitcher", {}).get("name")
            p_opp = opp_lineup.get("starterPitcher", {}).get("name")
            if p_kt: today_lineup["ktPitcher"] = p_kt; today_lineup["pitcher"] = p_kt
            if p_opp: today_lineup["oppPitcher"] = p_opp

            batters = kt_lineup.get("batters", [])
            if batters:
                today_lineup["batters"] = [
                    {"order": b.get("order", "-"), "name": b.get("name", "-"), "pos": b.get("pos", "-")}
                    for b in batters
                ]

    # 4. 순위 정렬 및 게임차 계산 (KBO 공식 룰)
    def calc_wra(w, l):
        total = w + l
        return (w / total) if total > 0 else 0.0

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

    # 5. 최종 JSON 출력
    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_info,
        "todayH2H": today_h2h,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ [동기화 완료] 오늘 경기: {today_game_info['opponent'] if today_game_info else '휴식일'} | 선발: {today_lineup['ktPitcher']} vs {today_lineup['oppPitcher']} | 상대전적: {today_h2h['text']}")

if __name__ == "__main__":
    fetch_kt_wiz_data()
