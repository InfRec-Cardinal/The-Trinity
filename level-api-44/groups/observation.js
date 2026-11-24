import { rulesFor } from "../rules.mjs";

const NODES = [ "a", "d", "e", "e-f" ];

const C = {
    teal: 5741969,
    brass: 14136686,
    ink: 2373952,
    white: 15921625,
    red: 14122086,
    blue: 8629445
};

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));

const mix = (a, b, t) => a + (b - a) * t;

const pair = (a, b, t) => a.map((n, i) => mix(n, b[i], t));

function inspectionSpec(variant) {
    const patterns = [ [ [ "zig", "open" ], [ "zig", "closed" ], [ "bend", "kink" ], [ "bend", "straight" ], [ "hole", "empty" ], [ "hole", "pin" ], [ "paint", "open" ], [ "none", "closed" ] ], [ [ "hole", "empty" ], [ "zig", "closed" ], [ "hole", "empty" ], [ "bend", "kink" ], [ "paint", "open" ], [ "zig", "open" ], [ "bend", "straight" ], [ "hole", "pin" ] ], [ [ "bend", "straight" ], [ "hole", "pin" ], [ "zig", "open" ], [ "paint", "open" ], [ "bend", "kink" ], [ "hole", "empty" ], [ "zig", "closed" ], [ "none", "closed" ] ], [ [ "zig", "open" ], [ "hole", "pin" ], [ "bend", "kink" ], [ "zig", "closed" ], [ "hole", "empty" ], [ "paint", "open" ], [ "hole", "empty" ], [ "bend", "straight" ] ] ];
    return {
        variant: variant,
        budget: [ 9, 10, 9, 10 ][variant],
        members: patterns[variant].map(([front, back], i) => ({
            id: "ABCD"[i >> 1] + (i % 2 + 1),
            front: front,
            back: back,
            covered: variant === 3 && [ 4, 6 ].includes(i)
        }))
    };
}

function defectOf(front, back) {
    if (front === "zig" && back === "open") return "crack";
    if (front === "bend" && back === "kink") return "bend";
    if (front === "hole" && back === "empty") return "loose";
    return "none";
}

function inspectionObservation(spec, station, lifted = false) {
    if (!Number.isInteger(station) || station < 0 || station > 3) return [];
    const rear = station >= 2, half = station % 2;
    const rows = spec.members.slice(half * 4, half * 4 + 4).map(m => ({
        id: m.id,
        face: rear ? "back" : "front",
        value: rear && m.covered && !lifted ? null : m[rear ? "back" : "front"]
    }));
    return rear ? rows.reverse() : rows;
}

function inspectionGrade(spec, evidence, reports) {
    const full = spec.members.every(m => [ "front", "back" ].every(face => evidence[m.id]?.[face] != null));
    const expected = Object.fromEntries(spec.members.map(m => [ m.id, defectOf(m.front, m.back) ]).filter(([, d]) => d !== "none"));
    return full && Object.keys(reports).length === Object.keys(expected).length && Object.entries(expected).every(([id, d]) => reports[id] === d);
}

const ATTRIBUTE = {
    tone: "body color",
    bands: "brass bands",
    notches: "side notches",
    badge: "rear badge",
    dots: "badge rivets",
    relation: "seal and latch",
    stamp: "base stamp"
};

const VIEW = {
    front: "front",
    side: "side close-up",
    back: "rear wide",
    macro: "rear macro",
    blocked: "curtained angle",
    under: "underside"
};

