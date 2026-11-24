import { rulesFor } from "../rules.mjs";

const validVariant = v => Number.isInteger(v) && v >= 0 && v < 4;

const gateConfigs = [ {
    length: 7,
    aCargo: [ 6 ],
    bCargo: [],
    aGates: [ {
        edge: 2,
        out: 1,
        back: 1
    }, {
        edge: 4,
        out: 4,
        back: 4
    } ],
    bGates: [ {
        edge: 2,
        plate: 3
    } ],
    budget: 17,
    title: ""
}, {
    length: 7,
    aCargo: [ 6 ],
    bCargo: [ 6 ],
    aGates: [ {
        edge: 2,
        out: 1,
        back: 1
    }, {
        edge: 4,
        out: 4,
        back: 4
    } ],
    bGates: [ {
        edge: 2,
        plate: 3
    } ],
    budget: 18,
    title: ""
}, {
    length: 8,
    aCargo: [ 7 ],
    bCargo: [ 5 ],
    aGates: [ {
        edge: 0,
        out: 0,
        back: 2
    }, {
        edge: 2,
        out: 1,
        back: 2
    }, {
        edge: 5,
        out: 5,
        back: 4
    } ],
    bGates: [ {
        edge: 3,
        plate: 4
    } ],
    budget: 20,
    title: ""
}, {
    length: 8,
    aCargo: [ 7 ],
    bCargo: [ 7 ],
    aGates: [ {
        edge: 0,
        out: 0,
        back: 2
    }, {
        edge: 2,
        out: 1,
        back: 2
    }, {
        edge: 5,
        out: 5,
        back: 4
    } ],
    bGates: [ {
        edge: 2,
        plate: 3
    }, {
        edge: 5,
        plate: 5
    } ],
    budget: 23,
    title: ""
} ];

function gateInitial() {
    return {
        a: 0,
        b: 0,
        pa: 0,
        pb: 0,
        tick: 0,
        done: false
    };
}

function crossed(x, y, edge) {
    return x !== y && Math.min(x, y) === edge;
}

function gateStep(config, state, da, db) {
    if (state.done) return {
        error: "Episode ended."
    };
    if (![ -1, 0, 1 ].includes(da) || ![ -1, 0, 1 ].includes(db)) return {
        error: "Directions must be left, stay or right."
    };
    const a = state.a + da, b = state.b + db;
    if (a < 0 || a >= config.length || b < 0 || b >= config.length) return {
        error: "Outside the track."
    };
    const blocked = config.aGates.some(g => crossed(state.a, a, g.edge) && b !== (da > 0 ? g.out : g.back)) || config.bGates.some(g => crossed(state.b, b, g.edge) && a !== g.plate);
    if (blocked) return {
        ...state,
        tick: state.tick + 1,
        blocked: true
    };
    let pa = state.pa, pb = state.pb;
    config.aCargo.forEach((p, i) => {
        if (a === p) pa |= 1 << i;
    });
    config.bCargo.forEach((p, i) => {
        if (b === p) pb |= 1 << i;
    });
    const done = a === 0 && b === 0 && pa === (1 << config.aCargo.length) - 1 && pb === (1 << config.bCargo.length) - 1;
    return {
        a: a,
        b: b,
        pa: pa,
        pb: pb,
        tick: state.tick + 1,
        done: done,
        blocked: false
    };
}

