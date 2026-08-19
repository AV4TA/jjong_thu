import json
import datetime
import urllib.request
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url, referer='https://m.sports.naver.com/'):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': referer
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"  [API 오류] {url} -> {e}")
        return None

def deep_find_pitcher(obj, team_hint=""):
    """JSON 객체 안에서 투수 이름(2~4글자 한글)을 재귀적으로 탐색"""
    if not obj:
        return None
    if isinstance(obj, str) and 2 <= len(obj.strip()) <= 4 and obj.strip() not in ["미정", "None", "VS", "결과", "예정"]:
        return obj.strip()
    if isinstance(obj, dict):
        for k in ['name', 'playerName', 'pitcherName', 'starterPitcherName', 'homeStarterName', 'awayStarterName', 'starterName']:
            if k in obj and obj[k]:
                val = str(obj[k]).strip()
                if 2 <= len(val) <= 4 and val not in ["미정", "None"]:
                    return val
    return None

def update_starter_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 업데이트 시작: {today_str}] ===")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ktwiz_data.json 파일 읽기 실패: {e}")
        sys.exit(1)

    today_match = data.get("todayMatch")
    if not today_match or not today_match.get("gameId"):
        print("ℹ️ 오늘 KT 경기 일정이 없거나 gameId가 없습니다.")
        return

    game_id = today_match["gameId"]
    is_home = today_match.get("isHome", True)
    
    kt_p = None
    opp_p = None
    batters = []

    # 1. 🔍 [1순위] 네이버 프리뷰 API 탐색
    print(f"1. 네이버 프리뷰 조회 중... (GameID: {game_id})")
    prev_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview"
    p_data = fetch_json(prev_url)
    if p_data and "result" in p_data:
        res = p_data.get("result", {})
        g_info = res.get("gameInfo", {})

        h_p = (
            deep_find_pitcher(res.get("homeStarterPitcher")) or
            deep_find_pitcher(res.get("homeStarter")) or
            deep_find_pitcher(g_info.get("homeStarterPitcherName")) or
            deep_find_pitcher(g_info.get("homeStarterName"))
        )
        a_p = (
            deep_find_pitcher(res.get("awayStarterPitcher")) or
            deep_find_pitcher(res.get("awayStarter")) or
            deep_find_pitcher(g_info.get("awayStarterPitcherName")) or
            deep_find_pitcher(g_info.get("awayStarterName"))
        )
        if is_home:
            if h_p: kt_p = h_p
            if a_p: opp_p = a_p
        else:
            if a_p: kt_p = a_p
            if h_p: opp_p = h_p
        print(f"   👉 프리뷰 결과: KT={kt_p}, 상대={opp_p}")

    # 2. 🔍 [2순위] 다음(Daum) 스포츠 API 탐색
    if not kt_p or not opp_p:
        print("2. Daum 스포츠 API 조회 중...")
        daum_url = f"https://sports.daum.net/prx/hermes/api/game/schedule.json?page=1&leagueCode=kbo&fromDate={today_compact}&toDate={today_compact}"
        d_data = fetch_json(daum_url, referer='https://sports.daum.net/')
        if d_data and "schedule" in d_data:
            for g in d_data.get("schedule", {}).get(today_compact, []):
                h_team = str(g.get("homeTeamName", ""))
                a_team = str(g.get("awayTeamName", ""))
                if "KT" in h_team or "KT" in a_team or "kt" in h_team or "kt" in a_team:
                    h_starter = deep_find_pitcher(g.get("homeStarterPitcherName")) or deep_find_pitcher(g.get("homeResult", {}).get("starterPitcherName"))
                    a_starter = deep_find_pitcher(g.get("awayStarterPitcherName")) or deep_find_pitcher(g.get("awayResult", {}).get("starterPitcherName"))
                    if is_home:
                        if h_starter and not kt_p: kt_p = h_starter
                        if a_starter and not opp_p: opp_p = a_starter
                    else:
                        if a_starter and not kt_p: kt_p = a_starter
                        if h_starter and not opp_p: opp_p = h_starter
                    break
        print(f"   👉 Daum 조회 후: KT={kt_p}, 상대={opp_p}")

    # 3. 🔍 [3순위] 네이버 릴레이 API 탐색 (확정 라인업 및 타순)
    print("3. 네이버 릴레이 API 조회 중...")
    relay_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/relay"
    r_data = fetch_json(relay_url)
    if r_data and "result" in r_data:
        l_root = r_data.get("result", {}).get("lineup", {})
        kt_l = l_root.get("home" if is_home else "away", {})
        opp_l = l_root.get("away" if is_home else "home", {})

        real_kt_p = deep_find_pitcher(kt_l.get("starterPitcher")) or deep_find_pitcher(kt_l.get("pitcher"))
        real_opp_p = deep_find_pitcher(opp_l.get("starterPitcher")) or deep_find_pitcher(opp_l.get("pitcher"))
        if real_kt_p: kt_p = real_kt_p
        if real_opp_p: opp_p = real_opp_p

        # 타순
        b_list = kt_l.get("batters", [])
        if b_list:
            batters = [
                {
                    "order": str(b.get("order", idx + 1)),
                    "name": str(b.get("name", b.get("playerName", "-"))),
                    "pos": str(b.get("pos", b.get("position", "-")))
                }
                for idx, b in enumerate(b_list)
            ]
        print(f"   👉 릴레이 조회 후: KT={kt_p}, 상대={opp_p}, 타자={len(batters)}명")

    # 최종 기본값 처리
    final_kt_p = kt_p if kt_p else (today_match.get("ktPitcher") or "미정")
    final_opp_p = opp_p if opp_p else (today_match.get("oppPitcher") or "미정")

    # JSON 반영
    data["todayMatch"]["ktPitcher"] = final_kt_p
    data["todayMatch"]["oppPitcher"] = final_opp_p
    data["todayLineup"] = {
        "ktPitcher": final_kt_p,
        "oppPitcher": final_opp_p,
        "pitcher": final_kt_p,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 최종 저장 완료: KT [{final_kt_p}] vs 상대 [{final_opp_p}]")

if __name__ == "__main__":
    update_starter_pitchers()
