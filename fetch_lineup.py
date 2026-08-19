import json
import datetime
import urllib.request
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def fetch_json_get(url, referer='https://m.sports.naver.com/'):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Referer': referer
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
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
    except Exception as e:
        print(f"KBO 통신 오류 [{url}]: {e}")
        return None

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 상세 비교 & 라인업 갱신: {today_str}] ===")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ktwiz_data.json 읽기 실패: {e}")
        sys.exit(1)

    today_match = data.get("todayMatch")
    if not today_match:
        print("ℹ️ 오늘 경기 일정이 없습니다.")
        return

    game_id = today_match.get("gameId")
    is_home = today_match.get("isHome", True)
    opponent_name = today_match.get("opponent", "")
    
    kt_p = today_match.get("ktPitcher") or "미정"
    opp_p = today_match.get("oppPitcher") or "미정"
    batters = []
    kbo_game_id = None

    # 기본 선발 스펙 객체
    kt_stat = {"name": kt_p, "era": "-", "record": "-"}
    opp_stat = {"name": opp_p, "era": "-", "record": "-"}

    # 1. ⚾ KBO 메인 전광판에서 선발투수 이름 & KBO GameID 가져오기
    main_res = fetch_kbo_post(
        "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList",
        f"leId=1&srId=0&date={today_compact}"
    )

    if main_res and "game" in main_res:
        for g in main_res.get("game", []):
            h_name = g.get("HOME_NM", "")
            a_name = g.get("AWAY_NM", "")
            
            if "KT" in h_name or "kt" in h_name or "KT" in a_name or "kt" in a_name:
                kbo_game_id = g.get("G_ID")
                h_starter = g.get("B_PIT_P_NM") or g.get("HOME_PIT_P_NM")
                a_starter = g.get("T_PIT_P_NM") or g.get("AWAY_PIT_P_NM")
                
                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                break

    kt_stat["name"] = kt_p
    opp_stat["name"] = opp_p

    # 2. 🔍 네이버 게임센터 프리뷰 API에서 투수 ERA / 승패 성적 가져오기
    if game_id:
        prev_data = fetch_json_get(f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview")
        if prev_data and "result" in prev_data:
            res = prev_data.get("result", {})
            h_pitcher_info = res.get("homeStarterPitcher") or {}
            a_pitcher_info = res.get("awayStarterPitcher") or {}

            # 홈팀 투수 스펙
            h_era = str(h_pitcher_info.get("era", "-"))
            h_w = h_pitcher_info.get("w", "-")
            h_l = h_pitcher_info.get("l", "-")
            h_rec = f"{h_w}승 {h_l}패" if h_w != "-" and h_l != "-" else "-"

            # 원정팀 투수 스펙
            a_era = str(a_pitcher_info.get("era", "-"))
            a_w = a_pitcher_info.get("w", "-")
            a_l = a_pitcher_info.get("l", "-")
            a_rec = f"{a_w}승 {a_l}패" if a_w != "-" and a_l != "-" else "-"

            if is_home:
                kt_stat["era"] = h_era
                kt_stat["record"] = h_rec
                opp_stat["era"] = a_era
                opp_stat["record"] = a_rec
            else:
                kt_stat["era"] = a_era
                kt_stat["record"] = a_rec
                opp_stat["era"] = h_era
                opp_stat["record"] = h_rec

    # 3. 📋 KBO 공식 선발 타순 (1~9번 라인업) 조회
    if kbo_game_id:
        lineup_res = fetch_kbo_post(
            "https://www.koreabaseball.com/ws/Schedule.asmx/GetLineUp",
            f"gameDate={today_compact}&gameId={kbo_game_id}&leagueId=1&sectionId=0"
        )
        
        if lineup_res:
            target_key = "homeLineUp" if is_home else "awayLineUp"
            raw_batters = lineup_res.get(target_key, []) or lineup_res.get("lineUp", [])
            
            if raw_batters:
                for idx, b in enumerate(raw_batters):
                    order = str(b.get("TURN") or b.get("BAT_ORDER_NO") or (idx + 1))
                    name = str(b.get("P_NM") or b.get("NAME") or "-").strip()
                    pos = str(b.get("POS_NM") or b.get("POSITION") or "-").strip()
                    
                    if name != "-" and idx < 9:
                        batters.append({
                            "order": order,
                            "name": name,
                            "pos": pos
                        })

    # 4. ⚔️ 올시즌 상대 전적(H2H) 계산
    h2h_wins = 0
    h2h_draws = 0
    h2h_losses = 0

    schedule_dict = data.get("schedule", {})
    opp_short = opponent_name.split()[0] if opponent_name else ""

    for g_date, g_info in schedule_dict.items():
        if g_date >= today_str:
            continue

        g_opp = g_info.get("opponent", "")
        if opp_short in g_opp or g_opp in opponent_name:
            res = g_info.get("result")
            if res == "win":
                h2h_wins += 1
            elif res == "lose":
                h2h_losses += 1
            elif res == "draw":
                h2h_draws += 1

    total_h2h_games = h2h_wins + h2h_losses + h2h_draws
    d_txt = f"{h2h_draws}무 " if h2h_draws > 0 else ""

    if total_h2h_games > 0:
        h2h_text = f"올시즌 {total_h2h_games}전 {h2h_wins}승 {d_txt}{h2h_losses}패"
    else:
        h2h_text = "올 시즌 첫 맞대결"

    # 5. JSON 파일 저장
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    
    data["todayH2H"] = {
        "text": h2h_text,
        "record": f"{h2h_wins}승 {d_txt}{h2h_losses}패"
    }

    data["pitcherComparison"] = {
        "kt": kt_stat,
        "opp": opp_stat
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

    print(f"🎯 투수 비교 스펙 갱신: KT[{kt_p}: {kt_stat['era']}, {kt_stat['record']}] vs 상대[{opp_p}: {opp_stat['era']}, {opp_stat['record']}]")

if __name__ == "__main__":
    update_lineup_and_pitchers()
