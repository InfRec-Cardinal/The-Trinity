                                                           

                                                                             
                                                                              
                                                                               
                                         
   

from __future__ import annotations

import argparse
import heapq
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class ColoredRect:
    color: int
    rect: Rect
    wall_id: int | None = None


@dataclass(frozen=True)
class ShiftHandle:
    rect: Rect
    src: int
    dst: int


@dataclass(frozen=True)
class Problem:
    gravity: tuple[int, int]
    grid_size: tuple[int, int]
    vessels0: tuple[Rect, ...]
    targets0: tuple[ColoredRect, ...]
    payloads: tuple[ColoredRect, ...]
    walls: tuple[Rect, ...]
    floors: tuple[Rect, ...]
    shifts: tuple[ShiftHandle, ...]
    swaps: tuple[Rect, ...]


@dataclass(frozen=True)
class State:
    vessels: tuple[Rect, ...]
    targets: tuple[ColoredRect, ...]


Action = tuple[str, int]


def load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("vc33_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rect(sprite: Any) -> Rect:
    return Rect(sprite.x, sprite.y, sprite.width, sprite.height)


def sprite_color(sprite: Any) -> int | None:
    ignored = {0, 1, 4, 5, 9}
    values = sorted({int(x) for row in sprite.pixels for x in row})
    colors = [value for value in values if value >= 0 and value not in ignored]
    return colors[0] if colors else None


def collides(a: Rect, b: Rect) -> bool:
    return a.x < b.x + b.w and a.x + a.w > b.x and a.y < b.y + b.h and a.y + a.h > b.y


def positive(problem: Problem) -> bool:
    dx, dy = problem.gravity
    return dx > 0 or dy > 0


def horizontal(problem: Problem) -> bool:
    return problem.gravity[0] != 0


def axis(problem: Problem, r: Rect) -> int:
    return r.y if horizontal(problem) else r.x


def cross(problem: Problem, r: Rect) -> int:
    return r.x if horizontal(problem) else r.y


def thickness(problem: Problem, r: Rect) -> int:
    return r.h if horizontal(problem) else r.w


def length(problem: Problem, r: Rect) -> int:
    return r.w if horizontal(problem) else r.h


def far(problem: Problem, r: Rect) -> int:
    return cross(problem, r) + length(problem, r) if positive(problem) else cross(problem, r)


def near(problem: Problem, r: Rect) -> int:
    return cross(problem, r) if positive(problem) else cross(problem, r) + length(problem, r)


def move_rect(r: Rect, dx: int, dy: int) -> Rect:
    return Rect(r.x + dx, r.y + dy, r.w, r.h)


def resize_shift(problem: Problem, src: Rect, dst: Rect) -> tuple[Rect, Rect]:
    dx, dy = problem.gravity
    q = abs(dx or dy)
    if dx != 0:
        src = Rect(src.x + (dx if dx >= 0 else 0), src.y, src.w - q, src.h)
        dst = Rect(dst.x + (-dx if dx >= 0 else 0), dst.y, dst.w + q, dst.h)
    else:
        src = Rect(src.x, src.y + (dy if dy >= 0 else 0), src.w, src.h - q)
        dst = Rect(dst.x, dst.y + (-dy if dy >= 0 else 0), dst.w, dst.h + q)
    return src, dst


def vessel_walls(problem: Problem, vessel: Rect) -> list[int]:
    ids = []
    for i, wall in enumerate(problem.walls):
        if axis(problem, wall) + thickness(problem, wall) == axis(problem, vessel) or axis(problem, wall) == axis(problem, vessel) + thickness(problem, vessel):
            ids.append(i)
    return ids


def target_on_vessel(problem: Problem, target: Rect, vessel: Rect) -> bool:
    return (
        axis(problem, target) >= axis(problem, vessel)
        and axis(problem, target) < axis(problem, vessel) + thickness(problem, vessel)
        and far(problem, target) == near(problem, vessel)
    )


def targets_on_vessel(problem: Problem, state: State, vessel_id: int) -> list[int]:
    vessel = state.vessels[vessel_id]
    return [i for i, target in enumerate(state.targets) if target_on_vessel(problem, target.rect, vessel)]


def floor_limit(problem: Problem, state: State, vessel_id: int) -> int:
    vessel = state.vessels[vessel_id]
    if positive(problem):
        floors = [floor for floor in problem.floors if axis(problem, floor) == axis(problem, vessel) and far(problem, floor) < far(problem, vessel)]
    else:
        floors = [floor for floor in problem.floors if axis(problem, floor) == axis(problem, vessel) and far(problem, floor) > far(problem, vessel)]

    if floors:
        if targets_on_vessel(problem, state, vessel_id):
            return max(far(problem, floor) - (6 if problem.gravity[0] == -3 else 4) for floor in floors)
        return max(far(problem, floor) for floor in floors)

    walls = [problem.walls[i] for i in vessel_walls(problem, vessel)]
    if positive(problem):
        return max(near(problem, wall) for wall in walls)
    return min(near(problem, wall) for wall in walls)


def shift(problem: Problem, state: State, handle_id: int) -> State | None:
    handle = problem.shifts[handle_id]
    src = state.vessels[handle.src]
    dst = state.vessels[handle.dst]
    if length(problem, src) <= 0:
        return None
    limit = floor_limit(problem, state, handle.dst)
    can_move = cross(problem, dst) > limit if positive(problem) else near(problem, dst) < limit
    if not can_move:
        return None

    dx, dy = problem.gravity
    target_ids_src = targets_on_vessel(problem, state, handle.src)
    target_ids_dst = targets_on_vessel(problem, state, handle.dst)
    targets = list(state.targets)
    for target_id in target_ids_src:
        target = targets[target_id]
        targets[target_id] = ColoredRect(target.color, move_rect(target.rect, dx, dy), target.wall_id)
    for target_id in target_ids_dst:
        target = targets[target_id]
        targets[target_id] = ColoredRect(target.color, move_rect(target.rect, -dx, -dy), target.wall_id)

    vessels = list(state.vessels)
    vessels[handle.src], vessels[handle.dst] = resize_shift(problem, src, dst)
    next_state = State(tuple(vessels), tuple(targets))
    return next_state if next_state != state else None


def swap_pair(problem: Problem, state: State, swap_rect: Rect) -> tuple[int, int] | None:
    candidates = [
        i
        for i, vessel in enumerate(state.vessels)
        if near(problem, vessel) == far(problem, swap_rect)
    ]
    left = [
        i
        for i in candidates
        if axis(problem, state.vessels[i]) + thickness(problem, state.vessels[i]) == axis(problem, swap_rect)
    ]
    right = [
        i
        for i in candidates
        if axis(problem, state.vessels[i]) == axis(problem, swap_rect) + thickness(problem, swap_rect)
    ]
    if not left or not right:
        return None
    return left[0], right[0]


def swap(problem: Problem, state: State, swap_id: int) -> State | None:
    pair = swap_pair(problem, state, problem.swaps[swap_id])
    if pair is None:
        return None
    left_id, right_id = pair
    left = state.vessels[left_id]
    right = state.vessels[right_id]
    left_targets = targets_on_vessel(problem, state, left_id)
    right_targets = targets_on_vessel(problem, state, right_id)
    if not left_targets and not right_targets:
        return None

    targets = list(state.targets)
    if horizontal(problem):
        for target_id in left_targets:
            target = targets[target_id]
            y = right.y + right.h // 2 - target.rect.h // 2
            targets[target_id] = ColoredRect(target.color, Rect(target.rect.x, y, target.rect.w, target.rect.h), target.wall_id)
        for target_id in right_targets:
            target = targets[target_id]
            y = left.y + left.h // 2 - target.rect.h // 2
            targets[target_id] = ColoredRect(target.color, Rect(target.rect.x, y, target.rect.w, target.rect.h), target.wall_id)
    else:
        for target_id in left_targets:
            target = targets[target_id]
            x = right.x + right.w // 2 - target.rect.w // 2
            targets[target_id] = ColoredRect(target.color, Rect(x, target.rect.y, target.rect.w, target.rect.h), target.wall_id)
        for target_id in right_targets:
            target = targets[target_id]
            x = left.x + left.w // 2 - target.rect.w // 2
            targets[target_id] = ColoredRect(target.color, Rect(x, target.rect.y, target.rect.w, target.rect.h), target.wall_id)

    next_state = State(state.vessels, tuple(targets))
    return next_state if next_state != state else None


def next_states(problem: Problem, state: State) -> list[tuple[Action, State]]:
    out: list[tuple[Action, State]] = []
    for i in range(len(problem.shifts)):
        nxt = shift(problem, state, i)
        if nxt is not None:
            out.append((("shift", i), nxt))
    for i in range(len(problem.swaps)):
        nxt = swap(problem, state, i)
        if nxt is not None:
            out.append((("swap", i), nxt))
    return out


def satisfied_targets(problem: Problem, state: State) -> int:
    count = 0
    for target in state.targets:
        target_vessels = [i for i, vessel in enumerate(state.vessels) if target_on_vessel(problem, target.rect, vessel)]
        if not target_vessels:
            continue
        wall_ids = set(vessel_walls(problem, state.vessels[target_vessels[0]]))
        ok = any(
            payload.color == target.color
            and cross(problem, payload.rect) == cross(problem, target.rect)
            and payload.wall_id in wall_ids
            for payload in problem.payloads
        )
        if ok:
            count += 1
    return count


def is_win(problem: Problem, state: State) -> bool:
    return satisfied_targets(problem, state) == len(state.targets)


def heuristic(problem: Problem, state: State) -> int:
    return len(state.targets) - satisfied_targets(problem, state)


def signature(state: State) -> tuple[Any, ...]:
    return (
        tuple((v.x, v.y, v.w, v.h) for v in state.vessels),
        tuple((t.color, t.rect.x, t.rect.y, t.rect.w, t.rect.h) for t in state.targets),
    )


def astar(problem: Problem, start: State, max_expansions: int) -> tuple[list[Action] | None, int, int]:
    queue: list[tuple[int, int, int, State, list[Action]]] = []
    counter = 0
    heapq.heappush(queue, (heuristic(problem, start), 0, counter, start, []))
    best = {signature(start): 0}
    expansions = 0
    while queue and expansions < max_expansions:
        _, cost, _, state, path = heapq.heappop(queue)
        if is_win(problem, state):
            return path, expansions, len(best)
        if cost != best.get(signature(state)):
            continue
        expansions += 1
        for action, nxt in next_states(problem, state):
            ncost = cost + 1
            sig = signature(nxt)
            if ncost >= best.get(sig, 10**9):
                continue
            best[sig] = ncost
            counter += 1
            heapq.heappush(queue, (ncost + heuristic(problem, nxt), ncost, counter, nxt, path + [action]))
    return None, expansions, len(best)


def extract_problem(module: Any, level_index: int) -> tuple[Problem, State]:
    game = module.Vc33()
    game.set_level(level_index)
    level = game.current_level
    vessels_src = level.get_sprites_by_tag("0043nzrtobajqi")
    vessel_ids = {id(sprite): i for i, sprite in enumerate(vessels_src)}
    walls_src = level.get_sprites_by_tag("0025yfyiswdvoh")
    walls = tuple(rect(sprite) for sprite in walls_src)
    floors = tuple(rect(sprite) for sprite in level.get_sprites_by_tag("0001symqacyexa"))

    payloads = []
    for sprite in level.get_sprites_by_tag("0010gnulkywfpz"):
        color = sprite_color(sprite)
        wall_id = None
        for i, wall in enumerate(walls_src):
            if wall.collides_with(sprite):
                wall_id = i
                break
        if color is not None:
            payloads.append(ColoredRect(color, rect(sprite), wall_id))

    targets = []
    for sprite in level.get_sprites_by_tag("0016uciqlhjlom"):
        color = sprite_color(sprite)
        if color is not None:
            targets.append(ColoredRect(color, rect(sprite), None))

    shifts = []
    for control, (src, dst) in game.wrcxjliglr.items():
        shifts.append(ShiftHandle(rect(control), vessel_ids[id(src)], vessel_ids[id(dst)]))

    problem = Problem(
        gravity=tuple(level.get_data("Gravity")),
        grid_size=tuple(level.grid_size),
        vessels0=tuple(rect(sprite) for sprite in vessels_src),
        targets0=tuple(targets),
        payloads=tuple(payloads),
        walls=walls,
        floors=floors,
        shifts=tuple(shifts),
        swaps=tuple(rect(sprite) for sprite in level.get_sprites_by_tag("0004sttgkofqwb")),
    )
    return problem, State(problem.vessels0, problem.targets0)


def source_state(module: Any, game: Any) -> State:
    targets = []
    for sprite in game.current_level.get_sprites_by_tag("0016uciqlhjlom"):
        color = sprite_color(sprite)
        if color is not None:
            targets.append(ColoredRect(color, rect(sprite), None))
    vessels = tuple(rect(sprite) for sprite in game.current_level.get_sprites_by_tag("0043nzrtobajqi"))
    return State(vessels, tuple(targets))


def settle_source(game: Any, max_steps: int = 300) -> bool:
    steps = 0
    while game.bnnqyrupir is not None and steps < max_steps:
        if game.bnnqyrupir.xryezihexa():
            game.bnnqyrupir = None
            game.wpcgsoumbr()
            return True
        steps += 1
    return game.bnnqyrupir is None


def apply_to_source(module: Any, game: Any, problem: Problem, action: Action) -> bool:
    kind, index = action
    if kind == "shift":
        handle = problem.shifts[index].rect
        matches = [
            sprite
            for sprite in game.current_level.get_sprites_by_tag("0022jvmlspyigc")
            if rect(sprite) == handle
        ]
        if not matches:
            return False
        game.iootdyzbwv(matches[0])
        game.wpcgsoumbr()
        return True
    swap_rect = problem.swaps[index]
    matches = [
        sprite
        for sprite in game.current_level.get_sprites_by_tag("0004sttgkofqwb")
        if rect(sprite) == swap_rect
    ]
    if not matches or not game.ezbubuphlm(matches[0]):
        return False
    game.bnnqyrupir = game.mwsdltsaxd(matches[0])
    for lock in game.current_level.get_sprites_by_tag("0007gyluczquhi"):
        lock.set_visible(False)
    return settle_source(game)


def replay_on_source(module: Any, level_index: int, problem: Problem, start: State, plan: list[Action]) -> tuple[bool, str]:
    game = module.Vc33()
    game.set_level(level_index)
    compact = start
    if signature(source_state(module, game)) != signature(compact):
        return False, "initial_state_mismatch"
    for step_index, action in enumerate(plan, 1):
        if action[0] == "shift":
            compact_next = shift(problem, compact, action[1])
        else:
            compact_next = swap(problem, compact, action[1])
        if compact_next is None:
            return False, f"compact_rejected_step_{step_index}_{action}"
        if not apply_to_source(module, game, problem, action):
            return False, f"source_rejected_step_{step_index}_{action}"
        compact = compact_next
        src = source_state(module, game)
        if signature(src) != signature(compact):
            return False, f"state_mismatch_step_{step_index}_{action}: compact={signature(compact)} source={signature(src)}"
    if is_win(problem, compact) != game.ielczunthe():
        return False, f"win_mismatch compact={is_win(problem, compact)} source={game.ielczunthe()}"
    return game.ielczunthe(), "win" if game.ielczunthe() else "plan_did_not_win"


def action_label(problem: Problem, action: Action) -> str:
    kind, index = action
    if kind == "shift":
        h = problem.shifts[index]
        return f"shift#{index}@({h.rect.x},{h.rect.y}) src={h.src}->dst={h.dst}"
    r = problem.swaps[index]
    return f"swap#{index}@({r.x},{r.y})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--max-expansions", type=int, default=200_000)
    parser.add_argument("--levels", default="all", help="Comma-separated 1-based levels, or all")
    args = parser.parse_args()

    module = load_module(args.source)
    if args.levels == "all":
        level_indices = range(len(module.levels))
    else:
        level_indices = [int(part) - 1 for part in args.levels.split(",") if part.strip()]

    for level_index in level_indices:
        problem, start = extract_problem(module, level_index)
        plan, expansions, seen = astar(problem, start, args.max_expansions)
        print(
            f"[VC33_VALIDATE] level={level_index + 1} "
            f"plan={'FOUND' if plan else 'NONE'} depth={len(plan) if plan else None} "
            f"expansions={expansions} seen={seen} "
            f"start_satisfied={satisfied_targets(problem, start)}/{len(start.targets)}"
        )
        print(
            f"[VC33_VALIDATE] level={level_index + 1} model "
            f"vessels={len(problem.vessels0)} shifts={len(problem.shifts)} "
            f"swaps={len(problem.swaps)} payloads={[(p.color, p.wall_id, p.rect) for p in problem.payloads]} "
            f"targets={[(t.color, t.rect) for t in problem.targets0]}"
        )
        if not plan:
            continue
        ok, reason = replay_on_source(module, level_index, problem, start, plan)
        print(f"[VC33_VALIDATE] level={level_index + 1} source_replay={ok} reason={reason}")
        print(
            f"[VC33_VALIDATE] level={level_index + 1} actions="
            + " | ".join(action_label(problem, action) for action in plan)
        )


if __name__ == "__main__":
    main()
