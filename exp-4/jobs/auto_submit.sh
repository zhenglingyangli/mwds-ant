#!/bin/bash
#
# Auto-submit SLURM jobs in batches for exp-4 (Dual-Deep v6 vs baseline).
# Usage: nohup bash auto_submit.sh > auto_submit.log 2>&1 &

BATCH_SIZE=50
POLL_INTERVAL=300  # seconds between checks (5 min)
SUBMIT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SUBMIT_DIR" || exit 1

ALL_SCRIPTS=($(ls jobslurm-dual-deep-T1-* jobslurm-deep-v6-T1-* \
                 jobslurm-dual-deep-T2-* jobslurm-deep-v6-T2-* \
                 2>/dev/null | sort))

TOTAL=${#ALL_SCRIPTS[@]}
echo "$(date): Found $TOTAL scripts to submit (batch size: $BATCH_SIZE)"
echo "Order: dual-deep-T1 -> deep-v6-T1 -> dual-deep-T2 -> deep-v6-T2"
echo "========================================================"

SUBMITTED=0

for ((i=0; i<TOTAL; )); do
    while true; do
        RUNNING=$(squeue -u $USER -h | wc -l)
        if [ "$RUNNING" -lt "$BATCH_SIZE" ]; then
            SLOTS=$((BATCH_SIZE - RUNNING))
            echo "$(date): Queue has $RUNNING jobs, $SLOTS slots available"
            break
        fi
        echo "$(date): Queue has $RUNNING jobs, waiting..."
        sleep $POLL_INTERVAL
    done

    COUNT=0
    while [ $i -lt $TOTAL ] && [ $COUNT -lt $SLOTS ]; do
        SCRIPT="${ALL_SCRIPTS[$i]}"
        sbatch "$SCRIPT" 2>/dev/null
        if [ $? -eq 0 ]; then
            SUBMITTED=$((SUBMITTED + 1))
            COUNT=$((COUNT + 1))
        else
            echo "$(date): WARN: sbatch $SCRIPT failed, will retry later"
            break
        fi
        sleep 0.5
        i=$((i + 1))
    done
    echo "$(date): Submitted $COUNT this batch ($SUBMITTED / $TOTAL total)"

    if [ $i -lt $TOTAL ]; then
        echo "$(date): Waiting $POLL_INTERVAL s before next check..."
        sleep $POLL_INTERVAL
    fi
done

echo "========================================================"
echo "$(date): All $SUBMITTED / $TOTAL scripts submitted!"
echo "Monitor with: squeue -u \$USER | wc -l"
