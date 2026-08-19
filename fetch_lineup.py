import json
import datetime
import urllib.request

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
    except Exception as e:
        print(f"JSON 호출 실패 [{url}]: {e}")
        return None

def extract_pitcher_name(obj):
    """다양한 네이버 API 구조에서 투수 이름을 안전하게 추출"""
    if not obj:
        return None
    if isinstance(obj, str) and obj.strip() not in ["", "미정", "None"]:
        return obj.strip()
    if isinstance(obj, dict):
        for k in ['name', 'playerName', 'pitcherName', 'starterName']:
            if obj.get(k) and str(obj[k]).strip() not in ["", "미정"]:
                return str(obj[k]).strip()
    return None

def update_lineup():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ktwiz_data.json 읽기 오류: {e}")
        return

    today_match = data.get("todayMatch")
    if not today_match or not today_match.get("gameId"):
        print("오늘 KT 경기가 없거나 gameId가 없습니다.")
        return

    game_id = today_match["gameId"]
    is_home = today_match.get("isHome", True)

    kt_pitcher = today_match.get("ktPitcher") or "미정"
    opp_pitcher = today_match.get("oppPitcher") or "미정"
    batters = []

    # 1. 📅 기본 일정 데이터에서 선발투수 재확인
    sched_url = f"https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={today_str}&toDate={today_str}&size=10"
    s_data = fetch_json(sched_url)
    if s_data and "result" in s_data:
        for g in s_data.get("result", {}).get("games", []):
            if g.get("gameId") == game_id:
                h_p = extract_pitcher_name(g.get("homeStarterPitcher")) or extract_pitcher_name(g.get("homeStarterName")) or extract_pitcher_name(g.get("homeStarterPitcherName"))
                a_p = extract_pitcher_name(g.get("awayStarterPitcher")) or extract_pitcher_name(g.get("awayStarterName")) or extract_pitcher_name(g.get("awayStarterPitcherName"))
                if is_home:
                    if h_p: kt_pitcher = h_p
                    if a_p: opp_pitcher = a_p
                else:
                    if a_p: kt_pitcher = a_p
                    if h_p: opp_pitcher = h_p

    # 2. 🔍 프리뷰 API (오전/낮 예고 선발투수 추출)
    prev_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview"
    p_data = fetch_json(prev_url)
    if p_data and "result" in p_data:
        res = p_data.get("result", {})
        g_info = res.get("gameInfo", {})
        
        # preview 내부의 다양한 위치 탐색
        h_starter = (
            extract_pitcher_name(res.get("homeStarterPitcher")) or
            extract_pitcher_name(res.get("homeStarter")) or
            extract_pitcher_name(g_info.get("homeStarterPitcherName")) or
            extract_pitcher_name(g_info.get("homeStarterName"))
        )
        a_starter = (
            extract_pitcher_name(res.get("awayStarterPitcher")) or
            extract_pitcher_name(res.get("awayStarter")) or
            extract_pitcher_name(g_info.get("awayStarterPitcherName")) or
            extract_pitcher_name(g_info.get("awayStarterName"))
        )

        if is_home:
            if h_starter: kt_pitcher = h_starter
            if a_starter: opp_pitcher = a_starter
        else:
            if a_starter: kt_pitcher = a_starter
            if h_starter: opp_pitcher = h_starter

    # 3. 📋 중계 릴레이 API (경기 시작 직전 확정 라인업 및 타순)
    relay_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/relay"
    r_data = fetch_json(relay_url)
    if r_data and "result" in r_data:
        lineup_root = r_data.get("result", {}).get("lineup", {})
        kt_l = lineup_root.get("home" if is_home else "away", {})
        opp_l = lineup_root.get("away" if is_home else "home", {})

        real_kt_p = extract_pitcher_name(kt_l.get("starterPitcher")) or extract_pitcher_name(kt_l.get("pitcher"))
        real_opp_p = extract_pitcher_name(opp_l.get("starterPitcher")) or extract_pitcher_name(opp_l.get("pitcher"))
        if real_kt_p: kt_pitcher = real_kt_p
        if real_opp_p: opp_pitcher = real_opp_p

        # 1~9번 타순 파싱
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

    # 오늘 경기 데이터 동기화
    data["todayMatch"]["ktPitcher"] = kt_pitcher
    data["todayMatch"]["oppPitcher"] = opp_pitcher
    
    data["todayLineup"] = {
        "ktPitcher": kt_pitcher,
        "oppPitcher": opp_pitcher,
        "pitcher": kt_pitcher,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 선발투수 반영 성공: KT [{kt_pitcher}] vs 상대 [{opp_pitcher}] (타자: {len(batters)}명)")

if __name__ == "__main__":
    update_lineup()
