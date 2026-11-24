                                                                              
                                                                   
                                                                              
                                                                           
                                                                              
                                                                               
 
                                   
                                                                         
                                                                               
                                       
                                                                                 
                                                                         
                                                                           
                                                                 
                                                                              
                                                                             
                                            
                                                                                     
 
                                         
                                                                           
                                                 
                                                                              
import importlib.util
import logging
import os
import sys
from pathlib import Path

import numpy as np
from arcengine import FrameData, GameAction, GameState

try:
    from ..agent import Agent
except Exception:
    from agents.agent import Agent

logger = logging.getLogger(__name__)

                                                                               
                                                                           
                                                                         
                                                                              
                                                                               
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_CANDIDATES = [
    _HERE / "submitted_my_agent.py",                                        
    _ROOT / "submission" / "my_agent.py",
    _ROOT / "fallback" / "fallback_explorer.py",
]
_SRC = next((p for p in _CANDIDATES if p.exists()), None)
if _SRC is None:
    raise RuntimeError("No FallbackExplorer source found; cannot run diagnostic.")

logger.info("[FALLBACK_DIAG] importing FallbackExplorer from %s", _SRC)
_spec = importlib.util.spec_from_file_location("_fb_src", _SRC)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["_fb_src"] = _mod
_spec.loader.exec_module(_mod)
FallbackExplorer = _mod.FallbackExplorer

                                                                               
_fb_board = getattr(_mod, "fb_board", None) or getattr(_mod, "board_from_any", None)
_fb_signature = getattr(_mod, "fb_signature", None) or getattr(_mod, "_signature", None)


def _board(frame):
    try:
        if _fb_board is not None:
            return _fb_board(frame)
    except Exception:
        pass
    raw = getattr(frame, "frame", frame)
    if raw is None:
        return None
    a = np.array(raw, dtype=np.int16)
    return a[-1] if a.ndim == 3 else (a if a.ndim == 2 else None)


def _sig(grid):
    try:
        if _fb_signature is not None:
            return _fb_signature(grid)
    except Exception:
        pass
    return "n/a"


class FallbackOnly(Agent):
    pass                                                                              

                                                                                  
    MAX_ACTIONS = int(os.getenv("FALLBACK_MAX_ACTIONS", "600"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.explorer = FallbackExplorer()
        self._last_level = -1
        self._actions_this_level = 0
        self._total = 0
        self._sig_counts = {}                                                    
        self._prev_sig = None
        self._prev_board = None
        self._noops = 0
        self._game_over_count = 0
        self._term_reason = None
        self._max_level = 0

                                                                                
    def is_done(self, frames, latest_frame):
        state = getattr(latest_frame, "state", None)
        lvl = int(getattr(latest_frame, "levels_completed", 0) or 0)
        self._max_level = max(self._max_level, lvl)
        if state is GameState.GAME_OVER:
            self._game_over_count += 1
        if state in (GameState.WIN, GameState.GAME_OVER):
            self._term_reason = "WIN" if state is GameState.WIN else "GAME_OVER"
            logger.info(
                "[FALLBACK_DIAG] TERMINAL reason=%s level=%d max_level=%d "
                "total_actions=%d noops=%d game_overs=%d distinct_sigs=%d",
                self._term_reason, lvl, self._max_level, self._total,
                self._noops, self._game_over_count, len(self._sig_counts),
            )
            return True
        return False

    def choose_action(self, frames, latest_frame):
        lvl = int(getattr(latest_frame, "levels_completed", 0) or 0)
        state = getattr(latest_frame, "state", None)

                                     
        if lvl != self._last_level:
            if self._last_level >= 0:
                logger.info(
                    "[FALLBACK_DIAG] LEVEL_ADVANCE into=%d prev_level_actions=%d "
                    "total=%d", lvl, self._actions_this_level, self._total,
                )
            self._last_level = lvl
            self._actions_this_level = 0

                                                    
        board = _board(latest_frame)
        sig = _sig(board)
        self._sig_counts[sig] = self._sig_counts.get(sig, 0) + 1
        repeat_n = self._sig_counts[sig]

        diff_size = None
        is_noop = False
        if self._prev_board is not None and board is not None and \
                getattr(self._prev_board, "shape", None) == getattr(board, "shape", None):
            diff_size = int(np.sum(self._prev_board != board))
            if diff_size == 0:
                is_noop = True
                self._noops += 1

                                                               
        untried_here = None
        try:
            untried_here = len(self.explorer.untried.get(sig, []))
        except Exception:
            pass

                           
        try:
            action = self.explorer.choose_action(frames, latest_frame)
        except Exception as exc:
            logger.exception("[FALLBACK_DIAG] explorer raised: %s", exc)
            self._term_reason = "EXPLORER_ERROR"
            return GameAction.RESET

                                               
        aid = getattr(action, "value", action)
        xy = None
        data = getattr(action, "data", None) or getattr(action, "_data", None)
        if isinstance(data, dict):
            xy = (data.get("x"), data.get("y"))

        logger.info(
            "[FALLBACK_DIAG] step=%d lvl=%d state=%s action=%s xy=%s sig=%s "
            "repeat=%d untried=%s diff=%s noop=%s",
            self._total, lvl, state, aid, xy, sig, repeat_n,
            untried_here, diff_size, is_noop,
        )

        self._prev_sig = sig
        self._prev_board = board
        self._actions_this_level += 1
        self._total += 1
        return action

                                                                   
    def cleanup(self, *args, **kwargs):
        logger.info(
            "[FALLBACK_DIAG] SUMMARY term=%s max_level=%d total_actions=%d "
            "noops=%d game_overs=%d distinct_sigs=%d",
            self._term_reason or "BUDGET_EXHAUSTED", self._max_level,
            self._total, self._noops, self._game_over_count, len(self._sig_counts),
        )
        try:
            return super().cleanup(*args, **kwargs)
        except Exception:
            return None
