import json
import urllib.request
import datetime

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except: return None

def fetch_kt_wiz_data():
    year = datetime.datetime.now().year
    start_date = f"{year}-03-28" # 정규시즌 시작일
    
    # API 호출 시점부터 정규시즌 데이터만 요청
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={start_date}&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    team_map = {'KT': 'kt wiz', 'SS': '삼성 라이온즈', 'LG': 'LG 트윈스', 'OB': '두산 베어스', 
                'HT': 'KIA 타이거즈', 'HH': '한화 이글스', 'NC': 'NC 다이노스', 'LT': '롯데 자이언츠', 
                'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'}
    
    stats = {name: {"W": 0, "L": 0, "D": 0, "G": 0} for name in team_map.values()}
    kt_schedule = {}
    
    if s_data and "result" in s_data:
        for g in s_data["result"].get("games", []):
            game_date = g.get("gameDateTime", "").split("T")[0]
            
            # 3월 28일 이전 데이터는 확실하게 제외
            if game_date < start_date: continue

            h_code = g.get("homeTeamCode")
            a_code = g.get("awayTeamCode")
            h_name = team_map.get(h_code, g.get("homeTeamName"))
            a_name = team_map.get(a_code, g.get("awayTeamName"))
            
            # 경기 결과 통계 누적
            if g.get("statusCode") in ['RESULT', 'END']:
                h_s = int(g.get("homeTeamScore", 0))
                a_s = int(g.get("awayTeamScore", 0))
                
                if h_name in stats and a_name in stats:
                    stats[h_name]["G"] += 1; stats[a_name]["G"] += 1
                    if h_s > a_s: stats[h_name]["W"] += 1; stats[a_name]["L"] += 1
                    elif h_s < a_s: stats[h_name]["L"] += 1; stats[a_name]["W"] += 1
                    else: stats[h_name]["D"] += 1; stats[a_name]["D"] += 1
            
            # KT 일정 처리
            if h_code == "KT" or a_code == "KT":
                res = "scheduled"
                if g.get("statusCode") in ['RESULT', 'END']:
                    h_s = int(g.get("homeTeamScore", 0))
                    a_s = int(g.get("awayTeamScore", 0))
                    kt_s = h_s if h_code == "KT" else a_s
                    opp_s = a_s if h_code == "KT" else h_s
                    res = "win" if kt_s > opp_s else ("lose" if kt_s < opp_s else "draw")
                
                kt_schedule[game_date] = {
                    "date": game_date, 
                    "opponent": a_name if h_code == "KT" else h_name, 
                    "result": res
                }

    # 순위 정렬
    sorted_teams = sorted(stats.items(), key=lambda x: (x[1]["W"]/(x[1]["G"] if x[1]["G"]>0 else 1), x[1]["W"]), reverse=True)
    
    rankings = []
    top_w = sorted_teams[0][1]["W"] if sorted_teams else 0
    top_l = sorted_teams[0][1]["L"] if sorted_teams else 0

    for i, (name, s) in enumerate(sorted_teams):
        wra = (s["W"] / s["G"]) if s["G"] > 0 else 0
        diff = ((top_w - s["W"]) + (s["L"] - top_l)) / 2.0
        
        rankings.append({
            "rank": str(i + 1),
            "teamName": name,
            "games": str(s["G"]),
            "win": str(s["W"]),
            "lose": str(s["L"]),
            "draw": str(s["D"]),
            "wra": f"{wra:.3f}",
            "gameDiff": f"{diff:.1f}".replace('.0', '')
        })

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump({"rankings": rankings, "schedule": kt_schedule}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
