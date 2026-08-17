import json
import datetime
import urllib.request

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
        print(f"API 요청 실패: {e}")
        return None

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year
    today_str = today.strftime("%Y-%m-%d")

    # 1. 2026 정규시즌 전체 일정 수집
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    kt_schedule = {}
    today_game_id = None
    today_game_info = None

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    # 전체 구단 순위 계산용 딕셔너리
    all_teams = ['LG', 'SSG', '두산', 'KIA', '삼성', '롯데', '한화', 'NC', '키움', 'KT']
    standings = {t: {"teamName": team_map[t], "games": 0, "win": 0, "draw": 0, "lose": 0} for t in all_teams}

    if s_data and "result" in s_data:
        games_list = s_data.get("result", {}).get("games", [])
        for g in games_list:
            raw_dt = g.get("gameDateTime", "")
            game_date = raw_dt.split("T")[0] if "T" in raw_dt else raw_dt[:10]
            
            # [A] 경기 결과 집계 (종료된 경기만!)
            status_code = g.get("statusCode", "")
            # 실제 종료된 경기(RESULT/END) AND 오늘 이전 날짜만 카운트
            if status_code in ['RESULT', 'END'] and game_date <= today_str:
                h_code = g.get("homeTeamCode")
                a_code = g.get("awayTeamCode")
                h_score = g.get("homeTeamScore")
                a_score = g.get("awayTeamScore")
                
                if h_code in standings and a_code in standings:
                    standings[h_code]["games"] += 1
                    standings[a_code]["games"] += 1
                    if h_score > a_score:
                        standings[h_code]["win"] += 1
                        standings[a_code]["lose"] += 1
                    elif h_score < a_score:
                        standings[a_code]["win"] += 1
                        standings[h_code]["lose"] += 1
                    else:
                        standings[h_code]["draw"] += 1
                        standings[a_code]["draw"] += 1

            # [B] KT Wiz 일정 필터링
            if "KT" in g.get("homeTeamName", "") or "KT" in g.get("awayTeamName", ""):
                is_home = ("KT" in g.get("homeTeamName", ""))
                score_str = f"{g.get('homeTeamScore')} : {g.get('awayTeamScore')}" if status_code in ['RESULT', 'END'] else "VS"
                
                kt_schedule[game_date] = {
                    "date": game_date,
                    "opponent": g.get("awayTeamName") if is_home else g.get("homeTeamName"),
                    "score": score_str,
                    "result": "win" if (is_home and g.get('homeTeamScore') > g.get('awayTeamScore')) or (not is_home and g.get('awayTeamScore') > g.get('homeTeamScore')) else "lose"
                }
                if game_date == today_str:
                    today_game_id = g.get("gameId")
                    today_game_info = kt_schedule[game_date]

    # [C] 계산된 데이터로 순위 정렬
    rank_list = []
    for code, d in standings.items():
        w, l, d_raw = d["win"], d["lose"], d["draw"]
        total = w + l # 승률은 승/(승+패)
        win_rate = (w / total) if total > 0 else 0.0
        rank_list.append({
            "teamName": d["teamName"], "games": d["games"], "win": w, "draw": d_raw, "lose": l, 
            "wra": f"{win_rate:.3f}", "wra_num": win_rate
        })
    
    # 승률 순으로 정렬
    rank_list.sort(key=lambda x: (x["wra_num"], x["win"]), reverse=True)
    
    final_rankings = []
    for i, r in enumerate(rank_list):
        final_rankings.append({
            "rank": str(i+1), "teamName": r["teamName"], "games": r["games"], 
            "win": r["win"], "draw": r["draw"], "lose": r["lose"], "wra": r["wra"], "gameDiff": "-"
        })

    # [D] 최종 패키징
    final_payload = {
        "todayMatch": today_game_info,
        "rankings": final_rankings,
        "schedule": kt_schedule,
        "playerStats": {"batters": [], "pitchers": []} # 필요 시 위 코드 참고하여 추가
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