function verificationSpec(variant) {
    const expected = {
        tone: "teal",
        bands: 2,
        notches: 2,
        badge: "upward triangle",
        dots: 2,
        relation: "seal left of latch"
    };
    if (variant === 3) expected.stamp = "triangle and two circles";
    const actual = {
        ...expected
    };
    if (variant === 1) actual.dots = 3;
    if (variant === 2) actual.relation = "seal right of latch";
    const decoyA = {
        ...expected,
        notches: 3,
        badge: "downward triangle",
        dots: 2
    };
    const decoyB = {
        ...expected,
        tone: "blue-green",
        bands: 3,
        relation: "seal right of latch"
    };
    return {
        variant: variant,
        budget: 5,
        target: "Q7",
        expected: expected,
        objects: [ {
            id: "Q7",
            attrs: actual
        }, {
            id: "Q1",
            attrs: decoyA
        }, {
            id: "O7",
            attrs: decoyB
        } ]
    };
}

function verificationObservation(spec, view) {
    const fields = {
        front: [ "tone", "bands" ],
        side: [ "notches" ],
        back: [ "badge" ],
        macro: [ "dots", "relation" ],
        blocked: [],
        under: [ "stamp" ]
    }[view];
    if (!fields) return [];
    const order = {
        front: [ 0, 1, 2 ],
        side: [ 2, 0, 1 ],
        back: [ 1, 2, 0 ],
        macro: [ 2, 1, 0 ],
        blocked: [ 0, 2, 1 ],
        under: [ 1, 0, 2 ]
    }[view];
    return order.map(i => ({
        id: spec.objects[i].id,
        bodyTone: spec.objects[i].attrs.tone,
        attrs: Object.fromEntries(fields.filter(k => k in spec.expected).map(k => [ k, spec.objects[i].attrs[k] ]))
    }));
}

function verificationGrade(spec, evidence, yes, reason) {
    const observed = evidence[spec.target] || {};
    const missing = Object.keys(spec.expected).filter(k => !(k in observed));
    const contradictions = Object.keys(spec.expected).filter(k => k in observed && !same(observed[k], spec.expected[k]));
    if (yes) return {
        success: missing.length === 0 && contradictions.length === 0,
        kind: missing.length ? "missing" : contradictions.length ? "contradiction" : "supported"
    };
    return {
        success: contradictions.includes(reason),
        kind: contradictions.includes(reason) ? "contradiction" : "unsupported-negative"
    };
}

const ACTORS = [ "A", "B", "C", "D" ];

const BINS = [ "left bin", "middle bin", "right bin" ];

const BASE_X = [ -4.2, -1.4, 1.4, 4.2 ];

function filmSpec(variant) {
    const routes = [ [ [ 2, 0, 1 ], [ 18, 1, 2 ] ], [ [ 2, 0, 2 ], [ 14, 2, 3 ], [ 26, 3, 1 ] ], [ [ 2, 0, 1 ], [ 18, 1, 0 ], [ 26, 0, 3 ] ], [ [ 2, 0, 1 ], [ 10, 1, 2 ], [ 18, 2, 1 ], [ 26, 1, 3 ] ] ];
    const occlusion = [ 10, 18, 10, 14 ][variant], destination = [ 2, 0, 1, 0 ][variant];
    const transfers = routes[variant].map(([time, from, to]) => ({
        time: time,
        from: from,
        to: to,
        kind: "transfer",
        token: 0
    }));
    let holder = 0, other = 3;
    const events = [];
    for (let segment = 0; segment < 8; segment++) {
        const time = segment * 4 + 2, transfer = transfers.find(e => e.time === time);
        if (transfer) {
            events.push(transfer);
            holder = transfer.to;
        } else if (time === occlusion) events.push({
            time: time,
            kind: "occlusion",
            actor: holder,
            token: 0
        }); else if (time === 30) events.push({
            time: time,
            kind: "deposit",
            actor: holder,
            bin: destination,
            token: 0
        }); else if (time === 22) events.push({
            time: time,
            kind: "meet",
            from: holder,
            to: (holder + 1) % 4,
            token: 0
        }); else {
            const to = [ 0, 1, 2, 3 ].find(i => i !== other && i !== holder);
            events.push({
                time: time,
                kind: "transfer",
                from: other,
                to: to,
                token: 1
            });
            other = to;
        }
    }
    return {
        variant: variant,
        length: 32,
        budget: 8,
        destination: destination,
        events: events,
        segments: Array.from({
            length: 8
        }, (_, i) => ({
            id: i,
            start: i * 4,
            end: (i + 1) * 4
        }))
    };
}

