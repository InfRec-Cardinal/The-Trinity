const obj = p => ({
    type: "object",
    additionalProperties: false,
    properties: p,
    required: Object.keys(p)
});

const str = values => ({
    type: "string",
    enum: values
});

const int = (min, max) => ({
    type: "integer",
    minimum: min,
    maximum: max
});

const arr = (items, min, max) => ({
    type: "array",
    items: items,
    minItems: min,
    maxItems: max
});

const tool = (name, p = {}, cost = 1) => ({
    name: name,
    input_schema: obj(p),
    cost: cost
});

const stations = [ "west front A/B", "east front C/D", "west rear B/A", "east rear D/C" ];

const views = [ "side close-up", "rear wide", "rear macro", "curtained angle", "underside" ];

const reasons = [ "body color", "brass bands", "side notches", "rear badge", "badge rivets", "seal and latch", "base stamp" ];

export function actionsFor(node, v) {
    if (node === "a") return [ tool("inspect_station", {
        station: str(stations)
    }), ...v === 3 ? [ tool("raise_cover") ] : [], tool("record_defect", {
        member: str([ "A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2" ]),
        kind: str([ "crack", "bend", "loose", "remove" ])
    }), tool("submit_inspection") ];
    if (node === "d") {
        const submit = tool("submit_verification", {
            yes: {
                type: "boolean"
            },
            reason: str(reasons.slice(0, v === 3 ? 7 : 6))
        });
        submit.input_schema.required = [ "yes" ];
        return [ tool("inspect_view", {
            view: str(views.slice(0, v === 3 ? 5 : 4))
        }), submit ];
    }
    if (node === "e" || node === "e-f") return [ tool("watch_segment", {
        segment: int(1, 8)
    }, node === "e" ? "1 if not purchased; otherwise 0" : 0), ...node === "e" ? [ tool("preview_frame", {
        time: {
            type: "integer",
            enum: [ 0, 8, 16, 24, 32 ]
        }
    }, 0), tool("submit_evidence", {
        segments: {
            ...arr(int(1, 8), 1, 8),
            uniqueItems: true
        }
    }) ] : [ tool("submit_video_answer", {
        destination: str([ "left bin", "middle bin", "right bin" ]),
        count: int(0, 4),
        recipients: arr(str([ "A", "B", "C", "D" ]), 0, 4)
    }) ] ];
    if (node === "c") return [ tool("joint_move", {
        a: str([ "left", "stay", "right" ]),
        b: str([ "left", "stay", "right" ])
    }) ];
    if (node === "c-d") return [ tool("submit_shift", {
        woodWorkers: int(0, 4),
        oreWorkers: int(0, 4),
        energyWorkers: int(0, 4),
        productX: int(0, 2),
        productY: int(0, 2),
        expand: {
            type: "boolean"
        }
    }) ];
    if (node === "c-d-a") return [ tool("write_cell", {
        row: int(1, 4),
        column: int(1, 4),
        value: int(1, 4)
    }), tool("undo_write"), tool("submit_board") ];
    if (node === "b") return [ tool("read_archive", {
        time: {
            type: "integer",
            enum: [ 0, 1, 2, 4 ]
        }
    }, "1 if unopened; otherwise 0"), tool("review_round", {round: int(1, 6)}, 0), tool("submit_allocation", {
        troops: arr(int(0, v === 3 ? 14 : 13), 3, 3)
    }) ];
    if (node === "c-a") return [ tool("scan_room"), tool("move_room", {
        room: str([ "window", "tool rack", "arch" ])
    }), tool("seal_orders"), tool("take_cabinet", {
        cabinet: int(1, 4)
    }), tool("deliver_batch"), tool("return_last_item") ];
    if (node === "d-a") return [ tool("move_direction", {
        direction: str([ "up", "right", "down", "left" ])
    }) ];
    if (node === "d-b") return [ tool("submit_code", {
        symbols: arr(str("ABCDEF".slice(0, [ 6, 5, 6, 5 ][v]).split("")), [ 4, 5, 5, 6 ][v], [ 4, 5, 5, 6 ][v])
    }) ];
    throw Error("Unknown environment");
}

function valid(value, s) {
    if (s.enum && !s.enum.includes(value)) return false;
    if (s.type === "integer") return Number.isInteger(value) && (s.minimum == null || value >= s.minimum) && (s.maximum == null || value <= s.maximum);
    if (s.type === "string") return typeof value === "string";
    if (s.type === "boolean") return typeof value === "boolean";
    if (s.type === "array") return Array.isArray(value) && value.length >= s.minItems && value.length <= s.maxItems && (!s.uniqueItems || new Set(value).size === value.length) && value.every(x => valid(x, s.items));
    if (s.type === "object") return value && typeof value === "object" && !Array.isArray(value) && Object.keys(value).every(k => Object.hasOwn(s.properties, k) && valid(value[k], s.properties[k])) && s.required.every(k => Object.hasOwn(value, k));
    return false;
}

function receipt(r, kind, cost, error = null, frames = null) {
    const s = r.inspect();
    return {
        accepted: kind !== "rejected",
        kind: kind,
        cost: cost,
        steps: s.steps,
        budget: s.budget,
        terminated: s.ended,
        reward: s.ended ? Number(s.success) : 0,
        error: error,
        task: r.task(),
        observation: {
            mimeType: "image/png",
            data: r.frame()
        },
        ...frames ? {
            frames: frames
        } : {}
    };
}

