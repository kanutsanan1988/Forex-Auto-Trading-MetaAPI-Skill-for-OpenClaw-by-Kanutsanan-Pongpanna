#!/bin/bash
# =============================================================================
# Kanutsanan Pongpanna AI Auto Trading v5.0 - Setup Script
# =============================================================================
# ติดตั้งระบบเทรดอัตโนมัติ + systemd timer
# Usage: sudo bash setup.sh
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRADE_SCRIPT="$SCRIPT_DIR/auto_trade.py"
USER=$(whoami)

echo "============================================="
echo "  Installing Auto Trade System v5.0"
echo "============================================="
echo "  Script: $TRADE_SCRIPT"
echo "  User: $USER"
echo ""

# Install dependencies
echo "[1/4] Installing Python packages..."
pip3 install requests urllib3 2>/dev/null || pip install requests urllib3 2>/dev/null
echo "  Done."

# Create systemd service
echo "[2/4] Creating systemd service..."
cat > /etc/systemd/system/auto-trade.service << EOF
[Unit]
Description=Kanutsanan Pongpanna AI Auto Trading v5.0
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$SCRIPT_DIR
Environment="OPENROUTER_API_KEY=${OPENROUTER_API_KEY}"
Environment="METAAPI_TOKEN=${METAAPI_TOKEN}"
Environment="METAAPI_ACCOUNT_ID=${METAAPI_ACCOUNT_ID}"
Environment="AI_MODEL=${AI_MODEL:-google/gemini-3.5-flash}"
ExecStart=/usr/bin/python3 $TRADE_SCRIPT
TimeoutStartSec=180
StandardOutput=append:$SCRIPT_DIR/auto_trade.log
StandardError=append:$SCRIPT_DIR/auto_trade.log

[Install]
WantedBy=multi-user.target
EOF
echo "  Done."

# Create systemd timer (every 5 minutes)
echo "[3/4] Creating systemd timer..."
cat > /etc/systemd/system/auto-trade.timer << EOF
[Unit]
Description=Auto Trade Timer (every 5 min)

[Timer]
OnBootSec=60
OnUnitActiveSec=300
AccuracySec=10
Persistent=true

[Install]
WantedBy=timers.target
EOF
echo "  Done."

# Reload systemd
echo "[4/4] Reloading systemd..."
systemctl daemon-reload
echo "  Done."

echo ""
echo "============================================="
echo "  Installation Complete!"
echo "============================================="
echo ""
echo "  Commands:"
echo "    Start:   sudo systemctl start auto-trade.timer"
echo "    Stop:    sudo systemctl stop auto-trade.timer"
echo "    Enable:  sudo systemctl enable auto-trade.timer"
echo "    Status:  sudo systemctl status auto-trade.timer"
echo "    Logs:    journalctl -u auto-trade.service -f"
echo ""
echo "  Manual:"
echo "    Check:   python3 $TRADE_SCRIPT check"
echo "    Approve: python3 $TRADE_SCRIPT approve"
echo "    Auto:    python3 $TRADE_SCRIPT auto 5"
echo ""