function filmRequirements(spec) {
    return [ 0, ...spec.events.filter(e => e.token === 0).flatMap(e => e.kind === "meet" ? [] : [ e.time - 1.3, e.time, e.time + 1.3 ]) ];
}

function filmEvidenceGrade(spec, unlocked, selected) {
    if (!selected.length || new Set(selected).size !== selected.length || selected.some(i => !unlocked.includes(i))) return false;
    const required = filmRequirements(spec);
    const covers = ids => required.every(t => ids.some(i => spec.segments[i] && t >= spec.segments[i].start && t <= spec.segments[i].end));
    return covers(selected) && selected.every(id => !covers(selected.filter(i => i !== id)));
}

function filmAnswer(spec) {
    const transfers = spec.events.filter(e => e.kind === "transfer" && e.token === 0);
    return {
        destination: spec.destination,
        count: transfers.length,
        route: transfers.map(e => ACTORS[e.to]).join("→")
    };
}

function filmAnswerGrade(spec, destination, count, route) {
    const a = filmAnswer(spec);
    return destination === a.destination && count === a.count && route === a.route;
}

const preferredGrip = actor => [ 1, -1, -1, 1 ][actor];

function filmHoldings(spec, time) {
    const held = [ {owner: 0, side: preferredGrip(0)}, {owner: 3, side: preferredGrip(3)} ];
    const arrivals = [ 1, 0, 0, 1 ];
    for (const e of spec.events) if (e.kind === "transfer" && time >= e.time) {
        const preferred = preferredGrip(e.to) * (arrivals[e.to] % 2 ? -1 : 1);
        const occupied = held.some((h, i) => i !== e.token && h.owner === e.to && h.side === preferred);
        held[e.token] = {owner: e.to, side: occupied ? -preferred : preferred};
        arrivals[e.to]++;
    }
    return held;
}

const hand = (actors, index, side) => [ actors[index][0] + side * .38, 1.06, actors[index][1] + .25 ];

function filmFrame(spec, time) {
    const t = clamp(time, 0, spec.length), actors = BASE_X.map(x => [ x, 0 ]), held = filmHoldings(spec, t);
    const event = spec.events.find(e => Math.abs(t - e.time) <= 1.5);
    const transferGrips = event?.kind === "transfer" ? {
        from: filmHoldings(spec, event.time - .001)[event.token].side,
        to: filmHoldings(spec, event.time)[event.token].side
    } : null;
    if (event && [ "transfer", "meet" ].includes(event.kind)) {
        const amount = clamp((1.5 - Math.abs(t - event.time)) / .8), center = (BASE_X[event.from] + BASE_X[event.to]) / 2;
        const direction = Math.sign(BASE_X[event.to] - BASE_X[event.from]);
        actors[event.from][0] = mix(BASE_X[event.from], center - direction * .7, amount);
        actors[event.to][0] = mix(BASE_X[event.to], center + direction * .7, amount);
        actors[event.from][1] = 1.1 * amount;
        actors[event.to][1] = 1.1 * amount;
    }
    if (event?.kind === "occlusion") {
        const depth = 1 - Math.abs(t - event.time) / 1.5;
        actors[event.actor] = [ BASE_X[event.actor] * (1 - depth), -.65 * clamp(depth * 3) ];
    }
    const deposit = spec.events.find(e => e.kind === "deposit");
    const depositProgress = clamp((t - deposit.time + 1.3) / 2.6);
    if (t >= deposit.time - 1.3) actors[deposit.actor] = pair([ BASE_X[deposit.actor], 0 ], [ (deposit.bin - 1) * 3.4 - held[0].side * .38, -1.75 ], clamp(depositProgress / .7));
    const tokens = held.map(({owner, side}, i) => ({
        pos: hand(actors, owner, side),
        ring: i === 0 && t < 1,
        owner: owner,
        side: side,
        hidden: false
    }));
    if (event?.kind === "transfer") {
        const p = clamp(t - event.time + .5);
        tokens[event.token].pos = pair(hand(actors, event.from, transferGrips.from), hand(actors, event.to, transferGrips.to), p);
        tokens[event.token].pos[1] += .45 * Math.sin(Math.PI * p);
        tokens[event.token].pos[2] += .25 * Math.sin(Math.PI * p);
        tokens[event.token].shared = p > .35 && p < .65;
    }
    if (t >= deposit.time - 1.3) {
        const p = clamp((depositProgress - .7) / .3), end = [ (deposit.bin - 1) * 3.4, .45, -2.65 ];
        tokens[0].pos = pair(hand(actors, deposit.actor, held[0].side), end, p);
        tokens[0].hidden = p >= 1;
    }
    if (event?.kind === "occlusion") tokens[0].hidden = Math.abs(tokens[0].pos[0]) < .67;
    return {
        time: t,
        actors: actors,
        tokens: tokens,
        transferGrips: transferGrips,
        event: event ? {
            ...event
        } : null
    };
}

