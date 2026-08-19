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
    except Exception:
        return None

def update_lineup():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")

    # 기존 생성된 JSON 데이터 불러오기
    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON 파일 읽기 실패: {e}")
        return

    today_match = data.get("todayMatch")
    if not today_match or not today_match.get("gameId"):
        print("오늘 예정된 KT 경기가 없거나 gameId가 없습니다.")
        return

    game_id = today_match["gameId"]
    is_home = today_match.get("isHome", True)

    kt_pitcher = "미정"
    opp_pitcher = "미정"
    batters = []

    # [1단계] 프리뷰 API (오전/낮 예고 선발투수 확보)
    prev_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview"
    p_data = fetch_json(prev_url)
    if p_data and "result" in p_data:
        g_info = p_data.get("result", {}).get("gameInfo", {})
        h_starter = p_data.get("result", {}).get("homeStarterPitcher", {}).get("name") or g_info.get("homeStarterPitcherName")
        a_starter = p_data.get("result", {}).get("awayStarterPitcher", {}).get("name") or g_info.get("awayStarterPitcherName")

        if is_home:
            if h_starter: kt_pitcher = h_starter
            if a_starter: opp_pitcher = a_starter
        else:
            if a_starter: kt_pitcher = a_starter
            if h_starter: opp_pitcher = h_starter

    # [2단계] 릴레이 API (경기 1시간 전 확정 선발투수 & 타자 라인업 보강)
    relay_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/relay"
    r_data = fetch_json(relay_url)
    if r_data and "result" in r_data:
        lineup_root = r_data.get("result", {}).get("lineup", {})
        kt_lineup = lineup_root.get("home" if is_home else "away", {})
        opp_lineup = lineup_root.get("away" if is_home else "home", {})

        # 확정 선발투수가 들어왔다면 갱신
        real_kt_p = kt_lineup.get("starterPitcher", {}).get("name")
        real_opp_p = opp_lineup.get("starterPitcher", {}).get("name")
        if real_kt_p: kt_pitcher = real_kt_p
        if real_opp_p: opp_pitcher = real_opp_p

        # 선발 타순 (1~9번)
        b_list = kt_lineup.get("batters", [])
        if b_list:
            batters = [
                {"order": b.get("order", "-"), "name": b.get("name", "-"), "pos": b.get("pos", "-")}
                for b in b_list
            ]

    # 데이터 업데이트
    data["todayLineup"] = {
        "ktPitcher": kt_pitcher,
        "oppPitcher": opp_pitcher,
        "pitcher": kt_pitcher,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 선발 라인업 동기화 완료: KT({kt_pitcher}) vs 상대({opp_pitcher}) | 타자 {len(batters)}명")

if __name__ == "__main__":
    update_lineup()
