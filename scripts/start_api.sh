#!/bin/bash
# Start FastAPI server for RAG system

echo "========================================"
echo "Starting RAG API Server"
echo "========================================"

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Make sure to set OPENAI_API_KEY and other environment variables."
fi

# Check if Qdrant is running
echo "Checking Qdrant connection..."
if ! curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "WARNING: Cannot connect to Qdrant at localhost:6333"
    echo "Make sure Qdrant is running:"
    echo "  docker-compose up -d"
    echo ""
    echo "Continuing anyway..."
fi

# Start API server
echo ""
echo "========================================"
echo "Starting API on http://localhost:8000"
echo "========================================"
echo "Documentation: http://localhost:8000/docs"
echo "ReDoc: http://localhost:8000/redoc"
echo "Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

# Run with uvicorn
uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info