function note(ui, message) {
    ui.log(message);
    ui.say(message);
}

function mergeEvidence(evidence, rows) {
    for (const row of rows) evidence[row.id] = {
        ...evidence[row.id],
        ...row.attrs
    };
}

function physicalLine(ui, x, y, z, dx, dy, color = C.ink, width = .055) {
    const mesh = ui.box(x + dx / 2, y + dy / 2, z, width, Math.hypot(dx, dy), .06, color);
    mesh.rotation.z = -Math.atan2(dx, dy);
}

function arm(ui, start, end) {
    const a = new ui.THREE.Vector3(...start), b = new ui.THREE.Vector3(...end), direction = b.clone().sub(a);
    const center = a.clone().add(b).multiplyScalar(.5), length = direction.length();
    if (length < .001) return;
    const mesh = ui.box(center.x, center.y, center.z, .075, length, .075, C.white);
    mesh.quaternion.setFromUnitVectors(new ui.THREE.Vector3(0, 1, 0), direction.normalize());
    ui.ball(...end, .09, C.white);
}

function triangle(ui, x, y, z, up = true) {
    const s = .23, sign = up ? 1 : -1;
    physicalLine(ui, x - s, y - sign * .15, z, s, sign * .4, C.brass);
    physicalLine(ui, x, y + sign * .25, z, s, -sign * .4, C.brass);
    physicalLine(ui, x - s, y - sign * .15, z, 2 * s, 0, C.brass);
}

function inspectionGlyph(ui, value, x, y) {
    ui.box(x, y, 0, .22, 1.05, .24, 9413796);
    for (const dx of [ -.36, .36 ]) ui.box(x + dx, y, 0, .025, 1.2, .05, C.brass);
    if (value === "zig") {
        physicalLine(ui, x - .22, y + .25, .2, .28, -.2);
        physicalLine(ui, x + .06, y + .05, .2, -.2, -.18);
        physicalLine(ui, x - .14, y - .13, .2, .32, -.18);
    }
    if (value === "paint") physicalLine(ui, x - .2, y + .2, .2, .4, -.4, 2698803, .07);
    if (value === "bend") {
        physicalLine(ui, x, y - .5, .1, .5, .5, C.white, .16);
        physicalLine(ui, x + .5, y, .1, -.5, .5, C.white, .16);
    }
    if (value === "hole" || value === "empty") {
        ui.ball(x, y, .25, .18, C.brass);
        ui.ball(x, y, .4, .105, C.ink);
    }
    if (value === "pin") {
        ui.ball(x, y, .25, .18, C.brass);
        ui.box(x, y, .42, .09, .4, .08, C.white);
    }
    if (value === "open") {
        ui.box(x, y, .22, .5, .13, .08, C.ink);
        ui.box(x + .18, y + .2, .22, .12, .3, .08, C.white);
    }
    if (value === "closed") ui.box(x, y, .22, .5, .035, .08, C.ink);
    if (value === "kink") {
        physicalLine(ui, x - .3, y - .4, .22, .45, .4, C.white, .09);
        physicalLine(ui, x + .15, y, .22, -.45, .4, C.white, .09);
    }
    if (value === "straight") physicalLine(ui, x - .25, y - .4, .22, .5, .8, C.white, .09);
    if (value === null) ui.box(x, y, .6, .85, 1.2, .12, 4543843);
}

