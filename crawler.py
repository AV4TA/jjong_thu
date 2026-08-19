import json
import urllib.request
import re
import datetime
import ssl

# SSL 인증서 문제 방지
ssl_ctx = ssl._create_unverified_context()

def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as res:
            return res.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"HTML 가져오기 오류 [{url}]: {e}")
        return None

def fetch_kt_wiz_data():
    kst_tz = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst_tz)
    year = now.year
    today_str = now.strftime("%Y-%m-%d")
    
    # 📌 3월 28일 정규시즌 시작일 기준
    regular_start = f"{year}-03-28"

    team_map = {
        'KT': 'kt wiz', 'kt': 'kt wiz', 'LG': 'LG 트윈스', 'SSG': 'SSG 랜더스', '두산': '두산 베어스',
        'KIA': 'KIA 타이거즈', '삼성': '삼성 라이온즈', '롯데': '롯데 자이언츠',
        '한화': '한화 이글스', 'NC': 'NC 다이노스', '키움': '키움 히어로즈'
    }

    def clean_team_name(raw):
        for k, v in team_map.items():
            if k in raw:
                return v
        return raw.strip()

    kbo_teams = [
        'kt wiz', '삼성 라이온즈', 'LG 트윈스', '두산 베어스', 'KIA 타이거즈',
        '한화 이글스', 'NC 다이노스', '롯데 자이언츠', 'SSG 랜더스', '키움 히어로즈'
    ]
    stats = {t: {"W": 0, "L": 0, "D": 0, "G": 0} for t in kbo_teams}

    kt_schedule = {}
    today_game_obj = None

    # 1. 📅 KBO 공식 모바일 일정 페이지에서 3월~10월 일정 스크래핑 (API 미사용)
    # KBO 모바일 일정 URL 형식: https://m.koreabaseball.com/Schedule/GameList.aspx?month=03&year=2026
    for m in range(3, 11):
        m_str = f"{m:02d}"
        url = f"https://m.koreabaseball.com/Schedule/GameList.aspx?month={m_str}&year={year}"
        html = fetch_html(url)
        if not html:
            continue

        # 날짜별 블록 분리 (class="tbl-schedule" 또는 <li> 구조)
        day_blocks = re.findall(r'(<div class="schedule-day".*?)(?=<div class="schedule-day"|$)', html, re.DOTALL)
        if not day_blocks:
            # 대체 구조 파싱
            day_blocks = re.findall(r'(<li[^>]*data-date="(\d{4}-\d{2}-\d{2})".*?</li>)', html, re.DOTALL)

        # 경기 정보 추출 정규식
        # 날짜, 원정팀, 원정점수, 홈점수, 홈팀
        games_raw = re.findall(r'(\d{4}[.-]\d{2}[.-]\d{2})[\s\S]*?([가-힣a-zA-Z]+)\s*(\d+)?\s*[:vsVS-]+\s*(\d+)?\s*([가-힣a-zA-Z]+)', html)
        
        # 경기 태그 기반 상세 파싱
        match_rows = re.findall(r'<tr[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*>([\s\S]*?)</tr>', html)
        if not match_rows:
            # 모바일 리스트 구조 파싱
            match_items = re.findall(r'<li[^>]*>([\s\S]*?)</li>', html)
            for item in match_items:
                date_m = re.search(r'(\d{4}[.-]\d{2}[.-]\d{2})', item)
                if not date_m:
                    continue
                g_date = date_m.group(1).replace('.', '-')
                
                # 3월 28일 이전(시범경기) 제외
                if g_date < regular_start:
                    continue

                teams = re.findall(r'<span class="team[^"]*">([^<]+)</span>', item)
                scores = re.findall(r'<span class="score[^"]*">(\d+)</span>', item)
                
                if len(teams) >= 2:
                    away_team = clean_team_name(teams[0])
                    home_team = clean_team_name(teams[1])

                    # 경기 완료 여부 및 순위 집계
                    if len(scores) >= 2 and scores[0].isdigit() and scores[1].isdigit():
                        a_score = int(scores[0])
                        h_score = int(scores[1])

                        if home_team in stats and away_team in stats:
                            stats[home_team]["G"] += 1
                            stats[away_team]["G"] += 1
                            if h_score > a_score:
                                stats[home_team]["W"] += 1
                                stats[away_team]["L"] += 1
                            elif h_score < a_score:
                                stats[home_team]["L"] += 1
                                stats[away_team]["W"] += 1
                            else:
                                stats[home_team]["D"] += 1
                                stats[away_team]["D"] += 1

                    # KT 위즈 일정 기록
                    is_kt_home = (home_team == 'kt wiz')
                    is_kt_away = (away_team == 'kt wiz')

                    if is_kt_home or is_kt_away:
                        opp_team = away_team if is_kt_home else home_team
                        stadium = "수원 위즈파크 (홈)" if is_kt_home else "원정구장"
                        res_type = "scheduled"
                        score_str = "VS"

                        if len(scores) >= 2:
                            kt_s = h_score if is_kt_home else a_score
                            opp_s = a_score if is_kt_home else h_score
                            score_str = f"KT {kt_s} : {opp_s} {opp_team.split(' ')[0]}"
                            res_type = "win" if kt_s > opp_s else ("lose" if kt_s < opp_s else "draw")

                        game_entry = {
                            "date": g_date,
                            "time": "18:30",
                            "opponent": opp_team,
                            "isHome": is_kt_home,
                            "stadium": stadium,
                            "result": res_type,
                            "score": score_str
                        }
                        kt_schedule[g_date] = game_entry
                        if g_date == today_str:
                            today_game_obj = game_entry

    # 2. 📊 KBO 공식 순위 직접 계산 (승률 = 승 / (승 + 패))
    def calc_wra(w, l):
        tot = w + l
        return (w / tot) if tot > 0 else 0.0

    sorted_teams = sorted(
        stats.items(),
        key=lambda x: (calc_wra(x[1]["W"], x[1]["L"]), x[1]["W"]),
        reverse=True
    )

    rankings = []
    top_w = sorted_teams[0][1]["W"] if sorted_teams else 0
    top_l = sorted_teams[0][1]["L"] if sorted_teams else 0

    for i, (team, s) in enumerate(sorted_teams):
        wra = calc_wra(s["W"], s["L"])
        diff = ((top_w - s["W"]) + (s["L"] - top_l)) / 2.0
        diff_str = "0.0" if i == 0 or diff <= 0 else f"{diff:.1f}".rstrip('0').rstrip('.') if f"{diff:.1f}".endswith('.0') else f"{diff:.1f}"

        rankings.append({
            "rank": str(i + 1),
            "teamName": team,
            "games": str(s["G"]),
            "win": str(s["W"]),
            "draw": str(s["D"]),
            "lose": str(s["L"]),
            "wra": f"{wra:.3f}",
            "gameDiff": diff_str
        })

    # 3. JSON 저장
    final_payload = {
        "updatedAt": now.strftime("%Y-%m-%d %H:%M:%S (KST)"),
        "todayMatch": today_game_obj,
        "todayLineup": {"pitcher": "-", "batters": []},
        "rankings": rankings,
        "schedule": kt_schedule
    }

    with open("ktwiz_data.json", "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"✅ KBO 모바일 직접 수집 완료: 3/28 이후 순위 {len(rankings)}팀 직접 계산 완료")

if __name__ == "__main__":
    fetch_kt_wiz_data()
