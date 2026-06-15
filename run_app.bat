@echo off
echo Starting Backend (FastAPI)...
start cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload --port 8000"

echo Starting Frontend (React/Vite)...
start cmd /k "cd frontend && npm run dev"

echo Both servers are starting! The frontend will be available at http://localhost:5173
