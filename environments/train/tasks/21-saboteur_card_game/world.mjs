                                                                                                                                  
                                                                                                                         
import { Raster } from '../../lib/raster.mjs';

const DIRS = [[0, -1], [1, 0], [0, 1], [-1, 0]], DNAME = ['N', 'E', 'S', 'W'], OPP = [2, 3, 0, 1];
const PLAYERS = 5, HAND = 6, ROUNDS = 3, MAX_STEPS = 60, MAX_REJECTS = 3;
export const SAB_GOALS = [{ x: 8, y: -2 }, { x: 8, y: 0 }, { x: 8, y: 2 }];
const TOOLS = ['pick', 'lantern', 'cart'];

                                                                                                                                         
                                                                                                                                     
                                                                                 
const PATH_SPEC = [
  ['cross', 'NESW', true, 5], ['tee-NES', 'NES', true, 5], ['tee-NEW', 'NEW', true, 5], ['straight-NS', 'NS', true, 4], ['straight-EW', 'EW', true, 3],
  ['curve-NE', 'NE', true, 4], ['curve-NW', 'NW', true, 5],
  ['dead-N', 'N', false, 1], ['dead-E', 'E', false, 1], ['dead-NS', 'NS', false, 1], ['dead-EW', 'EW', false, 1], ['dead-NE', 'NE', false, 1], ['dead-NW', 'NW', false, 1],
  ['dead-NES', 'NES', false, 1], ['dead-NEW', 'NEW', false, 1], ['dead-NESW', 'NESW', false, 1]];
const ACTION_SPEC = [['break', ['pick'], 3], ['break', ['lantern'], 3], ['break', ['cart'], 3], ['repair', ['pick'], 2], ['repair', ['lantern'], 2], ['repair', ['cart'], 2],
  ['repair', ['pick', 'lantern'], 1], ['repair', ['pick', 'cart'], 1], ['repair', ['lantern', 'cart'], 1], ['rockfall', [], 3], ['map', [], 6]];
const NUGGETS = [...Array(16).fill(1), ...Array(8).fill(2), ...Array(4).fill(3)];
const openOf = letters => DNAME.map(d => letters.includes(d));
function buildDeck() {
  const cards = []; let n = 0;
  for (const [shape, letters, connected, count] of PATH_SPEC) for (let i = 0; i < count; i++) cards.push({ id: `c${++n}`, kind: 'path', shape, open: openOf(letters), connected });
  for (const [type, tools, count] of ACTION_SPEC) for (let i = 0; i < count; i++) cards.push({ id: `c${++n}`, kind: 'action', type, tools: tools.slice() });
  if (cards.length !== 67) throw new Error('Saboteur deck inventory changed');
  return cards;
}
const DECK = buildDeck(), CARD = new Map(DECK.map(c => [c.id, c]));
const rotate = open => [open[2], open[3], open[0], open[1]];
function describe(id) {
  const c = CARD.get(id);
  if (c.kind === 'path') return { id, card: 'path', openings: DNAME.filter((_, i) => c.open[i]).join(''), deadEnd: !c.connected };
  if (c.type === 'break') return { id, card: 'broken_tool', tool: c.tools[0] };
  if (c.type === 'repair') return { id, card: 'repair', tools: c.tools.slice() };
  return { id, card: c.type };
}

