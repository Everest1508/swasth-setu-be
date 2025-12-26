#!/bin/bash
# Quick script to start the Django backend server

set -e  # Exit on error

cd "$(dirname "$0")"

echo "=========================================="
echo "Starting Django Backend Server"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found!"
    echo "Please run: ./install_backend.sh first"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if Django is installed
if ! python -c "import django" 2>/dev/null; then
    echo "❌ Error: Django not installed!"
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Run system check
echo ""
echo "Running system checks..."
if ! python manage.py check --deploy 2>&1 | grep -q "System check identified no issues"; then
    echo "⚠️  System check found some warnings (these are OK for development)"
fi

# Check if migrations are applied
if [ ! -f "db.sqlite3" ]; then
    echo ""
    echo "Database not found. Creating migrations..."
    python manage.py makemigrations
    echo "Applying migrations..."
    python manage.py migrate
fi

# Check if port is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo ""
    echo "⚠️  Port 8000 is already in use!"
    echo "Another server might be running. Killing existing process..."
    pkill -f "manage.py runserver" 2>/dev/null || true
    sleep 2
fi

# Start the server
echo ""
echo "=========================================="
echo "Starting server..."
echo "=========================================="
echo "Server will be available at:"
echo "  ✓ http://localhost:8000"
echo "  ✓ http://127.0.0.1:8000"
echo "  ✓ http://192.168.1.15:8000 (for physical devices)"
echo ""
echo "API Endpoints:"
echo "  ✓ http://localhost:8000/api/auth/register/"
echo "  ✓ http://localhost:8000/api/auth/login/"
echo "  ✓ http://localhost:8000/api/appointments/doctors/"
echo "  ✓ http://localhost:8000/api/video-calls/"
echo ""
echo "Make sure your phone and computer are on the same WiFi network!"
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

python manage.py runserver 0.0.0.0:8000

