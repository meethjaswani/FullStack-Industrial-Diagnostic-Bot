#!/bin/bash

# Development startup script for SentientGrid
# This script ensures proper environment setup before starting the services

echo "🚀 Starting SentientGrid Development Environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one with your GROQ_API_KEY:"
    echo "   echo 'GROQ_API_KEY=your_api_key_here' > .env"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Verify API key is available
echo "🔑 Checking API key..."
if python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ API Key found' if os.getenv('GROQ_API_KEY') else '❌ API Key missing')"; then
    echo "✅ Environment setup complete"
else
    echo "❌ Environment setup failed"
    exit 1
fi

# Start API server in background
echo "🚀 Starting API server..."
python api_server.py &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start Streamlit app
echo "🌐 Starting Streamlit web interface..."
streamlit run streamlit_app.py

# Cleanup: Kill API server when Streamlit exits
echo "🛑 Shutting down API server..."
kill $API_PID 2>/dev/null || true

echo "✅ Development environment stopped"
