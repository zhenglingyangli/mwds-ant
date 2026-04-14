#!/bin/bash
#
# Auto-submit SLURM jobs in batches.
# Usage: nohup bash auto_submit.sh > auto_submit.log 2>&1 &
#
# Submits jobs in batches of BATCH_SIZE, waits for running jobs
# to drop below BATCH_SIZE before submitting the next batch.

BATCH_SIZE=50
POLL_INTERVAL=300  # seconds between checks (5 min)
SUBMIT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SUBMIT_DIR" || exit 1

# Collect all jobslurm scripts, sorted for predictable order
ALL_SCRIPTS=($(ls jobslurm-dual-fast-T1-* jobslurm-fast-v19-T1-* \
                 jobslurm-dual-fast-T2-* jobslurm-fast-v19-T2-* \
                 2>/dev/null | sort))

TOTAL=${#ALL_SCRIPTS[@]}
echo "$(date): Found $TOTAL scripts to submit (batch size: $BATCH_SIZE)"
echo "Order: dual-fast-T1 -> fast-v19-T1 -> dual-fast-T2 -> fast-v19-T2"
echo "========================================================"

# Track which scripts are already done (submitted or running)
# Skip scripts whose result directories already exist
SUBMITTED=0
SKIPPED=0

for ((i=0; i<TOTAL; )); do
    # Wait until queue has room
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

    # Submit a batch
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

    # Wait a bit before checking again
    if [ $i -lt $TOTAL ]; then
        echo "$(date): Waiting $POLL_INTERVAL s before next check..."
        sleep $POLL_INTERVAL
    fi
done

echo "========================================================"
echo "$(date): All $SUBMITTED / $TOTAL scripts submitted!"
echo "Monitor with: squeue -u \$USER | wc -l"
