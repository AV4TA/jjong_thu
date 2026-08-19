import json
import urllib.request
import datetime

def get_data(url):
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
        print(f"Request Error [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst_tz)
    year = now.year
    today_str = now.strftime("%Y-%m-%d")
    start_date = f"{year}-03-28"  # 정규시즌 개막일

    team_map = {
        'KT': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠',
        '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈',
        'SS': '삼성 라이온즈', 'OB': '두산 베어스', 'HT': 'KIA 타이거즈',
        'HH': '한화 이글스', 'LT': '롯데 자이언츠', 'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'
    }

    # 1. 🏆 KBO 공식 실시간 순위표 수집
    rankings = []
    rank_url = "https://api-gw.sports.naver.com/baseball/kbo/ranking/team"
    r_res = get_data(rank_url)

    if r_res and "result" in r_res:
        raw_ranks = r_res["result"].get("teamRankList", []) or r_res["result"].get("regularSeason", [])
        for item in raw_ranks:
            raw_name = item.get("teamName") or item.get("name", "")
            t_name = team_map.get(raw_name, raw_name)
            
            rankings.append({
                "rank": str(item.get("rank") or item.get("ranking", "-")),
                "teamName": t_name,
                "games": str(item.get("gameCount") or item.get("games", 0)),
                "win": str(item.get("winCount") or item.get("wins", 0)),
                "draw": str(item.get("drawCount") or item.get("draws", 0)),
                "lose": str(item.get("loseCount") or item.get("loses", 0)),
                "wra": str(item.get("wra") or item.get("winRate", "0.000")),
                "gameDiff": str(item.get("gameDiff") or item.get("diff", "0.0"))
            })

    # 2. 📅 정규시즌 전 경기 일정 & KT 경기 파싱 (시범경기 완전 제외)
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={start_date}&toDate={year}-12-31&size=1000"
    s_res = get_data(sched_url)

    kt_schedule = {}
    today_game_obj = None
    h2h_tracker = {}

    if s_res and "result" in s_res:
        games = s_res["result"].get("games", [])
        for g in games:
            raw_dt = g.get("gameDateTime", "")
            g_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]
            
            # 3월 28일 이전 및 시범경기 제외
            if g_date < start_date or "시범" in g.get("categoryName", ""):
                continue

            h_code = g.get("homeTeamCode", "")
            a_code = g.get("awayTeamCode", "")
            h_raw = g.get("homeTeamName", "")
            a_raw = g.get("awayTeamName", "")
            
            home_team = team_map.get(h_code, team_map.get(h_raw, h_raw))
            away_team = team_map.get(a_code, team_map.get(a_raw, a_raw))

            is_kt_home = (h_code == "KT" or "KT" in h_raw)
            is_kt_away = (a_code == "KT" or "KT" in a_raw)

            if is_kt_home or is_kt_away:
                opp_team = away_team if is_kt_home else home_team
                stadium = "수원 위즈파크 (홈)" if is_kt_home else f"{g.get('stadium', '원정구장')} (원정)"
                g_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                h_score = g.get("homeTeamScore")
                a_score = g.get("awayTeamScore")
                st_code = g.get("statusCode", "")
                st_txt = g.get("status", "")

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in st_txt or st_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif st_code in ['RESULT', 'END'] or (h_score is not None and a_score is not None and str(h_score) != ""):
                    try:
                        kt_s = int(h_score if is_kt_home else a_score)
                        opp_s = int(a_score if is_kt_home else h_score)
                        score_str = f"KT {kt_s} : {opp_s} {opp_team.split(' ')[0]}"
                        
                        if opp_team not in h2h_tracker:
                            h2h_tracker[opp_team] = {"W": 0, "L": 0, "D": 0}

                        if kt_s > opp_s:
                            res_type = "win"
                            h2h_tracker[opp_team]["W"] += 1
                        elif kt_s < opp_s:
                            res_type = "lose"
                            h2h_tracker[opp_team]["L"] += 1
                        else:
                            res_type = "draw"
                            h2h_tracker[opp_team]["D"] += 1
                    except:
                        pass

                # 선발투수 이름 추출
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

    # 3. ⚔️ 오늘 상대전적 요약
    today_h2h = {"text": "올 시즌 맞대결 기록 집계 중", "record": "-"}
    if today_game_obj:
        opp = today_game_obj["opponent"]
        if opp in h2h_tracker:
            stat = h2h_tracker[opp]
            tot = stat["W"] + stat["L"] + stat["D"]
            if tot > 0:
                d_txt = f"{stat['D']}무 " if stat['D'] > 0 else ""
                today_h2h = {
                    "text": f"올시즌 {tot}전 {stat['W']}승 {d_txt}{stat['L']}패",
                    "record": f"{stat['W']}승 {d_txt}{stat['L']}패"
                }
            else:
                today_h2h = {"text": "올 시즌 첫 맞대결", "record": "0승 0패"}
        else:
            today_h2h = {"text": "올 시즌 첫 맞대결", "record": "0승 0패"}

    # 4. ⚾ 오늘 라인업 & 확정 선발투수 갱신
    today_lineup = {
        "ktPitcher": today_game_obj.get("ktPitcher", "미정") if today_game_obj else "미정",
        "oppPitcher": today_game_obj.get("oppPitcher", "미정") if today_game_obj else "미정",
        "pitcher": today_game_obj.get("ktPitcher", "미정") if today_game_obj else "미정",
        "batters": []
    }

    if today_game_obj and today_game_obj.get("gameId"):
        r_url = f"https://api-gw.sports.naver.com/schedule/games/{today_game_obj['gameId']}/relay"
        r_res = get_data(r_url)
        if r_res and "result" in r_res:
            l_root = r_res["result"].get("lineup", {})
            is_h = today_game_obj["isHome"]
            kt_l = l_root.get("home" if is_h else "away", {})
            opp_l = l_root.get("away" if is_h else "home", {})

            kt_sp = kt_l.get("starterPitcher", {}).get("name")
            opp_sp = opp_l.get("starterPitcher", {}).get("name")
            if kt_sp: today_lineup["ktPitcher"] = kt_sp; today_lineup["pitcher"] = kt_sp
            if opp_sp: today_lineup["oppPitcher"] = opp_sp

            batters = kt_l.get("batters", [])
            if batters:
                today_lineup["batters"] = [
                    {"order": b.get("order", "-"), "name": b.get("name", "-"), "pos": b.get("pos", "-")}
                    for b in batters
                ]

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

    print(f"✅ 동기화 완료: 순위 {len(rankings)}팀 | 오늘경기: {'있음' if today_game_obj else '휴식일'} | 선발: {today_lineup['ktPitcher']} vs {today_lineup['oppPitcher']}")

if __name__ == "__main__":
    fetch_kt_wiz_data()
