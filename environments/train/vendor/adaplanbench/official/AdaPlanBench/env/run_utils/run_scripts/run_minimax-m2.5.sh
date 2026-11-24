#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="MiniMax-M2.5"
MODEL_TEMPERATURES=("0.0")
ITERATIONS=(2 3)
MEMORY_MODE="config"                      
LOG_DIR="logs"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$LOG_DIR"

CONFIG_PATH="${1:-env/run_config.yaml}"
if [[ $# -gt 0 ]]; then
  shift
fi

MEMORY_ARGS=()
case "$MEMORY_MODE" in
  config)
    MEMORY_TAG="memcfg"
    ;;
  on)
    MEMORY_ARGS+=(--memory)
    MEMORY_TAG="memon"
    ;;
  off)
    MEMORY_ARGS+=(--no-memory)
    MEMORY_TAG="memoff"
    ;;
  *)
    echo "[run_${MODEL_NAME//\//-}] invalid MEMORY_MODE=$MEMORY_MODE (expected: config|on|off)" >&2
    exit 1
    ;;
esac

MODEL_TOKEN="${MODEL_NAME//\//-}"
RUN_LABEL="run_${MODEL_TOKEN}"
RUN_STAMP="$(date +%Y%m%d_%H%M%S)"
TOTAL_ITERS="${#ITERATIONS[@]}"
TOTAL_TEMPS="${#MODEL_TEMPERATURES[@]}"
TOTAL_COMBOS=$((TOTAL_ITERS * TOTAL_TEMPS))
COMBO_INDEX=0

for IDX in "${!ITERATIONS[@]}"; do
  ITER="${ITERATIONS[$IDX]}"
  for TEMP in "${MODEL_TEMPERATURES[@]}"; do
    COMBO_INDEX=$((COMBO_INDEX + 1))
    LOG_PATH="${LOG_DIR}/${MODEL_TOKEN}_iter_${ITER}_temp_${TEMP}_${MEMORY_TAG}_${RUN_STAMP}.log"
    echo "[${RUN_LABEL}] (${COMBO_INDEX}/${TOTAL_COMBOS}) starting ban_iterative_sample_num=${ITER} model_temperature=${TEMP} memory=${MEMORY_MODE} -> ${LOG_PATH}"
    python -m env.run \
      --config "$CONFIG_PATH" \
      --model "$MODEL_NAME" \
      --model_temperature "$TEMP" \
      --ban_iterative_sample_num "$ITER" \
      "${MEMORY_ARGS[@]}" \
      "$@" \
      >"$LOG_PATH" 2>&1
    echo "[${RUN_LABEL}] (${COMBO_INDEX}/${TOTAL_COMBOS}) finished ban_iterative_sample_num=${ITER} model_temperature=${TEMP} memory=${MEMORY_MODE}"
  done
done
