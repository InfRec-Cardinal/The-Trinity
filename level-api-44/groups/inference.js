import { rulesFor } from "../rules.mjs";

const MARKS = [ "triangle", "square", "circle" ];

const ROOMS = [ "window", "tool rack", "arch" ];

const DIRS = [ [ "up", 0, -1 ], [ "right", 1, 0 ], [ "down", 0, 1 ], [ "left", -1, 0 ] ];

const sum = a => a.reduce((x, y) => x + y, 0);

const mod = (x, n) => (x % n + n) % n;

function feedback(secret, guess) {
    let exact = 0;
    const s = new Map, g = new Map;
    secret.forEach((x, i) => {
        if (x === guess[i]) exact++; else {
            s.set(x, (s.get(x) || 0) + 1);
            g.set(guess[i], (g.get(guess[i]) || 0) + 1);
        }
    });
    return [ exact, [ ...s ].reduce((n, [x, count]) => n + Math.min(count, g.get(x) || 0), 0) ];
}

function hypotheses() {
    return [ 0, 1, 2 ].flatMap(p => [ 1, 2 ].flatMap(d => [ 0, 1 ].flatMap(a => [ 0, 1 ].map(r => ({
        p: p,
        d: d,
        a: a,
        r: r
    })))));
}

function opponent(v, h, t, signal) {
    const base = [ [ 8, 4, 1 ], [ 9, 3, 1 ], [ 7, 5, 1 ], [ 8, 5, 1 ] ][v];
    const shift = mod(h.p + h.d * t + h.a * Math.floor(t / 2) + h.r * signal, 3);
    const order = v === 1 && t % 2 === 1 ? [ ...base ].reverse() : base;
    return order.map((_, i) => order[mod(i - shift, 3)]);
}

function winsBattle(own, other) {
    return own.filter((n, i) => n > other[i]).length >= 2;
}

function nextSignal(v, own, other, prior = 0) {
    if (v === 1) return own.indexOf(Math.max(...own));
    if (v === 2) {
        const loss = own.findIndex((x, i) => x <= other[i]);
        return loss < 0 ? 0 : loss;
    }
    if (v === 3) return prior;
    return own.indexOf(Math.min(...own));
}

function transformed(code, v, failedRound) {
    if (v < 2) return [ ...code ];
    if (v === 3 && failedRound % 2 === 0) return [ ...code ].reverse();
    return [ ...code.slice(1), code[0] ];
}

function itemMatches(item, query, remembered) {
    return [ "mark", "rim", "dots" ].every(k => {
        const q = query[k];
        if (typeof q === "number") return item[k] === q;
        const ref = remembered[q.ref];
        if (!ref) return false;
        return item[k] === (q.op === "opposite" ? 3 - ref[k] : ref[k]);
    });
}

function mazeGraph(seed, w = 4, h = 4) {
    let n = seed >>> 0;
    const rand = () => {
        n = Math.imul(n, 1664525) + 1013904223 >>> 0;
        return n / 4294967296;
    };
    const adj = Array.from({
        length: w * h
    }, () => []), seen = new Set([ 0 ]), stack = [ 0 ];
    const neighbors = u => DIRS.map(([, dx, dy]) => [ u % w + dx, Math.floor(u / w) + dy ]).filter(([x, y]) => x >= 0 && x < w && y >= 0 && y < h).map(([x, y]) => y * w + x);
    const add = (a, b) => {
        adj[a].push(b);
        adj[b].push(a);
    };
    while (stack.length) {
        const u = stack.at(-1), ns = neighbors(u).filter(x => !seen.has(x));
        if (!ns.length) stack.pop(); else {
            const b = ns[Math.floor(rand() * ns.length)];
            add(u, b);
            seen.add(b);
            stack.push(b);
        }
    }
    const missing = [];
    for (let u = 0; u < w * h; u++) for (const b of neighbors(u)) if (u < b && !adj[u].includes(b)) missing.push([ u, b ]);
    for (let i = missing.length - 1; i > 0; i--) {
        const j = Math.floor(rand() * (i + 1));
        [missing[i], missing[j]] = [ missing[j], missing[i] ];
    }
    const gates = missing.slice(0, 2), shortcuts = missing.slice(2, 4);
    gates.forEach(([a, b]) => add(a, b));
    return {
        w: w,
        h: h,
        adj: adj,
        gates: gates,
        shortcuts: shortcuts
    };
}

