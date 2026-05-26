#!/bin/bash
set -euo pipefail

BATCH_SIZE=${BATCH_SIZE:-20}
SLEEP_SEC=${SLEEP_SEC:-120}

submitted_file=".submitted_jobs"
touch "$submitted_file"

while true; do
  running=$(squeue -u "$USER" -h | wc -l)
  available=$((BATCH_SIZE - running))
  if [ "$available" -le 0 ]; then
    echo "$(date) queue=$running >= BATCH_SIZE=$BATCH_SIZE; sleeping ${SLEEP_SEC}s"
    sleep "$SLEEP_SEC"
    continue
  fi

  submitted=0
  for script in jobslurm-*; do
    [ -f "$script" ] || continue
    if grep -qx "$script" "$submitted_file"; then
      continue
    fi
    sbatch "$script"
    echo "$script" >> "$submitted_file"
    submitted=$((submitted + 1))
    sleep 1
    if [ "$submitted" -ge "$available" ]; then
      break
    fi
  done

  total_left=$(comm -23 <(ls jobslurm-* 2>/dev/null | sort) <(sort "$submitted_file") | wc -l)
  echo "$(date) submitted_now=$submitted remaining=$total_left queue_before=$running"
  if [ "$submitted" -eq 0 ] && [ "$total_left" -eq 0 ]; then
    echo "All generated Stage-1 jobs have been submitted."
    break
  fi
  sleep "$SLEEP_SEC"
done
