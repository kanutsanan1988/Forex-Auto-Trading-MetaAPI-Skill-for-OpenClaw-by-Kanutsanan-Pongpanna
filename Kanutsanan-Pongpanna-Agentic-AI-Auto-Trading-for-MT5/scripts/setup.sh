#!/bin/bash

# =============================================================================
# Auto Trade System Setup Script
# =============================================================================

echo "======================================================="
echo "  Auto Trade System Setup (OpenRouter AI + MetaAPI)    "
echo "======================================================="

# 1. Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo or as root."
  echo "Example: sudo ./setup.sh"
  exit 1
fi

# 2. Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Installing from directory: $SCRIPT_DIR"

# 3. Install required system packages
echo "Installing required system packages..."
apt-get update
apt-get install -y python3 python3-pip python3-venv cron

# 4. Setup Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

# 5. Install Python dependencies
echo "Installing Python dependencies..."
pip install requests python-dotenv urllib3

# 6. Create log file and set permissions
echo "Setting up log file..."
touch /var/log/auto_trade.log
chmod 666 /var/log/auto_trade.log

# 7. Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Creating .env file from .env.example..."
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        echo "WARNING: Please edit $SCRIPT_DIR/.env with your actual API keys before running!"
    else
        echo "ERROR: .env.example not found. Please create .env manually."
    fi
fi

# 8. Setup Cron Job (Run every 5 minutes)
echo "Setting up cron job..."
CRON_CMD="*/5 * * * * cd $SCRIPT_DIR && $SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/auto_trade.py >> /var/log/auto_trade_cron.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -v "auto_trade.py") | crontab -
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "Cron job installed. The script will run every 5 minutes."
echo "You can check the cron logs at: /var/log/auto_trade_cron.log"
echo "You can check the application logs at: /var/log/auto_trade.log"

# 9. Make scripts executable
chmod +x "$SCRIPT_DIR/auto_trade.py"
chmod +x "$SCRIPT_DIR/trade_log.py"

echo "======================================================="
echo "  Setup Complete!                                      "
echo "======================================================="
echo "Next steps:"
echo "1. Edit $SCRIPT_DIR/.env and add your API keys"
echo "2. Test the script manually: cd $SCRIPT_DIR && ./venv/bin/python auto_trade.py"
echo "3. View logs: python3 trade_log.py"
