import json
import datetime
import urllib.request
import urllib.error
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url, post_data=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.sports.naver.com/'
    }
    data_bytes = post_data.encode('utf-8') if post_data else None
    if post_data:
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            body = res.read().decode('utf-8-sig')
            return json.loads(body)
    except Exception as e:
        print(f"❌ 통신 에러 [{url}]: {e}")
        return None

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 및 네이버 스포츠 라인업 업데이트: {today_str}] ===")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8-sig") as f:
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
    naver_game_id = None

    # 1. ⚾ KBO 메인 전광판에서 선발투수 및 경기 ID 조회 (기존 방식 유지)
    main_res = fetch_json(
        "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList",
        f"leId=1&srId=0&date={today_compact}"
    )

    if main_res and "game" in main_res:
        for g in main_res.get("game", []):
            h_name = g.get("HOME_NM", "")
            a_name = g.get("AWAY_NM", "")
            
            if "kt" in h_name.lower() or "kt" in a_name.lower():
                h_starter = g.get("B_PIT_P_NM") or g.get("HOME_PIT_P_NM")
                a_starter = g.get("T_PIT_P_NM") or g.get("AWAY_PIT_P_NM")
                
                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                break

    print(f"  👉 선발투수: KT [{kt_p}] vs 상대 [{opp_p}]")

    # 2. 📋 네이버 스포츠 API를 통해 오늘 날짜의 경기 고유 ID(gameId) 찾기
    schedule_url = f"https://api-sports.naver.com/v1/kbo/games?date={today_compact}"
    # 네이버 스포츠 비공식 API 혹은 스케줄 주소 호출 대안
    # 네이버 모바일 웹이 참조하는 일정 목록 API 활용
    naver_schedule_url = f"https://m.sports.naver.com/kbaseball/schedule/index?date={today_compact}"
    
    # 더 안정적인 네이버 스포츠 내부 JSON 스케줄 엔드포인트 호출
    naver_api_url = f"https://sports.news.naver.com/kbaseball/schedule/list?date={today_compact}&category=kbo"
    schedule_res = fetch_json(naver_api_url)

    if schedule_res:
        games = schedule_res.get("result", {}).get("games", [])
        for g in games:
            h_team = g.get("homeTeamName", "")
            a_team = g.get("awayTeamName", "")
            if "kt" in h_team.lower() or "kt" in a_team.lower():
                naver_game_id = g.get("gameId")
                break

    # 3. 📋 네이버 스포츠 라인업 API 호출
    if naver_game_id:
        lineup_url = f"https://sports.news.naver.com/kbaseball/game/centerLineup?gameId={naver_game_id}"
        lineup_res = fetch_json(lineup_url)
        
        if lineup_res:
            res_data = lineup_res.get("result", {})
            target_key = "homeLineUp" if is_home else "awayLineUp"
            raw_batters = res_data.get(target_key, []) or res_data.get("lineup", [])
            
            if raw_batters:
                for idx, b in enumerate(raw_batters):
                    order = str(b.get("order") or b.get("turn") or (idx + 1))
                    name = str(b.get("playerName") or b.get("name") or "-").strip()
                    pos = str(b.get("positionName") or b.get("position") or "-").strip()
                    
                    if name != "-" and idx < 9:
                        batters.append({
                            "order": order,
                            "name": name,
                            "pos": pos
                        })

    # 💡 방어 코드: 라인업 데이터가 비어있으면 기존에 저장된 데이터 유지
    if not batters and "todayLineup" in data and "batters" in data["todayLineup"]:
        batters = data["todayLineup"]["batters"]
        print("  ℹ️ 네이버 스포츠에서 라인업을 가져오지 못해 기존 데이터를 유지합니다.")

    print(f"  👉 최종 선발 타순 등록: {len(batters)}명")

    # 4. ⚔️ 올시즌 상대 전적 계산
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

    data["todayLineup"] = {
        "ktPitcher": kt_p,
        "oppPitcher": opp_p,
        "pitcher": kt_p,
        "batters": batters
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    if "pitcherComparison" in data:
        del data["pitcherComparison"]

    with open("ktwiz_data.json", "w", encoding="utf-8-sig") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 저장 완료: KT [{kt_p}] vs 상대 [{opp_p}] / 전적 [{h2h_text}]")

if __name__ == "__main__":
    update_lineup_and_pitchers()
