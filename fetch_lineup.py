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
        print(f"KBO 통신 오류 [{url}]: {e}")
        return None

def update_lineup_and_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [KBO 공식 데이터 동기화 시작: {today_str}] ===")

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
    kt_p = today_match.get("ktPitcher") or "미정"
    opp_p = today_match.get("oppPitcher") or "미정"
    batters = []
    kbo_game_id = None

    # 1. ⚾ KBO 메인 전광판 데이터 (예고 선발투수 & KBO 경기 고유 ID 확보)
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

    print(f"  👉 선발투수: KT [{kt_p}] vs 상대 [{opp_p}] (KBO GameID: {kbo_game_id})")

    # 2. 📋 KBO 공식 선발 타순 (1~9번 라인업) 조회
    if kbo_game_id:
        lineup_res = fetch_kbo_post(
            "https://www.koreabaseball.com/ws/Schedule.asmx/GetLineUp",
            f"gameDate={today_compact}&gameId={kbo_game_id}&leagueId=1&sectionId=0"
        )
        
        if lineup_res:
            # 홈/원정 구분하여 KT 타자 목록 추출
            target_key = "homeLineUp" if is_home else "awayLineUp"
            raw_batters = lineup_res.get(target_key, []) or lineup_res.get("lineUp", [])
            
            if raw_batters:
                for idx, b in enumerate(raw_batters):
                    # 1~9번 선발 타자만 필터링
                    order = str(b.get("TURN") or b.get("BAT_ORDER_NO") or (idx + 1))
                    name = str(b.get("P_NM") or b.get("NAME") or "-").strip()
                    pos = str(b.get("POS_NM") or b.get("POSITION") or "-").strip()
                    
                    if name != "-" and idx < 9:
                        batters.append({
                            "order": order,
                            "name": name,
                            "pos": pos
                        })

    print(f"  👉 선발 타순 등록: {len(batters)}명")

    # 3. JSON 저장
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

    print(f"🎯 KBO 공식 선발투수 & 라인업 전체 갱신 완료!")

if __name__ == "__main__":
    update_lineup_and_pitchers()