const factoryConfigs = [ {
    title: "",
    days: 7,
    initial: [ 4, 3, 2 ],
    storage: [ 6, 6, 4 ],
    workers: [ 4, 4, 4, 4, 4, 4, 4 ],
    woodYield: [ 2, 2, 2, 2, 2, 2, 2 ],
    oreYield: [ 2, 2, 2, 2, 2, 2, 2 ],
    maintenance: [],
    due: [ {
        day: 2,
        x: 1,
        y: 0
    }, {
        day: 4,
        x: 1,
        y: 1
    }, {
        day: 7,
        x: 3,
        y: 2
    } ],
    reserve: [ 0, 0, 0 ]
}, {
    title: "",
    days: 8,
    initial: [ 3, 4, 2 ],
    storage: [ 6, 5, 4 ],
    workers: [ 4, 4, 4, 4, 4, 4, 4, 4 ],
    woodYield: [ 2, 2, 2, 2, 2, 2, 2, 2 ],
    oreYield: [ 2, 2, 0, 0, 2, 2, 0, 2 ],
    maintenance: [],
    due: [ {
        day: 2,
        x: 0,
        y: 1
    }, {
        day: 5,
        x: 2,
        y: 1
    }, {
        day: 8,
        x: 3,
        y: 2
    } ],
    reserve: [ 0, 0, 0 ]
}, {
    title: "",
    days: 7,
    initial: [ 5, 3, 3 ],
    storage: [ 6, 6, 4 ],
    workers: [ 4, 4, 3, 4, 4, 3, 4 ],
    woodYield: [ 2, 2, 2, 2, 2, 2, 2 ],
    oreYield: [ 2, 2, 2, 2, 2, 2, 2 ],
    maintenance: [ 4 ],
    due: [ {
        day: 2,
        x: 1,
        y: 1
    }, {
        day: 4,
        x: 1,
        y: 1
    }, {
        day: 7,
        x: 3,
        y: 1
    } ],
    reserve: [ 0, 0, 0 ]
}, {
    title: "",
    days: 8,
    initial: [ 5, 4, 2 ],
    storage: [ 6, 6, 4 ],
    workers: [ 4, 4, 3, 4, 4, 4, 3, 4 ],
    woodYield: [ 2, 2, 2, 2, 2, 2, 2, 2 ],
    oreYield: [ 2, 2, 0, 2, 2, 0, 2, 2 ],
    maintenance: [ 5 ],
    due: [ {
        day: 2,
        x: 1,
        y: 1
    }, {
        day: 5,
        x: 2,
        y: 1
    }, {
        day: 8,
        x: 2,
        y: 2
    } ],
    reserve: [ 1, 1, 1 ]
} ];

function factoryInitial(config) {
    return {
        day: 0,
        wood: config.initial[0],
        ore: config.initial[1],
        energy: config.initial[2],
        x: 0,
        y: 0,
        cap: 1,
        done: false,
        failed: false
    };
}

function factoryStep(config, state, action) {
    if (state.done || state.failed || state.day >= config.days) return {
        error: "Production ended."
    };
    const {w: w, o: o, e: e, x: x, y: y, build: build} = action;
    if ([ w, o, e, x, y ].some(v => !Number.isInteger(v) || v < 0) || typeof build !== "boolean") return {
        error: "Workers must be nonnegative integers; expansion must be boolean."
    };
    const d = state.day;
    if (w + o + e + x + y + Number(build) > config.workers[d]) return {
        error: `Available workers: ${config.workers[d]}; expansion uses one worker.`
    };
    const s = {
        ...state,
        day: d + 1
    };
    if (build) {
        if (s.cap === 2) return {
            error: "Already expanded."
        };
        if (s.wood < 3 || s.ore < 2) return {
            error: "Expansion requires 3 wood and 2 ore at shift start."
        };
        s.wood -= 3;
        s.ore -= 2;
        s.cap = 2;
    }
    const capacity = config.maintenance.includes(d + 1) ? 1 : s.cap;
    if (x + y > capacity) return {
        error: `Machine capacity: ${capacity}; capacity exceeded.`
    };
    s.wood += w * config.woodYield[d];
    s.ore += o * config.oreYield[d];
    s.energy += e * 2;
    if (s.wood < 2 * x + y || s.ore < x + 2 * y || s.energy < x + 2 * y) return {
        error: "Insufficient resources after collection."
    };
    s.wood -= 2 * x + y;
    s.ore -= x + 2 * y;
    s.energy -= x + 2 * y;
    s.x += x;
    s.y += y;
    const lost = [ Math.max(0, s.wood - config.storage[0]), Math.max(0, s.ore - config.storage[1]), Math.max(0, s.energy - config.storage[2]) ];
    s.wood = Math.min(s.wood, config.storage[0]);
    s.ore = Math.min(s.ore, config.storage[1]);
    s.energy = Math.min(s.energy, config.storage[2]);
    s.lost = lost;
    const delivery = config.due.find(q => q.day === s.day);
    if (delivery) if (s.x < delivery.x || s.y < delivery.y) s.failed = true; else {
        s.x -= delivery.x;
        s.y -= delivery.y;
    }
    if (s.day === config.days && !s.failed) {
        s.failed = s.wood < config.reserve[0] || s.ore < config.reserve[1] || s.energy < config.reserve[2];
        s.done = !s.failed;
    }
    return s;
}

