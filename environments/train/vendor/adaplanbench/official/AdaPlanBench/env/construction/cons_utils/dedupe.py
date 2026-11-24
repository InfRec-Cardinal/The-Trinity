from __future__ import annotations

from typing import Callable, List, Sequence


def dedupe_preserve_order(
    items: Sequence[str],
    *,
    key: Callable[[str], str] = str.casefold,
) -> List[str]:
    pass                                                                             
    seen = set()
    out: List[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        normalized = key(text)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(text)
    return out


def union_dedupe(*lists: Sequence[str]) -> List[str]:
    pass                                                                             
    merged: List[str] = []
    for items in lists:
        for item in items:
            merged.append(str(item))
    return dedupe_preserve_order(merged)


def is_subset(
    prev: Sequence[str],
    curr: Sequence[str],
    *,
    key: Callable[[str], str] = str.casefold,
) -> bool:
    pass                                                             
    prev_keys = {key(str(item).strip()) for item in prev if str(item).strip()}
    curr_keys = {key(str(item).strip()) for item in curr if str(item).strip()}
    return prev_keys.issubset(curr_keys)
