import json
import datetime
import urllib.request
import ssl
import sys

ssl_ctx = ssl._create_unverified_context()

def update_starter_pitchers():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst_tz)
    today_str = now_kst.strftime("%Y-%m-%d")
    today_compact = now_kst.strftime("%Y%m%d")

    print(f"=== [KBO 공식 전광판 데이터 조회: {today_str}] ===")

    try:
        with open("ktwiz_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ ktwiz_data.json 파일 읽기 실패: {e}")
        sys.exit(1)

    today_match = data.get("todayMatch")
    if not today_match:
        print("ℹ️ 오늘 경기 일정이 없습니다.")
        return

    is_home = today_match.get("isHome", True)
    kt_p = "미정"
    opp_p = "미정"

    # ⚾ ktwiz-board 방식: KBO 메인 전광판 데이터 직접 호출
    kbo_url = "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList"
    req = urllib.request.Request(
        kbo_url,
        data=f"leId=1&srId=0&date={today_compact}".encode('utf-8'),
        headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',
            'Referer': 'https://www.koreabaseball.com/'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as res:
            res_json = json.loads(res.read().decode('utf-8'))
            game_list = res_json.get("game", [])
            
            for g in game_list:
                h_name = g.get("HOME_NM", "")
                a_name = g.get("AWAY_NM", "")
                
                # KT 경기 블록 매칭
                if "KT" in h_name or "kt" in h_name or "KT" in a_name or "kt" in a_name:
                    # KBO 공식 선발투수 필드
                    h_starter = g.get("B_PIT_P_NM") or g.get("HOME_PIT_P_NM")
                    a_starter = g.get("T_PIT_P_NM") or g.get("AWAY_PIT_P_NM")
                    
                    if is_home:
                        if h_starter: kt_p = str(h_starter).strip()
                        if a_starter: opp_p = str(a_starter).strip()
                    else:
                        if a_starter: kt_p = str(a_starter).strip()
                        if h_starter: opp_p = str(h_starter).strip()
                    break
    except Exception as e:
        print(f"KBO 엔드포인트 호출 실패: {e}")

    # JSON 반영
    data["todayMatch"]["ktPitcher"] = kt_p
    data["todayMatch"]["oppPitcher"] = opp_p
    data["todayLineup"] = {
        "ktPitcher": kt_p,
        "oppPitcher": opp_p,
        "pitcher": kt_p,
        "batters": []
    }
    data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"🎯 KBO 전광판 추출 완료: KT [{kt_p}] vs 상대 [{opp_p}]")

if __name__ == "__main__":
    update_starter_pitchers()
