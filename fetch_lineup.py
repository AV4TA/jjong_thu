import json
import datetime
import urllib.request
import urllib.error
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (ktwiz-board live fetcher)',
            'Referer': 'https://m.sports.naver.com/'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            return json.loads(res.read().decode('utf-8-sig'))
    except Exception as e:
        print(f"❌ 네이버 API 통신 에러 [{url}]: {e}")
        return None

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [선발투수 및 라인업 업데이트 (네이버 연동): {today_str}] ===")

    # 1. ktwiz_data.json 읽기
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

    # 2. 네이버 스포츠 API를 통해 오늘 경기 목록 및 선발/라인업 조회
    api_url = f"https://api-gw.sports.naver.com/schedule/games?fields=basic,stadium,statusNum,homeStarterName,awayStarterName&upperCategoryId=kbaseball&categoryId=kbo&fromDate={today_compact}&toDate={today_compact}&size=200"
    schedule_res = fetch_json(api_url)

    game_id = None
    if schedule_res and "result" in schedule_res:
        games = schedule_res.get("result", {}).get("games", [])
        for g in games:
            h_name = g.get("homeTeamName", "")
            a_name = g.get("awayTeamName", "")
            
            if "kt" in h_name.lower() or "kt" in a_name.lower():
                game_id = g.get("gameId")
                h_starter = g.get("homeStarterName")
                a_starter = g.get("awayStarterName")
                
                if is_home:
                    if h_starter: kt_p = str(h_starter).strip()
                    if a_starter: opp_p = str(a_starter).strip()
                else:
                    if a_starter: kt_p = str(a_starter).strip()
                    if h_starter: opp_p = str(h_starter).strip()
                break

    print(f"  👉 선발투수: KT [{kt_p}] vs 상대 [{opp_p}]")

    # 3. 네이버 프리뷰 API를 통해 라인업 가져오기
    if game_id:
        preview_url = f"https://api-gw.sports.naver.com/schedule/games/{game_id}/preview"
        preview_res = fetch_json(preview_url)
        
        if preview_res and "result" in preview_res:
            pd = preview_res.get("result", {}).get("previewData", {})
            target_side = "homeTeamLineUp" if is_home else "awayTeamLineUp"
            lineup_data = pd.get(target_side, {})
            full_lineup = lineup_data.get("fullLineUp", [])
            
            if full_lineup and len(full_lineup) >= 9:
                # 타순 순서대로 정렬
                valid_batters = [p for p in full_lineup if p.get("batorder") and int(p.get("batorder")) > 0]
                valid_batters.sort(key=lambda x: int(x.get("batorder")))
                
                for idx, b in enumerate(valid_batters):
                    if idx < 9:
                        batters.append({
                            "order": str(b.get("batorder")),
                            "name": str(b.get("playerName", "-")).strip(),
                            "pos": str(b.get("positionName", "-")).strip()
                        })

    # 💡 방어 코드: 새 라인업을 못 가져왔다면 기존에 저장된 데이터 유지
    if not batters and "todayLineup" in data and "batters" in data["todayLineup"]:
        batters = data["todayLineup"]["batters"]
        print("  ℹ️ 네이버 API에서 라인업을 가져오지 못해 기존 데이터를 안전하게 유지합니다.")

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

    # 5. ktwiz_data.json 파일로 저장
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
