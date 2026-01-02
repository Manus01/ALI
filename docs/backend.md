# ALI Platform - Backend Documentation

## Overview
The ALI Backend is a high-performance, asynchronous web service built with **FastAPI**. It serves as the intelligence engine for the platform, orchestrating AI agents, managing data persistence with Firestore, and handling external integrations.

## Tech Stack
- **Framework**: FastAPI (Python 3.10+)
- **Database**: Google Cloud Firestore (via `firebase-admin` and `google-cloud-firestore`)
- **AI/ML**: Google Vertex AI, LangChain, LangGraph
- **Asynchronous Processing**: Python `asyncio`, FastAPI BackgroundTasks
- **Server**: Uvicorn (ASGI)

## Directory Structure
```
ali-backend/
├── app/
│   ├── agents/           # AI Logic & Agent definitions (BrandAgent, CampaignAgent, etc.)
│   ├── core/             # Core configurations (security, database singleton)
│   ├── routers/          # API Route controllers
│   ├── services/         # Business logic & helper services
│   └── main.py           # Application entrypoint & configuration
├── data/                 # Local data storage (if applicable)
├── Dockerfile            # Container configuration
└── requirements.txt      # Python dependencies
```

## Setup & Installation

### Prerequisites
- Python 3.10 or higher
- Google Cloud Service Account credentials (JSON)
- `.env` file configured

### Installation
1. Navigate to the backend directory:
   ```bash
   cd ali-backend
   ```
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Create a `.env` file in `ali-backend/` with the following variables (example):
```env
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
PROJECT_ID="your-gcp-project-id"
MAX_REQUEST_SIZE_BYTES=5242880 # 5MB
```

### Running Locally
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.
Docs available at `http://localhost:8000/docs`.

## Architecture Highlights

### Router Management
The application uses a dynamic `safe_import_router` pattern in `app/main.py` to robustly load API modules. This ensures the application can start even if non-critical modules fail to load.

### AI Agents
ALI uses a specialized agentic architecture:
- **BrandAgent**: Analyzes brand DNA from generic inputs.
- **CampaignAgent**: Generates strategic campaign initiatives.
- **OrchestratorAgent**: Manages complex, multi-step workflows.

### Security
- **CORS**: Configured for specific frontend origins.
- **Security Headers**: Custom middleware adds `Content-Security-Policy`, `X-Content-Type-Options`, and secure Cache-Control directives.
- **Request Size Limiting**: Middleware rejects requests larger than 5MB to prevent DoS.
