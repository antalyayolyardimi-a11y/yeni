#!/bin/bash

# Trading Bot Startup Script
# This script helps start the trading bot with proper environment setup

echo "🤖 Trading Bot Startup Script"
echo "============================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the trading_bot directory"
    echo "   cd trading_bot && ./start_bot.sh"
    exit 1
fi

# Check if Python dependencies are installed
echo "📦 Checking dependencies..."
python3 -c "import pandas, numpy, requests" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Dependencies are installed"
else
    echo "⚠️  Some dependencies are missing. Installing..."
    pip install pandas numpy requests
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp ../.env.example .env
    echo "📝 Please edit .env file with your API credentials"
    echo "   You can run the bot in demo mode without real API keys"
fi

# Run the test suite first
echo "🧪 Running tests..."
python3 test_bot.py
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "🚀 Starting Trading Bot..."
echo "   Press Ctrl+C to stop the bot"
echo "   Check trading_bot.log for detailed logs"
echo ""

# Start the bot
python3 main.py