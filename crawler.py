import json
import datetime
import urllib.request
import re

def fetch_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[HTML 요청 실패] {url} -> {e}")
        return None

def fetch_json(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.sports.naver.com/'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        return None

def clean_tag(txt):
    return re.sub(r'<[^>]+>', '', txt).strip()

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 2026 정규시즌 KT 일정 & 오늘 경기 (기존 잘 되던 공식 API)
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
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
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]

            if game_date < f"{year}-03-28":
                continue

            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")
            home_code = g.get("homeTeamCode", "")
            away_code = g.get("awayTeamCode", "")

            if "KT" in home or "KT" in away or home_code == "KT" or away_code == "KT":
                is_home = ("KT" in home) or (home_code == "KT")
                opp_raw = away if is_home else home
                opp_name = team_map.get(opp_raw, opp_raw)
                stadium = g.get("stadium", "수원 케이티위즈파크" if is_home else "원정구장")
                game_time = raw_dt.split("T")[1][:5] if "T" in raw_dt else "18:30"

                home_score = g.get("homeTeamScore")
                away_score = g.get("awayTeamScore")
                status = g.get("status", "")
                status_code = g.get("statusCode", "")

                res_type = "scheduled"
                score_str = "VS"

                if "취소" in status or status_code == "CANCEL":
                    res_type = "canceled"
                    score_str = "취소"
                elif status_code in ['RESULT', 'END'] or (home_score is not None and away_score is not None and str(home_score) != "" and str(away_score) != ""):
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

    # 2. 오늘 라인업
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

    # 3. KBO 공식 모바일 사이트 실시간 순위 파싱 (차단 0%)
    rankings = []
    kbo_rank_html = fetch_html("https://m.koreabaseball.com/Record/TeamRank/TeamRank.aspx")
    if kbo_rank_html:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', kbo_rank_html, re.DOTALL)
        for r in rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
            if len(tds) >= 8:
                vals = [clean_tag(t) for t in tds]
                # 순위 / 팀명 / 경기 / 승 / 패 / 무 / 승률 / 게임차
                rankings.append({
                    "rank": vals[0],
                    "teamName": vals[1],
                    "games": vals[2],
                    "win": vals[3],
                    "lose": vals[4],
                    "draw": vals[5],
                    "wra": vals[6],
                    "gameDiff": vals[7]
                })

    # 4. KBO 공식 KT Wiz 선수단 실시간 기록 파싱 (차단 0%)
    player_stats = {"batters": [], "pitchers": []}
    
    # KT 타자 순위
    kbo_hitter_html = fetch_html(f"https://m.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx?team={year}KT")
    if not kbo_hitter_html:
        kbo_hitter_html = fetch_html("https://m.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx?team=KT")
    if kbo_hitter_html:
        h_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', kbo_hitter_html, re.DOTALL)
        for r in h_rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
            if len(tds) >= 7:
                vals = [clean_tag(t) for t in tds]
                # 선수명 / 타율 / 안타 / 홈런 / 타점 / OPS 등
                player_stats["batters"].append({
                    "name": vals[1],
                    "hra": vals[2],
                    "hit": vals[7] if len(vals) > 7 else vals[4],
                    "hr": vals[9] if len(vals) > 9 else vals[5],
                    "rbi": vals[11] if len(vals) > 11 else vals[6],
                    "ops": vals[13] if len(vals) > 13 else "-"
                })

    # KT 투수 순위
    kbo_pitcher_html = fetch_html(f"https://m.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx?team={year}KT")
    if not kbo_pitcher_html:
        kbo_pitcher_html = fetch_html("https://m.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx?team=KT")
    if kbo_pitcher_html:
        p_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', kbo_pitcher_html, re.DOTALL)
        for r in p_rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
            if len(tds) >= 7:
                vals = [clean_tag(t) for t in tds]
                player_stats["pitchers"].append({
                    "name": vals[1],
                    "era": vals[2],
                    "win": vals[4] if len(vals) > 4 else vals[3],
                    "lose": vals[5] if len(vals) > 5 else vals[4],
                    "save": vals[6] if len(vals) > 6 else vals[5],
                    "so": vals[10] if len(vals) > 10 else "-"
                })

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "playerStats": {
            "batters": player_stats["batters"][:15],
            "pitchers": player_stats["pitchers"][:15]
        },
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"[수집 성공] 일정: {len(kt_schedule)}개 | 순위: {len(rankings)}팀 | 타자: {len(player_stats['batters'])}명 | 투수: {len(player_stats['pitchers'])}명")

if __name__ == "__main__":
    fetch_kt_wiz_data()