function relationHolds(a, q) {
    if (q.type === "sum") return q.cells.reduce((n, i) => n + a[i], 0) === q.total;
    if (q.type === "lt") return a[q.cells[0]] < a[q.cells[1]];
    if (q.type === "diff") return Math.abs(a[q.cells[0]] - a[q.cells[1]]) === q.total;
    if (q.type === "sameParity") return a[q.cells[0]] % 2 === a[q.cells[1]] % 2;
    if (q.type === "odd") return q.cells.filter(i => a[i] % 2 === 1).length === q.total;
    return false;
}

function boardValid(config, values, stage) {
    if (values.length !== 16 || values.some(n => !Number.isInteger(n) || n < 1 || n > 4)) return false;
    if (Object.entries(config.clues).some(([i, n]) => values[i] !== n)) return false;
    for (let r = 0; r < 4; r++) {
        if (new Set(values.slice(r * 4, r * 4 + 4)).size !== 4) return false;
        if (new Set([ 0, 1, 2, 3 ].map(c => values[c * 4 + r])).size !== 4) return false;
    }
    for (let r = 0; r < 4; r += 2) for (let c = 0; c < 4; c += 2) if (new Set([ values[r * 4 + c], values[r * 4 + c + 1], values[(r + 1) * 4 + c], values[(r + 1) * 4 + c + 1] ]).size !== 4) return false;
    return config.stages[stage].every(q => relationHolds(values, q));
}

const boardConfigs = [ {
    title: "",
    clues: {
        0: 1,
        15: 3
    },
    draft: [ 1, 2, 0, 1, 3, 0, 0, 1, 4, 0, 1, 2, 3, 1, 4, 3 ],
    stages: [ [ {
        type: "sum",
        cells: [ 3, 13 ],
        total: 5
    }, {
        type: "sum",
        cells: [ 8, 15 ],
        total: 7
    }, {
        type: "lt",
        cells: [ 0, 6 ]
    } ], [ {
        type: "sum",
        cells: [ 4, 15 ],
        total: 7
    }, {
        type: "sum",
        cells: [ 2, 11 ],
        total: 5
    }, {
        type: "lt",
        cells: [ 11, 14 ]
    } ] ],
    budget: 14,
    change: ""
}, {
    title: "",
    clues: {
        3: 4,
        12: 3
    },
    draft: [ 0, 0, 3, 4, 4, 4, 0, 2, 1, 2, 1, 0, 3, 4, 2, 1 ],
    stages: [ [ {
        type: "diff",
        cells: [ 6, 12 ],
        total: 2
    }, {
        type: "lt",
        cells: [ 15, 0 ]
    }, {
        type: "diff",
        cells: [ 8, 14 ],
        total: 1
    } ], [ {
        type: "diff",
        cells: [ 3, 13 ],
        total: 3
    }, {
        type: "diff",
        cells: [ 6, 13 ],
        total: 0
    }, {
        type: "lt",
        cells: [ 4, 3 ]
    } ] ],
    budget: 22,
    change: ""
}, {
    title: "",
    clues: {
        2: 4,
        13: 3
    },
    draft: [ 3, 0, 4, 2, 1, 2, 1, 3, 2, 4, 0, 1, 2, 3, 0, 0 ],
    stages: [ [ {
        type: "lt",
        cells: [ 5, 15 ]
    }, {
        type: "diff",
        cells: [ 0, 7 ],
        total: 0
    }, {
        type: "odd",
        cells: [ 0, 1, 15 ],
        total: 2
    } ], [ {
        type: "sum",
        cells: [ 2, 9 ],
        total: 8
    }, {
        type: "diff",
        cells: [ 1, 6 ],
        total: 0
    }, {
        type: "sum",
        cells: [ 3, 4 ],
        total: 5
    } ] ],
    budget: 18,
    change: ""
}, {
    title: "",
    clues: {
        0: 4,
        15: 3
    },
    draft: [ 4, 0, 4, 2, 2, 3, 2, 4, 0, 0, 2, 1, 1, 0, 4, 3 ],
    stages: [ [ {
        type: "lt",
        cells: [ 8, 14 ]
    }, {
        type: "odd",
        cells: [ 3, 4, 8 ],
        total: 1
    }, {
        type: "sum",
        cells: [ 6, 12 ],
        total: 2
    } ], [ {
        type: "sum",
        cells: [ 3, 13 ],
        total: 5
    }, {
        type: "sum",
        cells: [ 4, 11 ],
        total: 7
    }, {
        type: "odd",
        cells: [ 3, 8, 14 ],
        total: 1
    } ], [ {
        type: "sum",
        cells: [ 6, 12 ],
        total: 4
    }, {
        type: "sum",
        cells: [ 3, 9 ],
        total: 4
    }, {
        type: "diff",
        cells: [ 9, 14 ],
        total: 0
    } ] ],
    budget: 33,
    change: ""
} ];

