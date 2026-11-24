import http from "node:http";

import fs from "node:fs/promises";

import path from "node:path";

import { fileURLToPath, pathToFileURL } from "node:url";

import { randomUUID } from "node:crypto";

const root = fileURLToPath(new URL(".", import.meta.url));

export const environments = JSON.parse(await fs.readFile(new URL("manifest.json", import.meta.url), "utf8"));

export async function createEngine() {
    const {chromium: chromium} = await (process.env.PLAYWRIGHT_MODULE ? import(pathToFileURL(process.env.PLAYWRIGHT_MODULE)) : import("playwright"));
    const token = randomUUID(), allowed = new Set([ "runtime.mjs", "actions.mjs", "rules.mjs", "groups/observation.js", "groups/planning.js", "groups/inference.js", "vendor/three.module.js", "vendor/three.core.js" ]);
    const assets = http.createServer(async (req, res) => {
        const key = (req.url ?? "").split("?")[0].slice(token.length + 2);
        if (!req.url?.startsWith("/" + token + "/") || !allowed.has(key)) {
            res.writeHead(404);
            res.end();
            return;
        }
        try {
            res.writeHead(200, {
                "Content-Type": "text/javascript",
                "Access-Control-Allow-Origin": "*"
            });
            res.end(await fs.readFile(path.join(root, key)));
        } catch {
            res.writeHead(404);
            res.end();
        }
    });
    await new Promise(resolve => assets.listen(0, "127.0.0.1", resolve));
    const base = `http://127.0.0.1:${assets.address().port}/${token}/`;
    let browser;
    try {
        browser = await chromium.launch({
            headless: true,
            args: [ "--no-sandbox", "--enable-unsafe-swiftshader" ]
        });
    } catch (e) {
        await new Promise(resolve => assets.close(resolve));
        throw e;
    }
    const sessions = new Map;
    function find(id) {
        const session = sessions.get(id);
        if (!session) throw Error("session_not_found");
        return session;
    }
    function serial(id, fn) {
        const s = find(id), next = s.pending.then(() => fn(s));
        s.pending = next.catch(() => {});
        return next;
    }
    async function create({node: node, variant: variant = 0} = {}) {
        if (!environments.some(e => e.node === node && e.variant === variant)) throw Error("invalid_environment");
        const context = await browser.newContext({
            viewport: {
                width: 1200,
                height: 900
            }
        });
        try {
            const page = await context.newPage();
            await page.setContent('<!doctype html><meta charset="utf-8">');
            await page.evaluate(async ({base: base, node: node, variant: variant}) => {
                const [{createRuntime: createRuntime}, actions] = await Promise.all([ import(base + "runtime.mjs"), import(base + "actions.mjs") ]);
                const runtime = createRuntime(node, variant);
                globalThis.transport = {
                    observe: () => actions.observe(runtime),
                    step: async (name, input) => {
                        const result = actions.execute(runtime, node, variant, name, input);
                        if (result.frames) {
                            result.frameSheets = [];
                            for (let i = 0; i < result.frames.length; i += 2) {
                                const frames = result.frames.slice(i, i + 2);
                                const bitmaps = await Promise.all(frames.map(async f => createImageBitmap(await (await fetch('data:image/png;base64,' + f.data)).blob())));
                                const canvas = document.createElement('canvas');
                                canvas.width = Math.max(...bitmaps.map(b => b.width));
                                canvas.height = bitmaps.reduce((n, b) => n + b.height, 0);
                                const ctx = canvas.getContext('2d');
                                ctx.fillStyle = '#12232c'; ctx.fillRect(0, 0, canvas.width, canvas.height);
                                let y = 0;
                                const locations = bitmaps.map((b, j) => {
                                    ctx.drawImage(b, 0, y);
                                    const location = {timestamp:frames[j].timestamp,x:0,y:y,width:b.width,height:b.height};
                                    y += b.height; b.close(); return location;
                                });
                                result.frameSheets.push({frames:locations,mimeType:'image/png',data:canvas.toDataURL('image/png').split(',')[1]});
                            }
                        }
                        return result;
                    },
                    contract: () => ({
                        node: node,
                        variant: variant,
                        budget: runtime.inspect().budget,
                        rules: runtime.inspect().rules,
                        actions: actions.actionsFor(node, variant)
                    })
                };
            }, {
                base: base,
                node: node,
                variant: variant
            });
            const id = randomUUID();
            const [contract, observation] = await Promise.all([ page.evaluate(() => transport.contract()), page.evaluate(() => transport.observe()) ]);
            sessions.set(id, {
                context: context,
                page: page,
                node: node,
                variant: variant,
                pending: Promise.resolve()
            });
            return {
                id: id,
                ...contract,
                ...observation
            };
        } catch (e) {
            await context.close();
            throw e;
        }
    }
    async function observe(id) {
        return serial(id, s => s.page.evaluate(() => transport.observe()));
    }
    async function step(id, request) {
        if (!request || typeof request !== "object" || Object.keys(request).some(k => ![ "action", "args" ].includes(k)) || typeof request.action !== "string") throw Error("invalid_request");
        return serial(id, s => s.page.evaluate(({action: action, args: args}) => transport.step(action, args), {
            action: request.action,
            args: request.args ?? {}
        }));
    }
    async function closeSession(id) {
        return serial(id, async s => {
            sessions.delete(id);
            await s.context.close();
            return {
                closed: true
            };
        });
    }
    async function close() {
        await Promise.all([ ...sessions.values() ].map(s => s.pending.then(() => s.context.close())));
        sessions.clear();
        await browser.close();
        await new Promise(resolve => assets.close(resolve));
    }
    return {
        environments: environments,
        create: create,
        observe: observe,
        step: step,
        closeSession: closeSession,
        close: close
    };
}
