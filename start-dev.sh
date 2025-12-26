#!/bin/bash
# Development startup script for JobApplicationBot
# Starts both backend and frontend servers

echo "🚀 Starting JobApplicationBot Development Environment"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found"
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend/job-automation-dashboard" ]; then
    echo "❌ Error: frontend directory not found"
    exit 1
fi

# Start backend server
echo -e "${BLUE}📊 Starting Backend (FastAPI on http://localhost:8000)${NC}"
cd backend
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend server
echo -e "${GREEN}🎨 Starting Frontend (Next.js on http://localhost:3000)${NC}"
cd frontend/job-automation-dashboard
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "✅ Development servers started!"
echo ""
echo "📊 Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Health:       http://localhost:8000/health"
echo ""
echo "🎨 Frontend:     http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Wait for both processes
wait
