#!/usr/bin/env bash
                                                                                                             
                                                                                                    
                                                                            
                                                                                                          
                                                                                                                            
                                                                                                            
                                                                                                               
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

coup() {
  local src="$ROOT/../vendor/TextArena/textarena" file
  for file in __init__.py envs/Coup/env.py envs/ColonelBlotto/env.py; do
    [ -f "$src/$file" ] || { echo "Missing bundled TextArena source: $file; re-extract the full release" >&2; return 1; }
  done
  echo "Using bundled TextArena: $src"
}

buildarena() {
  local src="$ROOT/tasks/07-buildarena/BuildArena-1.0" file
  for file in run_h0.py levels.yaml h0_client.py; do
    [ -f "$src/$file" ] || { echo "Missing bundled BuildArena source: $file; re-extract the full release" >&2; return 1; }
  done
  echo "Using bundled BuildArena: $src"
}

if [ "$#" -eq 0 ]; then set -- coup buildarena; fi
for name in "$@"; do
  case "$name" in
    coup) coup ;;
    buildarena) buildarena ;;
    *) echo "error: unknown source '$name' (known: coup buildarena)" >&2; exit 2 ;;
  esac
done
