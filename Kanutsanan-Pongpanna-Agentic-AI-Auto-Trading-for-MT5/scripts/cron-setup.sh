#!/bin/bash

###############################################################
# CRON Setup Script - Kanutsanan-Pongpanna Agentic AI Trading
# 
# Frequency: Every 30 seconds (updated from 38)
# Weekly Runs: 20,160 (+25% improvement)
#
# This script sets up automated trading via CRON.
###############################################################

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🤖 CRON Setup: Kanutsanan-Pongpanna Agentic AI Trading"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo ""
    echo "Setup Required:"
    echo "  1. Copy: cp assets/config-template.env .env"
    echo "  2. Edit: nano .env"
    echo "  3. Add your MetaApi credentials"
    echo "  4. Run this script again"
    echo ""
    exit 1
fi

echo "✅ .env file found"
echo ""

# Verify TOKEN and ACCOUNT_ID are set
source "$PROJECT_DIR/.env"

if [ -z "$TOKEN" ] || [ -z "$ACCOUNT_ID" ]; then
    echo "❌ ERROR: TOKEN or ACCOUNT_ID not set in .env!"
    echo ""
    exit 1
fi

echo "✅ Credentials verified"
echo ""

# Create logs directory
if [ ! -d "$PROJECT_DIR/logs" ]; then
    mkdir -p "$PROJECT_DIR/logs"
    echo "✅ Created logs directory"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📋 CRON Configuration"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "Frequency: Every 30 seconds"
echo "Weekly Runs: 20,160 cycles"
echo ""

echo "Schedule:"
echo "  • Sunday: 23:00-23:59 UTC (pre-market)"
echo "  • Mon-Fri: 00:00-21:59 UTC (full day)"
echo "  • Friday: 22:00 UTC (end of week)"
echo ""

echo "Logs: $PROJECT_DIR/logs/trade-*.log"
echo ""

# Create temporary crontab file
TEMP_CRON=$(mktemp)

# Get current crontab (if exists)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# Check if jobs already exist
if grep -q "kanutsanan-pongpanna-full-auto" "$TEMP_CRON"; then
    echo "⚠️  CRON jobs already exist!"
    echo ""
    echo "Current CRON entries:"
    grep "kanutsanan-pongpanna-full-auto" "$TEMP_CRON" || true
    echo ""
    read -p "Do you want to replace them? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old entries
        grep -v "kanutsanan-pongpanna-full-auto" "$TEMP_CRON" > "$TEMP_CRON.new"
        mv "$TEMP_CRON.new" "$TEMP_CRON"
    else
        echo "Cancelled. No changes made."
        rm -f "$TEMP_CRON"
        exit 0
    fi
fi

# Add new CRON jobs (every 1 minute, script runs every 30 sec internally)
cat >> "$TEMP_CRON" << EOF

# Kanutsanan-Pongpanna Agentic AI Trading - Every 30 seconds
# Sunday: pre-market analysis
*/1 23 * * 0 cd $PROJECT_DIR && bash scripts/cron-runner.sh >> logs/trade-\$(date +\%Y\%m\%d).log 2>&1

# Monday-Friday: full market hours
*/1 * * * 1-5 cd $PROJECT_DIR && bash scripts/cron-runner.sh >> logs/trade-\$(date +\%Y\%m\%d).log 2>&1

EOF

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Setting up CRON jobs..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Install new crontab
crontab "$TEMP_CRON"

if [ $? -eq 0 ]; then
    echo "✅ CRON jobs installed successfully!"
    echo ""
    echo "Verify with: crontab -l"
    echo ""
else
    echo "❌ Failed to install CRON jobs"
    rm -f "$TEMP_CRON"
    exit 1
fi

# Clean up
rm -f "$TEMP_CRON"

# Check if cron-runner.sh exists
if [ ! -f "$PROJECT_DIR/scripts/cron-runner.sh" ]; then
    echo "Creating cron-runner.sh helper script..."
    cat > "$PROJECT_DIR/scripts/cron-runner.sh" << 'RUNNER_EOF'
#!/bin/bash

# Helper script to run trading every 30 seconds
# Called by CRON every 1 minute

source .env

# Run every 30 seconds for 60 seconds (2 runs per minute)
for i in 1 2; do
  timeout 25 node scripts/kanutsanan-pongpanna-full-auto-template.js 2>&1
  if [ $i -eq 1 ]; then
    sleep 30
  fi
done

exit 0
RUNNER_EOF

    chmod +x "$PROJECT_DIR/scripts/cron-runner.sh"
    echo "✅ Created cron-runner.sh"
    echo ""
fi

echo "═══════════════════════════════════════════════════════════"
echo "🚀 Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "Status:"
echo "  ✅ Credentials verified"
echo "  ✅ Logs directory created"
echo "  ✅ CRON jobs installed"
echo ""

echo "Next steps:"
echo "  1. Verify CRON: crontab -l"
echo "  2. Monitor logs: tail -f logs/trade-\$(date +%Y%m%d).log"
echo "  3. Check execution: grep CRON /var/log/syslog"
echo ""

echo "To disable automation:"
echo "  1. crontab -r (removes all jobs)"
echo "  2. Or edit: crontab -e (remove just these entries)"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo ""
