#!/usr/bin/env bash
                   

                                                    
                                             
           
                              
            
                       
                    
                              
                                  
 
              
                                                                                                     
                                                                                                    
                                                                                                                 

MAX_WORKERS=1
LOG_DIR="logs"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

CONFIG_PATH="${1:-env/run_config.yaml}"
CONTINUE_FROM_DIR="${2:-results}"
if [[ $# -gt 0 ]]; then
  shift
fi
if [[ $# -gt 0 ]]; then
  shift
fi

RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
FAILURES=0

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
  local iter="$2"
  shift 2

  local model_token="${model//\//-}"
  local log_path="${LOG_DIR}/${model_token}_iter_${iter}_temp_0.0_memoff_refineon_${RUN_STAMP}.log"

  echo "[temp_refine_rubrics_suite] starting model=${model} iter=${iter} -> ${log_path}"

  python -m env.run \
    --config "$CONFIG_PATH" \
    --model "$model" \
    --ban_iterative_sample_num "$iter" \
    --model_temperature 0.0 \
    --no-memory \
    --refine_rubrics \
    --rubrics_refine_max_turns 6 \
    --rubrics_refine_continue_from "$CONTINUE_FROM_DIR" \
    "$@" \
    >"$log_path" 2>&1

  echo "[temp_refine_rubrics_suite] finished model=${model} iter=${iter}"
}

if (( MAX_WORKERS <= 1 )); then
  run_one "gpt-5-mini" "2" "$@"
  run_one "Qwen3-14B" "2" "$@"
  run_one "Llama-3.3-70B-Instruct" "2" "$@"
else
  wait_for_slot
  run_one "gpt-5-mini" "2" "$@" &
  wait_for_slot
  run_one "Qwen3-14B" "2" "$@" &
  wait_for_slot
  run_one "Llama-3.3-70B-Instruct" "2" "$@" &
fi

wait_for_all_jobs

if (( FAILURES > 0 )); then
  echo "[temp_refine_rubrics_suite] completed with ${FAILURES} failed run(s)" >&2
  exit 1
fi

echo "[temp_refine_rubrics_suite] all runs completed"
