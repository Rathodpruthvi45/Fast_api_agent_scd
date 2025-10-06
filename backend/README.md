# Windows Compliance Checker Backend

This is the FastAPI backend for the Windows Compliance Checker project.

## Setup

1. Create a virtual environment and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Structure

- `app/main.py`: FastAPI entry point
- `app/core/`: Core logic modules
- `app/models/`: Pydantic models
- `app/api/endpoints/`: API endpoints
- `app/utils/`: Utility functions