const cellName = i => `R${Math.floor(i / 4) + 1}C${i % 4 + 1}`;

function relationText(q) {
    const c = q.cells.map(cellName);
    if (q.type === "sum") return `${c.join("+")} sum = ${q.total} (count each cell, including equal values)`;
    if (q.type === "lt") return `${c[0]} < ${c[1]}`;
    if (q.type === "diff") return `${c[0]} and ${c[1]} absolute difference = ${q.total}`;
    if (q.type === "sameParity") return `${c[0]} and ${c[1]} have equal parity`;
    return `${c.join(", ")} contain exactly ${q.total} odd values`;
}

function createGate(v, ui) {
    const config = gateConfigs[v];
    let state = gateInitial();
    const rules = rulesFor("c", v);
    function draw() {
        ui.camera.position.set(0, 11, 10);
        ui.camera.lookAt(0, 0, 0);
        const xx = x => (x - (config.length - 1) / 2) * 1.3;
        for (const [role, z, col] of [ [ "A", -1.7, 6859485 ], [ "B", 1.7, 14657134 ] ]) {
            for (let x = 0; x < config.length; x++) {
                ui.box(xx(x), 0, z, 1.2, .15, 1.3, 6651267);
                ui.text(`${role}${x}`, xx(x), .18, z + .4, .23);
            }
            const cargo = role === "A" ? config.aCargo : config.bCargo, mask = role === "A" ? state.pa : state.pb;
            cargo.forEach((x, i) => {
                if (!(mask & 1 << i)) ui.box(xx(x), .35, z, .42, .5, .42, 15126648);
            });
            const pos = role === "A" ? state.a : state.b;
            ui.ball(xx(pos), .65, z, .33, col);
            ui.text(role, xx(pos), 1.25, z, .28);
        }
        config.aGates.forEach((g, i) => {
            ui.box((xx(g.edge) + xx(g.edge + 1)) / 2, .55, -1.7, .1, 1.2, 1.1, 12348786);
            ui.text(`G${i + 1}`, (xx(g.edge) + xx(g.edge + 1)) / 2, 1.55, -1.7, .25);
        });
        config.bGates.forEach((g, i) => {
            ui.box((xx(g.edge) + xx(g.edge + 1)) / 2, .55, 1.7, .1, 1.2, 1.1, 11770065);
            ui.text(`H${i + 1}`, (xx(g.edge) + xx(g.edge + 1)) / 2, 1.55, 1.7, .25);
        });
        ui.overlay(`Tracks A and B: 0-${config.length - 1}; left=-1, stay=0, right=+1\nPosition: A${state.a} / B${state.b}; cargo A ${state.pa ? "collected" : "pending"} / B ${config.bCargo.length ? state.pb ? "collected" : "pending" : "not required"}\n` + config.aGates.map((g, i) => `G${i + 1}: A ${g.edge}↔${g.edge + 1}, right requires B${g.out}, left requires B${g.back}`).join("\n") + "\n" + config.bGates.map((g, i) => `H${i + 1}: B ${g.edge}↔${g.edge + 1}, either direction requires A${g.plate}`).join("\n") + `\nCargo A: ${config.aCargo.join(", ")}; B: ${config.bCargo.join(", ") || "none"}; return point: 0.`);
        ui.choice("A direction", "da", [ "stay", "left", "right" ]);
        ui.choice("B direction", "db", [ "stay", "left", "right" ]);
        ui.command("joint move", () => {
            if (ui.isEnded()) return;
            const lookup = {
                stay: 0,
                left: -1,
                right: 1
            }, da = lookup[ui.value("da")], db = lookup[ui.value("db")];
            const next = gateStep(config, state, da, db);
            if (next.error) {
                ui.say(next.error);
                return;
            }
            ui.step(`A ${ui.value("da")} / B ${ui.value("db")}`, () => {
                state = next;
                ui.say(next.blocked ? "Interlock blocked; positions unchanged." : `Position: A${state.a} / B${state.b}`);
                if (state.done) ui.finish(true, "All cargo collected; both returned.");
            });
        });
    }
    return {
        rules: rules,
        budget: config.budget,
        draw: draw
    };
}

