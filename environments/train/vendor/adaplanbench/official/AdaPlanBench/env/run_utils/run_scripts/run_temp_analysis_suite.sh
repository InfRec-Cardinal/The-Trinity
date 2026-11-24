#!/usr/bin/env bash
                   

                                                            
 
         
                                 
                                       
                                                                  
 
                      
                                                                                
                                                                                    
                                                                          

                           
                               
                           

CONFIG_PATH="${1:-env/run_config.yaml}"
LOG_DIR="logs"

                                             
ITERATION=1

                                                                          
MODELS=(
  "Qwen3-14B"
  "Llama-3.3-70B-Instruct"
  "gemini-3-flash"
  "gpt-5-mini"
)

MODEL_TEMPERATURES=(
  "0.0"
  "0.0"
  "0.0"
  "1.0"
)

                                        
RUN_MEMORY_TRACKING=1
RUN_RUBRICS_REFINE=1
RUN_BAN_ONLY=1

                                                                                 
                                                                                 
REFINE_MAX_TURNS=6
CONTINUE_FROM_DIR="results"

                                                                    
BASE_RESPONSE_DIMENSION="tools,prefs"
BASE_ORDERED_ELICIT="tools,prefs,rubrics"

                             
TOOLS_RESPONSE_DIMENSION="tools"
TOOLS_ORDERED_ELICIT="tools,rubrics"
PREFS_RESPONSE_DIMENSION="prefs"
PREFS_ORDERED_ELICIT="prefs,rubrics"

                           
                 
                           

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

if [[ $# -gt 0 ]]; then
  shift
fi

RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
FAILURES=0

if [[ "${#MODELS[@]}" -ne "${#MODEL_TEMPERATURES[@]}" ]]; then
  echo "[temp_analysis_suite] MODELS and MODEL_TEMPERATURES must have the same length" >&2
  exit 1
fi

model_token() {
  local model="$1"
  echo "${model//\//-}"
}

run_job() {
  local model="$1"
  local temp="$2"
  local experiment="$3"
  local log_tag="$4"
  shift 4

  local token
  token="$(model_token "$model")"
  local log_path="${LOG_DIR}/${token}_iter_${ITERATION}_temp_${temp}_${log_tag}_${RUN_STAMP}.log"

  echo "[temp_analysis_suite] starting model=${model} experiment=${experiment} -> ${log_path}"

  python -m env.run \
    --config "$CONFIG_PATH" \
    --model "$model" \
    --model_temperature "$temp" \
    --ban_iterative_sample_num "$ITERATION" \
    "$@" \
    >"$log_path" 2>&1

  echo "[temp_analysis_suite] finished model=${model} experiment=${experiment}"
}

run_memory_tracking() {
  local model="$1"
  local temp="$2"
  run_job "$model" "$temp" "memory_tracking" "memon_refineoff_both" \
    --memory \
    --no-refine_rubrics \
    --ban_only null \
    --response_dimension "$BASE_RESPONSE_DIMENSION" \
    --ordered_elicit "$BASE_ORDERED_ELICIT"
}

run_rubrics_refine() {
  local model="$1"
  local temp="$2"
  run_job "$model" "$temp" "rubrics_refine" "memoff_refineon_mturns${REFINE_MAX_TURNS}" \
    --no-memory \
    --refine_rubrics \
    --rubrics_refine_max_turns "$REFINE_MAX_TURNS" \
    --rubrics_refine_continue_from "$CONTINUE_FROM_DIR" \
    --ban_only null \
    --response_dimension "$BASE_RESPONSE_DIMENSION" \
    --ordered_elicit "$BASE_ORDERED_ELICIT"
}

run_ban_only() {
  local model="$1"
  local temp="$2"
  local ban_scope="$3"

  if [[ "$ban_scope" == "tools" ]]; then
    run_job "$model" "$temp" "ban_only_tools" "memoff_refineoff_banonly_tools" \
      --no-memory \
      --no-refine_rubrics \
      --ban_only tools \
      --response_dimension "$TOOLS_RESPONSE_DIMENSION" \
      --ordered_elicit "$TOOLS_ORDERED_ELICIT"
  elif [[ "$ban_scope" == "prefs" ]]; then
    run_job "$model" "$temp" "ban_only_prefs" "memoff_refineoff_banonly_prefs" \
      --no-memory \
      --no-refine_rubrics \
      --ban_only prefs \
      --response_dimension "$PREFS_RESPONSE_DIMENSION" \
      --ordered_elicit "$PREFS_ORDERED_ELICIT"
  else
    echo "[temp_analysis_suite] unsupported ban scope: ${ban_scope}" >&2
    return 1
  fi
}

run_model_worker() {
  local model="$1"
  local temp="$2"

  echo "[temp_analysis_suite] worker start model=${model} temp=${temp}"

  if [[ "$RUN_MEMORY_TRACKING" == "1" ]]; then
    run_memory_tracking "$model" "$temp" || return 1
  fi

  if [[ "$RUN_RUBRICS_REFINE" == "1" ]]; then
    run_rubrics_refine "$model" "$temp" || return 1
  fi

  if [[ "$RUN_BAN_ONLY" == "1" ]]; then
    run_ban_only "$model" "$temp" "tools" || return 1
    run_ban_only "$model" "$temp" "prefs" || return 1
  fi

  echo "[temp_analysis_suite] worker done model=${model}"
}

pids=()
for idx in "${!MODELS[@]}"; do
  run_model_worker "${MODELS[$idx]}" "${MODEL_TEMPERATURES[$idx]}" &
  pids+=("$!")
done

for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    FAILURES=$((FAILURES + 1))
  fi
done

if (( FAILURES > 0 )); then
  echo "[temp_analysis_suite] completed with ${FAILURES} failed worker(s)" >&2
  exit 1
fi

echo "[temp_analysis_suite] all runs completed"
