import json
import datetime
import urllib.request
import ssl

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://sports.daum.net/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"API 호출 실패: {e}")
        return None

def update_starter_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_compact = now_kst.strftime("%Y%m%d")

    # 1. 기존 JSON 파일 로드
    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON 로드 오류: {e}")
        return

    today_match = data.get("todayMatch")
    if not today_match:
        print("오늘 KT 경기 일정이 없습니다.")
        return

    is_home = today_match.get("isHome", True)
    kt_p = "미정"
    opp_p = "미정"

    # 2. 전날 예고 선발까지 즉시 내려오는 다음(Daum) 스포츠 공식 일정 API 호출
    api_url = f"https://sports.daum.net/prx/hermes/api/game/schedule.json?page=1&leagueCode=kbo&fromDate={today_compact}&toDate={today_compact}"
    res_data = fetch_json(api_url)

    if res_data and "schedule" in res_data:
        games = res_data.get("schedule", {}).get(today_compact, [])
        for g in games:
            h_team = g.get("homeTeamName", "")
            a_team = g.get("awayTeamName", "")
            
            # KT가 포함된 경기 찾기
            if "KT" in h_team or "KT" in a_team or "kt" in h_team or "kt" in a_team:
                # API 구조 내에서 예고 선발투수 이름 추출
                h_starter = g.get("homeStarterPitcherName") or g.get("homeResult", {}).get("starterPitcherName")
                a_starter = g.get("awayStarterPitcherName") or g.get("awayResult", {}).get("starterPitcherName")
                
                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                break

    # 3. 데이터 반영 및 저장
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    
    if "todayLineup" not in data or not isinstance(data["todayLineup"], dict):
        data["todayLineup"] = {}

    data["todayLineup"]["ktPitcher"] = kt_p
    data["todayLineup"]["oppPitcher"] = opp_p
    data["todayLineup"]["pitcher"] = kt_p
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 선발투수 동기화 완료: KT [{kt_p}] vs 상대 [{opp_p}]")

if __name__ == "__main__":
    update_starter_pitchers()