function createFactory(v, ui) {
    const config = factoryConfigs[v];
    let state = factoryInitial(config);
    const rules = rulesFor("c-d", v);
    function draw() {
        [ [ "wood", state.wood, 12227173 ], [ "ore", state.ore, 9088959 ], [ "energy", state.energy, 14926947 ], [ "X", state.x, 7322276 ], [ "Y", state.y, 11898052 ] ].forEach(([name, n, color], i) => {
            const x = (i - 2) * 2.05;
            ui.box(x, .1, 0, 1.7, .2, 2.5, 4679024);
            for (let k = 0; k < Math.min(n, 12); k++) ui.box(x + (k % 2 - .5) * .5, .4 + Math.floor(k / 4) * .4, (Math.floor(k % 4 / 2) - .5) * .65, .4, .35, .5, color);
            ui.text(name, x, 1.9, 0, .32);
        });
        ui.overlay(`Stock: wood ${state.wood} / ore ${state.ore} / energy ${state.energy} / X${state.x} / Y${state.y}\nCompleted ${state.day}/${config.days} shifts; capacity ${state.cap}; ${state.day < config.days ? "Next shift workers: " + config.workers[state.day] + ", effective capacity: " + (config.maintenance.includes(state.day + 1) ? 1 : state.cap) : "Production ended"}\nStorage wood/ore/energy=${config.storage.join("/")}; final reserves wood/ore/energy>=${config.reserve.join("/")}\n` + config.due.map(q => `#${q.day} shift delivery X${q.x}+Y${q.y}${state.day >= q.day ? " (settled)" : ""}`).join("; ") + "\nCalendar (shift: workers/wood yield/ore yield/maintenance):\n" + config.workers.map((n, i) => `${i + 1}: ${n}/${config.woodYield[i]}/${config.oreYield[i]}/${config.maintenance.includes(i + 1) ? "yes" : "no"}${i === state.day ? " <- current" : ""}`).join("; "));
        ui.number("wood workers", "wood", 0, 0, 4);
        ui.number("ore workers", "ore", 0, 0, 4);
        ui.number("energy workers", "energy", 0, 0, 4);
        ui.number("X workers", "makeX", 0, 0, 2);
        ui.number("Y workers", "makeY", 0, 0, 2);
        ui.choice("expand (one worker)", "build", [ "no", "yes" ]);
        ui.command("execute shift", () => {
            if (ui.isEnded()) return;
            const action = {
                w: +ui.value("wood"),
                o: +ui.value("ore"),
                e: +ui.value("energy"),
                x: +ui.value("makeX"),
                y: +ui.value("makeY"),
                build: ui.value("build") === "yes"
            };
            const next = factoryStep(config, state, action);
            if (next.error) {
                ui.say(next.error);
                return;
            }
            ui.step(`#${state.day + 1} shift wood/ore/energy/X/Y=${[ action.w, action.o, action.e, action.x, action.y ].join("/")}, expand=${action.build ? "yes" : "no"}`, () => {
                state = next;
                ui.say(`Stock: wood ${state.wood} ore ${state.ore} energy ${state.energy} X${state.x} Y${state.y}; overflow losses ${state.lost.join("/")}`);
                if (state.failed) ui.finish(false, "Delivery or final reserve requirement failed."); else if (state.done) ui.finish(true, "All deliveries and final reserves completed.");
            });
        });
    }
    return {
        rules: rules,
        budget: config.days,
        draw: draw
    };
}