const RAW = {
    zig: "zigzag crossing the column",
    paint: "black line on a flat surface",
    bend: "column outside the gold gauge",
    hole: "dark hole in the washer",
    none: "continuous column",
    open: "open joint with right offset",
    closed: "closed joint",
    kink: "kinked brace",
    straight: "straight continuous brace",
    pin: "cross-pin in the hole",
    empty: "open mounting hole without pin"
};

function createInspection(variant, ui) {
    const spec = inspectionSpec(variant), evidence = {}, reports = {};
    let station = -1, lifted = false;
    const rules = rulesFor("a", variant);
    function acquire(s) {
        station = s;
        for (const row of inspectionObservation(spec, s, lifted)) {
            evidence[row.id] ??= {};
            if (row.value !== null) evidence[row.id][row.face] = row.value;
        }
        note(ui, inspectionObservation(spec, s, lifted).map(r => `${r.id} ${r.face === "front" ? "front" : "rear"}: ${r.value === null ? "cover occlusion" : RAW[r.value]}`).join("; "));
    }
    function draw() {
        ui.camera.position.set(0, 5.5, 10.5);
        ui.camera.lookAt(0, 1.6, 0);
        ui.overlay(`Reports: ${Object.keys(reports).length} items: ${Object.entries(reports).map(([id, kind]) => id + " " + kind).join("; ") || "none"}; station: ${station < 0 ? "not selected" : [ "west front A/B", "east front C/D", "west rear B/A", "east rear D/C" ][station]}. Submission costs 1.`);
        const rows = station < 0 ? spec.members.map(m => ({
            id: m.id,
            value: null
        })) : inspectionObservation(spec, station, lifted);
        rows.forEach((r, i) => {
            const x = (i % (station < 0 ? 4 : 2) - (station < 0 ? 1.5 : .5)) * 2.7, y = 3 - Math.floor(i / (station < 0 ? 4 : 2)) * 2.2;
            ui.box(x, y - .65, -.2, 2, .1, 1, 9271648);
            inspectionGlyph(ui, r.value, x, y);
            ui.text(r.id, x, y + .85, 0, .29);
        });
        [ "west front A/B", "east front C/D", "west rear B/A", "east rear D/C" ].forEach((name, i) => ui.command("inspect " + name + " / 1 step", () => ui.step("inspection " + name, () => acquire(i))));
        if (variant === 3) ui.command("raise east rear cover / 1 step", () => {
            if (station !== 3 || lifted) {
                ui.say(lifted ? "Cover already raised." : "East rear station required.");
                return;
            }
            ui.step("raise cover", () => {
                lifted = true;
                acquire(3);
            });
        });
        ui.choice("member", "obs-member", spec.members.map(m => m.id));
        ui.choice("report", "obs-fault", [ "crack", "bend", "loose", "undo" ]);
        ui.command("record member / 1 step", () => {
            const id = ui.value("obs-member"), kind = ui.value("obs-fault");
            if (!spec.members.some(m => m.id === id) || ![ "crack", "bend", "loose", "undo" ].includes(kind)) return;
            if (kind === "undo" && !reports[id]) {
                ui.say("No report for this member.");
                return;
            }
            ui.step(`report ${id} ${kind}`, () => {
                if (kind === "undo") delete reports[id]; else reports[id] = kind;
                ui.say(`Recorded ${id} ${kind}.`);
            });
        });
        ui.command("submit inspection / 1 step", () => ui.step("submit inspection", () => ui.finish(inspectionGrade(spec, evidence, reports), "Inspection evaluated.")));
    }
    return {
        budget: spec.budget,
        rules: rules,
        draw: draw
    };
}

