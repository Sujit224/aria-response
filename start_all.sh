#!/bin/bash

echo "Starting ARIA Response System locally..."

# Start Backend
echo "Starting backend..."
source venv/bin/activate
# pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Guest PWA
echo "Starting Guest PWA..."
cd frontend/guest-pwa
npm install
npm run dev -- --port 3000 &
GUEST_PID=$!
cd ../..

# Start Staff Dashboard
echo "Starting Staff Dashboard..."
cd frontend/staff-dashboard
npm install
npm run dev -- --port 3001 &
STAFF_PID=$!
cd ../..

echo "All services started."
echo "Backend: $BACKEND_PID"
echo "Guest PWA: $GUEST_PID"
echo "Staff Dashboard: $STAFF_PID"

wait $BACKEND_PID $GUEST_PID $STAFF_PID
