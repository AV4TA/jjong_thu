// KBO 및 KT 위즈 라이브 데이터 수집 (수집 성공 버전 + 웹페이지 호환 구조)
const fs = require('fs');
const path = require('path');

const UA = { 'User-Agent': 'Mozilla/5.0 (ktwiz-board live fetcher)' };
const API = 'https://api-gw.sports.naver.com';

function kstNow() {
  return new Date(Date.now() + 9 * 3600 * 1000); // UTC+9
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

function mapGame(g) {
  return {
    id: g.gameId,
    date: g.gameDate,
    time: (g.gameDateTime || '').slice(11, 16),
    stadium: g.stadium,
    away: g.awayTeamName, home: g.homeTeamName,
    as: g.awayTeamScore, hs: g.homeTeamScore,
    status: g.cancel ? '취소' : g.statusInfo,
    code: g.cancel ? 'CANCEL' : g.statusCode,
    ap: g.awayStarterName || '', hp: g.homeStarterName || '',
    wp: g.winPitcherName || '', lp: g.losePitcherName || ''
  };
}

function mapLineup(lu) {
  if (!lu || !lu.fullLineUp || lu.fullLineUp.length < 9) return null;
  const starters = lu.fullLineUp.filter(p => p.positionName === '선발투수');
  const starterName = starters.length > 0 ? starters[0].playerName : '미정';
  
  const batters = lu.fullLineUp
    .filter(p => +p.batorder > 0)
    .sort((a, b) => +a.batorder - +b.batorder)
    .map(p => ({
      order: String(p.batorder),
      name: String(p.playerName || '-').trim(),
      pos: String(p.positionName || '-').trim()
    }));
    
  if (batters.length < 9) return null;
  return { starter: starterName, batters };
}

(async () => {
  const now = kstNow();
  const today = ymd(now);
  const todayCompact = today.replace(/-/g, '');

  const file = path.join(__dirname, 'ktwiz_data.json');
  let prev = null;
  try { prev = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) {}

  // 1) 오늘 경기 조회 (검증된 방식 사용)
  const todayGames = (await games(todayCompact, todayCompact)).map(mapGame);
  const ktTodayGames = todayGames.filter(g => g.home === 'KT' || g.away === 'KT');
  const ktActive = ktTodayGames.find(g => g.code === 'STARTED' || g.code === 'LIVE')
    || ktTodayGames.find(g => !['RESULT', 'ENDED', 'CANCEL'].includes(g.code))
    || ktTodayGames[ktTodayGames.length - 1] || null;

  let ktLineupObj = null, oppLineupObj = null, ktGameId = null, ktStarters = null;
  let todayMatch = null;

  for (const g of todayGames) {
    try {
      const p = await j(`${API}/schedule/games/${g.id}/preview`);
      const pd = p.result && p.result.previewData;
      if (!pd) continue;

      if (ktActive && g.id === ktActive.id) {
        ktGameId = g.id;
        const isHome = g.home === 'KT';
        const opponent = isHome ? g.away : g.home;
        
        const ktSide = isHome ? 'homeTeamLineUp' : 'awayTeamLineUp';
        const opSide = isHome ? 'awayTeamLineUp' : 'homeTeamLineUp';
        
        ktLineupObj = mapLineup(pd[ktSide]);
        oppLineupObj = mapLineup(pd[opSide]);

        const ktPitcherName = isHome ? g.hp : g.ap;
        const oppPitcherName = isHome ? g.ap : g.hp;

        let score = 'VS';
        if (g.code === 'RESULT' || g.code === 'ENDED') {
          score = `KT ${isHome ? g.hs : g.as} : ${isHome ? g.as : g.hs} ${opponent}`;
        }

        todayMatch = {
          date: today,
          time: g.time || '18:30',
          stadium: g.stadium || '수원',
          opponent: opponent,
          isHome: isHome,
          score: score,
          ktPitcher: ktPitcherName || '미정',
          oppPitcher: oppPitcherName || '미정'
        };

        const mapStarter = (s) => s && s.playerInfo ? {
          name: s.playerInfo.name,
          era: (s.currentSeasonStats || {}).era,
          w: (s.currentSeasonStats || {}).w, l: (s.currentSeasonStats || {}).l,
          pitches: (s.currentPitKindStats || []).map(p => ({ type: p.type, rt: p.pit_rt, spd: p.speed }))
        } : null;

        ktStarters = {
          kt: mapStarter(isHome ? pd.homeStarter : pd.awayStarter),
          opp: mapStarter(isHome ? pd.awayStarter : pd.homeStarter),
          oppName: opponent
        };
      }
    } catch (e) {
      console.error('preview fail', g.id, e.message);
    }
  }

  // 방어 코드: 오늘 KT 경기가 없거나 매치업을 못 찾으면 기존 데이터 유지
  if (!todayMatch && prev && prev.todayMatch) {
    todayMatch = prev.todayMatch;
  }

  // 라인업 방어 코드
  let batters = ktLineupObj ? ktLineupObj.batters : [];
  if (!batters.length && prev && prev.todayLineup && prev.todayLineup.batters) {
    batters = prev.todayLineup.batters;
  }

  const todayLineup = {
    ktPitcher: todayMatch ? todayMatch.ktPitcher : '미정',
    oppPitcher: todayMatch ? todayMatch.oppPitcher : '미정',
    pitcher: todayMatch ? todayMatch.ktPitcher : '미정',
    batters: batters
  };

  // 3) KBO 공식 순위표 조회 (웹페이지 호환 매핑)
  let rankings = [];
  try {
    const rankRes = await j(`https://api-gw.sports.naver.com/ranking/teamRank?categoryId=kbo`);
    const rankList = rankRes.result || rankRes.table || [];
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

  // 웹페이지가 완벽하게 읽어 갈 수 있는 최종 데이터 구조 결합
  const finalData = {
    todayMatch: todayMatch,
    todayH2H: prev ? prev.todayH2H : { text: "올 시즌 상대 전적 확인 중...", record: "0승 0패" },
    todayLineup: todayLineup,
    rankings: rankings.length > 0 ? rankings : (prev ? prev.rankings : []),
    schedule: prev ? prev.schedule : {},
    lineupUpdatedAt: now.toISOString(),
    // 기존 board 사이트용 데이터도 함께 보존 (호환성 극대화)
    games: todayGames,
    kt: {
      gameId: ktGameId,
      lineup: ktLineupObj,
      oppLineup: oppLineupObj,
      starters: ktStarters || (prev && prev.kt ? prev.kt.starters : null)
    }
  };

  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(finalData, null, 2), 'utf-8');
  console.log(`🎯 ktwiz_data.json 최종 통합 저장 완료!`);
})().catch(e => { console.error(e); process.exit(1); });
