#!/bin/sh
# Start both LangGraph server and API server

# Start API server in background
echo "Starting API server on port 8001..."
python -m learning_agent.api_server &
API_PID=$!

# Give API server time to start
sleep 2

# Start LangGraph server (this will block)
echo "Starting LangGraph server on port 2024..."
cd /app && langgraph dev --no-reload --host 0.0.0.0 --port 2024

# If LangGraph server exits, kill API server
kill $API_PID 2>/dev/null
