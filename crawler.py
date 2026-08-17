import json
import datetime
import urllib.request

def fetch_kt_wiz_data():
    today = datetime.datetime.now()
    year = today.year

    # 시즌 시작인 3월 1일부터 12월 31일까지 전 경기 한 번에 수집
    url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={year}-03-01&toDate={year}-12-31&size=1000"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"데이터 조회 실패: {e}")
        return

    games_list = data.get("result", {}).get("games", [])
    kt_schedule = {}

    team_map = {
        'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스', 'KIA': 'KIA 타이거즈',
        '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠', '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈', 'KT': 'kt wiz'
    }

    for g in games_list:
        home = g.get("homeTeamName", "")
        away = g.get("awayTeamName", "")
        home_code = g.get("homeTeamCode", "")
        away_code = g.get("awayTeamCode", "")

        # kt wiz 경기 필터링
        if "KT" in home or "KT" in away or home_code == "KT" or away_code == "KT":
            game_date = g.get("gameDateTime", "").split("T")[0]
            is_home = ("KT" in home) or (home_code == "KT")
            opp_raw = away if is_home else home
            opp_name = team_map.get(opp_raw, opp_raw)
            stadium = g.get("stadium", "수원 케이티위즈파크" if is_home else "원정구장")
            
            home_score = g.get("homeTeamScore")
            away_score = g.get("awayTeamScore")
            status = g.get("status", "")
            status_code = g.get("statusCode", "")

            res_type = "scheduled"
            score_str = "VS"

            if "취소" in status or status_code == "CANCEL":
                res_type = "canceled"
                score_str = "취소"
            elif home_score is not None and away_score is not None:
                kt_score = int(home_score if is_home else away_score)
                opp_score = int(away_score if is_home else home_score)
                score_str = f"KT {kt_score} : {opp_score} {opp_raw}"
                if kt_score > opp_score:
                    res_type = "win"
                elif kt_score < opp_score:
                    res_type = "lose"
                else:
                    res_type = "draw"

            kt_schedule[game_date] = {
                "date": game_date,
                "opponent": opp_name,
                "isHome": is_home,
                "stadium": f"수원 위즈파크 (홈)" if is_home else f"{stadium} (원정)",
                "result": res_type,
                "score": score_str,
                "statusCode": status_code
            }

    final_payload = {
        "updatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print("kt wiz 전체 시즌 데이터 수집 완료!")

if __name__ == "__main__":
    fetch_kt_wiz_data()
