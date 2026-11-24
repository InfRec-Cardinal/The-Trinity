import * as T from "./vendor/three.module.js";

import { createLevel as observation } from "./groups/observation.js";

import { createLevel as planning } from "./groups/planning.js";

import { createLevel as inference } from "./groups/inference.js";

export function createRuntime(node, variant, {width: width = 1200, height: height = 612} = {}) {
    const scene = new T.Scene;
    scene.background = new T.Color("#213641");
    const renderer = new T.WebGLRenderer({
        antialias: true,
        preserveDrawingBuffer: true
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(1);
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    const camera = new T.PerspectiveCamera(48, width / height, .1, 100);
    scene.add(new T.HemisphereLight(14939391, 6840396, 2.3));
    const sun = new T.DirectionalLight(16769980, 3);
    sun.position.set(3, 10, 5);
    scene.add(sun);
    let group = new T.Group, steps = 0, ended = false, success = null, status = "", overlay = "", history = [], level, labels = [], commands = new Map, fields = new Map;
    scene.add(group);
    const colors = [ 15040361, 7714712, 7186140, 14992497, 10981063, 8632766 ];
    function box(x, y, z, w, h, d, color = 7441297) {
        const m = new T.Mesh(new T.BoxGeometry(w, h, d), new T.MeshStandardMaterial({
            color: color,
            roughness: .65
        }));
        m.position.set(x, y, z);
        group.add(m);
        return m;
    }
    function ball(x, y, z, r, color) {
        const m = new T.Mesh(new T.SphereGeometry(r, 24, 16), new T.MeshStandardMaterial({
            color: color,
            roughness: .65
        }));
        m.position.set(x, y, z);
        group.add(m);
        return m;
    }
    function text(label, x, y, z, size = .45, color = "#eef6f3") {
        labels.push(String(label));
        const c = document.createElement("canvas");
        let ctx = c.getContext("2d");
        ctx.font = "64px sans-serif";
        c.width = Math.min(1800, Math.max(88, Math.ceil(ctx.measureText(label).width + 40)));
        c.height = 128;
        ctx = c.getContext("2d");
        ctx.fillStyle = "#10252ce8";
        ctx.fillRect(0, 0, c.width, 128);
        ctx.fillStyle = color;
        ctx.font = "64px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, c.width / 2, 64, c.width - 24);
        const tex = new T.CanvasTexture(c);
        tex.colorSpace = T.SRGBColorSpace;
        const s = new T.Sprite(new T.SpriteMaterial({
            map: tex,
            depthTest: false
        }));
        s.scale.set(Math.min(size * c.width / 128, 5.8), size, 1);
        s.position.set(x, y, z);
        group.add(s);
        return s;
    }
    function clear() {
        group.traverse(o => {
            o.geometry?.dispose();
            if (o.material) {
                o.material.map?.dispose();
                o.material.dispose();
            }
        });
        scene.remove(group);
        group = new T.Group;
        scene.add(group);
        camera.position.set(0, 10, 13);
        camera.lookAt(0, 0, 0);
        box(0, -.35, 0, 12, .3, 10, 3427411);
    }
    function draw() {
        if (!level) return;
        clear();
        commands.clear();
        fields.clear();
        labels = [];
        overlay = "";
        level.draw();
        renderer.render(scene, camera);
    }
    const ui = {
        THREE: T,
        camera: camera,
        colors: colors,
        group: () => group,
        box: box,
        ball: ball,
        text: text,
        command(label, fn) {
            if (commands.has(label)) throw Error("Duplicate command");
            commands.set(label, fn);
        },
        number(label, id, value, min = 0, max = 20) {
            fields.set(id, {
                value: String(value),
                min: min,
                max: max
            });
        },
        choice(label, id, options) {
            fields.set(id, {
                value: String(options[0]),
                options: options.map(String)
            });
        },
        value: id => fields.get(id)?.value,
        index: id => fields.get(id)?.options.indexOf(fields.get(id).value),
        say: t => {
            status = String(t);
        },
        log: t => {
            history.push(String(t));
        },
        overlay: t => {
            overlay = String(t);
        },
        isEnded: () => ended,
        steps: () => steps,
        finish(ok, message) {
            if (ended) return;
            ended = true;
            success = !!ok;
            status = (ok ? "Success: " : "Ended: ") + message;
        },
        step(message, fn) {
            if (ended) return false;
            steps++;
            history.push(`${steps}. ${message}`);
            fn();
            if (!ended && steps >= level.budget) ui.finish(false, "Decision budget exhausted.");
            draw();
            return true;
        },
        redraw: draw
    };
    level = observation(node, variant, ui) || planning(node, variant, ui) || inference(node, variant, ui);
    if (!level) throw Error("Unknown environment");
    status = "Ready.";
    draw();
    function inspect() {
        return {
            node: node,
            variant: variant,
            steps: steps,
            budget: level.budget,
            ended: ended,
            success: success,
            rules: level.rules,
            status: status,
            overlay: overlay,
            history: [ ...history ],
            labels: [ ...labels ],
            commands: [ ...commands.keys() ],
            fields: Object.fromEntries([ ...fields ].map(([k, v]) => [ k, structuredClone(v) ]))
        };
    }
    function set(id, value) {
        if (ended) throw Error("Episode ended");
        const f = fields.get(id);
        if (!f) throw Error("Unknown parameter");
        if (f.options && !f.options.includes(String(value))) throw Error("Invalid option");
        f.value = String(value);
    }
    function call(label) {
        if (ended) throw Error("Episode ended");
        const command = commands.get(label);
        if (!command) throw Error("Action unavailable");
        command();
        renderer.render(scene, camera);
    }
    function frame() {
        renderer.render(scene, camera);
        return renderer.domElement.toDataURL("image/png").split(",")[1];
    }
    function task() {
        if (level.task) return level.task();
        const lines = overlay.split("\n");
        if (node === "c") return {constraints: lines.filter(line => /^(Tracks |G\d+:|H\d+:|Cargo A:)/.test(line))};
        if (node === "c-d") return {constraints: lines.slice(2).map(line => line.replaceAll(" (settled)", "").replaceAll(" <- current", ""))};
        if (node === "c-d-a") return {revision: lines[0].split(" (")[0], constraints: lines.filter(line => /^\d+\. /.test(line))};
        if (node === "c-a") return {orders: lines.filter(line => /^Order \d+:/.test(line))};
        if (node === "e" || node === "e-f") return {segments: [...commands.keys()].filter(line => /^(replay segment |unlock \/ 1 step )/.test(line)).map(line => line.replace(/^(replay segment |unlock \/ 1 step )/, ""))};
        return {};
    }
    function close() {
        level.dispose?.();
        clear();
        renderer.dispose();
    }
    return {
        inspect: inspect,
        set: set,
        call: call,
        frame: frame,
        task: task,
        close: close
    };
}
