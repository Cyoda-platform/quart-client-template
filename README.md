# Test Management System — Local Run Instructions

This repository contains a runnable scaffold for a Test Management System built with FastAPI and an in-memory data client for testing and local development.

Prerequisites
- Python 3.8+ (3.10 recommended)
- pip

Install dependencies
```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Or using pyproject.toml with pip:
```bash
pip install .
pip install fastapi uvicorn
```

Run the app locally
```bash
uvicorn application.main:app --reload --port 8000
```

Swagger UI
- Once running, open: http://localhost:8000/docs

API Endpoints
- POST /test-runs — create a TestRun
- POST /test-runs/{run_id}/start — start execution (allocates run executions and creates step executions)
- POST /events/update-step-status — post UPDATE_STEP_STATUS events
- GET /reports/{run_id} — get ExecutionReport
- POST /test-runs/{run_id}/complete — complete and lock a run

Testing
```bash
pytest -q
```

Notes
- The in-memory data client lives at application/clients/data_client.py and is used by processors.
- Processors are implemented under application/processors and wired manually in application/main.py.
- This scaffold is intended for local development and demonstrations. For production, replace the in-memory client with the Cyoda data client and configure asynchronous processing for long-running processors.