function mazeExits(graph, pos, returned, variant) {
    let exits = [ ...graph.adj[pos] ];
    if (returned && variant >= 2) {
        for (const [a, b] of graph.gates.slice(0, variant === 3 ? 2 : 1)) {
            if (a === pos) exits = exits.filter(x => x !== b);
            if (b === pos) exits = exits.filter(x => x !== a);
        }
        for (const [a, b] of graph.shortcuts.slice(0, variant === 3 ? 2 : 1)) {
            if (a === pos) exits.push(b);
            if (b === pos) exits.push(a);
        }
    }
    return exits;
}

const searchBudget = [ 18, 18, 18, 18 ];

const mazeBudget = [ 32, 58, 58, 58 ];

const codeBudget = [ 6, 7, 7, 8 ];

function validVariant(v) {
    return Number.isInteger(v) && v >= 0 && v < 4;
}

function safeStep(ui, message, fn) {
    if (!ui.isEnded()) ui.step(message, fn);
}

export function createLevel(node, v, ui) {
    if (![ "b", "c-a", "d-a", "d-b" ].includes(node)) return null;
    if (!validVariant(v)) throw new RangeError("variant must be 0..3");
    return {
        b: blotto,
        "c-a": search,
        "d-a": maze,
        "d-b": codeLock
    }[node](v, ui);
}

function blotto(v, ui) {
    const hidden = hypotheses()[[ 15, 5, 20, 11 ][v]], total = v === 3 ? 14 : 13;
    const archiveSignals = {0: 0, 1: 1, 2: 2, 4: 2};
    let round = 0, wins = 0, signal = 0, previousMin = 0;
    let selected = {kind: "archive", index: 0};
    const opened = new Set([ 0 ]), records = [];
    const rules = rulesFor("b", v);
    function draw() {
        ui.camera.position.set(0, 9, 11);
        ui.camera.lookAt(0, .2, 0);
        const record = selected.kind === "archive" ? {
            time: selected.index, signal: archiveSignals[selected.index], own: null,
            other: opponent(v, hidden, selected.index, archiveSignals[selected.index])
        } : records[selected.index - 1];
        ui.text(selected.kind === "archive" ? `A${selected.index}` : `R${selected.index}`, -4.5, .3, -3.6, .38);
        ui.text(`T${record.time}`, -1.5, .3, -3.6, .38);
        ui.text(`S${record.signal}`, 1.5, .3, -3.6, .38);
        for (let i = 0; i < 3; i++) {
            const x = (i - 1) * 3.3;
            ui.box(x, 0, 0, 2.9, .2, 6, 4349801);
            ui.text("ABC"[i], x, .3, 0, .4);
            for (const [counts, direction, color] of [[record.other, -1, 14136686], [record.own, 1, 7714712]]) {
                if (!counts) continue;
                const count = counts[i];
                for (let j = 0; j < count; j++) {
                    const px = x + (j % 4 - 1.5) * .5, pz = direction * (.7 + Math.floor(j / 4) * .5);
                    ui.box(px, .32, pz, .28, .45, .28, color);
                    ui.ball(px, .64, pz, .13, color);
                }
                ui.text(String(count), x, .3, direction * 2.7, .44);
            }
            ui.number("ABC"[i], "b-" + i, i === 2 ? total - 8 : 4, 0, total);
        }
        for (const t of [0, 1, 2, 4]) {
            if (opened.has(t)) ui.command(`replay archive ${t} / free`, () => {
                selected = {kind: "archive", index: t};
                ui.redraw();
            });
            else ui.command(`read archive ${t} (1 step)`, () => safeStep(ui, "read archive " + t, () => {
                opened.add(t);
                selected = {kind: "archive", index: t};
            }));
        }
        records.forEach((_, i) => ui.command(`review round ${i + 1} / free`, () => {
            selected = {kind: "round", index: i + 1};
            ui.redraw();
        }));
        ui.command("submit allocation (1 step)", () => {
            const own = [0, 1, 2].map(i => Number(ui.value("b-" + i)));
            if (own.some(x => !Number.isInteger(x) || x < 0) || sum(own) !== total) return;
            safeStep(ui, "submit allocation", () => {
                const other = opponent(v, hidden, round + 4, signal), won = winsBattle(own, other), oldMin = previousMin;
                records.push({time: round + 4, signal: signal, own: own, other: other});
                previousMin = own.indexOf(Math.min(...own));
                signal = nextSignal(v, own, other, oldMin);
                round++;
                wins += Number(won);
                selected = {kind: "round", index: round};
                if (round === 6) ui.finish(wins >= 5, "Battle evaluated.");
            });
        });
    }
    return {
        rules: rules,
        budget: 9,
        draw: draw,
        task: () => ({openedArchives: [...opened].sort((a, b) => a - b), completedRounds: round, selectedRecord: {...selected}})
    };
}