function createBoard(v, ui) {
    const config = boardConfigs[v];
    let values = [ ...config.draft ], stage = 0, selection = 0, undo = [];
    const rules = rulesFor("c-d-a", v);
    function draw() {
        ui.camera.position.set(0, 10, 5);
        ui.camera.lookAt(0, 0, 0);
        for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
            const i = r * 4 + c, x = (c - 1.5) * 1.7 + (c >= 2 ? .12 : 0), z = (r - 1.5) * 1.7 + (r >= 2 ? .12 : 0), locked = Boolean(config.clues[i]);
            const choose = () => {
                if (ui.isEnded()) return;
                selection = i;
                ui.redraw();
            };
            ui.box(x, 0, z, 1.58, .15, 1.58, selection === i ? 12162387 : locked ? 3427426 : 7441800, choose);
            ui.text(`${values[i] || "·"}`, x, .3, z, .5, locked ? "#ffffff" : "#ffe7a0", choose);
        }
        for (let i = 0; i < 4; i++) {
            ui.text(`C${i + 1}`, (i - 1.5) * 1.7, .1, -4, .23);
            ui.text(`R${i + 1}`, -4, .1, (i - 1.5) * 1.7, .23);
        }
        ui.overlay(`Revision ${stage + 1}/${config.stages.length} (current only); selected ${cellName(selection)}\n` + "Board (.=empty, F=fixed, E=editable):\n" + [ 0, 1, 2, 3 ].map(r => `R${r + 1}: ` + [ 0, 1, 2, 3 ].map(c => `C${c + 1}=${values[r * 4 + c] || "·"}[${config.clues[r * 4 + c] ? "F" : "E"}]`).join(" ")).join("\n") + "\n" + config.stages[stage].map((q, i) => `${i + 1}. ${relationText(q)}`).join("\n"));
        ui.choice("row", "boardRow", [ "1", "2", "3", "4" ]);
        ui.choice("column", "boardCol", [ "1", "2", "3", "4" ]);
        ui.command("select cell", () => {
            if (ui.isEnded()) return;
            selection = ui.index("boardRow") * 4 + ui.index("boardCol");
            ui.redraw();
        });
        for (let n = 1; n <= 4; n++) ui.command(String(n), () => {
            if (ui.isEnded()) return;
            if (config.clues[selection]) {
                ui.say("Fixed clue cannot be edited.");
                return;
            }
            if (values[selection] === n) {
                ui.say("Value unchanged; no cost.");
                return;
            }
            ui.step(`write ${cellName(selection)}=${n}`, () => {
                undo.push({
                    i: selection,
                    old: values[selection]
                });
                values[selection] = n;
                ui.say("Cell updated.");
            });
        });
        ui.command("undo", () => {
            if (ui.isEnded()) return;
            if (!undo.length) {
                ui.say("Undo stack is empty.");
                return;
            }
            ui.step("undo current revision write", () => {
                const q = undo.pop();
                values[q.i] = q.old;
                ui.say("Cell restored.");
            });
        });
        ui.command("submit board", () => {
            if (ui.isEnded()) return;
            ui.step(`accept revision ${stage + 1}`, () => {
                const valid = boardValid(config, values, stage);
                if (!valid) {
                    if (stage === config.stages.length - 1) ui.finish(false, "Current constraints not satisfied."); else ui.say("Row, column, block or relation conflict.");
                    return;
                }
                if (stage === config.stages.length - 1) {
                    ui.finish(true, "All revisions accepted.");
                    return;
                }
                stage++;
                undo = [];
                ui.say("New revision: previous extra relations replaced; board retained.");
            });
        });
    }
    return {
        rules: rules,
        budget: config.budget,
        draw: draw
    };
}

export function createLevel(node, variant, ui) {
    if (![ "c", "c-d", "c-d-a" ].includes(node)) return null;
    if (!validVariant(variant)) throw new RangeError("variant must be 0..3");
    return node === "c" ? createGate(variant, ui) : node === "c-d" ? createFactory(variant, ui) : createBoard(variant, ui);
}
