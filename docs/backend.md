# ALI Platform - Backend Documentation

## Overview
The ALI Backend is a high-performance, asynchronous web service built with **FastAPI**. It serves as the intelligence engine for the platform, orchestrating AI agents, managing data persistence with Firestore, and handling external integrations.

## Tech Stack
- **Framework**: FastAPI (Python 3.10+)
- **Database**: Google Cloud Firestore
- **AI/ML**: Google Vertex AI (Gemini 2.5, Imagen 4.0), LangChain
- **Media**: Gemini TTS, Imagen image generation
- **Asynchronous**: Python `asyncio`, tenacity retry
- **Server**: Uvicorn (ASGI)

## Directory Structure
```
ali-backend/
├── app/
│   ├── agents/           # AI agents (Tutorial, Campaign, Brand Monitoring)
│   ├── core/             # Core configurations (security, database)
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic (audio, image, BigQuery)
│   ├── middleware/       # Observability and request handling
│   ├── types/            # Pydantic models
│   └── utils/            # Utilities (zip_builder, etc.)
├── docs/                 # Backend-specific documentation
├── tests/                # Unit tests
├── Dockerfile            # Container configuration
└── requirements.txt      # Python dependencies
```

## Key Agents

| Agent | Purpose |
|-------|---------|
| `tutorial_agent.py` | Generates 4C/ID tutorials with media assets |
| `campaign_agent.py` | Creates multi-channel marketing campaigns |
| `troubleshooting_agent.py` | Autonomous error diagnosis |
| `competitor_agent.py` | Competitive intelligence |
| `protection_agent.py` | Brand threat detection |
| `radar_agent.py` | Market intelligence |

## Key Services

| Service | Purpose |
|---------|---------|
| `audio_agent.py` | Gemini TTS with WAV header generation |
| `image_agent.py` | Imagen 4.0 with retry logic |
| `brand_monitoring_scanner.py` | Brand scan orchestration |
| `adaptive_scan_service.py` | Dynamic scan scheduling |
| `bigquery_service.py` | Analytics and logging |

## Setup & Running

### Prerequisites
- Python 3.10+
- GCP Service Account credentials

### Installation
```bash
cd ali-backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Create `.env` in `ali-backend/`:
```env
GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
PROJECT_ID="your-gcp-project-id"
GCS_BUCKET_NAME="your-bucket.appspot.com"
TTS_MODEL="gemini-2.5-flash-preview-tts"
```

### Running Locally
```bash
uvicorn app.main:app --reload
```
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

## Additional Documentation

See `ali-backend/docs/` for detailed guides:
- [Architecture Overview](ali-backend/docs/architecture.md)
- [Brand Monitoring System](ali-backend/docs/brand_monitoring.md)
- [GCP Scheduler Setup](ali-backend/docs/gcp_scheduler_setup.md)
