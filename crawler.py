import json
import datetime
import urllib.request
import re

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

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

def fetch_kbo_rankings():
    team_name_map = {
        'KT': 'kt wiz', '삼성': '삼성 라이온즈', 'LG': 'LG 트윈스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '한화': '한화 이글스', 'NC': 'NC 다이노스', '롯데': '롯데 자이언츠',
        'SSG': 'SSG 랜더스', '키움': '키움 히어로즈'
    }

    # 1차: KBO 공식 기록실 정적 테이블 파싱
    html = fetch_html("https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx")
    rankings = []
    if html:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL)
        for r in rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
            if len(tds) >= 8:
                clean_tds = [re.sub(r'<[^>]+>', '', td).strip() for td in tds]
                rank_str = clean_tds[0]
                if rank_str.isdigit() and 1 <= int(rank_str) <= 10:
                    raw_team = clean_tds[1]
                    rankings.append({
                        "rank": rank_str,
                        "teamName": team_name_map.get(raw_team, raw_team),
                        "games": clean_tds[2],
                        "win": clean_tds[3],
                        "lose": clean_tds[4],
                        "draw": clean_tds[5],
                        "wra": clean_tds[6],
                        "gameDiff": clean_tds[7]
                    })
        if len(rankings) == 10:
            return rankings

    # 2차 백업: 네이버 야구 기록실 내부 데이터
    n_html = fetch_html("https://sports.news.naver.com/kbaseball/record/index?category=kbo")
    if n_html:
        match = re.search(r'jsonTeamRecord\s*=\s*(\{.*?\});', n_html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                for item in data.get("regularTeamRecordList", []):
                    raw_name = item.get("name", "")
                    rankings.append({
                        "rank": str(item.get("rank", "-")),
                        "teamName": team_name_map.get(raw_name, raw_name),
                        "games": str(item.get("gameCount", "-")),
                        "win": str(item.get("won", "-")),
                        "draw": str(item.get("drawn", "0")),
                        "lose": str(item.get("lost", "-")),
                        "wra": str(item.get("winRates", "-")),
                        "gameDiff": str(item.get("gameDiff", "-"))
                    })
                if len(rankings) == 10:
                    return rankings
            except Exception:
                pass

    return []

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    # 1. 2026 시즌 KT 일정 & 결과
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

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
                stadium = "수원 위즈파크 (홈)" if is_home else f"{g.get('stadium', '원정구장')} (원정)"
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
                    "stadium": stadium,
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

    # 3. KBO 공식 실시간 순위표 수집
    rankings = fetch_kbo_rankings()

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todayMatch": today_game_info,
        "todayLineup": today_lineup,
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ 수집 완료: 일정 {len(kt_schedule)}개 | 공식 순위 {len(rankings)}팀")

if __name__ == "__main__":
    fetch_kt_wiz_data()