function verificationGlyph(ui, row, x, view) {
    const a = row.attrs;
    ui.box(x, 1.4, 0, 2.25, 2.25, 1.2, row.bodyTone === "blue-green" ? 4887199 : C.teal);
    ui.text(row.id, x, 3, 0, .38);
    if ("bands" in a) for (let i = 0; i < a.bands; i++) ui.box(x + (i - (a.bands - 1) / 2) * .6, 1.4, .65, .13, 2.2, .07, C.brass);
    if ("notches" in a) for (let i = 0; i < a.notches; i++) ui.box(x - .6 + i * .5, 1.9, .67, .16, .3, .07, C.ink);
    if ("badge" in a) triangle(ui, x, 1.55, .67, a.badge === "upward triangle");
    if ("dots" in a) {
        for (let i = 0; i < a.dots; i++) ui.ball(x + (i - (a.dots - 1) / 2) * .28, 1.25, .72, .07, C.white);
    }
    if ("relation" in a) {
        ui.box(x, .65, .7, .13, .23, .09, C.brass);
        ui.box(x + (a.relation === "seal left of latch" ? -.48 : .48), .65, .7, .2, .25, .08, C.white);
    }
    if ("stamp" in a) {
        triangle(ui, x - .4, 1.4, .7);
        ui.ball(x + .1, 1.4, .7, .09, C.ink);
        ui.ball(x + .4, 1.4, .7, .09, C.ink);
    }
    if (view === "blocked") ui.box(x, 1.4, 1, 2.3, 1.6, .12, 4871011);
}

function createVerification(variant, ui) {
    const spec = verificationSpec(variant), evidence = {};
    let view = "front";
    mergeEvidence(evidence, verificationObservation(spec, "front"));
    const rules = rulesFor("d", variant);
    function draw() {
        ui.camera.position.set(0, 4.5, 11);
        ui.camera.lookAt(0, 1.3, 0);
        verificationObservation(spec, view).forEach((r, i) => verificationGlyph(ui, r, (i - 1) * 3.25, view));
        ui.overlay(`${VIEW[view]} / visible readings: ${verificationObservation(spec, view).map(r => r.id + ": " + (Object.entries(r.attrs).map(([k, v]) => ATTRIBUTE[k] + " " + v).join(", ") || "occluded; no new attributes")).join("; ")}.`);
        for (const id of [ "side", "back", "macro", "blocked", ...variant === 3 ? [ "under" ] : [] ]) ui.command(VIEW[id] + " / 1 step", () => ui.step("inspect " + VIEW[id], () => {
            view = id;
            const rows = verificationObservation(spec, id);
            mergeEvidence(evidence, rows);
            note(ui, rows.map(r => `${r.id}: ${Object.entries(r.attrs).map(([k, v]) => ATTRIBUTE[k] + " " + v).join(", ") || "occluded; no new attributes"}`).join("; "));
        }));
        ui.choice("contradiction attribute", "obs-reason", Object.keys(spec.expected).map(k => ATTRIBUTE[k]));
        const submit = yes => {
            const reason = Object.keys(spec.expected)[ui.index("obs-reason")];
            ui.step(yes ? "confirm and stop" : "reject and stop", () => {
                const result = verificationGrade(spec, evidence, yes, reason);
                ui.finish(result.success, result.success ? "Evidence supports the decision." : result.kind === "missing" ? "Required evidence is missing." : result.kind === "unsupported-negative" ? "No observed contradiction for that attribute." : "Observed evidence contradicts confirmation.");
            });
        };
        ui.command("confirm all requirements / 1 step", () => submit(true));
        ui.command("reject selected contradiction / 1 step", () => submit(false));
    }
    return {
        budget: spec.budget,
        rules: rules,
        draw: draw
    };
}

