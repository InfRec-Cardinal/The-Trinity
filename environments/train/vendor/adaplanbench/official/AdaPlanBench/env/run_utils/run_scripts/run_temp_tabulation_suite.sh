#!/usr/bin/env bash
                   

                                                   
 
                  
                                                       
                                        
                                                                      
                                                                         
 
                                                                     
                                   
 
        
                                                              
                                                                  
                                                                          
                              

MAX_WORKERS=2
LOG_DIR="logs"

                               
                                                                                   
MODEL_SPECS=(
  "gemini-3-flash:0.7,1.0"
)

                                             
EXTRA_RUN_ARGS=(
  --ban_iterative_sample_num 2
  --ban_verbal_sample_num 3
  --no-memory
  --no-refine_rubrics
)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

CONFIG_PATH="${1:-env/run_config.yaml}"
if [[ $# -gt 0 ]]; then
  shift
fi
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
FAILURES=0

declare -a RUN_ARGS=("${EXTRA_RUN_ARGS[@]}" "$@")
declare -A SEEN_MODELS=()

is_numeric() {
  [[ "$1" =~ ^-?[0-9]+([.][0-9]+)?$ ]]
}

sanitize_token() {
  local value="$1"
  value="${value//\//-}"
  value="${value// /_}"
  printf '%s' "$value"
}

resolve_output_paths() {
  local model="$1"
  local temperature="$2"
  shift 2

  python - "$CONFIG_PATH" "$model" "$temperature" "$@" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from env.run import build_arg_parser, resolve_args
from env.run_utils.dataworker import DataWorker

config_path = sys.argv[1]
model = sys.argv[2]
temperature = sys.argv[3]
extra_args = sys.argv[4:]

parser = build_arg_parser()
parsed_args = parser.parse_args([
    "--config", config_path,
    "--model", model,
    "--model_temperature", temperature,
    *extra_args,
])
args = resolve_args(parsed_args)
worker = DataWorker(args)
print(worker.build_result_path())
PY
}

should_skip_existing() {
  local model="$1"
  local temperature="$2"
  shift 2

  local result_path
  mapfile -t _resolved_paths < <(resolve_output_paths "$model" "$temperature" "$@")
  if (( ${#_resolved_paths[@]} >= 1 )); then
    result_path="${_resolved_paths[0]}"
  else
    result_path=""
  fi

  if [[ -n "$result_path" && -d "$result_path" ]]; then
    echo "[temp_tabulation_suite] skipping model=${model} temperature=${temperature}; result folder exists at ${result_path}"
    return 0
  fi
  return 1
}

wait_for_slot() {
  if (( MAX_WORKERS <= 1 )); then
    return 0
  fi
  while true; do
    local active
    active=$(jobs -pr | wc -l | tr -d ' ')
    if (( active < MAX_WORKERS )); then
      return 0
    fi
    if ! wait -n; then
      FAILURES=$((FAILURES + 1))
    fi
  done
}

wait_for_all_jobs() {
  while true; do
    local active
    active=$(jobs -pr | wc -l | tr -d ' ')
    if (( active == 0 )); then
      return 0
    fi
    if ! wait -n; then
      FAILURES=$((FAILURES + 1))
    fi
  done
}

run_one() {
  local model="$1"
  local temperature="$2"
  shift 2

  if should_skip_existing "$model" "$temperature" "$@"; then
    return 0
  fi

  local model_token temp_token log_path
  model_token="$(sanitize_token "$model")"
  temp_token="$(sanitize_token "$temperature")"
  log_path="${LOG_DIR}/${model_token}_temp_${temp_token}_${RUN_STAMP}.log"

  echo "[temp_tabulation_suite] starting model=${model} temperature=${temperature} -> ${log_path}"

  python -m env.run \
    --config "$CONFIG_PATH" \
    --model "$model" \
    --model_temperature "$temperature" \
    "$@" \
    >"$log_path" 2>&1

  echo "[temp_tabulation_suite] finished model=${model} temperature=${temperature}"
}

run_model_pipeline() {
  local model="$1"
  local temps_csv="$2"
  shift 2

  local -a temps=()
  IFS=',' read -r -a temps <<< "$temps_csv"

  local temp
  for temp in "${temps[@]}"; do
    if [[ -z "$temp" ]]; then
      continue
    fi
    run_one "$model" "$temp" "$@"
  done
}

if ! [[ "$MAX_WORKERS" =~ ^[1-9][0-9]*$ ]]; then
  echo "[temp_tabulation_suite] MAX_WORKERS must be a positive integer" >&2
  exit 1
fi

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "[temp_tabulation_suite] config not found: $CONFIG_PATH" >&2
  exit 1
fi

if (( ${#MODEL_SPECS[@]} == 0 )); then
  echo "[temp_tabulation_suite] MODEL_SPECS is empty" >&2
  exit 1
fi

for arg in "${RUN_ARGS[@]}"; do
  case "$arg" in
    --model|--model_temperature)
      echo "[temp_tabulation_suite] please do not pass ${arg} after --; the suite controls it." >&2
      exit 1
      ;;
  esac
done

for spec in "${MODEL_SPECS[@]}"; do
  if [[ "$spec" != *:* ]]; then
    echo "[temp_tabulation_suite] invalid spec (expected model:temp1,temp2,...): $spec" >&2
    exit 1
  fi

  model="${spec%%:*}"
  temps_csv="${spec#*:}"

  if [[ -z "$model" || -z "$temps_csv" ]]; then
    echo "[temp_tabulation_suite] invalid spec (empty model or temperature list): $spec" >&2
    exit 1
  fi

  if [[ -n "${SEEN_MODELS[$model]:-}" ]]; then
    echo "[temp_tabulation_suite] duplicate model spec detected: $model" >&2
    echo "[temp_tabulation_suite] put all temperatures for one model into a single spec." >&2
    exit 1
  fi
  SEEN_MODELS["$model"]=1

  IFS=',' read -r -a temps <<< "$temps_csv"
  if (( ${#temps[@]} == 0 )); then
    echo "[temp_tabulation_suite] empty temperature list for model: $model" >&2
    exit 1
  fi
  for temp in "${temps[@]}"; do
    if [[ -z "$temp" ]] || ! is_numeric "$temp"; then
      echo "[temp_tabulation_suite] invalid temperature '${temp}' in spec: $spec" >&2
      exit 1
    fi
  done
done

TOTAL_MODELS="${#MODEL_SPECS[@]}"
if (( MAX_WORKERS > TOTAL_MODELS )); then
  echo "[temp_tabulation_suite] capping max-workers from ${MAX_WORKERS} to ${TOTAL_MODELS} (number of model pipelines)"
  MAX_WORKERS=$TOTAL_MODELS
fi

echo "[temp_tabulation_suite] config=${CONFIG_PATH}"
echo "[temp_tabulation_suite] max_workers=${MAX_WORKERS}"
echo "[temp_tabulation_suite] run_stamp=${RUN_STAMP}"

for spec in "${MODEL_SPECS[@]}"; do
  model="${spec%%:*}"
  temps_csv="${spec#*:}"
  wait_for_slot
  run_model_pipeline "$model" "$temps_csv" "${RUN_ARGS[@]}" &
done

wait_for_all_jobs

if (( FAILURES > 0 )); then
  echo "[temp_tabulation_suite] completed with ${FAILURES} failed pipeline(s)" >&2
  exit 1
fi

echo "[temp_tabulation_suite] all runs completed"
