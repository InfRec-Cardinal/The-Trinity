from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .storage import write_csv, write_json, write_text

PALETTE = ["#3E76AC", "#278878", "#8257A5", "#BE485D", "#A95D8B", "#147F9C", "#B8742B", "#5B6B7F"]


def build_trie(records: list[dict]) -> dict:
    root = {"id": "root", "capability": None, "route": [], "children": {}, "tasks": []}
    entry = lambda r, **extra: {"taskId": r["taskId"], "name": r.get("taskName") or r["taskId"], "cohort": r.get("cohort", "train"), "placement": r["placement"],
                                "subCategory": (r.get("taskTreeOrigin") or {}).get("subCategoryId"), **extra}
    for r in sorted((r for r in records if r.get("cohort", "train") == "train"), key=lambda r: r["taskId"]):
        node = root
        for c in r["capabilityPath"]:
            node = node["children"].setdefault(c, {"id": "-".join(node["route"] + [c]) or c, "capability": c, "route": node["route"] + [c], "children": {}, "tasks": []})
        node["tasks"].append(entry(r))
    for r in sorted((r for r in records if r.get("cohort") == "unseen"), key=lambda r: r["taskId"]):
        node, reached = root, []
        for c in r["capabilityPath"]:
            if c not in node["children"]:
                break
            node = node["children"][c]
            reached.append(c)
        node["tasks"].append(entry(r, **({"attachedAtPrefix": reached, "fullPath": r["capabilityPath"]} if reached != list(r["capabilityPath"]) else {})))
    return root


def flatten(node: dict, order: list[str], out: list | None = None) -> list[dict]:
    out = [] if out is None else out
    out.append({k: v for k, v in node.items() if k != "children"} | {"children": [c["id"] for c in sorted(node["children"].values(), key=lambda n: order.index(n["capability"]))]})
    for child in sorted(node["children"].values(), key=lambda n: order.index(n["capability"])):
        flatten(child, order, out)
    return out


def task_rows(records: list[dict]) -> list[dict]:
    return [{"taskId": r["taskId"], "taskName": r.get("taskName"), "cohort": r.get("cohort", "train"), "subCategory": (r.get("taskTreeOrigin") or {}).get("subCategoryId"),
             "trajectories": r["trajectories"], "success": r["success"], "failure": r["failure"], "placement": r["placement"], "capabilityPath": r["capabilityPath"],
             "missingCapabilities": r["missingCapabilities"], "defectTypes": [d["defectType"] for d in r["defectTypesObserved"]]} for r in records]


def _svg(elements: list[str], w: int, h: int) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif"><rect width="100%" height="100%" fill="#ffffff"/>{"".join(elements)}</svg>'


