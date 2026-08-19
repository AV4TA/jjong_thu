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

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 및 라인업 완벽 동기화: {today_str}] ===")

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

    kt_stat_text = "-"
    opp_stat_text = "-"

    # 1. ⚾ Daum 스포츠 API에서 예고 선발투수 및 시즌 성적(ERA/승패) 추출
    daum_url = f"https://sports.daum.net/prx/hermes/api/game/schedule.json?page=1&leagueCode=kbo&fromDate={today_compact}&toDate={today_compact}"
    res_data = fetch_json(daum_url)

    if res_data and "schedule" in res_data:
        games = res_data.get("schedule", {}).get(today_compact, [])
        for g in games:
            h_team = str(g.get("homeTeamName", ""))
            a_team = str(g.get("awayTeamName", ""))
            
            if any(k in h_team or k in a_team for k in ["KT", "kt"]):
                h_res = g.get("homeResult") or {}
                a_res = g.get("awayResult") or {}
                
                h_starter = g.get("homeStarterPitcherName") or h_res.get("starterPitcherName")
                a_starter = g.get("awayStarterPitcherName") or a_res.get("starterPitcherName")

                # Daum API 투수 시즌 성적 필드 추출
                h_era = g.get("homeStarterPitcherEra") or h_res.get("starterPitcherEra") or h_res.get("era")
                h_w = g.get("homeStarterPitcherW") or h_res.get("starterPitcherW") or h_res.get("w")
                h_l = g.get("homeStarterPitcherL") or h_res.get("starterPitcherL") or h_res.get("l")

                a_era = g.get("awayStarterPitcherEra") or a_res.get("starterPitcherEra") or a_res.get("era")
                a_w = g.get("awayStarterPitcherW") or a_res.get("starterPitcherW") or a_res.get("w")
                a_l = g.get("awayStarterPitcherL") or a_res.get("starterPitcherL") or a_res.get("l")

                h_txt = f"ERA {h_era} ({h_w}승 {h_l}패)" if h_era and h_w is not None else "-"
                a_txt = f"ERA {a_era} ({a_w}승 {a_l}패)" if a_era and a_w is not None else "-"

                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                    kt_stat_text = h_txt
                    opp_stat_text = a_txt
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                    kt_stat_text = a_txt
                    opp_stat_text = h_txt
                break

    # 2. 📋 KBO 메인 전광판에서 KBO GameID 및 1~9번 선발 라인업 조회
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
    data["pitcherComparison"] = {
        "kt": {"name": kt_p, "statText": kt_stat_text},
        "opp": {"name": opp_p, "statText": opp_stat_text}
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

    print(f"🎯 최종 동기화 완료: KT [{kt_p}: {kt_stat_text}] vs 상대 [{opp_p}: {opp_stat_text}]")

if __name__ == "__main__":
    update_lineup_and_pitchers()
