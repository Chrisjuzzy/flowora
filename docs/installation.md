# Installation
Flowora - Where AI Agents Flow Together.

This guide covers local development setup for both backend and frontend.

## Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

## Backend Setup
```bash
cd apps/backend
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Create a `.env` file based on `apps/backend/.env.example`, then run:
```bash
uvicorn main:app --reload
```

## Frontend Setup
```bash
cd apps/frontend
npm install
npm run dev
```

## Environment Variables
Key variables include:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `OPENAI_API_KEY` or other provider keys
- `NEXT_PUBLIC_API_URL`

## Verify
- Backend: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`
