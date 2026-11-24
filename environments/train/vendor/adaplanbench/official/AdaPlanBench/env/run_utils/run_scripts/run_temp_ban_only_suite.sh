#!/usr/bin/env bash
                   

                                              
                                             
           
                              
              
                        
                    
            
                       
                    
 
                                                   
                                                                                        
                                                                                        
                  
                  
                 
                      
                         

                                        
                                                                     
TOOLS_MODELS=(
  "gpt-5-mini"
  "DeepSeek-V3.2"
)

PREFS_MODELS=(
  "DeepSeek-V3.2"
  "gpt-5-mini"
)

LOG_DIR="logs"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

CONFIG_PATH="${1:-env/run_config.yaml}"
if [[ $# -gt 0 ]]; then
  shift
fi

RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
FAILURES=0

run_one() {
  local model="$1"
  local ban_scope="$2"
  shift 2

  local response_dimension ordered_elicit
  if [[ "$ban_scope" == "tools" ]]; then
    response_dimension="tools"
    ordered_elicit="tools,rubrics"
  elif [[ "$ban_scope" == "prefs" ]]; then
    response_dimension="prefs"
    ordered_elicit="prefs,rubrics"
  else
    echo "[temp_ban_only_suite] unsupported ban scope: ${ban_scope}" >&2
    return 1
  fi

  local model_token="${model//\//-}"
  local log_path="${LOG_DIR}/${model_token}_iter_2_temp_0.0_memoff_refineoff_banonly_${ban_scope}_${RUN_STAMP}.log"

  echo "[temp_ban_only_suite] starting model=${model} ban_only=${ban_scope} -> ${log_path}"

  python -m env.run \
    --config "$CONFIG_PATH" \
    --model "$model" \
    --ban_iterative_sample_num 2 \
    --model_temperature 0.0 \
    --ban_only "$ban_scope" \
    --response_dimension "$response_dimension" \
    --ordered_elicit "$ordered_elicit" \
    --no-memory \
    --no-refine_rubrics \
    "$@" \
    >"$log_path" 2>&1

  echo "[temp_ban_only_suite] finished model=${model} ban_only=${ban_scope}"
}

run_scope_pipeline() {
  local ban_scope="$1"
  shift
  local -a models=()
  if [[ "$ban_scope" == "tools" ]]; then
    models=("${TOOLS_MODELS[@]}")
  else
    models=("${PREFS_MODELS[@]}")
  fi
  local model
  for model in "${models[@]}"; do
    run_one "$model" "$ban_scope" "$@"
  done
}

run_scope_pipeline "tools" "$@" &
tools_pid=$!
run_scope_pipeline "prefs" "$@" &
prefs_pid=$!

if ! wait "$tools_pid"; then
  FAILURES=$((FAILURES + 1))
fi
if ! wait "$prefs_pid"; then
  FAILURES=$((FAILURES + 1))
fi

if (( FAILURES > 0 )); then
  echo "[temp_ban_only_suite] completed with ${FAILURES} failed run(s)" >&2
  exit 1
fi

echo "[temp_ban_only_suite] all runs completed"
