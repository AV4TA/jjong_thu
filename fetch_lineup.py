import json
import datetime
import urllib.request
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

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
        print(f"KBO 통신 에러 [{url}]: {e}")
        return None

def get_pitcher_season_stats(pitcher_name):
    """KBO 공식 기록실에서 투수 이름으로 올 시즌 성적 직접 조회"""
    if not pitcher_name or pitcher_name in ["미정", "-", "None"]:
        return {"name": pitcher_name or "미정", "era": "-", "record": "-"}

    try:
        # KBO 공식 선수 검색 엔드포인트 호출
        search_res = fetch_kbo_post(
            "https://www.koreabaseball.com/ws/Search.asmx/GetPlayerList",
            f"leId=1&searchWord={urllib.request.quote(pitcher_name)}"
        )
        
        if search_res and "rows" in search_res:
            for row in search_res.get("rows", []):
                # row 내부 필드 순서: [선수명, 팀명, 포지션, 경기수, ERA(평균자책점), 승, 패, 세이브, ...]
                row_data = row.get("row", [])
                if row_data:
                    # 텍스트 리스트 형태 매칭
                    pos = str(row_data[2]) if len(row_data) > 2 else ""
                    if "투" in pos or "P" in pos:
                        era = str(row_data[4]) if len(row_data) > 4 else "-"
                        w = str(row_data[5]) if len(row_data) > 5 else "-"
                        l = str(row_data[6]) if len(row_data) > 6 else "-"
                        rec = f"{w}승 {l}패" if (w != "-" and l != "-") else "-"
                        return {"name": pitcher_name, "era": era, "record": rec}
    except Exception as e:
        print(f"투수 성적 조회 실패 ({pitcher_name}): {e}")

    return {"name": pitcher_name, "era": "-", "record": "-"}

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [KBO 공식 데이터 & 투수 성적 완벽 동기화: {today_str}] ===")

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

    is_home = today_match.get("isHome", True)
    opponent_name = today_match.get("opponent", "")
    kt_p = today_match.get("ktPitcher") or "미정"
    opp_p = today_match.get("oppPitcher") or "미정"
    batters = []
    kbo_game_id = None

    # 1. ⚾ KBO 메인 전광판에서 선발투수 이름 추출
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

    # 2. 📊 양 팀 선발투수 시즌 공식 성적(ERA, 승패) 조회
    kt_stat = get_pitcher_season_stats(kt_p)
    opp_stat = get_pitcher_season_stats(opp_p)
    print(f"  👉 KT 선발: [{kt_stat['name']}] ERA: {kt_stat['era']}, {kt_stat['record']}")
    print(f"  👉 상대 선발: [{opp_stat['name']}] ERA: {opp_stat['era']}, {opp_stat['record']}")

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

    print(f"🎯 최종 저장 완료!")

if __name__ == "__main__":
    update_lineup_and_pitchers()
