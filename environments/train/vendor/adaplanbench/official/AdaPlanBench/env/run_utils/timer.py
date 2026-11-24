from __future__ import annotations

import threading
import time
from typing import Dict, List, Tuple


class RuntimeTimer:
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
        self._lock = threading.Lock()
        self._stats: Dict[Tuple[str, str], Dict[str, float]] = {}

    def record(self, role: str, model_label: str, duration_s: float) -> None:
        if not self.enabled:
            return
        key = (str(role), str(model_label))
        with self._lock:
            slot = self._stats.setdefault(
                key,
                {"count": 0.0, "total_seconds": 0.0},
            )
            slot["count"] += 1.0
            slot["total_seconds"] += max(0.0, float(duration_s))

    def timed_call(self, role: str, model_label: str, fn, *args, **kwargs):
        started = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            self.record(role, model_label, time.perf_counter() - started)

    def summary_rows(self) -> List[dict]:
        rows: List[dict] = []
        with self._lock:
            items = list(self._stats.items())
        for (role, model_name), stats in sorted(items, key=lambda item: (item[0][0], item[0][1])):
            count = int(stats.get("count", 0.0))
            total_seconds = float(stats.get("total_seconds", 0.0))
            avg_seconds = total_seconds / count if count > 0 else 0.0
            rows.append(
                {
                    "role": role,
                    "model": model_name,
                    "count": count,
                    "total_seconds": total_seconds,
                    "avg_seconds": avg_seconds,
                }
            )
        return rows

    def print_summary(self) -> None:
        if not self.enabled:
            return
        rows = self.summary_rows()
        if not rows:
            print("[timer] enabled but no LLM calls were recorded")
            return
        print("[timer] role/model timing summary")
        for row in rows:
            print(
                "[timer] "
                f"role={row['role']} model={row['model']} "
                f"count={row['count']} total_s={row['total_seconds']:.2f} avg_s={row['avg_seconds']:.2f}"
            )
