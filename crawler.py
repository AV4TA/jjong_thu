import json
import urllib.request
import re
import datetime

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"JSON Request Error [{url}]: {e}")
        return None

def fetch_kbo_mobile_starters():
    """KBO 공식 모바일 페이지(m.koreabaseball.com)에서 오늘 KT 경기 예고 선발투수 직접 스크래핑"""
    url = "https://m.koreabaseball.com/"
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode('utf-8', errors='ignore')
            match_blocks = re.findall(r'<li[^>]*>(.*?)</li>', html, re.DOTALL)
            for block in match_blocks:
                if 'KT' in block or 'kt' in block:
                    pitchers = re.findall(r'선발\s*[:：]?\s*([가-힣a-zA-Z]+)', block)
                    if len(pitchers) >= 2:
                        return {"p1": pitchers[0].strip(), "p2": pitchers[1].strip()}
    except Exception as e:
        print(f"KBO 모바일 선발투수 파싱 예외: {e}")
    return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst_tz)
    year = now.year
    today_str = now.strftime("%Y-%m-%d")

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
    h2h_tracker = {t: {"W": 0, "L": 0, "D": 0} for t in kbo_teams}

    # 1. 📅 1년치 KBO 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-01&toDate={year}-11-30&size=1000"
    s_res = fetch_json(sched_url)

    kt_schedule = {}
    today_game_obj = None

    if s_res and "result" in s_res:
        games = s_res["result"].get("games", [])
        for g in games:
            raw_dt = g.get("gameDateTime", "")
            g_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            cat_name = str(g.get("categoryName", ""))
            title = str(g.get("title", ""))
            l_type = str(g.get("leagueType", ""))

            # 🚫 시범경기만 정확하게 제외 (정규시즌만 허용)
            if "시범" in cat_name or "시범" in title or l_type in ["DEMONSTRATION", "EXHIBITION"]:
                continue

            home_raw = g.get("homeTeamName") or g.get("homeTeamCode", "")
            away_raw = g.get("awayTeamName") or g.get("awayTeamCode", "")
            home_team = get_team_name(home_raw)
            away_team = get_team_name(away_raw)

            home_score_val = g.get("homeTeamScore")
            away_score_val = g.get("awayTeamScore")
            st_code = g.get("statusCode", "")
            st_txt = g.get("status", "")

            has_score = (home_score_val is not None and away_score_val is not None and str(home_score_val) != "" and str(away_score_val) != "")
            is_finished = (st_code in ['RESULT', 'END'] or has_score) and ("취소" not in st_txt and st_code != "CANCEL")

            # 🏆 10개 구단 정규시즌 승패 집계
            if is_finished:
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
                g_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in st_txt or st_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif is_finished:
                    try:
                        kt_s = int(home_score_val if is_kt_home else away_score_val)
                        opp_s = int(away_score_val if is_kt_home else home_score_val)
                        score_str = f"KT {kt_s} : {opp_s} {opp_team.split(' ')[0]}"

                        if opp_team in h2h_tracker:
                            if kt_s > opp_s:
                                res_type = "win"
                                h2h_tracker[opp_team]["W"] += 1
                            elif kt_s < opp_s:
                                res_type = "lose"
                                h2h_tracker[opp_team]["L"] += 1
                            else:
                                res_type = "draw"
                                h2h_tracker[opp_team]["D"] += 1
                    except Exception:
                        pass

                kt_pitcher = g.get("homeStarterPitcherName" if is_kt_home else "awayStarterPitcherName") or g.get("homeStarterName" if is_kt_home else "awayStarterName") or "미정"
                opp_pitcher = g.get("awayStarterPitcherName" if is_kt_home else "homeStarterPitcherName") or g.get("awayStarterName" if is_kt_home else "homeStarterName") or "미정"

                game_entry = {
                    "gameId": g.get("gameId"),
                    "date": g_date,
                    "time": g_time,
                    "opponent": opp_team,
                    "isHome": is_kt_home,
                    "stadium": stadium,
                    "result": res_type,
                    "score": score_str,
                    "ktPitcher": kt_pitcher,
                    "oppPitcher": opp_pitcher
                }

                kt_schedule[g_date] = game_entry
                if g_date == today_str:
                    today_game_obj = game_entry

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

    # 3. ⚔️ 오늘 상대전적
    today_h2h = {"text": "올 시즌 맞대결 기록 없음", "record": "-"}
    if today_game_obj:
        opp = today_game_obj["opponent"]
        if opp in h2h_tracker:
            st = h2h_tracker[opp]
            tot = st["W"] + st["L"] + st["D"]
            if tot > 0:
                d_txt = f"{st['D']}무 " if st['D'] > 0 else ""
                today_h2h = {
                    "text": f"올시즌 {tot}전 {st['W']}승 {d_txt}{st['L']}패",
                    "record": f"{st['W']}승 {d_txt}{st['L']}패"
                }
            else:
                today_h2h = {"text": "올 시즌 첫 맞대결", "record": "0승 0패"}

    # 4. ⚾ 선발투수 2중 보강 (KBO 모바일 스크래핑)
    today_lineup = {
        "ktPitcher": today_game_obj.get("ktPitcher", "미정") if today_game_obj else "미정",
        "oppPitcher": today_game_obj.get("oppPitcher", "미정") if today_game_obj else "미정",
        "pitcher": today_game_obj.get("ktPitcher", "미정") if today_game_obj else "미정",
        "batters": []
    }

    if today_game_obj and (today_lineup["ktPitcher"] == "미정" or today_lineup["oppPitcher"] == "미정"):
        kbo_mobile_p = fetch_kbo_mobile_starters()
        if kbo_mobile_p:
            if today_game_obj["isHome"]:
                today_lineup["oppPitcher"] = kbo_mobile_p["p1"]
                today_lineup["ktPitcher"] = kbo_mobile_p["p2"]
                today_lineup["pitcher"] = kbo_mobile_p["p2"]
            else:
                today_lineup["ktPitcher"] = kbo_mobile_p["p1"]
                today_lineup["pitcher"] = kbo_mobile_p["p1"]
                today_lineup["oppPitcher"] = kbo_mobile_p["p2"]

    # 5. 최종 JSON 출력
    final_payload = {
        "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_obj,
        "todayH2H": today_h2h,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ [동기화 완료] 순위: {len(rankings)}팀 정규시즌 계산 완료 | KT경기 수: {len(kt_schedule)}개 | 오늘: {today_game_obj['opponent'] if today_game_obj else '경기 없음'}")

if __name__ == "__main__":
    fetch_kt_wiz_data()
