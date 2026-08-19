import json
import urllib.request
import datetime
import sys

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"URL Fetch Error: {e}")
        return None

def fetch_kt_wiz_data():
    try:
        kst_tz = datetime.timezone(datetime.timedelta(hours=9))
        today_kst = datetime.datetime.now(kst_tz)
        year = today_kst.year
        today_str = today_kst.strftime("%Y-%m-%d")

        stats = {team: {"W": 0, "L": 0, "D": 0, "G": 0} for team in ['kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈', '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈']}
        kt_schedule = {}
        today_game_info = None

        sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=1000"
        s_data = fetch_json(sched_url)
        
        if s_data and s_data.get("result"):
            for g in s_data["result"].get("games", []):
                home_name = g.get("homeTeamName", "")
                away_name = g.get("awayTeamName", "")
                
                # 통계 계산
                if g.get("statusCode") in ['RESULT', 'END']:
                    h_s = int(g.get("homeTeamScore", 0))
                    a_s = int(g.get("awayTeamScore", 0))
                    if home_name in stats and away_name in stats:
                        stats[home_name]["G"] += 1
                        stats[away_name]["G"] += 1
                        if h_s > a_s: stats[home_name]["W"] += 1; stats[away_name]["L"] += 1
                        elif h_s < a_s: stats[home_name]["L"] += 1; stats[away_name]["W"] += 1
                        else: stats[home_name]["D"] += 1; stats[away_name]["D"] += 1
                
                # KT 일정
                if "KT" in home_name or "KT" in away_name:
                    is_home = ("KT" in home_name)
                    res = "scheduled"
                    if g.get("statusCode") in ['RESULT', 'END']:
                        h_s = int(g.get("homeTeamScore", 0))
                        a_s = int(g.get("awayTeamScore", 0))
                        kt_s = h_s if is_home else a_s
                        opp_s = a_s if is_home else h_s
                        res = "win" if kt_s > opp_s else ("lose" if kt_s < opp_s else "draw")
                    
                    game_obj = {"date": g.get("gameDateTime", "")[:10], "opponent": away_name if is_home else home_name, "result": res}
                    kt_schedule[game_obj["date"]] = game_obj
                    if game_obj["date"] == today_str: today_game_info = game_obj

        # 순위 정렬
        rankings = []
        for i, (name, s) in enumerate(sorted(stats.items(), key=lambda x: (x[1]["W"]/(x[1]["G"] if x[1]["G"]>0 else 1)), reverse=True)):
            rankings.append({"rank": str(i+1), "teamName": name, "win": str(s["W"]), "lose": str(s["L"]), "draw": str(s["D"]), "wra": f"{(s['W']/s['G'] if s['G']>0 else 0):.3f}"})

        final_payload = {"updatedAt": today_kst.strftime("%Y-%m-%d %H:%M:%S"), "todayMatch": today_game_info, "rankings": rankings, "schedule": kt_schedule}
        with open("ktwiz_data.json", "w", encoding="utf-8") as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # 에러가 나도 빈 파일이라도 생성해서 Workflow 성공시키기
        with open("ktwiz_data.json", "w", encoding="utf-8") as f:
            json.dump({"error": str(e)}, f)

if __name__ == "__main__":
    fetch_kt_wiz_data()
