# Cloud Computer Deployment Guide

This guide explains how to deploy the standalone version of the Agentic AI Auto Trading System on a Cloud Computer (such as Manus Cloud Computer, AWS EC2, DigitalOcean, or any Ubuntu/Debian VPS).

## 💡 Why use a Cloud Computer?
Running the system on a Cloud Computer offers several advantages:
1. **Save Credits:** You can use your own API keys from cost-effective AI providers (like OpenRouter) instead of consuming agent credits.
2. **24/5 Uptime:** The script runs continuously via systemd/cron without needing your local machine to be turned on.
3. **Full Control:** You have complete access to the logs, configuration, and execution environment.

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare the Cloud Computer
Ensure you have an Ubuntu or Debian-based Cloud Computer with root or sudo access.

1. SSH into your Cloud Computer:
   ```bash
   ssh username@your_server_ip
   ```
2. Update the system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

### Step 2: Upload the Files
You need to upload the contents of the `cloud-computer-standalone/` folder to your server. You can do this via SCP, SFTP, or by cloning your repository directly.

```bash
# Example: Cloning the repository
git clone https://github.com/kanutsanan1988/Forex-Auto-Trading-MetaAPI-Skill-for-OpenClaw-by-Kanutsanan-Pongpanna.git
cd Forex-Auto-Trading-MetaAPI-Skill-for-OpenClaw-by-Kanutsanan-Pongpanna/cloud-computer-standalone
```

### Step 3: Configure Environment Variables
The system requires your API keys to function. These are stored securely in a `.env` file.

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Edit the file using `nano`:
   ```bash
   nano .env
   ```
3. Fill in your details:
   ```bash
   export METAAPI_ACCOUNT_ID="your_account_id_here"
   export METAAPI_TOKEN="your_metaapi_token_here"
   export OPENROUTER_API_KEY="your_openrouter_api_key_here"
   ```
4. Save and exit (Press `Ctrl+O`, `Enter`, then `Ctrl+X`).

### Step 4: Run the Setup Script
The provided `setup.sh` script will automatically install Python, set up a virtual environment, install required packages, and configure systemd timers to run the script every 10 minutes.

```bash
sudo bash setup.sh
```

*Note: The setup script will copy the files to `/opt/auto-trade/` and set up the systemd services.*

### Step 5: Verify the Installation
After the setup script completes, you can verify that the systemd timer is active:

```bash
systemctl list-timers | grep auto-trade
```

You should see `auto-trade.timer` listed, indicating when it will run next.

---

## 🔍 Monitoring and Maintenance

### Manual Trade Check
Before letting the system trade automatically, you can run a manual check to ensure everything is configured correctly and see what the AI would do:

```bash
cd /opt/auto-trade
source venv/bin/activate
python3 trade_check.py
```

### Viewing Logs
The system logs all activities, including AI decisions, API responses, and errors. You can view the logs using the provided `trade_log.py` utility:

```bash
cd /opt/auto-trade
source venv/bin/activate

# View the last 100 log lines
python3 trade_log.py 100

# View a summary of today's trades
python3 trade_log.py --summary
```

Alternatively, you can view the raw log file directly:
```bash
tail -f /var/log/auto_trade.log
```

### Stopping the System
If you need to temporarily stop the automated trading:

```bash
sudo systemctl stop auto-trade.timer
sudo systemctl disable auto-trade.timer
```

To restart it:
```bash
sudo systemctl enable auto-trade.timer
sudo systemctl start auto-trade.timer
```
