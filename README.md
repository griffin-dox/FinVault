# FinVault

A modern, secure, AI-enhanced banking MVP with passwordless authentication, behavioral risk analysis, and real-time fraud analytics.

---

## Directory Structure

```
FinVault/
├── backend/        # FastAPI backend (Python)
├── frontend/       # React frontend (TypeScript)
│   └── client/     # Main React app
├── attached_assets/
├── ...other config and docs
```

---

## Quickstart

### 1. Clone the repo
```bash
git clone <repo-url>
cd FinVault
```

### 2. Setup Backend
```bash
cd backend
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your secrets
uvicorn app.main:app --reload
```

### 3. Setup Frontend
```bash
cd frontend/client
npm install
cp .env.example .env  # Edit with your API URL, etc.
npm run dev
```

### 4. Local Dev Scripts (from project root)
```bash
# Start backend
npm run dev:backend
# Start frontend
npm run dev:frontend
# Start both (requires 'concurrently')
npm run dev:all
```

---

## Environment Variables
- See `.env.example` in both `backend/` and `frontend/client/` for required variables.

---

## Linting & Formatting
- Python: `black`, `flake8`
- JS/TS: `eslint`, `prettier`
- Pre-commit hooks auto-format and lint code before commit.

---

## Contributing
- See `CONTRIBUTING.md` (coming soon)
- PRs welcome! 