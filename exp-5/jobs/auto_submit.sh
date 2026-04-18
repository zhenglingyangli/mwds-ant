#!/bin/bash
#
# Auto-submit SLURM jobs in batches for exp-5 (Dual-Fast v19 vs baseline, paper config).
# Usage: nohup bash auto_submit.sh > auto_submit.log 2>&1 &
#
# Cluster hard limit (AssocGrpSubmitJobsLimit) is 200 concurrent jobs for
# account acs4vb4pqv. We keep BATCH_SIZE=180 so there's room for adhoc jobs.
# If submitter hits AssocGrpSubmitJobsLimit, it aborts that batch and retries
# on the next cycle.

BATCH_SIZE=180
POLL_INTERVAL=300  # seconds between checks (5 min)
SUBMIT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SUBMIT_DIR" || exit 1

# Collect all jobslurm scripts in a stable order (solver -> dataset -> seed -> chunk)
# Stage-1 (patch) scripts jobslurm-patch-* are NOT included here; submit them via submit_patch.sh.
ALL_SCRIPTS=($(ls jobslurm-dual-fast-T1-* jobslurm-fast-v19-T1-* \
                 jobslurm-dual-fast-T2-* jobslurm-fast-v19-T2-* \
                 2>/dev/null | sort))

TOTAL=${#ALL_SCRIPTS[@]}
if [ "$TOTAL" -eq 0 ]; then
    echo "No jobslurm-* scripts found. Run generate_scripts.py first."
    exit 1
fi

echo "$(date): Found $TOTAL scripts to submit (batch size: $BATCH_SIZE)"
echo "Order: dual-fast-T1 -> fast-v19-T1 -> dual-fast-T2 -> fast-v19-T2"
echo "========================================================"

SUBMITTED=0

for ((i=0; i<TOTAL; )); do
    # Wait until queue has room
    while true; do
        RUNNING=$(squeue -u $USER -h | wc -l)
        if [ "$RUNNING" -lt "$BATCH_SIZE" ]; then
            SLOTS=$((BATCH_SIZE - RUNNING))
            echo "$(date): Queue has $RUNNING jobs, $SLOTS slots available"
            break
        fi
        echo "$(date): Queue has $RUNNING jobs (limit $BATCH_SIZE), waiting..."
        sleep $POLL_INTERVAL
    done

    COUNT=0
    while [ $i -lt $TOTAL ] && [ $COUNT -lt $SLOTS ]; do
        SCRIPT="${ALL_SCRIPTS[$i]}"
        OUT=$(sbatch "$SCRIPT" 2>&1)
        if [ $? -eq 0 ]; then
            SUBMITTED=$((SUBMITTED + 1))
            COUNT=$((COUNT + 1))
        else
            # Common case: AssocGrpSubmitJobsLimit hit -> back off and retry
            echo "$(date): WARN: sbatch $SCRIPT failed: $OUT"
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