function search(v, ui) {
    const objects = Array.from({
        length: 12
    }, (_, i) => ({
        mark: i % 3,
        rim: Math.floor(i / 3) % 2 + 1,
        dots: Math.floor(i / 6) + 1
    }));
    const original = Array.from({
        length: 12
    }, (_, i) => objects[(i * [ 1, 5, 7, 11 ][v] + [ 0, 3, 5, 7 ][v]) % 12]);
    const targetIds = [ [ 1, 10, 6, 4 ], [ 8, 2, 5, 7 ], [ 1, 10, 6, 4 ], [ 2, 9, 4, 7 ] ][v];
    const roomLabel = id => `${ROOMS[Math.floor(id / 4)]}${id % 4 + 1} slot`;
    const refFor = (id, k, op) => original.findIndex((o, j) => j !== id && (op === "opposite" ? 3 - o[k] : o[k]) === original[id][k]);
    const queries = targetIds.map(id => Object.fromEntries([ "mark", "rim", "dots" ].map(k => {
        const relational = v >= 1 && k === "mark" || v >= 2 && k === "rim" || v === 3 && k === "dots";
        return [ k, relational ? {
            ref: refFor(id, k, k === "rim" ? "opposite" : "same"),
            op: k === "rim" ? "opposite" : "same"
        } : original[id][k] ];
    })));
    function jar(o, x, y, z) {
        ui.ball(x, y + 1, z, .35, 6469290);
        if (o.mark === 1) ui.box(x, y + 1.4, z, .45, .12, .45, 14073206);
        else {
            const cap = new ui.THREE.Mesh(new ui.THREE.CylinderGeometry(.32, .32, .12, o.mark === 0 ? 3 : 32), new ui.THREE.MeshStandardMaterial({color: 14073206, roughness: .65}));
            cap.position.set(x, y + 1.4, z);
            ui.group().add(cap);
        }
        for (let k = 0; k < o.rim; k++) ui.box(x, y + .88 + k * .18, z + .34, .65, .055, .05, 15261639);
        for (let k = 0; k < o.dots; k++) ui.ball(x + (k - (o.dots - 1) / 2) * .16, y + 1.22, z + .33, .045, 2307904);
    }
    const describe = o => `${MARKS[o.mark]} / ${o.rim} rings / ${o.dots} dots`;
    const queryText = q => [ "mark", "rim", "dots" ].map(k => {
        const value = q[k], name = {
            mark: "mark",
            rim: "ring count",
            dots: "dot count"
        }[k];
        if (typeof value === "number") return k === "mark" ? MARKS[value] : `${value}${k === "rim" ? " rings" : " dots"}`;
        return `${name}${value.op === "opposite" ? " versus " : " same as "}${roomLabel(value.ref)}${value.op === "opposite" ? " opposite (1<->2)" : ""}`;
    }).join("; ");
    let room = 0, sealed = false, scanned = false, bag = [], delivered = [];
    const taken = new Set;
    const objectAt = (r, slot) => r * 4 + (v === 3 && sealed ? mod(slot - 1, 4) : slot);
    const rules = rulesFor("c-a", v);
    function draw() {
        ui.camera.position.set(0, 4.5, 10);
        ui.camera.lookAt(0, 1, 0);
        ui.box(0, 1.7, -1.8, 11, 3.6, .2, 7112067);
        if (room === 0) {
            ui.box(-4.5, 2, -1.6, .7, 1.5, .1, 9554139);
            ui.box(-4.5, 2, -1.5, .06, 1.5, .1, 15260604);
        } else if (room === 1) for (let k = 0; k < 3; k++) ui.box(4.3 + k * .15, 2, -1.6, .08, 1, .1, 14992497); else {
            ui.box(-4.7, 1.4, -1.5, .3, 2.8, .3, 12958107);
            ui.box(-3.7, 1.4, -1.5, .3, 2.8, .3, 12958107);
            ui.box(-4.2, 2.8, -1.5, 1.3, .3, .3, 12958107);
        }
        for (let s = 0; s < 4; s++) {
            const x = (s - 1.5) * 2.35, id = objectAt(room, s), o = original[id];
            ui.box(x, 1, -.46, 2, 2, .08, 3427156);
            for (const side of [ -1, 1 ]) ui.box(x + side * .96, 1, 0, .08, 2, 1, 3427156);
            for (const height of [ 0, 2 ]) ui.box(x, height, 0, 2, .08, 1, 3427156);
            if (scanned && !taken.has(id)) {
                jar(o, x, 0, 0);
            } else ui.box(x, 1, .55, 1.9, 1.9, .08, 8164747);
            ui.text(String(s + 1), x, .2, .8, .3);
            if (sealed) ui.command(`take ${s + 1} slot (1 step)`, () => {
                if (bag.length >= 2) {
                    ui.say("Bag full.");
                    return;
                }
                if (taken.has(id)) {
                    ui.say("Cabinet empty.");
                    return;
                }
                safeStep(ui, "take " + ROOMS[room] + (s + 1) + " slot", () => {
                    taken.add(id);
                    bag.push(id);
                    ui.say("Item taken.");
                });
            });
        }
        ui.command("scan room (1 step)", () => safeStep(ui, "scan " + ROOMS[room], () => {
            scanned = true;
            ui.say("Attributes visible in current room only.");
        }));
        ROOMS.forEach((name, r) => {
            if (r !== room) ui.command("move to " + name + " (1 step)", () => safeStep(ui, "move to " + name, () => {
                room = r;
                scanned = false;
            }));
        });
        if (!sealed) ui.command("seal and receive orders (1 step)", () => safeStep(ui, "seal and receive orders", () => {
            sealed = true;
            scanned = false;
            ui.say(v === 3 ? "Items shifted right; references use original positions." : "Orders received.");
        })); else {
            bag.forEach((id, i) => jar(original[id], -1 + i * 2, 0, 2.8));
            ui.command("deliver batch (1 step)", () => {
                if (room !== 0) {
                    ui.say("Delivery requires the window room.");
                    return;
                }
                if (bag.length !== 2) {
                    ui.say("A batch must contain exactly two items.");
                    return;
                }
                safeStep(ui, "deliver batch", () => {
                    let ok;
                    if (v >= 2) ok = bag.every((id, i) => itemMatches(original[id], queries[delivered.length + i], original)); else ok = bag.every(id => targetIds.includes(id) && !delivered.includes(id));
                    if (!ok) {
                        ui.finish(false, "Items or order incorrect.");
                        return;
                    }
                    delivered.push(...bag);
                    bag = [];
                    if (delivered.length === 4) ui.finish(true, "All four orders delivered."); else ui.say("First batch accepted.");
                });
            });
            ui.command("return last item (1 step)", () => {
                const id = bag.at(-1);
                if (id === void 0 || Math.floor(id / 4) !== room) {
                    ui.say("Return requires the item's original room.");
                    return;
                }
                safeStep(ui, "return last item", () => {
                    bag.pop();
                    taken.delete(id);
                });
            });
        }
        ui.overlay(`${ROOMS[room]} / held ${bag.length}/2 / delivered ${delivered.length}/4 · ${sealed ? "order phase" : "observation phase"}` + (sealed ? "\n" + queries.map((q, i) => `Order ${i + 1}: ${queryText(q)}`).join("\n") : "") + (scanned ? "\nCurrent scan: " + Array.from({
            length: 4
        }, (_, slot) => {
            const id = objectAt(room, slot);
            return `${slot + 1} slot: ${taken.has(id) ? "empty" : describe(original[id])}`;
        }).join("; ") : "\nCabinets closed.") + (bag.length ? "\n" + bag.map((id, i) => `Held ${i + 1}: ${describe(original[id])}`).join("; ") : ""));
    }
    return {
        rules: rules,
        budget: searchBudget[v],
        draw: draw
    };
}

