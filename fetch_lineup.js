// KBO 및 KT 위즈 라이브 데이터 수집 (경기, 라인업, 순위표 완벽 통합 버전)
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
  const starter = lu.fullLineUp.find(p => p.positionName === '선발투수');
  const batters = lu.fullLineUp
    .filter(p => +p.batorder > 0)
    .sort((a, b) => +a.batorder - +b.batorder)
    .map(p => ({ o: +p.batorder, name: p.playerName, pos: p.positionName }));
  if (batters.length < 9) return null;
  return { starter: starter ? starter.playerName : '', batters };
}

(async () => {
  const now = kstNow();
  const today = ymd(now);

  const file = path.join(__dirname, 'ktwiz_data.json');
  let prev = null;
  try { prev = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) {}

  // 1) 오늘 경기 조회
  const todayGames = (await games(today, today)).map(mapGame);
  const ktTodayGames = todayGames.filter(g => g.home === 'KT' || g.away === 'KT');
  const ktActive = ktTodayGames.find(g => g.code === 'STARTED' || g.code === 'LIVE')
    || ktTodayGames.find(g => !['RESULT', 'ENDED', 'CANCEL'].includes(g.code))
    || ktTodayGames[ktTodayGames.length - 1] || null;

  let ktLineup = null, oppLineup = null, ktGameId = null, ktStarters = null;

  for (const g of todayGames) {
    try {
      const p = await j(`${API}/schedule/games/${g.id}/preview`);
      const pd = p.result && p.result.previewData;
      if (!pd) continue;

      if (ktActive && g.id === ktActive.id) {
        ktGameId = g.id;
        const ktSide = g.home === 'KT' ? 'homeTeamLineUp' : 'awayTeamLineUp';
        const opSide = g.home === 'KT' ? 'awayTeamLineUp' : 'homeTeamLineUp';
        ktLineup = mapLineup(pd[ktSide]);
        oppLineup = mapLineup(pd[opSide]);

        const mapStarter = (s) => s && s.playerInfo ? {
          name: s.playerInfo.name,
          era: (s.currentSeasonStats || {}).era,
          w: (s.currentSeasonStats || {}).w, l: (s.currentSeasonStats || {}).l,
          pitches: (s.currentPitKindStats || []).map(p => ({ type: p.type, rt: p.pit_rt, spd: p.speed }))
        } : null;

        ktStarters = {
          kt: mapStarter(g.home === 'KT' ? pd.homeStarter : pd.awayStarter),
          opp: mapStarter(g.home === 'KT' ? pd.awayStarter : pd.homeStarter),
          oppName: g.home === 'KT' ? g.away : g.home
        };
      }
    } catch (e) {
      console.error('preview fail', g.id, e.message);
    }
  }

  // 방어 코드
  if (!ktLineup && prev && prev.kt && prev.kt.lineup) {
    ktLineup = prev.kt.lineup;
    oppLineup = prev.kt.oppLineup;
  }
  if (!ktStarters && prev && prev.kt && prev.kt.starters) {
    ktStarters = prev.kt.starters;
  }

  // 2) KBO 리그 공식 순위표 조회 추가
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

  // 최종 저장 구조 (games, kt 정보 + 순위 rankings 포함)
  const out = {
    updated: new Date().toISOString(),
    updatedKST: `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}`,
    date: today,
    games: todayGames,
    rankings: rankings.length > 0 ? rankings : (prev ? prev.rankings : []),
    kt: {
      gameId: ktGameId,
      lineup: ktLineup,
      oppLineup: oppLineup,
      starters: ktStarters
    }
  };

  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(out, null, 1));
  console.log(`🎯 데이터 수집 완료: games=${todayGames.length}, rankings=${rankings.length}, lineup=${!!ktLineup}`);
})().catch(e => { console.error(e); process.exit(1); });
