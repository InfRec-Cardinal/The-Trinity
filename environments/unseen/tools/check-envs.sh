#!/usr/bin/env bash
                                                                                                                           
                                                                                                                             
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALL_ENVS="eda scigym balrog actiview phyre videomme coup hanabi poker buildarena-1.0"
OS="$(uname -s)"

is_known() {
  local n
  for n in $ALL_ENVS; do
    [ "$n" = "$1" ] && return 0
  done
  return 1
}

python_for() {
  local key="UNSEEN17_PY_$(echo "$1" | tr '[:lower:]' '[:upper:]' | tr -c 'A-Z0-9\n' '_')"
  echo "${!key:-$ROOT/envs/$1/bin/python}"
}

                                                                                                                   
                  
check_one() {
  local name="$1" dir="$2" code="$3" py out
  py="$(python_for "$name")"
  if [ ! -x "$py" ]; then
    echo "FAIL $name (no interpreter at $py; run tools/setup-envs.sh $name)"
    return 1
  fi
  if out="$(cd "$dir" && "$py" -I -c "$code" 2>&1)"; then
    echo "OK   $name"
    return 0
  fi
  echo "FAIL $name"
  printf '%s\n' "$out" | tail -n 3 | sed 's/^/     /'
  return 1
}

run_check() {
  local name="$1" dir code=""
  case "$name" in
    eda) dir="$ROOT/tasks/01-entity_deduction_arena/env"; code='import json, ast' ;;
    scigym) dir="$ROOT/tasks/02-scigym_small/env"; code='import sys; sys.path.insert(0,"src"); from scigym.controller import Controller' ;;
    balrog) dir="$ROOT/vendor/balrog"; code='import sys; sys.path.insert(0,"BALROG"); import nle, minihack, crafter; from balrog.environments import make_env' ;;
    actiview) dir="$ROOT/tasks/08-actiview_unseen/env"; code='import PIL, numpy, huggingface_hub' ;;
    phyre)
      dir="$ROOT/tasks/10-phyre_unseen_fold0/env"
      if [ "$OS" = "Darwin" ]; then
        export PHYRE_PKG_DIR="$dir/phyre-macos-arm64-py39"
        code='import sys,os; sys.path.insert(0, os.environ["PHYRE_PKG_DIR"]); import phyre'
      else
        code='import phyre'
      fi
      ;;
    videomme) dir="$ROOT/tasks/12-video_mme_v2_unseen/env"; code='import PIL, pandas' ;;
    coup) dir="$ROOT/tasks/13-coup_textarena_4p/env"; code='import textarena' ;;
    hanabi) dir="$ROOT/tasks/14-hanabi_hle_unseen/env"; code='from hanabi_learning_environment import rl_env' ;;
    poker) dir="$ROOT/tasks/15-hunlhe_game_arena/env"; code='import sys; sys.path.insert(0,"src"); import pyspiel; from game_arena.harness import model_generation' ;;
    buildarena-1.0) dir="$ROOT/tasks/07-buildarena/BuildArena-1.0"; code='import autogen_core, autogen_agentchat, trimesh, fcl, sqlmodel, yaml' ;;
  esac
  check_one "$name" "$dir" "$code"
}

if [ "$#" -eq 0 ]; then
  ENVS=($ALL_ENVS)
else
  ENVS=("$@")
fi

for name in "${ENVS[@]}"; do
  if ! is_known "$name"; then
    echo "error: unknown env '$name' (known: $ALL_ENVS)" >&2
    exit 2
  fi
done

fails=0
for name in "${ENVS[@]}"; do
  run_check "$name" || fails=$((fails + 1))
done

echo
echo "== Tools (informational) =="
if command -v codex >/dev/null 2>&1; then
  echo "OK   codex on PATH (EDA judge, Coup and Poker opponents use gpt-5.6-luna via 'codex exec'; log in with your OpenAI/ChatGPT account)"
else
  echo "WARN codex not on PATH (needed by EDA judge, Coup and Poker opponents)"
fi
if command -v node >/dev/null 2>&1; then
  node_version="$(node --version 2>/dev/null)"
  node_major="${node_version#v}"
  node_major="${node_major%%.*}"
  if [ "$node_major" -ge 20 ] 2>/dev/null; then
    echo "OK   node $node_version (>= 20)"
  else
    echo "WARN node $node_version (< 20; upgrade to 20 or newer)"
  fi
else
  echo "WARN node not on PATH (need version >= 20)"
fi

echo
if [ "$fails" -gt 0 ]; then
  echo "$fails of ${#ENVS[@]} env check(s) failed"
  exit 1
fi
echo "all ${#ENVS[@]} env check(s) passed"