export function observe(r) {
    return receipt(r, "observation", 0);
}

export function execute(r, node, v, name, input = {}) {
    const before = r.inspect(), spec = actionsFor(node, v).find(t => t.name === name);
    if (before.ended) return receipt(r, "rejected", 0, "episode_ended");
    if (!spec || !valid(input, spec.input_schema)) return receipt(r, "rejected", 0, "invalid_action");
    if (name === "submit_verification" && (!input.yes && !input.reason || input.yes && Object.hasOwn(input, "reason"))) return receipt(r, "rejected", 0, "invalid_action");
    if (name === "submit_video_answer" && input.count !== input.recipients.length) return receipt(r, "rejected", 0, "invalid_action");
    if (name === "submit_allocation" && input.troops.reduce((a, b) => a + b, 0) !== (v === 3 ? 14 : 13)) return receipt(r, "rejected", 0, "invalid_action");
    let free = false, frames = null;
    try {
        const set = (k, val) => r.set(k, val), call = label => r.call(label);
        if (name === "inspect_station") call("inspect " + input.station + " / 1 step"); else if (name === "raise_cover") call("raise east rear cover / 1 step"); else if (name === "record_defect") {
            set("obs-member", input.member);
            set("obs-fault", input.kind === "remove" ? "undo" : input.kind);
            call("record member / 1 step");
        } else if (name === "submit_inspection") call("submit inspection / 1 step"); else if (name === "inspect_view") call(input.view + " / 1 step"); else if (name === "submit_verification") {
            if (input.reason) set("obs-reason", input.reason);
            call(input.yes ? "confirm all requirements / 1 step" : "reject selected contradiction / 1 step");
        } else if (name === "preview_frame") {
            call("preview " + input.time + "s");
            free = true;
        } else if (name === "watch_segment") {
            const label = before.commands.find(x => new RegExp("^(replay segment |unlock / 1 step )" + input.segment + "\\.").test(x));
            if (!label) throw Error("unavailable");
            free = label.startsWith("replay");
            call(label);
            if (!r.inspect().ended) {
                frames = [];
                for (let i = 0; i < 17; i++) {
                    if (i) call("next frame +0.25s / free");
                    const timestamp = Number(r.inspect().overlay.match(/^Frame ([0-9.]+)s/)?.[1]);
                    if (!Number.isFinite(timestamp)) throw Error("frame_time");
                    frames.push({
                        timestamp: timestamp,
                        mimeType: "image/png",
                        data: r.frame()
                    });
                }
            }
        } else if (name === "submit_evidence") {
            const purchased = before.commands.filter(x => /^(deselect |select )evidence segment \d+ \/ free$/.test(x));
            if (input.segments.some(i => !purchased.some(x => x.includes("segment " + i + " /")))) return receipt(r, "rejected", 0, "segment_not_purchased");
            for (const label of purchased) {
                const i = Number(label.match(/segment (\d+)/)[1]);
                if (label.startsWith("deselect ") !== input.segments.includes(i)) call(label);
            }
            call("submit evidence set / 1 step");
        } else if (name === "submit_video_answer") {
            set("obs-dest", input.destination);
            set("obs-count", input.count);
            for (let i = 0; i < 4; i++) set("obs-route" + i, input.recipients[i] ?? "—");
            call("submit video answer / 1 step");
        } else if (name === "joint_move") {
            set("da", input.a);
            set("db", input.b);
            call("joint move");
        } else if (name === "submit_shift") {
            for (const [key, id] of Object.entries({
                woodWorkers: "wood",
                oreWorkers: "ore",
                energyWorkers: "energy",
                productX: "makeX",
                productY: "makeY"
            })) set(id, input[key]);
            set("build", input.expand ? "yes" : "no");
            call("execute shift");
        } else if (name === "write_cell") {
            set("boardRow", input.row);
            set("boardCol", input.column);
            call("select cell");
            call(String(input.value));
        } else if (name === "undo_write") call("undo"); else if (name === "submit_board") call("submit board"); else if (name === "read_archive") {
            const replay = "replay archive " + input.time + " / free";
            free = before.commands.includes(replay);
            call(free ? replay : "read archive " + input.time + " (1 step)");
        } else if (name === "review_round") {
            call("review round " + input.round + " / free");
            free = true;
        } else if (name === "submit_allocation") {
            input.troops.forEach((n, i) => set("b-" + i, n));
            call("submit allocation (1 step)");
        } else if (name === "scan_room") call("scan room (1 step)"); else if (name === "move_room") call("move to " + input.room + " (1 step)"); else if (name === "seal_orders") call("seal and receive orders (1 step)"); else if (name === "take_cabinet") call("take " + input.cabinet + " slot (1 step)"); else if (name === "deliver_batch") call("deliver batch (1 step)"); else if (name === "return_last_item") call("return last item (1 step)"); else if (name === "move_direction") call("move " + input.direction + " (1 step)"); else if (name === "submit_code") {
            input.symbols.forEach((s, i) => set("code-" + i, s));
            call("submit code (1 step)");
        }
        const cost = r.inspect().steps - before.steps;
        if (cost < 0 || cost > 1) throw Error("step_invariant");
        const result = receipt(r, cost ? "world" : free ? "observation" : "rejected", cost, cost || free ? null : "action_unavailable", frames);
        return result;
    } catch {
        const cost = r.inspect().steps - before.steps;
        return receipt(r, cost ? "world" : "rejected", cost, cost ? "observation_error" : "action_unavailable", frames);
    }
}
