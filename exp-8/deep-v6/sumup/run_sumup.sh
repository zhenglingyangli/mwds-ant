#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p analysis
python3 ./sumup_lb.py ../jobs/result --output_dir ./analysis
