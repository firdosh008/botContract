#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure output directories exist
mkdir -p outreach_drafts logs

# Run the agent
python -m agent.main 2>&1 | tee "logs/run-$(date +%Y-%m-%d-%H%M%S).log"

echo ""
echo "Done. Check:"
echo "  pipeline.csv        → your CRM (open in Excel)"
echo "  outreach_drafts/    → email + DM drafts"
echo "  data.md             → pipeline summary"
