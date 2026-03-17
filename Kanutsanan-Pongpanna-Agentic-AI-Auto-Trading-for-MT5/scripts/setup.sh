#!/bin/bash

###############################################################
# Setup Script - Kanutsanan-Pongpanna Agentic AI Trading
#
# This script prepares the environment for trading.
###############################################################

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🤖 Setup: Kanutsanan-Pongpanna Agentic AI Trading"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ ERROR: Node.js not found!"
    echo ""
    echo "Install Node.js from: https://nodejs.org/"
    echo ""
    exit 1
fi

NODE_VERSION=$(node -v)
echo "✅ Node.js found: $NODE_VERSION"

# Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ ERROR: npm not found!"
    echo ""
    exit 1
fi

NPM_VERSION=$(npm -v)
echo "✅ npm found: $NPM_VERSION"

echo ""
echo "Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Configuration"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp assets/config-template.env .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT:"
    echo "  1. Edit .env with your MetaApi credentials"
    echo "  2. Add your API Key (TOKEN)"
    echo "  3. Add your Account ID"
    echo ""
    echo "Run: nano .env"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Create logs directory
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo "✅ Created logs directory"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Setup Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "Next steps:"
echo ""
echo "1. Configure credentials:"
echo "   nano .env"
echo ""
echo "2. Test trade analysis:"
echo "   source .env && npm run check"
echo ""
echo "3. Setup automation:"
echo "   bash scripts/cron-setup.sh"
echo ""
echo "4. Monitor logs:"
echo "   npm run logs"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
