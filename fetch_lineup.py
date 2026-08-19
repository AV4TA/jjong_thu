import json
import datetime
import urllib.request
import re
import ssl
import traceback

ssl_ctx = ssl._create_unverified_context()

def fetch_content(url, is_json=False):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': '*/*'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as res:
            raw = res.read().decode('utf-8', errors='ignore')
            return json.loads(raw) if is_json else raw
    except Exception as e:
        print(f"조회 건너뜀 [{url}]: {e}")
        return None

def update_starter_pitchers():
    try:
        kst_tz = datetime.timezone(datetime.timedelta(hours=9))
        now_kst = datetime.datetime.now(kst_tz)
        today_compact = now_kst.strftime("%Y%m%d")

        # 1. 기존 JSON 파일 로드
        try:
            with open("ktwiz_data.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"ktwiz_data.json 파일 없음 또는 읽기 실패: {e}")
            return

        today_match = data.get("todayMatch")
        if not today_match:
            print("오늘 경기 일정이 없어 선발투수를 조회하지 않습니다.")
            return

        is_home = today_match.get("isHome", True)
        kt_p = today_match.get("ktPitcher") or "미정"
        opp_p = today_match.get("oppPitcher") or "미정"

        # 2. Daum KBO API 조회
        daum_url = f"https://sports.daum.net/prx/hermes/api/game/schedule.json?page=1&leagueCode=kbo&fromDate={today_compact}&toDate={today_compact}"
        daum_data = fetch_content(daum_url, is_json=True)
        
        if daum_data and "schedule" in daum_data:
            for g in daum_data.get("schedule", {}).get(today_compact, []):
                h_team = g.get("homeTeamName", "")
                a_team = g.get("awayTeamName", "")
                
                if "KT" in h_team or "KT" in a_team or "kt" in h_team or "kt" in a_team:
                    h_starter = g.get("homeStarterPitcherName") or g.get("homeResult", {}).get("starterPitcherName")
                    a_starter = g.get("awayStarterPitcherName") or g.get("awayResult", {}).get("starterPitcherName")
                    
                    if is_home:
                        if h_starter: kt_p = str(h_starter).strip()
                        if a_starter: opp_p = str(a_starter).strip()
                    else:
                        if a_starter: kt_p = str(a_starter).strip()
                        if h_starter: opp_p = str(h_starter).strip()
                    break

        # 3. KBO 공식 모바일 페이지 크롤링 (백업)
        if kt_p in ["", "미정", None] or opp_p in ["", "미정", None]:
            kbo_html = fetch_content("https://m.koreabaseball.com/")
            if kbo_html:
                blocks = re.findall(r'<li[^>]*>(.*?)</li>', kbo_html, re.DOTALL)
                for b in blocks:
                    if 'KT' in b or 'kt' in b:
                        pitchers = re.findall(r'선발\s*[:：]?\s*([가-힣a-zA-Z]+)', b)
                        if len(pitchers) >= 2:
                            if is_home:
                                opp_p, kt_p = pitchers[0].strip(), pitchers[1].strip()
                            else:
                                kt_p, opp_p = pitchers[0].strip(), pitchers[1].strip()
                            break

        # 4. JSON 파일 저장
        data["todayMatch"]["ktPitcher"] = kt_p
        data["todayMatch"]["oppPitcher"] = opp_p
        
        if "todayLineup" not in data or not isinstance(data["todayLineup"], dict):
            data["todayLineup"] = {}

        data["todayLineup"]["ktPitcher"] = kt_p
        data["todayLineup"]["oppPitcher"] = opp_p
        data["todayLineup"]["pitcher"] = kt_p
        data["lineupUpdatedAt"] = now_kst.strftime("%Y-%m-%d %H:%M:%S (KST)")

        with open("ktwiz_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 선발투수 업데이트 완료: KT [{kt_p}] vs 상대 [{opp_p}]")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    update_starter_pitchers()
