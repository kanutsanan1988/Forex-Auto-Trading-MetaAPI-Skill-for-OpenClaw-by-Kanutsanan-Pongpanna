#!/bin/bash
# =============================================================================
# Kanutsanan Pongpanna AI Auto Trading v3.0 - Setup Script
# =============================================================================
# ติดตั้งระบบเทรดอัตโนมัติ XAUUSD บน Cloud Computer
# - ติดตั้ง dependencies
# - สร้าง .env file (ถ้ายังไม่มี)
# - ตั้งค่า systemd timer สำหรับ auto trade
# =============================================================================

set -e

INSTALL_DIR="$HOME/auto_trade"
SERVICE_NAME="auto-trade"

echo "============================================"
echo "  Kanutsanan Pongpanna AI Auto Trading v3.0 - Setup"
echo "============================================"
echo ""

# 1. Install dependencies
echo "[1/5] Installing Python dependencies..."
pip3 install requests python-dotenv 2>/dev/null || pip install requests python-dotenv 2>/dev/null
echo "  Done."

# 2. Create directory
echo "[2/5] Setting up directory..."
mkdir -p "$INSTALL_DIR"

# Copy files if running from different directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    cp "$SCRIPT_DIR/auto_trade.py" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_DIR/trade_log.py" "$INSTALL_DIR/" 2>/dev/null || true
fi
echo "  Directory: $INSTALL_DIR"

# 3. Create .env if not exists
echo "[3/5] Checking .env file..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" << 'ENVEOF'
# Auto Trade System v3.0 - Environment Variables
# แก้ไขค่าด้านล่างนี้ให้ตรงกับบัญชีของคุณ

# MetaAPI Credentials
METAAPI_ACCOUNT_ID=YOUR_ACCOUNT_ID_HERE
METAAPI_TOKEN=YOUR_TOKEN_HERE

# OpenRouter API Key
OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY_HERE

# Trading Configuration
SYMBOL=XAUUSD.sml
MAX_MARGIN_PERCENT=50
MIN_LOT=0.001
MAX_LOT=0.1
MIN_STRENGTH=2
TRADE_INTERVAL_MINUTES=5

# OpenRouter Model (recommended: google/gemini-2.5-flash)
AI_MODEL=google/gemini-2.5-flash
ENVEOF
    echo "  Created .env template. Please edit: nano $INSTALL_DIR/.env"
else
    echo "  .env already exists. Skipping."
fi

# 4. Setup systemd timer
echo "[4/5] Setting up systemd timer..."

# Read interval from .env or default to 5
INTERVAL=$(grep TRADE_INTERVAL_MINUTES "$INSTALL_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d ' ' || echo "5")
INTERVAL=${INTERVAL:-5}
INTERVAL_SEC=$((INTERVAL * 60))

sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Kanutsanan Pongpanna AI Auto Trading v3.0
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/auto_trade.py
Environment=HOME=$HOME
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/${SERVICE_NAME}.timer > /dev/null << EOF
[Unit]
Description=Auto Trade Timer (every ${INTERVAL} minutes)

[Timer]
OnBootSec=60
OnUnitActiveSec=${INTERVAL_SEC}
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
echo "  Timer created (interval: ${INTERVAL} minutes)"

# 5. Summary
echo "[5/5] Setup complete!"
echo ""
echo "============================================"
echo "  Commands:"
echo "============================================"
echo ""
echo "  Manual check:"
echo "    cd $INSTALL_DIR && python3 auto_trade.py check"
echo ""
echo "  Approve trade:"
echo "    cd $INSTALL_DIR && python3 auto_trade.py approve"
echo ""
echo "  Start auto trade (systemd timer):"
echo "    sudo systemctl enable --now ${SERVICE_NAME}.timer"
echo ""
echo "  Stop auto trade:"
echo "    sudo systemctl stop ${SERVICE_NAME}.timer"
echo "    sudo systemctl disable ${SERVICE_NAME}.timer"
echo ""
echo "  View logs:"
echo "    python3 $INSTALL_DIR/trade_log.py"
echo "    python3 $INSTALL_DIR/trade_log.py log 100"
echo ""
echo "  View positions:"
echo "    python3 $INSTALL_DIR/trade_log.py positions"
echo ""
echo "============================================"