function segmentIndex(spec, i) {
    const segment = spec.segments[i];
    return `${i + 1}. ${segment.start}–${segment.end}s`;
}

function filmScene(ui, spec, t, preview = false) {
    const frame = filmFrame(spec, t);
    ui.camera.position.set(0, 6.2, 12.8);
    ui.camera.lookAt(0, .7, -.6);
    ui.box(0, -.15, 0, 11, .2, 7, 6520448);
    BINS.forEach((name, i) => {
        const x = (i - 1) * 3.4;
        ui.box(x, .5, -2.65, 1.7, 1.1, 1.2, [ 7904700, 8893067, 12822126 ][i]);
        ui.box(x, 1.07, -2.65, 1.25, .06, .8, C.ink);
        ui.text(name, x, 1.65, -2.65, .3);
    });
    frame.actors.forEach(([x, z], i) => {
        ui.box(x, .51, z, .48, .85, .4, [ 9813956, 12888956, 11376569, 10268544 ][i]);
        ui.ball(x, 1.18, z, .22, C.white);
        ui.text(ACTORS[i], x, 1.8, z, .3);
        for (const side of [ -1, 1 ]) {
            const token = frame.tokens.find(p => p.owner === i && p.side === side), e = frame.event;
            let endpoint = hand(frame.actors, i, side);
            if (token && !token.hidden) endpoint = token.pos;
            if (e?.kind === "transfer" && Math.abs(t - e.time) < .5 &&
                (e.from === i && frame.transferGrips.from === side || e.to === i && frame.transferGrips.to === side)) endpoint = frame.tokens[e.token].pos;
            arm(ui, [ x + side * .23, .85, z ], endpoint);
        }
    });
    for (let i = 0; i < 2; i++) {
        const token = frame.tokens[i];
        if (token.hidden) continue;
        const [x, y, z] = token.pos;
        ui.box(x, y, z, .3, .24, .3, C.brass);
        if (token.ring) {
            ui.box(x, y + .13, z, .32, .025, .34, C.white);
            ui.box(x, y, z + .16, .32, .25, .025, C.white);
        }
        if (token.shared) {
            ui.ball(x - .17, y, z, .08, C.white);
            ui.ball(x + .17, y, z, .08, C.white);
        }
    }
    if (frame.event?.kind === "occlusion") {
        ui.box(0, 1, -.2, 1.35, 2, .13, 3426648);
    }
}

