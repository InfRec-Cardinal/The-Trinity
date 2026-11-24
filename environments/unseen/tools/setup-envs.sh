#!/usr/bin/env bash
                                                                                                                        
                                                        
                                                              
                                                                                                                      
                                         
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALL_ENVS="eda scigym balrog actiview phyre videomme coup hanabi poker buildarena-1.0"
OS="$(uname -s)"
ARCH="$(uname -m)"

warn() { echo "warning: $*" >&2; }

pyver_for() {
  case "$1" in
    hanabi|buildarena-1.0) echo 3.12 ;;
    phyre|eda) echo 3.9 ;;
    *) echo 3.11 ;;
  esac
}

                                                                                                   
env_dir_for() {
  case "$1" in
    eda) echo "$ROOT/tasks/01-entity_deduction_arena/env" ;;
    scigym) echo "$ROOT/tasks/02-scigym_small/env" ;;
    balrog) echo "$ROOT/vendor/balrog" ;;
    buildarena-1.0) echo "$ROOT/tasks/07-buildarena/BuildArena-1.0" ;;
    actiview) echo "$ROOT/tasks/08-actiview_unseen/env" ;;
    phyre) echo "$ROOT/tasks/10-phyre_unseen_fold0/env" ;;
    videomme) echo "$ROOT/tasks/12-video_mme_v2_unseen/env" ;;
    coup) echo "$ROOT/tasks/13-coup_textarena_4p/env" ;;
    hanabi) echo "$ROOT/tasks/14-hanabi_hle_unseen/env" ;;
    poker) echo "$ROOT/tasks/15-hunlhe_game_arena/env" ;;
  esac
}

is_known() {
  local n
  for n in $ALL_ENVS; do
    [ "$n" = "$1" ] && return 0
  done
  return 1
}

                                                                                                          
setup_one() {
  local name="$1" ver venv env_dir req py
  ver="$(pyver_for "$name")"
  venv="$ROOT/envs/$name"
  env_dir="$(env_dir_for "$name")"
  req="$ROOT/requirements/$name.txt"
  py="$venv/bin/python"

  echo "== $name (Python $ver) =="

  if [ ! -x "$py" ]; then
    mkdir -p "$ROOT/envs" || return 1
    uv venv --python "$ver" "$venv" || { warn "uv venv failed for $name"; return 1; }
  else
    echo "venv exists: $venv"
  fi

  if [ "$name" = "eda" ]; then
    echo "eda: standard library only, no packages to install"
    return 0
  fi

  [ -f "$req" ] || { warn "missing requirements file $req"; return 1; }
  cd "$env_dir" 2>/dev/null || { warn "missing env directory $env_dir"; return 1; }

  case "$name" in
    hanabi)
                                                                                       
      local pkgs=()
      while IFS= read -r line; do
        pkgs+=("$line")
      done < <(grep -vE '^[[:space:]]*(#|$)' "$req" | grep -vx './hanabi-source' || true)
      uv pip install --python "$py" "${pkgs[@]}" || { warn "hanabi build tools failed"; return 1; }
      if ! uv pip install --python "$py" --no-build-isolation ./hanabi-source; then
        warn "hanabi-source build failed. It needs cmake and a C++ compiler:"
        echo "  macOS:         xcode-select --install && brew install cmake" >&2
        echo "  Ubuntu/Debian: sudo apt-get install -y build-essential cmake" >&2
        return 1
      fi
      return 0
      ;;
    phyre)
      if [ "$OS" = "Linux" ] && [ "$ARCH" = "x86_64" ]; then
        :
      elif [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
        if [ -d "$env_dir/phyre-macos-arm64-py39" ]; then
          echo "phyre: the session uses the bundled $env_dir/phyre-macos-arm64-py39 automatically (PHYRE_PKG_DIR)"
        else
          warn "bundled phyre-macos-arm64-py39 is missing from $env_dir"
        fi
      else
        warn "PHYRE needs Linux x86_64 or macOS arm64 (this is $OS $ARCH)"
      fi
      ;;
    scigym)
                                                                   
      if ! command -v dot >/dev/null 2>&1; then
        warn "scigym needs the graphviz C library (dot not found). Install it and rerun:"
        echo "  Ubuntu/Debian: sudo apt-get install -y graphviz libgraphviz-dev" >&2
        echo "  macOS:         brew install graphviz" >&2
        return 1
      fi
      ;;
    balrog)
                                                
      if ! command -v cmake >/dev/null 2>&1; then
        warn "cmake not found; balrog-nle needs it to build. Install it:"
        echo "  Ubuntu/Debian: sudo apt-get install -y build-essential cmake libbz2-dev flex bison" >&2
        echo "  macOS:         brew install cmake" >&2
      fi
      ;;
    coup)
      uv pip install --python "$py" -r "$req" --editable "$ROOT/../vendor/TextArena" || { warn "Coup setup failed"; return 1; }
      return 0
      ;;
    buildarena-1.0)
      [ "$OS" = "Darwin" ] || warn "for the optional Linux transport, see tasks/07-buildarena/README.md; game and mod are installed separately"
      ;;
  esac

  uv pip install --python "$py" -r "$req" || { warn "install failed for $name"; return 1; }
  return 0
}

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is not on PATH. Install it with:" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

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

succeeded=()
failed=()
for name in "${ENVS[@]}"; do
  if setup_one "$name"; then
    succeeded+=("$name")
  else
    failed+=("$name")
    echo "FAILED: $name" >&2
  fi
  echo
done

echo "== Summary =="
if [ ${#succeeded[@]} -gt 0 ]; then
  echo "succeeded: ${succeeded[*]}"
fi
if [ ${#failed[@]} -gt 0 ]; then
  echo "failed: ${failed[*]}" >&2
  exit 1
fi
echo "all ${#ENVS[@]} env(s) ready under $ROOT/envs"
