import json
import datetime
import urllib.request

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://m.sports.naver.com/'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode('utf-8'))
    except: return None

def fetch_kt_wiz_data():
    year = datetime.datetime.now().year
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    # KT Wiz 일정만 수집
    url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-28&toDate={year}-12-31&size=500"
    data = fetch_json(url)
    
    kt_schedule = {}
    today_game = None

    if data and "result" in data:
        for g in data["result"].get("games", []):
            if "KT" in g.get("homeTeamName", "") or "KT" in g.get("awayTeamName", ""):
                raw_dt = g.get("gameDateTime", "")
                date = raw_dt.split("T")[0]
                is_home = ("KT" in g.get("homeTeamName", ""))
                
                # 결과 처리
                status = g.get("statusCode", "")
                score_str = "VS"
                res = "scheduled"
                
                if status in ['RESULT', 'END']:
                    h_sc = g.get("homeTeamScore", 0)
                    a_sc = g.get("awayTeamScore", 0)
                    score_str = f"{h_sc} : {a_sc}"
                    kt_sc = h_sc if is_home else a_sc
                    op_sc = a_sc if is_home else h_sc
                    if kt_sc > op_sc: res = "win"
                    elif kt_sc < op_sc: res = "lose"
                    else: res = "draw"
                elif status == 'CANCEL':
                    res = "canceled"
                    score_str = "취소"

                game_obj = {
                    "date": date,
                    "opponent": g.get("awayTeamName") if is_home else g.get("homeTeamName"),
                    "stadium": g.get("stadium", "수원"),
                    "result": res,
                    "score": score_str
                }
                kt_schedule[date] = game_obj
                
                if date == today_str:
                    today_game = game_obj

    final = {"todayMatch": today_game, "schedule": kt_schedule}
    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_kt_wiz_data()
