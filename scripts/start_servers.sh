#!/bin/sh
# Start both LangGraph server and API server

# Start API server (aux endpoints) in background
echo "Starting internal API server on port 8001..."
python -m learning_agent.api_server &
API_PID=$!

# Give API server a moment to start
sleep 2

# Start standalone LangGraph ASGI app (in-process) on 2024
echo "Starting standalone LangGraph server on port 2024..."
exec uvicorn learning_agent.server:app --host 0.0.0.0 --port 2024
