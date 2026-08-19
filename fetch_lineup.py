import json
import datetime
import urllib.request
import re
import ssl

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://m.sports.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception:
        return ""

def update_lineup():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON 로드 오류: {e}")
        return

    today_match = data.get("todayMatch")
    if not today_match or not today_match.get("gameId"):
        print("오늘 KT 경기 일정이 없습니다.")
        return

    game_id = today_match["gameId"]
    is_home = today_match.get("isHome", True)

    kt_p = "미정"
    opp_p = "미정"
    batters = []

    # 1. 🔍 네이버 프리뷰 API 전체 탐색
    p_data = fetch_json(f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview")
    if p_data and "result" in p_data:
        res = p_data.get("result", {})
        g_info = res.get("gameInfo", {})
        
        # 홈/원정 선발투수 추출
        h_cand = [
            res.get("homeStarterPitcher", {}).get("name") if isinstance(res.get("homeStarterPitcher"), dict) else None,
            res.get("homeStarter", {}).get("name") if isinstance(res.get("homeStarter"), dict) else None,
            g_info.get("homeStarterPitcherName"),
            g_info.get("homeStarterName")
        ]
        a_cand = [
            res.get("awayStarterPitcher", {}).get("name") if isinstance(res.get("awayStarterPitcher"), dict) else None,
            res.get("awayStarter", {}).get("name") if isinstance(res.get("awayStarter"), dict) else None,
            g_info.get("awayStarterPitcherName"),
            g_info.get("awayStarterName")
        ]

        h_starter = next((c for c in h_cand if c and str(c).strip() not in ["", "미정"]), None)
        a_starter = next((c for c in a_cand if c and str(c).strip() not in ["", "미정"]), None)

        if is_home:
            if h_starter: kt_p = h_starter
            if a_starter: opp_p = a_starter
        else:
            if a_starter: kt_p = a_starter
            if h_starter: opp_p = h_starter

    # 2. 🔍 KBO 모바일 웹페이지 예비 탐색 (네이버에 아직 안 떴을 경우)
    if kt_p == "미정" or opp_p == "미정":
        kbo_html = fetch_html("https://m.koreabaseball.com/")
        if kbo_html:
            # KT 경기 블록 탐색
            blocks = re.findall(r'<li[^>]*>(.*?)</li>', kbo_html, re.DOTALL)
            for b in blocks:
                if 'KT' in b or 'kt' in b:
                    found = re.findall(r'선발\s*[:：]?\s*([가-힣a-zA-Z]+)', b)
                    if len(found) >= 2:
                        if is_home:
                            opp_p = found[0].strip()
                            kt_p = found[1].strip()
                        else:
                            kt_p = found[0].strip()
                            opp_p = found[1].strip()
                        break

    # 3. 📋 네이버 릴레이 API (경기 시작 직전 라인업 및 타순)
    r_data = fetch_json(f"https://api-gw.sports.naver.com/schedule/games/{game_id}/relay")
    if r_data and "result" in r_data:
        l_root = r_data.get("result", {}).get("lineup", {})
        kt_l = l_root.get("home" if is_home else "away", {})
        opp_l = l_root.get("away" if is_home else "home", {})

        p_kt = kt_l.get("starterPitcher", {}).get("name") or kt_l.get("pitcher", {}).get("name")
        p_opp = opp_l.get("starterPitcher", {}).get("name") or opp_l.get("pitcher", {}).get("name")
        if p_kt: kt_p = p_kt
        if p_opp: opp_p = p_opp

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

    # JSON 데이터 업데이트
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    data["todayLineup"] = {
        "ktPitcher": kt_p,
        "oppPitcher": opp_p,
        "pitcher": kt_p,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 선발투수 갱신 완료: KT [{kt_p}] vs 상대 [{opp_p}] (타자 {len(batters)}명)")

if __name__ == "__main__":
    update_lineup()
