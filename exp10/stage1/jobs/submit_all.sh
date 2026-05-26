#!/bin/bash
set -euo pipefail
sbatch jobslurm-v005
sleep 1
sbatch jobslurm-v006
sleep 1
sbatch jobslurm-v007
sleep 1
sbatch jobslurm-v009
sleep 1
echo 'submitted 4 stage1 jobs'