def _card(el, x, y, tasks, colour):
    h = 10 + 20 * len(tasks)
    w = 24 + max(len(t["name"]) for t in tasks) * 7.2 + 60
    el.append(f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="8" fill="#f7f8fa" stroke="{colour}" stroke-width="1.2"/>')
    for i, t in enumerate(sorted(tasks, key=lambda t: (t["cohort"] != "train", t["name"].lower()))):
        unseen = t["cohort"] != "train"
        fill = "#8a5a00" if unseen else "#1f2a37"
        style = ' font-style="italic"' if unseen else ""
        label = f'{t.get("subCategory") or ""} {t["name"]}{" (U)" if unseen else ""}'.strip()
        el.append(f'<text x="{x + 12}" y="{y + 20 + 20 * i}" font-size="13" fill="{fill}"{style}>{escape(label)}</text>')
    return w, h


def structured_svg(root: dict, order: list[str], names: dict[str, str]) -> str:
    el, X0, COL, y0 = [], 260, 520, 80
    colour = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(order)}
    edges, tops = [], []

    def place(node, depth, y):
        x = X0 + (depth - 1) * COL
        c = node["capability"]
        el.append(f'<rect x="{x}" y="{y}" width="340" height="34" rx="17" fill="{colour[c]}22" stroke="{colour[c]}" stroke-width="1.6"/>')
        el.append(f'<circle cx="{x + 18}" cy="{y + 17}" r="13" fill="{colour[c]}"/><text x="{x + 18}" y="{y + 22}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{c}</text>')
        el.append(f'<text x="{x + 40}" y="{y + 22}" font-size="15" font-weight="bold" fill="#1f2a37">{escape(names.get(c, c))}</text>')
        bottom = y + 34
        if node["tasks"]:
            _, h = _card(el, x + 20, y + 42, node["tasks"], colour[c])
            bottom = y + 42 + h
        cy = y
        for child in sorted(node["children"].values(), key=lambda n: order.index(n["capability"])):
            b = place(child, depth + 1, cy)
            edges.append((x + 340, y + 17, X0 + depth * COL, cy + 17))
            cy = b + 20
            bottom = max(bottom, b)
        return bottom

    y = y0
    for child in sorted(root["children"].values(), key=lambda n: order.index(n["capability"])):
        tops.append(y)
        y = place(child, 1, y) + 24
    if root["tasks"]:
        tops.append(y)
        el.append(f'<text x="{X0}" y="{y + 18}" font-size="14" font-style="italic" fill="#5b6b7f">No capability gap observed</text>')
        _, h = _card(el, X0 + 20, y + 30, root["tasks"], "#9aa3b2")
        y += 30 + h + 20
    ry = (tops[0] + tops[-1]) / 2 if tops else y0
    el.append(f'<rect x="40" y="{ry - 10}" width="150" height="54" rx="12" fill="#243246"/><text x="115" y="{ry + 14}" font-size="20" font-weight="bold" fill="#fff" text-anchor="middle">H0</text>'
              f'<text x="115" y="{ry + 34}" font-size="12" fill="#fff" text-anchor="middle">capability tree</text>')
    for t in tops:
        el.insert(0, f'<path d="M190,{ry + 17} L225,{ry + 17} L225,{t + 17} L{X0},{t + 17}" fill="none" stroke="#97a3b3" stroke-width="1.4"/>')
    for sx, sy, tx, ty in edges:
        mx = tx - 24
        el.insert(0, f'<path d="M{sx},{sy} L{mx},{sy} L{mx},{ty} L{tx},{ty}" fill="none" stroke="#97a3b3" stroke-width="1.4"/>')
    el.append(f'<text x="40" y="40" font-size="24" font-weight="bold" fill="#1f2a37">H0 capability tree (structured): order {", ".join(order)}</text>')
    return _svg(el, X0 + 4 * COL, y + 40)


def flat_svg(records: list[dict], order: list[str], names: dict[str, str]) -> str:
    el, X0, y = [], 260, 80
    colour = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(order)}
    tops = []
    for c in order:
        listed = [{"taskId": r["taskId"], "name": r.get("taskName") or r["taskId"], "cohort": r.get("cohort", "train"), "subCategory": (r.get("taskTreeOrigin") or {}).get("subCategoryId")} for r in records if c in r["capabilityPath"]]
        if not listed:
            continue
        tops.append(y)
        el.append(f'<rect x="{X0}" y="{y}" width="340" height="34" rx="17" fill="{colour[c]}22" stroke="{colour[c]}" stroke-width="1.6"/>')
        el.append(f'<circle cx="{X0 + 18}" cy="{y + 17}" r="13" fill="{colour[c]}"/><text x="{X0 + 18}" y="{y + 22}" font-size="14" font-weight="bold" fill="#fff" text-anchor="middle">{c}</text>')
        el.append(f'<text x="{X0 + 40}" y="{y + 22}" font-size="15" font-weight="bold" fill="#1f2a37">{escape(names.get(c, c))}</text>')
        _, h = _card(el, X0 + 20, y + 42, listed, colour[c])
        y += 42 + h + 24
    ry = (tops[0] + tops[-1]) / 2 if tops else 80
    el.append(f'<rect x="40" y="{ry - 10}" width="150" height="54" rx="12" fill="#243246"/><text x="115" y="{ry + 14}" font-size="20" font-weight="bold" fill="#fff" text-anchor="middle">H0</text>'
              f'<text x="115" y="{ry + 34}" font-size="12" fill="#fff" text-anchor="middle">flat capability tree</text>')
    for t in tops:
        el.insert(0, f'<path d="M190,{ry + 17} L225,{ry + 17} L225,{t + 17} L{X0},{t + 17}" fill="none" stroke="#97a3b3" stroke-width="1.4"/>')
    el.append('<text x="40" y="40" font-size="24" font-weight="bold" fill="#1f2a37">H0 flat capability tree: each capability lists every task that requires it</text>')
    return _svg(el, 1400, y + 40)


