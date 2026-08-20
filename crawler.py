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

def fetch_kt_wiz_games_and_results():
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

    # 3월 28일부터 전체 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={regular_season_start}&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_info = None

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            # 3월 28일 이전 및 시범경기 제외
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

            is_canceled = ("취소" in status or status_code in ["CANCEL", "POSTPONE"])
            is_really_finished = (status_code in ['RESULT', 'END'] or "종료" in status) and not is_canceled
            has_valid_scores = (home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != "")

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
                    today_game_info = game_obj

    # baseball.json 파일로 저장
    final_payload = {
        "updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_info,
        "schedule": kt_schedule
    }

    with open("baseball.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ KT wiz 전체 일정 및 결과 수집 완료! 총 경기 수: {len(kt_schedule)}개 (저장 파일: baseball.json)")

if __name__ == "__main__":
    fetch_kt_wiz_games_and_results()
