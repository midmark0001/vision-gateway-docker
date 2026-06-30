#!/bin/bash
set -e
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
sleep 2
echo "Xvfb started on PID $XVFB_PID"
exec uvicorn image_full:app --host 0.0.0.0 --port 7860 --workers 1
