# Cloud Computer Standalone Auto Trade System

This folder contains the standalone version of the Auto Trade System designed specifically to run on a Cloud Computer (such as Manus Cloud Computer or any Ubuntu/Debian VPS).

## 💡 Why use a Cloud Computer?
By running this script on a Cloud Computer, you can:
1. **Save Credits:** Use your own API keys from more cost-effective AI providers or directly from OpenRouter, rather than consuming agent credits.
2. **24/5 Uptime:** The script runs continuously via systemd/cron without needing your local machine to be on.
3. **Full Control:** You have complete access to the logs, configuration, and execution environment.

## 🚀 Quick Setup Guide

### 1. Configure Environment Variables
Copy the example environment file and add your API keys:
```bash
cp .env.example .env
nano .env
```

Fill in your details:
- `METAAPI_ACCOUNT_ID`: Your MetaAPI Account ID
- `METAAPI_TOKEN`: Your MetaAPI Token
- `OPENROUTER_API_KEY`: Your OpenRouter API Key

### 2. Run the Setup Script
The setup script will install Python, required packages, and configure a cron job to run the script every 5 minutes.
```bash
sudo bash setup.sh
```

### 3. Monitor the System
You can check the trading logs using the provided log viewer script:
```bash
# View today's summary
python3 trade_log.py --summary

# View the last 100 log lines
python3 trade_log.py 100
```

## ⚙️ System Requirements
- Ubuntu/Debian Linux
- Python 3.8+
- Internet connection

## 📂 Files Included
- `auto_trade.py`: The main trading logic and AI integration script.
- `setup.sh`: Automated setup script for dependencies and cron scheduling.
- `trade_log.py`: Utility script to view and summarize trading logs.
- `.env.example`: Template for environment variables.
