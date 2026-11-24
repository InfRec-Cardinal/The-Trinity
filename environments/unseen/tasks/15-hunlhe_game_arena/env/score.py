#!/usr/bin/env python3
                                                                           

                                                                            
                                                                       

                                                                         
                                                                     
                                                                           

                                                                           
                                                        

                                                                         
                                                                        
                                                                             
                                                                         
                                                                        
                        
   

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys

BIG_BLIND = 2


def load_episode(path: pathlib.Path) -> dict:
  text = path.read_text()
  rec = None
  try:
    obj = json.loads(text)
    rec = obj
  except json.JSONDecodeError:
    for line in text.splitlines():
      line = line.strip()
      if not line:
        continue
      r = json.loads(line)
      if r.get("kind") == "terminal":
        rec = r
  if rec is None:
    raise ValueError(f"{path}: no terminal record")
  per_hand = rec.get("perHand")
  if per_hand is not None:
    chips = sum(h["playerChips"] for h in per_hand)
    hands = len(per_hand)
  else:
    chips, hands = rec["playerChipDelta"], rec["hands"]
  ep = rec["episode"]
  ill = rec.get("illegal")
  if ill is None and per_hand is not None:
    ill = {}
    for h in per_hand:
      for k, v in h.get("illegal", {}).items():
        ill[k] = ill.get(k, 0) + v
  return {"episode": ep, "pair": ep // 2, "chips": chips, "hands": hands,
          "complete": rec.get("kind") == "terminal" and hands == 100,
          "illegal": ill or {}, "file": str(path)}


def bb100(chips: float, hands: int) -> float:
  return (chips / BIG_BLIND) / hands * 100 if hands else float("nan")


def bootstrap(blocks: list[tuple[float, int]], B: int, seed: int,
              alpha: float) -> tuple[float, float, float]:
  rng = random.Random(seed)
  n = len(blocks)
  stats = []
  for _ in range(B):
    c = h = 0
    for _ in range(n):
      bc, bh = blocks[rng.randrange(n)]
      c += bc
      h += bh
    stats.append(bb100(c, h))
  stats.sort()
  lo = stats[int((alpha / 2) * B)]
  hi = stats[min(B - 1, int((1 - alpha / 2) * B))]
  mean = sum(stats) / B
  return lo, hi, mean


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__,
                               formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("files", nargs="+", type=pathlib.Path)
  ap.add_argument("--block", choices=["episode", "pair"], default="episode")
  ap.add_argument("--B", type=int, default=10000)
  ap.add_argument("--seed", type=int, default=0)
  ap.add_argument("--alpha", type=float, default=0.05)
  ap.add_argument("--json", type=pathlib.Path)
  args = ap.parse_args()

  eps = [load_episode(p) for p in args.files]
  seen = {}
  for e in eps:
    if e["episode"] in seen:
      print(f"duplicate episode {e['episode']}: {seen[e['episode']]} and "
            f"{e['file']}", file=sys.stderr)
      return 2
    seen[e["episode"]] = e["file"]
  eps.sort(key=lambda e: e["episode"])

  total_c = sum(e["chips"] for e in eps)
  total_h = sum(e["hands"] for e in eps)
  ep_blocks = [(e["chips"], e["hands"]) for e in eps]
  pairs: dict[int, list[dict]] = {}
  for e in eps:
    pairs.setdefault(e["pair"], []).append(e)
  pair_blocks = [(sum(x["chips"] for x in v), sum(x["hands"] for x in v))
                 for _, v in sorted(pairs.items())]
  incomplete_pairs = [k for k, v in pairs.items() if len(v) != 2]
  incomplete_eps = [e["episode"] for e in eps if not e["complete"]]

  res = {
      "episodes": len(eps), "hands": total_h, "playerChipDelta": total_c,
      "bbPer100": bb100(total_c, total_h),
      "bootstrap": {}, "primaryBlock": args.block,
      "B": args.B, "seed": args.seed, "alpha": args.alpha,
      "incompletePairs": incomplete_pairs,
      "incompleteEpisodes": incomplete_eps,
      "illegal": {},
      "perEpisode": [{k: e[k] for k in ("episode", "pair", "hands", "chips")}
                     | {"bbPer100": bb100(e["chips"], e["hands"])} for e in eps],
      "perPair": [{"pair": k, "hands": sum(x["hands"] for x in v),
                   "chips": sum(x["chips"] for x in v),
                   "bbPer100": bb100(sum(x["chips"] for x in v),
                                     sum(x["hands"] for x in v))}
                  for k, v in sorted(pairs.items())],
  }
  for e in eps:
    for k, v in e["illegal"].items():
      res["illegal"][k] = res["illegal"].get(k, 0) + v
  for name, blocks in (("episode", ep_blocks), ("pair", pair_blocks)):
    if len(blocks) >= 2:
      lo, hi, m = bootstrap(blocks, args.B, args.seed, args.alpha)
      res["bootstrap"][name] = {"blocks": len(blocks), "lo": lo, "hi": hi,
                                "bootMean": m}

  print(f"episodes={len(eps)} hands={total_h} chips={total_c:+.1f}")
  print(f"BB/100 = {res['bbPer100']:+.2f}")
  for name in (args.block, "pair" if args.block == "episode" else "episode"):
    b = res["bootstrap"].get(name)
    tag = "primary" if name == args.block else "secondary"
    if b:
      print(f"  {100*(1-args.alpha):.0f}% CI, block={name} ({tag}, "
            f"{b['blocks']} blocks, B={args.B}): [{b['lo']:+.2f}, {b['hi']:+.2f}]")
    else:
      print(f"  block={name}: <2 blocks, no CI")
  if incomplete_pairs:
    print(f"  WARNING: incomplete duplicate pairs: {incomplete_pairs}")
  if incomplete_eps:
    print(f"  WARNING: episodes with != 100 hands or no terminal: {incomplete_eps}")
  print(f"  illegal: {res['illegal']}")
  if args.json:
    args.json.write_text(json.dumps(res, indent=2))
  return 0


if __name__ == "__main__":
  sys.exit(main())
