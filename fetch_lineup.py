import json
import datetime
import urllib.request
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url, referer='https://sports.daum.net/'):
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
        print(f"API 호출 실패: {url} -> {e}")
        return None

def fetch_kbo_post(url, data_str):
    req = urllib.request.Request(
        url,
        data=data_str.encode('utf-8'),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
            'Referer': 'https://www.koreabaseball.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception:
        return None

def update_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 및 라인업 업데이트: {today_str}] ===")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON 로드 실패: {e}")
        sys.exit(1)

    today_match = data.get("todayMatch")
    if not today_match:
        print("오늘 KT 경기 일정이 없습니다.")
        return

    is_home = today_match.get("isHome", True)
    opponent_name = today_match.get("opponent", "")
    kt_p = today_match.get("ktPitcher") or "미정"
    opp_p = today_match.get("oppPitcher") or "미정"
    kbo_game_id = None
    batters = []

    # 1. ⚾ Daum 스포츠 API에서 예고 선발투수 추출 (NoneType 에러 완벽 방지)
    daum_url = f"https://sports.daum.net/prx/hermes/api/game/schedule.json?page=1&leagueCode=kbo&fromDate={today_compact}&toDate={today_compact}"
    res_data = fetch_json(daum_url)

    if res_data and "schedule" in res_data:
        games = res_data.get("schedule", {}).get(today_compact, [])
        for g in games:
            h_team = str(g.get("homeTeamName", ""))
            a_team = str(g.get("awayTeamName", ""))
            
            if any(k in h_team or k in a_team for k in ["KT", "kt"]):
                # None일 경우 안전하게 빈 딕셔너리로 대체
                h_res = g.get("homeResult") or {}
                a_res = g.get("awayResult") or {}
                
                h_starter = g.get("homeStarterPitcherName") or h_res.get("starterPitcherName")
                a_starter = g.get("awayStarterPitcherName") or a_res.get("starterPitcherName")
                
                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                break

    # 2. 📋 KBO 메인 전광판에서 KBO 경기 ID 및 라인업 조회
    main_res = fetch_kbo_post(
        "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList",
        f"leId=1&srId=0&date={today_compact}"
    )
    if main_res and "game" in main_res:
        for g in main_res.get("game", []):
            h_name = g.get("HOME_NM", "")
            a_name = g.get("AWAY_NM", "")
            if any(k in h_name or k in a_name for k in ["KT", "kt"]):
                kbo_game_id = g.get("G_ID")
                break

    if kbo_game_id:
        lineup_res = fetch_kbo_post(
            "https://www.koreabaseball.com/ws/Schedule.asmx/GetLineUp",
            f"gameDate={today_compact}&gameId={kbo_game_id}&leagueId=1&sectionId=0"
        )
        if lineup_res:
            target_key = "homeLineUp" if is_home else "awayLineUp"
            raw_batters = lineup_res.get(target_key, []) or lineup_res.get("lineUp", [])
            for idx, b in enumerate(raw_batters):
                order = str(b.get("TURN") or b.get("BAT_ORDER_NO") or (idx + 1))
                name = str(b.get("P_NM") or b.get("NAME") or "-").strip()
                pos = str(b.get("POS_NM") or b.get("POSITION") or "-").strip()
                if name != "-" and idx < 9:
                    batters.append({"order": order, "name": name, "pos": pos})

    # 3. ⚔️ 올시즌 상대 전적 계산
    h2h_wins, h2h_draws, h2h_losses = 0, 0, 0
    opp_short = opponent_name.split()[0] if opponent_name else ""
    for g_date, g_info in data.get("schedule", {}).items():
        if g_date >= today_str:
            continue
        g_opp = g_info.get("opponent", "")
        if opp_short in g_opp or g_opp in opponent_name:
            r = g_info.get("result")
            if r == "win": h2h_wins += 1
            elif r == "lose": h2h_losses += 1
            elif r == "draw": h2h_draws += 1

    tot = h2h_wins + h2h_losses + h2h_draws
    d_txt = f"{h2h_draws}무 " if h2h_draws > 0 else ""
    h2h_text = f"올시즌 {tot}전 {h2h_wins}승 {d_txt}{h2h_losses}패" if tot > 0 else "올 시즌 첫 맞대결"

    # 4. JSON 파일 저장
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    data["todayH2H"] = {
        "text": h2h_text,
        "record": f"{h2h_wins}승 {d_txt}{h2h_losses}패"
    }
    data["todayLineup"] = {
        "ktPitcher": kt_p,
        "oppPitcher": opp_p,
        "pitcher": kt_p,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 저장 완료: KT [{kt_p}] vs 상대 [{opp_p}] / 전적: {h2h_text}")

if __name__ == "__main__":
    update_data()
