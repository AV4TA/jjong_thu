// KBO 및 KT 위즈 라이브 데이터 수집 (ktwiz_data.json 완벽 호환 버전)
const fs = require('fs');
const path = require('path');

const UA = { 'User-Agent': 'Mozilla/5.0 (ktwiz-board live fetcher)' };
const API = 'https://api-gw.sports.naver.com';

function kstNow() {
  return new Date(Date.now() + 9 * 3600 * 1000);
}
function ymd(d) {
  return d.toISOString().slice(0, 10);
}

async function j(url) {
  const r = await fetch(url, { headers: UA, signal: AbortSignal.timeout(15000) });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

async function games(from, to, size) {
  const u = `${API}/schedule/games?fields=basic,stadium,statusNum,homeStarterName,awayStarterName,winPitcherName,losePitcherName&upperCategoryId=kbaseball&categoryId=kbo&fromDate=${from}&toDate=${to}&size=${size || 200}`;
  const d = await j(u);
  return (d.result && d.result.games) || [];
}

(async () => {
  const now = kstNow();
  const today = ymd(now);
  const todayCompact = today.replace(/-/g, '');

  const file = path.join(__dirname, 'ktwiz_data.json');
  let prev = null;
  try { prev = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) {}

  // 1) 오늘 경기 조회
  const todayGames = await games(todayCompact, todayCompact);
  const ktGame = todayGames.find(g => g.homeTeamName.includes('KT') || g.awayTeamName.includes('KT'));

  let todayMatch = null;
  let todayLineup = null;
  let ktPitcher = '미정';
  let oppPitcher = '미정';
  let batters = [];

  if (ktGame) {
    const isHome = ktGame.homeTeamName.includes('KT');
    const opponent = isHome ? ktGame.awayTeamName : ktGame.homeTeamName;
    ktPitcher = (isHome ? ktGame.homeStarterName : ktGame.awayStarterName) || '미정';
    oppPitcher = (isHome ? ktGame.awayStarterName : ktGame.homeStarterName) || '미정';

    let score = 'VS';
    if (ktGame.statusCode === 'RESULT' || ktGame.statusCode === 'ENDED') {
      const hs = ktGame.homeTeamScore || 0;
      const as = ktGame.awayTeamScore || 0;
      score = `KT ${isHome ? hs : as} : ${isHome ? as : hs} ${opponent}`;
    }

    todayMatch = {
      date: today,
      time: (ktGame.gameDateTime || '').slice(11, 16) || '18:30',
      stadium: ktGame.stadium || '수원',
      opponent: opponent,
      isHome: isHome,
      score: score,
      ktPitcher: ktPitcher,
      oppPitcher: oppPitcher
    };

    // 프리뷰 및 라인업 조회
    try {
      const p = await j(`${API}/schedule/games/${ktGame.gameId}/preview`);
      const pd = p.result && p.result.previewData;
      if (pd) {
        const ktSide = isHome ? 'homeTeamLineUp' : 'awayTeamLineUp';
        const lu = pd[ktSide];
        if (lu && lu.fullLineUp && lu.fullLineUp.length >= 9) {
          const validBatters = lu.fullLineUp.filter(p => p.batorder && +p.batorder > 0);
          validBatters.sort((a, b) => +a.batorder - +b.batorder);
          batters = validBatters.slice(0, 9).map(b => ({
            order: String(b.batorder),
            name: String(b.playerName || '-').trim(),
            pos: String(b.positionName || '-').trim()
          }));
        }
      }
    } catch (e) {
      console.error('preview/lineup fail', e.message);
    }
  }

  // 방어 코드: 라인업 못 가져오면 기존 유지
  if (!batters.length && prev && prev.todayLineup && prev.todayLineup.batters) {
    batters = prev.todayLineup.batters;
  }

  todayLineup = {
    ktPitcher: ktPitcher,
    oppPitcher: oppPitcher,
    pitcher: ktPitcher,
    batters: batters
  };

  // 2) KBO 공식 순위표 조회 (네이버 API 활용)
  let rankings = [];
  try {
    const rankRes = await j(`https://api-gw.sports.naver.com/ranking/teamRank?categoryId=kbo`);
    const rankList = rankRes.result || rankRes.table || [];
    // 네이버 팀 순위 데이터를 HTML이 요구하는 구조로 매핑
    rankings = rankList.map((r, idx) => ({
      rank: r.rank || (idx + 1),
      teamName: r.teamName || r.name,
      games: r.gameCount || r.games || 0,
      win: r.winCount || r.win || 0,
      draw: r.drawCount || r.draw || 0,
      lose: r.loseCount || r.lose || 0,
      wra: r.winRate || r.wra || '0.000',
      gameDiff: r.gameDiff || '0.0'
    }));
  } catch (e) {
    console.error('rankings fail', e.message);
    if (prev && prev.rankings) rankings = prev.rankings;
  }

  // 기존 데이터 파일에 있던 schedule 및 todayH2H 유지
  const finalData = {
    todayMatch: todayMatch || (prev ? prev.todayMatch : null),
    todayH2H: prev ? prev.todayH2H : { text: "올 시즌 상대 전적 확인 중...", record: "0승 0패" },
    todayLineup: todayLineup,
    rankings: rankings.length > 0 ? rankings : (prev ? prev.rankings : []),
    schedule: prev ? prev.schedule : {},
    lineupUpdatedAt: now.toISOString()
  };

  fs.writeFileSync(file, JSON.stringify(finalData, null, 2), 'utf-8');
  console.log('🎯 ktwiz_data.json 업데이트 완료!');
})().catch(e => { console.error(e); process.exit(1); });
