#!/bin/bash
set -e
BATCH_SIZE=50
POLL_INTERVAL=300
SUBMIT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SUBMIT_DIR"
ALL_SCRIPTS=($(ls jobslurm-* 2>/dev/null | sort))
TOTAL=${#ALL_SCRIPTS[@]}
if [ "$TOTAL" -eq 0 ]; then echo "No jobslurm-* scripts found. Run generate_scripts.py first."; exit 1; fi
echo "$(date): Found $TOTAL scripts to submit (batch size: $BATCH_SIZE)"
SUBMITTED=0
for ((i=0; i<TOTAL; )); do
  while true; do
    RUNNING=$(squeue -u $USER -h | wc -l)
    if [ "$RUNNING" -lt "$BATCH_SIZE" ]; then SLOTS=$((BATCH_SIZE - RUNNING)); break; fi
    echo "$(date): Queue has $RUNNING jobs (limit $BATCH_SIZE), waiting..."; sleep $POLL_INTERVAL
  done
  COUNT=0
  while [ $i -lt $TOTAL ] && [ $COUNT -lt $SLOTS ]; do
    SCRIPT="${ALL_SCRIPTS[$i]}"; OUT=$(sbatch "$SCRIPT" 2>&1) || { echo "$(date): WARN: sbatch $SCRIPT failed: $OUT"; break; }
    SUBMITTED=$((SUBMITTED+1)); COUNT=$((COUNT+1)); i=$((i+1)); sleep 0.5
  done
  echo "$(date): Submitted $COUNT this batch ($SUBMITTED / $TOTAL total)"
  if [ $i -lt $TOTAL ]; then sleep $POLL_INTERVAL; fi
done
echo "$(date): All $SUBMITTED / $TOTAL scripts submitted"