function maze(v, ui) {
    const graph = mazeGraph([ 714, 129, 442, 916 ][v]);
    const tokens = [ [ 6, 9, 14 ], [ 10, 3, 12 ], [ 7, 13, 2 ], [ 11, 4, 14, 3 ] ][v];
    const start = 0, goal = 15;
    let pos = start, returned = false, collected = [];
    const point = id => `(${id % 4 + 1},${Math.floor(id / 4) + 1})`;
    const rules = rulesFor("d-a", v);
    function draw() {
        const exits = mazeExits(graph, pos, returned, v), localFacts = [];
        ui.camera.position.set(0, 9, 8);
        ui.camera.lookAt(0, 0, 0);
        ui.box(0, 0, 0, 2, .2, 2, 7906716);
        ui.ball(0, .6, 0, .3, 15254384);
        ui.text(point(pos), 0, 1.4, 0, .38);
        const token = tokens.indexOf(pos);
        if (token >= 0) ui.text("ABCD"[token], 0, .4, 1.1, .3);
        for (const [label, dx, dy] of DIRS) {
            const x = pos % 4 + dx, y = Math.floor(pos / 4) + dy, b = y * 4 + x, inside = x >= 0 && x < 4 && y >= 0 && y < 4, open = inside && exits.includes(b);
            ui.box(dx * 2.3, open ? 0 : .7, dy * 2.3, 1.9, open ? .15 : 1.4, 1.9, open ? 6721159 : 3426388);
            const exitLabel = label + ": " + (open ? "open " + point(b) : "wall");
            localFacts.push(exitLabel);
            if (inside && v >= 2) {
                const gate = graph.gates.slice(0, v === 3 ? 2 : 1).some(e => e.includes(pos) && e.includes(b));
                const shortcut = graph.shortcuts.slice(0, v === 3 ? 2 : 1).some(e => e.includes(pos) && e.includes(b));
                if (gate || shortcut) {
                    const gateLabel = gate ? "amber: outbound open / return closed" : "cyan: outbound closed / return open";
                    localFacts.push(label + " gate " + gateLabel);
                    ui.box(dx * 1.5, 1.6, dy * 1.5, dx === 0 ? 1.9 : .12, .12, dy === 0 ? 1.9 : .12, gate ? 0xffd391 : 0x8df0e2);
                }
            }
            ui.command("move " + label + " (1 step)", () => safeStep(ui, "move " + label, () => {
                if (!open) {
                    ui.say("Wall hit; position unchanged.");
                    return;
                }
                pos = b;
                const k = tokens.indexOf(pos);
                if (k >= 0 && !collected.includes(k) && (v === 0 || k === collected.length)) {
                    collected.push(k);
                    ui.say("Collected stamp " + "ABCD"[k]);
                } else if (k >= 0 && !collected.includes(k)) ui.say("Stamp " + "ABCD"[k] + " is out of sequence."); else ui.say("Position " + point(pos));
                if (pos === goal && collected.length === tokens.length && !returned) {
                    returned = true;
                    ui.say(v >= 2 ? "Parcel collected; phase gates switched." : "Parcel collected.");
                }
                if (returned && pos === start) ui.finish(true, "Stamps and parcel returned.");
            }));
        }
        ui.overlay(`Position ${point(pos)} / stamps ${collected.map(k => "ABCD"[k]).join("") || "none"} / ${tokens.length} · ${returned ? "return: reach S(1,1)" : "outbound: collect stamps, then reach G(4,4)"}\n${localFacts.join("; ")}${token >= 0 ? "\nCurrent room stamp: " + "ABCD"[token] : ""}`);
    }
    return {
        rules: rules,
        budget: mazeBudget[v],
        draw: draw
    };
}

