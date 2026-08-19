import json
import urllib.request
import datetime

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except: return None

def fetch_kt_wiz_data():
    year = datetime.datetime.now().year
    # 1. 네이버에서 전체 일정 가져오기
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
    s_data = fetch_json(sched_url)

    # 팀 이름 매핑
    team_map = {'KT': 'kt wiz', 'SS': '삼성 라이온즈', 'LG': 'LG 트윈스', 'OB': '두산 베어스', 
                'HT': 'KIA 타이거즈', 'HH': '한화 이글스', 'NC': 'NC 다이노스', 'LT': '롯데 자이언츠', 
                'SK': 'SSG 랜더스', 'WO': '키움 히어로즈'}
    
    stats = {name: {"W": 0, "L": 0, "D": 0, "G": 0} for name in team_map.values()}

    if s_data and "result" in s_data:
        for g in s_data["result"].get("games", []):
            if g.get("statusCode") in ['RESULT', 'END']:
                h_name = team_map.get(g.get("homeTeamCode"), g.get("homeTeamName"))
                a_name = team_map.get(g.get("awayTeamCode"), g.get("awayTeamName"))
                h_score = int(g.get("homeTeamScore", 0))
                a_score = int(g.get("awayTeamScore", 0))
                
                if h_name in stats and a_name in stats:
                    stats[h_name]["G"] += 1; stats[a_name]["G"] += 1
                    if h_score > a_score: stats[h_name]["W"] += 1; stats[a_name]["L"] += 1
                    elif h_score < a_score: stats[h_name]["L"] += 1; stats[a_name]["W"] += 1
                    else: stats[h_name]["D"] += 1; stats[a_name]["D"] += 1

    # 승률 계산 및 정렬
    sorted_teams = sorted(stats.items(), key=lambda x: (x[1]["W"]/(x[1]["G"] if x[1]["G"]>0 else 1), x[1]["W"]), reverse=True)
    
    rankings = []
    for i, (name, s) in enumerate(sorted_teams):
        rankings.append({
            "rank": str(i + 1),
            "teamName": name,
            "games": str(s["G"]),
            "win": str(s["W"]),
            "lose": str(s["L"]),
            "draw": str(s["D"]),
            "wra": f"{(s['W']/s['G'] if s['G']>0 else 0):.3f}",
            "gameDiff": "-"
        })

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump({"rankings": rankings}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
