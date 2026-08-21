// KBO 라이브 데이터 수집 & ktwiz_data.json 호환 통합 스크립트
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
function addDays(d, n) {
  return new Date(d.getTime() + n * 86400000);
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

// KBO 공식 일정 — 취소 경기 목록
async function fetchCancelledList(yearMonths) {
  const out = [];
  for (const ym of yearMonths) {
    const [season, month] = ym.split('-');
    const r = await fetch('https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36',
        'Referer': 'https://www.koreabaseball.com/Schedule/Schedule.aspx',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: `leId=1&srIdList=0%2C9%2C6&seasonId=${season}&gameMonth=${month}&teamId=`,
      signal: AbortSignal.timeout(15000)
    });
    if (!r.ok) continue;
    const d = await r.json();
    let curDate = null;
    for (const row of d.rows || []) {
      let cells = row.row || [];
      if (cells[0] && cells[0].Class === 'day') {
        const m = (cells[0].Text || '').match(/(\d{2})\.(\d{2})/);
        if (m) curDate = `${season}-${m[1]}-${m[2]}`;
        cells = cells.slice(1);
      }
      if (!curDate || cells.length < 2) continue;
      const play = cells.find(c => c.Class === 'play');
      const remark = (cells[cells.length - 1].Text || '').replace(/<[^>]+>/g, '').trim();
      if (!play || !remark.includes('취소')) continue;
      const txt = (play.Text || '').replace(/<em>[\s\S]*?<\/em>/, '|');
      const [awayRaw, homeRaw] = txt.split('|');
      const clean = s => (s || '').replace(/<[^>]+>/g, '').replace(/\d+/g, '').trim();
      const away = clean(awayRaw), home = clean(homeRaw);
      const stadium = cells.length >= 2 ? (cells[cells.length - 2].Text || '').replace(/<[^>]+>/g, '').trim() : '';
      if (away && home) out.push({ date: curDate, away, home, stadium, reason: remark });
    }
  }
  return out;
}

// 자체 순위 계산 (경기 종료 즉시 갱신)
const KBO_TEAMS = ['KT', 'LG', '삼성', '두산', 'KIA', '롯데', 'SSG', 'NC', '키움', '한화'];

async function selfStandings(today) {
  const ranges = [['2026-03-28', '2026-04-30'], ['2026-05-01', '2026-06-30'], ['2026-07-01', today]];
  const agg = {};
  for (const [f, t] of ranges) {
    if (f > today) break;
    const gs = await games(f, t, 500);
    for (const g of gs) {
      if (g.statusCode !== 'RESULT' && g.statusCode !== 'ENDED') continue;
      if (!KBO_TEAMS.includes(g.homeTeamName) || !KBO_TEAMS.includes(g.awayTeamName)) continue;
      for (const [me, my, opsc] of [[g.homeTeamName, g.homeTeamScore, g.awayTeamScore], [g.awayTeamName, g.awayTeamScore, g.homeTeamScore]]) {
        if (!agg[me]) agg[me] = { w: 0, l: 0, d: 0 };
        if (my > opsc) agg[me].w++; else if (my < opsc) agg[me].l++; else agg[me].d++;
      }
    }
  }
  if (Object.keys(agg).length < 10) return null;
  return KBO_TEAMS.map(name => {
    const a = agg[name];
    const pct = a.w / Math.max(1, a.w + a.l);
    return { name, w: a.w, l: a.l, d: a.d, pct, wra: +pct.toFixed(3) };
  }).sort((x, y) => (y.pct - x.pct) || (y.w - x.w))
    .map((t, i) => ({ name: t.name, w: t.w, l: t.l, d: t.d, wra: t.wra, rank: i + 1 }));
}