function nextRandom(state) { state.rng = (Math.imul(state.rng, 1664525) + 1013904223) >>> 0; return state.rng / 4294967296; }
function shuffle(state, values) { const a = values.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(nextRandom(state) * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
const key = (x, y) => `${x},${y}`;

                                        
function cellAt(round, x, y) { return round.grid[key(x, y)] ?? null; }
function goalAt(round, x, y) { return round.goals.findIndex(g => g.x === x && g.y === y); }
                                                                                                      
function reach(round) {
  const seen = new Set([key(0, 0)]), queue = [[0, 0]], touchedGoals = new Set();
  for (let h = 0; h < queue.length; h++) {
    const [x, y] = queue[h], c = cellAt(round, x, y);
    for (let d = 0; d < 4; d++) {
      if (!c.open[d]) continue; const nx = x + DIRS[d][0], ny = y + DIRS[d][1], n = cellAt(round, nx, ny);
      const g = goalAt(round, nx, ny); if (g >= 0 && !round.goals[g].revealed) { touchedGoals.add(g); continue; }
      if (!n || !n.open[OPP[d]] || seen.has(key(nx, ny))) continue;
      if (n.connected) { seen.add(key(nx, ny)); queue.push([nx, ny]); }
    }
  }
  return { passable: seen, touchedGoals: [...touchedGoals].sort() };
}
export function sabPlacementProblem(round, cardId, x, y, rotated) {
  const c = CARD.get(cardId); if (!c || c.kind !== 'path') return 'not a path card';
  if (!Number.isSafeInteger(x) || !Number.isSafeInteger(y) || Math.abs(x) > 20 || Math.abs(y) > 20) return 'cell outside the table';
  if (cellAt(round, x, y) || goalAt(round, x, y) >= 0) return 'cell already occupied';
  const open = rotated ? rotate(c.open) : c.open, passable = reach(round).passable;
  let neighbours = 0, connects = false;
  for (let d = 0; d < 4; d++) {
    const nx = x + DIRS[d][0], ny = y + DIRS[d][1], g = goalAt(round, nx, ny), n = cellAt(round, nx, ny);
    if (g >= 0 && !round.goals[g].revealed) { neighbours++; continue; }
    if (!n) continue; neighbours++;
    if (open[d] !== n.open[OPP[d]]) return `edge ${DNAME[d]} does not fit the neighbouring card`;
    if (open[d] && passable.has(key(nx, ny))) connects = true;
  }
  if (!neighbours) return 'card must be placed next to a card already on the table';
  if (!connects) return 'card would not have an uninterrupted connection to the start card';
  return null;
}
function frontierCells(round) {
  const out = new Set();
  for (const k of Object.keys(round.grid)) { const [x, y] = k.split(',').map(Number); for (const [dx, dy] of DIRS) { const nx = x + dx, ny = y + dy; if (!cellAt(round, nx, ny) && goalAt(round, nx, ny) < 0) out.add(key(nx, ny)); } }
  return [...out].map(k => k.split(',').map(Number)).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}
                                                                                                                                    
function tunnelDistance(round, targets) {
  const { passable, touchedGoals } = reach(round); if (targets.some(t => touchedGoals.includes(t))) return 0;
  let best = 30;
  for (const k of passable) { const [x, y] = k.split(',').map(Number), c = cellAt(round, x, y);
    for (let d = 0; d < 4; d++) { if (!c.open[d]) continue; const nx = x + DIRS[d][0], ny = y + DIRS[d][1]; if (cellAt(round, nx, ny)) continue;
      for (const t of targets) { const g = round.goals[t]; best = Math.min(best, 1 + Math.abs(nx - g.x) + Math.abs(ny - g.y) - 1); } } }
  return best;
}

                                   
export function generateSaboteur({ seed, botSkill }) {
  if (!Number.isSafeInteger(seed) || seed < 0 || ![0, 1].includes(botSkill)) throw new Error('Invalid Saboteur instance');
                                                                                                        
  const agentSeat = seed % PLAYERS;
  return { seed, agentSeat, botSkill, players: PLAYERS, rounds: ROUNDS, roleCards: { saboteur: 2, goldMiner: 4 }, handSize: HAND, firstPlayer: (seed * 7 + 3) % PLAYERS };
}
function startRound(state, instance) {
  const roles = shuffle(state, ['saboteur', 'saboteur', 'miner', 'miner', 'miner', 'miner']);
  const goalOrder = shuffle(state, ['gold', 'stone-NW', 'stone-SW']), deck = shuffle(state, DECK.map(c => c.id));
  const round = { number: state.rounds.length + 1, roles: roles.slice(0, PLAYERS), asideRole: roles[PLAYERS],
    grid: { [key(0, 0)]: { card: 'start', open: [true, true, true, true], connected: true, by: null } },
    goals: SAB_GOALS.map((g, i) => ({ ...g, type: goalOrder[i], revealed: false, open: null })),
    hands: Array.from({ length: PLAYERS }, () => []), deck, discard: { faceUp: 0, faceDown: 0 }, broken: Array.from({ length: PLAYERS }, () => []),
    peeks: Array.from({ length: PLAYERS }, () => []), suspicion: Array(PLAYERS).fill(0), lastPathBy: null, ended: false, winner: null };
  for (let r = 0; r < HAND; r++) for (let p = 0; p < PLAYERS; p++) round.hands[p].push(round.deck.shift());
  state.round = round; state.nuggetDeck = shuffle(state, state.nuggetDeck);
  state.current = state.rounds.length === 0 ? instance.firstPlayer : state.nextStarter;
}

                                                                                            
function event(state, text) { state.events.push(`R${state.round.number} P${state.current}: ${text}`); }
function drawAfterPlay(round, seat) { if (round.deck.length) round.hands[seat].push(round.deck.shift()); }
function removeFromHand(round, seat, id) { const i = round.hands[seat].indexOf(id); if (i < 0) return false; round.hands[seat].splice(i, 1); return true; }
                                                                                
function applyAction(state, seat, a) {
  const round = state.round, hand = round.hands[seat];
  if (a.action === 'pass_discard') {
    if (a.card == null) { if (hand.length) return 'you must discard one card when your hand is not empty'; event(state, 'passed (empty hand)'); return null; }
    if (!hand.includes(a.card)) return `card ${a.card} is not in your hand`;
    removeFromHand(round, seat, a.card); round.discard.faceDown++; drawAfterPlay(round, seat); event(state, 'passed, discarding one card face down'); return null;
  }
  if (!hand.includes(a.card)) return `card ${a.card} is not in your hand`;
  const c = CARD.get(a.card);
  if (a.action === 'place_path') {
    if (c.kind !== 'path') return 'that card is not a path card';
    if (round.broken[seat].length) return 'you have a broken tool in front of you and may not play path cards';
    const problem = sabPlacementProblem(round, a.card, a.x, a.y, a.rotated === true); if (problem) return problem;
    const before = tunnelDistance(round, [0, 1, 2]);
    removeFromHand(round, seat, a.card); round.grid[key(a.x, a.y)] = { card: a.card, open: a.rotated ? rotate(c.open) : c.open.slice(), connected: c.connected, by: seat };
    round.lastPathBy = seat; state.lastPathBy = seat;
    event(state, `placed path ${DNAME.filter((_, i) => round.grid[key(a.x, a.y)].open[i]).join('')}${c.connected ? '' : ' (dead end)'} at (${a.x},${a.y})`);
    resolveGoals(state);
    const after = tunnelDistance(round, round.goals.map((g, i) => i).filter(i => !round.goals[i].revealed));
    round.suspicion[seat] += !c.connected ? 2 : after > before ? 1.5 : after < before ? -1 : 0;
    if (!round.ended) drawAfterPlay(round, seat); return null;
  }
  if (a.action === 'play_broken_tool') {
    if (c.kind !== 'action' || c.type !== 'break') return 'that card is not a broken-tool card';
    if (!Number.isSafeInteger(a.target) || a.target < 0 || a.target >= PLAYERS) return 'unknown target player';
    if (round.broken[a.target].includes(c.tools[0])) return `player ${a.target} already has a broken ${c.tools[0]}`;
    removeFromHand(round, seat, a.card); round.broken[a.target].push(c.tools[0]); round.broken[a.target].sort();
    if (a.target !== seat) round.suspicion[seat] += round.suspicion[a.target] < 0.5 ? 1.5 : -0.5;
    event(state, `broke the ${c.tools[0]} of player ${a.target}`); drawAfterPlay(round, seat); return null;
  }
  if (a.action === 'play_repair') {
    if (c.kind !== 'action' || c.type !== 'repair') return 'that card is not a repair card';
    if (!Number.isSafeInteger(a.target) || a.target < 0 || a.target >= PLAYERS) return 'unknown target player';
    const tool = a.tool ?? (c.tools.length === 1 ? c.tools[0] : null);
    if (!tool || !c.tools.includes(tool)) return 'name one tool shown on the repair card';
    if (!round.broken[a.target].includes(tool)) return `player ${a.target} has no broken ${tool}`;
    removeFromHand(round, seat, a.card); round.broken[a.target] = round.broken[a.target].filter(t => t !== tool); round.discard.faceUp += 2;
    if (a.target !== seat) round.suspicion[seat] -= 0.5;
    event(state, `repaired the ${tool} of player ${a.target}`); drawAfterPlay(round, seat); return null;
  }
  if (a.action === 'play_rockfall') {
    if (c.kind !== 'action' || c.type !== 'rockfall') return 'that card is not a rockfall card';
    const target = cellAt(round, a.x, a.y);
    if (!target || target.card === 'start' || target.goal != null) return 'rockfall must remove a placed path card (never the start or a goal card)';
    const before = tunnelDistance(round, [0, 1, 2]);
    removeFromHand(round, seat, a.card); delete round.grid[key(a.x, a.y)]; round.discard.faceUp += 2;
    const after = tunnelDistance(round, [0, 1, 2]); round.suspicion[seat] += after > before ? 1.5 : target.connected ? 0.5 : -1;
    event(state, `played rockfall and removed the path card at (${a.x},${a.y})`); drawAfterPlay(round, seat); return null;
  }
  if (a.action === 'play_map') {
    if (c.kind !== 'action' || c.type !== 'map') return 'that card is not a map card';
    if (![0, 1, 2].includes(a.goal)) return 'goal must be 0 (top), 1 (middle) or 2 (bottom)';
    if (round.goals[a.goal].revealed) return 'that goal card is already face up';
    removeFromHand(round, seat, a.card); round.discard.faceUp++;
    if (!round.peeks[seat].some(p => p.goal === a.goal)) round.peeks[seat].push({ goal: a.goal, type: round.goals[a.goal].type === 'gold' ? 'gold' : 'stone' });
    event(state, `looked secretly at goal card ${a.goal}`); drawAfterPlay(round, seat); return null;
  }
  return 'unknown action';
}
function resolveGoals(state) {
  const round = state.round;
  for (let guard = 0; guard < 3; guard++) {
    const touched = reach(round).touchedGoals; if (!touched.length) return;
    for (const g of touched) {
      const goal = round.goals[g]; goal.revealed = true;
      if (goal.type === 'gold') { goal.open = [true, true, true, true]; event(state, `connected the tunnel to goal ${g}: the TREASURE`); finishRound(state, 'miners'); return; }
                                                                                                                                 
      const base = goal.type === 'stone-NW' ? openOf('NW') : openOf('SW'), options = [base, rotate(base)];
      const fits = o => [0, 1, 2, 3].every(d => { const n = cellAt(round, goal.x + DIRS[d][0], goal.y + DIRS[d][1]); return !n || n.open[OPP[d]] === o[d]; });
      goal.open = options.find(fits) ?? base; round.grid[key(goal.x, goal.y)] = { card: `goal-${g}`, open: goal.open, connected: true, by: null, goal: g };
      event(state, `connected the tunnel to goal ${g}: only stone`);
    }
  }
}
function finishRound(state, winner) {
  const round = state.round; round.ended = true; round.winner = winner;
  const miners = round.roles.map((r, i) => r === 'miner' ? i : -1).filter(i => i >= 0), saboteurs = round.roles.map((r, i) => r === 'saboteur' ? i : -1).filter(i => i >= 0);
  const gains = Array(PLAYERS).fill(0);
  if (winner === 'miners') {
    const drawn = state.nuggetDeck.splice(0, miners.length).sort((a, b) => b - a);
                                                                                                                                       
    const order = []; for (let k = 0; k < PLAYERS; k++) { const p = (round.lastPathBy - k + PLAYERS) % PLAYERS; if (round.roles[p] === 'miner') order.push(p); }
    for (const p of order) gains[p] += drawn.shift() ?? 0;
  } else if (saboteurs.length) {
    const each = saboteurs.length === 1 ? 4 : 3;
    for (const p of saboteurs) { let need = each; while (need > 0) { const i = state.nuggetDeck.findIndex(v => v <= need) ; if (i < 0) break; need -= state.nuggetDeck[i]; gains[p] += state.nuggetDeck[i]; state.nuggetDeck.splice(i, 1); } }
  }
  for (let p = 0; p < PLAYERS; p++) state.totals[p] += gains[p];
  state.rounds.push({ number: round.number, winner, roles: round.roles.slice(), asideRole: round.asideRole, treasureGoal: round.goals.findIndex(g => g.type === 'gold'), gains });
  state.events.push(`Round ${round.number} ended: ${winner === 'miners' ? 'the gold miners reached the treasure' : 'the treasure was not reached'}. Roles revealed: ${round.roles.map((r, i) => `P${i} ${r === 'miner' ? 'gold miner' : 'saboteur'}`).join(', ')}.`);
  state.nextStarter = ((round.lastPathBy ?? state.current) + 1) % PLAYERS;
}

                                                                    
function policyNoise(state, instance, seat, salt, variant = 0) { let h = (instance.seed * 2654435761 + state.turnCounter * 40503 + seat * 9176 + salt * 131 + variant * 7777777) >>> 0; h ^= h >>> 13; h = Math.imul(h, 1274126177) >>> 0; h ^= h >>> 16; return h / 4294967296; }
function goalTargets(round, seat) { const gold = round.peeks[seat].find(p => p.type === 'gold'); if (gold) return [gold.goal]; const stones = new Set(round.peeks[seat].filter(p => p.type === 'stone').map(p => p.goal)); const t = [0, 1, 2].filter(i => !stones.has(i) && !round.goals[i].revealed); return t.length ? t : [1]; }
function pathOptions(round, seat) {
  const out = []; for (const id of round.hands[seat]) { const c = CARD.get(id); if (c.kind !== 'path') continue;
    for (const [x, y] of frontierCells(round)) for (const rotated of [false, true]) { if (rotated && c.open.join() === rotate(c.open).join()) continue; if (!sabPlacementProblem(round, id, x, y, rotated)) out.push({ action: 'place_path', card: id, x, y, rotated }); } }
  return out;
}
function simulatePlacement(round, opt) {
  const c = CARD.get(opt.card), copy = { ...round, grid: { ...round.grid, [key(opt.x, opt.y)]: { card: opt.card, open: opt.rotated ? rotate(c.open) : c.open, connected: c.connected } } };
  return copy;
}
function policyAction(state, instance, seat, variant = 0) {
  const noiseOf = salt => policyNoise(state, instance, seat, salt, variant);
  const round = state.round, hand = round.hands[seat], role = round.roles[seat], skill = instance.botSkill, noiseAmp = [1.2, 0.6][skill];
  if (!hand.length) return { action: 'pass_discard', card: null };
  const cards = hand.map(id => CARD.get(id)), find = pred => cards.find(pred);
  const targets = goalTargets(round, seat), dist = tunnelDistance(round, targets), others = [0, 1, 2, 3, 4].filter(p => p !== seat);
  const repairSelf = cards.find(c => c.type === 'repair' && c.tools.some(t => round.broken[seat].includes(t)));
  const mostSuspect = others.slice().sort((p, q) => round.suspicion[q] - round.suspicion[p] || p - q)[0];
  const mostTrusted = others.slice().sort((p, q) => round.suspicion[p] - round.suspicion[q] || p - q)[0];
  if (role === 'miner') {
    if (repairSelf) return { action: 'play_repair', card: repairSelf.id, target: seat, tool: repairSelf.tools.find(t => round.broken[seat].includes(t)) };
    if (!round.broken[seat].length) {
      let best = null;
      for (const opt of pathOptions(round, seat)) { const sim = simulatePlacement(round, opt), d = tunnelDistance(sim, targets), c = CARD.get(opt.card);
        const score = d + (c.connected ? 0 : 3) + noiseAmp * noiseOf(opt.x * 31 + opt.y * 7 + (opt.rotated ? 3 : 0) + Number(opt.card.slice(1))); if (!best || score < best.score) best = { score, opt, d }; }
      if (best && best.d < dist) return best.opt;
    }
    const map = find(c => c.type === 'map'); if (map && !round.peeks[seat].some(p => p.type === 'gold') && dist <= 6) { const g = targets.find(t => !round.peeks[seat].some(p => p.goal === t)); if (g != null) return { action: 'play_map', card: map.id, goal: g }; }
    const brk = cards.find(c => c.type === 'break' && round.suspicion[mostSuspect] >= 2 && !round.broken[mostSuspect].includes(c.tools[0])); if (brk) return { action: 'play_broken_tool', card: brk.id, target: mostSuspect };
    const rep = cards.find(c => c.type === 'repair' && c.tools.some(t => round.broken[mostTrusted].includes(t)) && round.suspicion[mostTrusted] < 1);
    if (rep) return { action: 'play_repair', card: rep.id, target: mostTrusted, tool: rep.tools.find(t => round.broken[mostTrusted].includes(t)) };
    const dead = cards.find(c => c.kind === 'path' && !c.connected) ?? cards.find(c => c.type === 'break') ?? cards.find(c => c.type === 'rockfall') ?? cards[cards.length - 1];
    return { action: 'pass_discard', card: dead.id };
  }
                                                                                       
  const victim = others.slice().sort((p, q) => round.suspicion[p] - round.suspicion[q] || p - q).find(p => round.broken[p].length === 0);
  const brk = victim != null ? cards.find(c => c.type === 'break' && !round.broken[victim].includes(c.tools[0])) : null;
  if (brk && (dist <= 4 || noiseOf(5) < 0.3)) return { action: 'play_broken_tool', card: brk.id, target: victim };
  if (!round.broken[seat].length) {
    const opts = pathOptions(round, seat); let block = null, help = null;
    for (const opt of opts) { const d = tunnelDistance(simulatePlacement(round, opt), [0, 1, 2]), c = CARD.get(opt.card), n = noiseAmp * noiseOf(opt.x * 13 + opt.y * 5 + Number(opt.card.slice(1)));
      const blockScore = d + (c.connected ? 0 : 2) + n; if (!block || blockScore > block.score) block = { score: blockScore, opt, d };
      const helpScore = d + n; if (!help || helpScore < help.score) help = { score: helpScore, opt, d }; }
    const now = tunnelDistance(round, [0, 1, 2]);
    if (block && now <= 3 && block.d >= now) return block.opt;
    if (help && now >= 5 && noiseOf(9) < 0.5) return help.opt;
    if (block && block.d > now) return block.opt;
  }
  const rock = find(c => c.type === 'rockfall');
  if (rock) { let best = null; for (const k of Object.keys(round.grid)) { const cell = round.grid[k]; if (cell.card === 'start' || cell.goal != null) continue; const [x, y] = k.split(',').map(Number); const sim = { ...round, grid: { ...round.grid } }; delete sim.grid[k]; const d = tunnelDistance(sim, [0, 1, 2]); if (!best || d > best.d) best = { d, x, y }; }
    if (best && best.d > tunnelDistance(round, [0, 1, 2]) && tunnelDistance(round, [0, 1, 2]) <= 3) return { action: 'play_rockfall', card: rock.id, x: best.x, y: best.y }; }
  if (repairSelf) return { action: 'play_repair', card: repairSelf.id, target: seat, tool: repairSelf.tools.find(t => round.broken[seat].includes(t)) };
  const toss = cards.find(c => c.kind === 'path' && c.connected && c.open.filter(Boolean).length >= 3) ?? cards.find(c => c.type === 'repair') ?? cards[0];
  return { action: 'pass_discard', card: toss.id };
}

                                    
function roundOverByExhaustion(round) { return !round.deck.length && round.hands.every(h => !h.length); }
function advance(state, instance) {
  for (let guard = 0; guard < 400 && !state.ended; guard++) {
    if (state.round.ended) { if (state.rounds.length >= ROUNDS) { endGame(state, instance); return; } startRound(state, instance); continue; }
    if (roundOverByExhaustion(state.round)) { finishRound(state, 'saboteurs'); continue; }
    if (state.current === instance.agentSeat) {
      if (state.round.hands[state.current].length) return;
      event(state, 'passed (empty hand)'); state.current = (state.current + 1) % PLAYERS; continue;                                   
    }
    state.turnCounter++;
    const a = policyAction(state, instance, state.current), problem = applyAction(state, state.current, a);
    if (problem) { const fallback = state.round.hands[state.current][0]; applyAction(state, state.current, { action: 'pass_discard', card: fallback ?? null }); }
    if (!state.round.ended) state.current = (state.current + 1) % PLAYERS;
  }
}
function endGame(state, instance) {
  const mine = state.totals[instance.agentSeat], best = Math.max(...state.totals);
  state.ended = true; state.outcome = mine >= best ? 'success' : 'failure'; state.reason = mine >= best ? 'highest_or_tied_highest_nugget_total' : 'another_player_has_more_nuggets';
}
const ACTIONS = ['place_path', 'play_broken_tool', 'play_repair', 'play_rockfall', 'play_map', 'pass_discard'];
export function normalizeSaboteurAction(v) {
  if (!v || typeof v !== 'object' || Array.isArray(v) || !ACTIONS.includes(v.action)) return null;
  const spec = { place_path: [['card', 'x', 'y'], ['rotated']], play_broken_tool: [['card', 'target'], []], play_repair: [['card', 'target'], ['tool']], play_rockfall: [['card', 'x', 'y'], []], play_map: [['card', 'goal'], []], pass_discard: [[], ['card']] }[v.action];
  if (Object.keys(v).some(k => k !== 'action' && !spec[0].includes(k) && !spec[1].includes(k)) || spec[0].some(k => v[k] === undefined)) return null;
  const out = { action: v.action };
  if (v.card !== undefined) { if (v.card === null ? v.action !== 'pass_discard' : typeof v.card !== 'string' || !/^c\d{1,2}$/.test(v.card)) return null; out.card = v.card; }
  for (const f of ['x', 'y', 'target', 'goal']) if (v[f] !== undefined) { if (!Number.isSafeInteger(v[f]) || Math.abs(v[f]) > 99) return null; out[f] = v[f]; }
  if (v.action === 'place_path') { if (v.rotated !== undefined && typeof v.rotated !== 'boolean') return null; out.rotated = v.rotated === true; }
  if (v.tool !== undefined) { if (!TOOLS.includes(v.tool)) return null; out.tool = v.tool; }
  if (v.action === 'pass_discard' && out.card === undefined) out.card = null;
  return out;
}

export function createSaboteur(instance) {
  const state = { step: 0, rng: (instance.seed * 2246822519 + 3266489917) >>> 0, rounds: [], round: null, totals: Array(PLAYERS).fill(0), nuggetDeck: NUGGETS.slice(), current: 0, nextStarter: 0, lastPathBy: null,
    turnCounter: 0, events: [], rejections: 0, lastRejection: null, ended: false, outcome: null, reason: null };
  startRound(state, instance); advance(state, instance);
  const seat = instance.agentSeat;
  return {
    state,
    step(input) {
      const a = normalizeSaboteurAction(input); if (!a) throw new Error('Malformed Saboteur action');
      if (state.ended) throw new Error('Saboteur game ended');
      state.step++; const previousEvents = state.events; state.events = []; state.lastRejection = null;
      const problem = applyAction(state, seat, a);
      if (problem) { state.events = previousEvents; state.rejections++; state.lastRejection = problem; if (state.rejections >= MAX_REJECTS) { state.ended = true; state.outcome = 'failure'; state.reason = 'three_rejected_illegal_actions'; } }
      else { if (!state.round.ended) state.current = (state.current + 1) % PLAYERS; advance(state, instance); }
      if (!state.ended && state.step >= MAX_STEPS) { state.ended = true; state.outcome = 'failure'; state.reason = 'agent_turn_budget_exhausted_before_round_three_ended'; }
    },
    publicView() {
      const round = state.round, roleNow = round.roles[seat];
      const cells = Object.entries(round.grid).map(([k, c]) => { const [x, y] = k.split(',').map(Number); return { x, y, card: c.card === 'start' ? 'start' : c.goal != null ? 'goal_stone' : 'path', openings: DNAME.filter((_, i) => c.open[i]).join(''), deadEnd: !c.connected }; }).sort((p, q) => p.x - q.x || p.y - q.y);
      const view = {
        task: 'Saboteur, 5 players, 3 rounds. You are player ' + seat + '. On your turn play exactly one card: place a path card (edges must match all neighbours, must connect back to the start through open tunnels; 180-degree rotation allowed; not while you have a broken tool), put a broken tool or repair in front of a player, play rockfall (remove one placed path card), play map (peek at one face-down goal), or pass by discarding one card face down. You then draw automatically. Gold miners win a round by connecting the start to the treasure goal; saboteurs win if it is never reached. Most nuggets after round 3 wins (ties share). Three rejected actions lose the game.',
        you: { seat, role: roleNow === 'miner' ? 'gold_miner' : 'saboteur', nuggets: state.totals[seat], hand: round.hands[seat].map(describe), brokenTools: round.broken[seat].slice(), goalKnowledge: round.peeks[seat].slice() },
        round: round.number, currentPlayer: state.ended ? null : state.current, turnOrder: [0, 1, 2, 3, 4], coordinates: 'x grows east toward the goals, y grows south; start at (0,0)',
        tunnel: cells, goals: round.goals.map((g, i) => ({ goal: i, x: g.x, y: g.y, faceUp: g.revealed, ...(g.revealed ? { shows: g.type === 'gold' ? 'treasure' : 'stone' } : {}) })),
        players: [0, 1, 2, 3, 4].map(p => ({ seat: p, handCount: round.hands[p].length, brokenTools: round.broken[p].slice() })),
        drawPile: round.deck.length, discardPile: round.discard.faceUp + round.discard.faceDown,
        completedRounds: state.rounds.map(r => ({ round: r.number, winningTeam: r.winner === 'miners' ? 'gold_miners' : 'saboteurs', roles: r.roles.map(x => x === 'miner' ? 'gold_miner' : 'saboteur'), yourNuggetsGained: r.gains[seat] })),
        eventsSinceYourLastTurn: state.events.slice(-30), rejectedLastAction: state.lastRejection, rejectedActionsSoFar: state.rejections, turnsRemaining: MAX_STEPS - state.step,
        ...(state.ended ? { finalNuggetTotals: state.rounds.length >= ROUNDS ? state.totals.slice() : null } : {}) };
      return { text: JSON.stringify(view), reward: state.ended && state.outcome === 'success' ? 1 : 0, info: { round: round.number, rejections: state.rejections },
        terminal: { ended: state.ended, outcome: state.outcome, reason: state.reason, ...(state.ended ? { score: state.outcome === 'success' ? 1 : 0, evaluation: { agentTurns: state.step, rejectedActions: state.rejections, totals: state.totals.slice(), agentTotal: state.totals[seat], marginOverRunnerUp: state.totals[seat] - Math.max(...state.totals.filter((_, p) => p !== seat)), rounds: state.rounds.map(r => ({ ...r })) } } : {}) } };
    },
    render() {
      const r = new Raster(640, 420), round = state.round, cell = 34, ox = 120, oy = 190;
      r.text(`SABOTEUR ROUND ${round.number} NUGGETS ${state.totals[seat]}`, 16, 14, [38, 54, 72], 2);
      for (const [k, c] of Object.entries(round.grid)) { const [x, y] = k.split(',').map(Number), px = ox + x * cell, py = oy + y * cell;
        r.rect(px, py, cell - 2, cell - 2, c.card === 'start' ? [120, 170, 110] : c.goal != null ? [170, 160, 150] : [196, 170, 128]);
        const cx = px + cell / 2 - 1, cy = py + cell / 2 - 1; for (let d = 0; d < 4; d++) if (c.open[d]) r.line(cx, cy, cx + DIRS[d][0] * cell / 2, cy + DIRS[d][1] * cell / 2, [70, 50, 35], 5);
        if (!c.connected) r.rect(cx - 5, cy - 5, 10, 10, [60, 60, 60]); }
      for (const g of round.goals) if (!g.revealed) { r.rect(ox + g.x * cell, oy + g.y * cell, cell - 2, cell - 2, [60, 80, 120]); r.text('?', ox + g.x * cell + 12, oy + g.y * cell + 10, [255, 255, 255], 2); }
      r.text(`DECK ${round.deck.length}`, 16, 396, [38, 54, 72], 2);
      return r;
    },
  };
}