function codeLock(v, ui) {
    const length = [ 4, 5, 5, 6 ][v], colors = [ 6, 5, 6, 5 ][v];
    let secret = [ [ 4, 1, 4, 2 ], [ 3, 0, 3, 4, 1 ], [ 5, 2, 5, 0, 2 ], [ 4, 1, 4, 0, 1, 3 ] ][v].slice();
    const oldGuesses = [ Array(length).fill(0), Array(length).fill(1) ];
    const archive = oldGuesses.map(g => ({
        guess: g,
        result: feedback(secret, g)
    })), history = [];
    let round = 0;
    const alphabet = "ABCDEF".slice(0, colors).split("");
    const rules = rulesFor("d-b", v);
    function draw() {
        ui.camera.position.set(0, 12, 8);
        ui.camera.lookAt(0, 0, 0);
        const rows = [...archive, ...history], palette = [0x66c2a5, 0xe6b862, 0x8da0cb, 0xd993ad, 0xa6c878, 0xb49cd1];
        ui.box(0, -.08, 0, 11, .2, 9.8, 4349801);
        for (let i = 0; i < length; i++) {
            ui.text(String(i + 1), -3.7 + i * 1.02, .35, -4.6, .25);
            ui.choice("#" + (i + 1) + " position", "code-" + i, alphabet);
        }
        rows.forEach((entry, row) => {
            const z = -3.9 + row * .86;
            ui.box(0, .06, z, 10.6, .12, .74, row < 2 ? 5463404 : 3756632);
            ui.text(row < 2 ? `A${row + 1}` : `G${row - 1}`, -4.75, .38, z, .32);
            entry.guess.forEach((value, i) => {
                const x = -3.7 + i * 1.02;
                ui.ball(x, .33, z, .23, palette[value]);
                ui.text(alphabet[value], x, .65, z, .36);
            });
            for (let i = 0; i < length; i++) {
                const x = 3 + i % 3 * .58, pz = z + (Math.floor(i / 3) - .5) * .28;
                ui.box(x, .2, pz, .38, .08, .22, 7963526);
                if (i < entry.result[0]) ui.ball(x, .34, pz, .13, 2373952);
                else if (i < sum(entry.result)) ui.ball(x, .34, pz, .13, 15921625);
            }
        });
            ui.command("submit code (1 step)", () => {
            const guess = Array.from({
                length: length
            }, (_, i) => alphabet.indexOf(ui.value("code-" + i)));
            if (guess.some(x => x < 0)) {
                ui.say("Invalid symbol.");
                return;
            }
            safeStep(ui, "submit code " + guess.map(x => alphabet[x]).join(""), () => {
                const result = feedback(secret, guess);
                round++;
                const entry = {
                    guess: guess,
                    result: result
                };
                history.push(entry);
                ui.say(`exact ${result[0]} / misplaced ${result[1]}`);
                if (result[0] === length) ui.finish(true, "Code matched."); else secret = transformed(secret, v, round);
            });
        });
    }
    return {
        rules: rules,
        budget: codeBudget[v],
        draw: draw,
        task: () => ({recordIds: ["A1", "A2", ...history.map((_, i) => "G" + (i + 1))]})
    };
}