def drawio_from_svg(svg: str, name: str) -> str:
    import base64
    data = base64.b64encode(svg.encode()).decode()
    return (f'<mxfile host="trees.py"><diagram name="{escape(name)}" id="{escape(name)}"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            f'<mxCell id="2" value="" style="shape=image;imageAspect=1;image=data:image/svg+xml,{data};" vertex="1" parent="1"><mxGeometry x="0" y="0" width="1400" height="900" as="geometry"/></mxCell>'
            f'</root></mxGraphModel></diagram></mxfile>')


def write_trees(records: list[dict], catalogue: dict, out_dir: Path) -> None:
    order = catalogue["order"]
    names = {cid: c["name"] for cid, c in catalogue["capabilities"].items()}
    train, unseen = [r for r in records if r.get("cohort", "train") == "train"], [r for r in records if r.get("cohort") == "unseen"]
    for folder, structured in (("1-structured-capability-tree", True), ("2-flat-capability-tree", False)):
        d = out_dir / folder
        (d / "figures").mkdir(parents=True, exist_ok=True)
        (d / "tasks").mkdir(parents=True, exist_ok=True)
        rows = task_rows(records)
        write_json(d / "tasks" / "task-capability-gaps.json", records)
        write_csv(d / "tasks" / "task-capability-gaps.csv", [["taskId", "taskName", "cohort", "subCategory", "trajectories", "success", "failure", "placement", "capabilityPath" if structured else "listedUnder", "missingCapabilities", "defectTypes"]]
                  + [[r["taskId"], r["taskName"], r["cohort"], r["subCategory"], r["trajectories"], r["success"], r["failure"], r["placement"],
                      (" -> ".join(r["capabilityPath"]) if structured else ", ".join(sorted(r["capabilityPath"], key=order.index))) or "-",
                      "; ".join(f"{k}:{v}" for k, v in r["missingCapabilities"].items()), "; ".join(r["defectTypes"])] for r in rows])
        tree = {"schema": "h0-structured-capability-tree-v1" if structured else "h0-flat-capability-tree-v1", "tasks": {"train": len(train), "unseen": len(unseen)}, "order": order,
                "orderRule": catalogue.get("orderRule"), "capabilities": {c: {"name": names[c]} for c in order}}
        if structured:
            root = build_trie(records)
            tree["nodes"] = flatten(root, order)
            paths = {}
            for r in records:
                paths.setdefault(" -> ".join(r["capabilityPath"]) or "(none)", []).append({"taskId": r["taskId"], "name": r.get("taskName"), "cohort": r.get("cohort", "train")})
            tree["paths"] = [{"path": p, "tasks": v} for p, v in sorted(paths.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
            write_csv(d / "routes.csv", [["path", "trainTasks", "unseenTasks"]]
                      + [[p["path"], "; ".join(x["name"] or x["taskId"] for x in p["tasks"] if x["cohort"] == "train"), "; ".join(x["name"] or x["taskId"] for x in p["tasks"] if x["cohort"] == "unseen")] for p in tree["paths"]])
            svg = structured_svg(root, order, names)
        else:
            tree["capabilityLists"] = {c: [{"taskId": r["taskId"], "name": r.get("taskName"), "cohort": r.get("cohort", "train")} for r in records if c in r["capabilityPath"]] for c in order}
            write_csv(d / "capability-tree.csv", [["capability", "name", "trainTasks", "unseenTasks"]]
                      + [[c, names[c], "; ".join(x["name"] or x["taskId"] for x in tree["capabilityLists"][c] if x["cohort"] == "train"), "; ".join(x["name"] or x["taskId"] for x in tree["capabilityLists"][c] if x["cohort"] == "unseen")] for c in order])
            svg = flat_svg(records, order, names)
        write_json(d / "capability-tree.json", tree)
        write_text(d / "figures" / "h0-capability-tree.svg", svg)
        write_text(d / "figures" / "h0-capability-tree.drawio", drawio_from_svg(svg, folder))