(async () => {
  const now = kstNow();
  const today = ymd(now);

  const file = path.join(__dirname, 'ktwiz_data.json');
  let prev = null;
  try { prev = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) {}

  const todayGames = (await games(today, today)).map(mapGame);
  
  const standings = {};
  let ktLineup = null, oppLineup = null, ktGameId = null, ktStarters = null;
  const ktTodayGames = todayGames.filter(g => g.home === 'KT' || g.away === 'KT');
  const ktActive = ktTodayGames.find(g => g.code === 'STARTED' || g.code === 'LIVE')
    || ktTodayGames.find(g => !['RESULT', 'ENDED', 'CANCEL'].includes(g.code))
    || ktTodayGames[ktTodayGames.length - 1] || null;

  for (const g of todayGames) {
    try {
      const p = await j(`${API}/schedule/games/${g.id}/preview`);
      const pd = p.result && p.result.previewData;
      if (!pd) continue;
      for (const s of [pd.homeStandings, pd.awayStandings]) {
        if (s && s.name) standings[s.name] = {
          name: s.name, rank: s.rank, w: s.w, l: s.l, d: s.d,
          wra: s.wra, era: s.era, hra: s.hra, hr: s.hr
        };
      }
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
    } catch (e) { console.error('preview fail', g.id, e.message); }
  }

  let finalStandings = null;
  try {
    const self = await selfStandings(today);
    if (self) finalStandings = self.map(t => Object.assign({}, standings[t.name] || {}, t));
  } catch (e) { console.error('selfStandings fail', e.message); }
  if (!finalStandings) {
    finalStandings = Object.keys(standings).length >= 10
      ? Object.values(standings).sort((a, b) => a.rank - b.rank)
      : ((prev && prev.rankings) || []);
  }

  // 기존 HTML(인덱스)이 호환되도록 데이터 매핑 변환
  const ktGame = todayGames.find(g => g.home === 'KT' || g.away === 'KT');
  let todayMatch = null;
  if (ktGame) {
    const isHome = ktGame.home === 'KT';
    const opponent = isHome ? ktGame.away : ktGame.home;
    let score = 'VS';
    if (ktGame.code === 'RESULT' || ktGame.code === 'ENDED') {
      score = `KT ${isHome ? ktGame.hs : ktGame.as} : ${isHome ? ktGame.as : ktGame.hs} ${opponent}`;
    } else if (ktGame.code === 'CANCEL') {
      score = '경기 취소';
    }
    todayMatch = {
      date: today,
      time: ktGame.time || '18:30',
      stadium: ktGame.stadium || '수원',
      opponent: opponent,
      isHome: isHome,
      score: score,
      ktPitcher: (ktStarters && ktStarters.kt) ? ktStarters.kt.name : (isHome ? ktGame.hp : ktGame.ap) || '미정',
      oppPitcher: (ktStarters && ktStarters.opp) ? ktStarters.opp.name : (isHome ? ktGame.ap : ktGame.hp) || '미정'
    };
  }

  let batters = [];
  if (ktLineup && ktLineup.batters) {
    batters = ktLineup.batters.map(b => ({
      order: String(b.o),
      name: b.name,
      pos: b.pos
    }));
  } else {
    // 오늘 라인업이 아직 발표되지 않은 경우 어제 데이터를 재사용하지 않고 비웁니다.
    batters = [];
  }

  const todayLineup = {
    ktPitcher: todayMatch ? todayMatch.ktPitcher : '미정',
    oppPitcher: todayMatch ? todayMatch.oppPitcher : '미정',
    pitcher: todayMatch ? todayMatch.ktPitcher : '미정',
    batters: batters
  };

  const rankings = finalStandings.map((t, i) => ({
    rank: t.rank || (i + 1),
    teamName: t.name,
    games: (t.w + (t.l || 0) + (t.d || 0)),
    win: t.w,
    draw: t.d || 0,
    lose: t.l,
    wra: t.wra || '0.000',
    gameDiff: '0.0'
  }));

  const out = {
    todayMatch: todayMatch,
    todayH2H: prev ? prev.todayH2H : { text: "올 시즌 상대 전적", record: "0승 0패" },
    todayLineup: todayLineup,
    rankings: rankings,
    games: todayGames,
    kt: {
      gameId: ktGameId,
      lineup: ktLineup,
      starters: ktStarters
    },
    updated: new Date().toISOString()
  };

  fs.writeFileSync(file, JSON.stringify(out, null, 2), 'utf-8');
  console.log(`🎯 ktwiz_data.json 통합 저장 완료: games=${todayGames.length}, rankings=${rankings.length}`);
})().catch(e => { console.error(e); process.exit(1); });
