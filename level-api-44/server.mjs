import http from "node:http";
import {getPackageInfo} from "./package-info.mjs";

import { pathToFileURL } from "node:url";

import { createEngine } from "./engine.mjs";

export async function startServer({port: port = Number(process.env.PORT ?? 8771), host: host = "127.0.0.1"} = {}) {
    getPackageInfo();
    const engine = await createEngine();
    const server = http.createServer(async (req, res) => {
        const send = (status, data) => {
            res.writeHead(status, {
                "Content-Type": "application/json",
                "Cache-Control": "no-store"
            });
            res.end(JSON.stringify(data));
        };
        const read = async () => {
            let data = "";
            for await (const chunk of req) {
                data += chunk;
                if (Buffer.byteLength(data) > 65536) throw Error("request_too_large");
            }
            return data ? JSON.parse(data) : {};
        };
        try {
            const url = new URL(req.url, "http://localhost"), parts = url.pathname.split("/").filter(Boolean);
            if (req.method === "GET" && url.pathname === "/v1/package") return send(200, getPackageInfo());
            if (req.method === "GET" && url.pathname === "/v1/environments") return send(200, {
                environments: engine.environments
            });
            if (req.method === "POST" && url.pathname === "/v1/sessions") {
                const input = await read();
                if (Object.keys(input).some(k => ![ "node", "variant" ].includes(k))) throw Error("invalid_request");
                return send(201, await engine.create(input));
            }
            if (parts.length >= 3 && parts[0] === "v1" && parts[1] === "sessions") {
                const id = parts[2];
                if (req.method === "DELETE" && parts.length === 3) return send(200, await engine.closeSession(id));
                if (req.method === "POST" && parts.length === 4 && parts[3] === "step") return send(200, await engine.step(id, await read()));
                if (req.method === "GET" && parts.length === 4 && parts[3] === "observation") return send(200, await engine.observe(id));
                if (req.method === "GET" && parts.length === 4 && parts[3] === "frame.png") {
                    const result = await engine.observe(id);
                    res.writeHead(200, {
                        "Content-Type": "image/png",
                        "Cache-Control": "no-store"
                    });
                    return res.end(Buffer.from(result.observation.data, "base64"));
                }
            }
            send(404, {
                error: "not_found"
            });
        } catch (e) {
            send(e.message === "session_not_found" ? 404 : 400, {
                error: [ "session_not_found", "invalid_request", "invalid_environment", "request_too_large" ].includes(e.message) ? e.message : "request_failed"
            });
        }
    });
    try {await new Promise((resolve, reject) => {server.once("error", reject);server.listen(port, host, resolve);});}
    catch(error){await engine.close();throw error;}
    return {
        address: `http://${host}:${server.address().port}`,
        close: async () => {
            await new Promise(resolve => server.close(resolve));
            await engine.close();
        }
    };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    const app = await startServer();
    console.log(app.address);
    for (const signal of [ "SIGINT", "SIGTERM" ]) process.once(signal, async () => {
        await app.close();
        process.exit(0);
    });
}