function createFilm(node, variant, ui) {
    const spec = filmSpec(variant), unlocked = [], selected = [];
    let time = 0, active = -1, preview = true, playing = false, raf = 0, disposed = false, last = 0;
    const free = node === "e-f";
    const rules = rulesFor(node, variant);
    function stop() {
        playing = false;
        if (raf && typeof cancelAnimationFrame === "function") cancelAnimationFrame(raf);
        raf = 0;
    }
    function seek(t) {
        stop();
        time = t;
        ui.redraw();
    }
    function play() {
        stop();
        if (!free && active < 0) {
            ui.say("Unlock a segment first.");
            return;
        }
        preview = false;
        playing = true;
        const start = active < 0 ? 0 : spec.segments[active].start, end = active < 0 ? spec.length : spec.segments[active].end;
        time = start;
        last = 0;
        const frame = stamp => {
            if (disposed || ui.isEnded() || !playing) {
                stop();
                return;
            }
            if (!last) last = stamp;
            if (stamp - last >= 125) {
                time = Math.min(end, time + .25);
                last = stamp;
                ui.redraw();
            }
            if (time >= end) {
                playing = false;
                ui.redraw();
                return;
            }
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
    }
    function open(i) {
        stop();
        active = i;
        preview = false;
        time = spec.segments[i].start;
    }
    function draw() {
        filmScene(ui, spec, time, preview && !free);
        ui.overlay(`Frame ${time.toFixed(2)}s; ${preview && !free ? "sparse preview" : active < 0 ? "full film" : "segment " + (active + 1)}; ${playing ? "playing" : "paused"}. ` + (free ? "Full footage available." : `Purchased: ${unlocked.map(i => i + 1).join(", ") || "none"}; selected: ${selected.map(i => i + 1).join(", ") || "none"}.`));
        spec.segments.forEach((s, i) => ui.command((free || unlocked.includes(i) ? "replay segment " : "unlock / 1 step ") + segmentIndex(spec, i), () => {
            if (free || unlocked.includes(i)) {
                open(i);
                ui.redraw();
                return;
            }
            ui.step("unlock segment " + (i + 1), () => {
                unlocked.push(i);
                selected.push(i);
                open(i);
                note(ui, "Segment unlocked.");
            });
        }));
        if (!free) {
            [ 0, 8, 16, 24, 32 ].forEach(t => ui.command(`preview ${t}s`, () => {
                stop();
                active = -1;
                preview = true;
                time = t;
                ui.redraw();
            }));
            unlocked.forEach(i => ui.command(`${selected.includes(i) ? "deselect " : "select "}evidence segment ${i + 1} / free`, () => {
                const at = selected.indexOf(i);
                if (at < 0) selected.push(i); else selected.splice(at, 1);
                ui.redraw();
            }));
            ui.command("submit evidence set / 1 step", () => {
                stop();
                ui.step("submit video evidence", () => ui.finish(filmEvidenceGrade(spec, unlocked, selected), "Evidence coverage evaluated."));
            });
        } else {
            ui.command("play full film / free", () => {
                active = -1;
                play();
            });
            ui.choice("destination", "obs-dest", BINS);
            ui.choice("handoffs", "obs-count", [ "0", "1", "2", "3", "4" ]);
            for (let i = 0; i < 4; i++) ui.choice(`#${i + 1} recipient`, "obs-route" + i, [ "—", ...ACTORS ]);
            ui.command("submit video answer / 1 step", () => {
                const destination = ui.index("obs-dest"), count = Number(ui.value("obs-count")), parts = Array.from({
                    length: 4
                }, (_, i) => ui.value("obs-route" + i));
                if (!Number.isInteger(count) || count < 0 || count > 4 || parts.slice(0, count).some(p => !ACTORS.includes(p)) || parts.slice(count).some(p => p !== "—")) {
                    ui.say("Recipient count mismatch.");
                    return;
                }
                stop();
                ui.step("submit video answer", () => ui.finish(filmAnswerGrade(spec, destination, count, parts.slice(0, count).join("→")), "Video answer evaluated."));
            });
        }
        if (free || active >= 0) {
            const lo = active < 0 ? 0 : spec.segments[active].start, hi = active < 0 ? spec.length : spec.segments[active].end;
            ui.command("previous frame -0.25s / free", () => seek(Math.max(lo, time - .25)));
            ui.command("next frame +0.25s / free", () => seek(Math.min(hi, time + .25)));
            ui.command(playing ? "pause" : "play segment / free", () => {
                if (playing) {
                    stop();
                    ui.redraw();
                } else play();
            });
        }
    }
    return {
        rules: rules,
        budget: free ? 1 : spec.budget,
        draw: draw,
        dispose() {
            disposed = true;
            stop();
        }
    };
}

export function createLevel(node, variant, ui) {
    if (!NODES.includes(node)) return null;
    if (!Number.isInteger(variant) || variant < 0 || variant > 3) throw Error("Observation variant must be 0..3");
    return node === "a" ? createInspection(variant, ui) : node === "d" ? createVerification(variant, ui) : createFilm(node, variant, ui);
}
