# REVORA — AI Revenue Recovery Experiment Agent

Built for the **Razorpay AI Buildathon 2026** (AI Revenue Recovery Track).

REVORA is an intelligent autonomous experiment agent designed to minimize payment failures, optimize dunning workflows, and maximize recovered revenue.

---

## Project Structure

```text
REVORA/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application entrypoint & root routes
│   │   ├── config.py        # Settings and environment variable configurations
│   │   ├── database.py      # SQLAlchemy engine, session maker, and Base
│   │   ├── models/          # Database models
│   │   ├── routes/          # API route definitions
│   │   ├── services/        # Business logic and external service helpers
│   │   └── agents/          # AI Revenue Recovery agent logic
│   ├── requirements.txt
│   └── .env.example
├── data/                    # Local storage / datasets
├── docs/                    # Architecture and documentation
├── .gitignore
└── README.md
```

---

## Local Backend Setup

### 1. Prerequisites
- Python 3.11+
- `pip`

### 2. Set Up Virtual Environment

From the root directory:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload
```

The server will start at: `http://127.0.0.1:8000`

### 6. Verify Endpoints

- **Root:**
  ```bash
  curl http://127.0.0.1:8000/
  ```
  Response:
  ```json
  {
    "name": "Revora",
    "description": "AI Revenue Recovery Experiment Agent",
    "status": "running"
  }
  ```

- **Health:**
  ```bash
  curl http://127.0.0.1:8000/health
  ```
  Response:
  ```json
  {
    "status": "healthy"
  }
  ```

- **API Documentation:**
  Interactive Swagger UI is available at `http://127.0.0.1:8000/docs`.
