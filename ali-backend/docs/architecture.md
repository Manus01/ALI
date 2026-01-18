# Backend Architecture Overview

## System Components

The ALI Platform backend is built with FastAPI and organized into three main layers:

```
ali-backend/
├── app/
│   ├── agents/          # AI-powered task agents
│   ├── services/        # Business logic & external APIs
│   ├── routers/         # API endpoints
│   ├── middleware/      # Request/response middleware
│   ├── types/           # Pydantic models
│   └── utils/           # Shared utilities
```

---

## Agents

AI-powered agents handle complex, multi-step tasks:

| Agent | Purpose |
|-------|---------|
| `tutorial_agent.py` | Generates 4C/ID-based tutorials with media assets |
| `campaign_agent.py` | Creates multi-channel marketing campaigns |
| `troubleshooting_agent.py` | Autonomous error diagnosis & remediation |
| `competitor_agent.py` | Competitive intelligence analysis |
| `protection_agent.py` | Brand protection and threat detection |
| `pr_agent.py` | PR and communications monitoring |
| `learning_agent.py` | Personalized learning recommendations |
| `radar_agent.py` | Market intelligence and trend detection |

---

## Media Generation Pipeline

The tutorial engine generates rich media assets (audio, images) with built-in resilience:

### Retry Mechanism

```python
# Orchestration-level retry in fabricate_block()
@retry(
    retry=retry_if_result(_is_transient_failure),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30)
)
def _call_with_orchestration_retry(agent_call, block_type):
    return agent_call()
```

**Retry Configuration:**
- Max Attempts: 3
- Backoff: Exponential (2-30 seconds)
- Retryable: `None`, `timeout`, `quota_exhausted`, `generation_failed`
- Non-retryable: `content_policy`, `validation`

### Audio Generation (Gemini TTS)

```
Text Input → AudioAgent → Raw L16 PCM → WAV Header Added → GCS Upload → Public URL
```

The `_add_wav_header()` function adds proper WAV container headers to raw PCM audio for browser compatibility.

### Image Generation (Imagen)

```
Prompt → ImageAgent → PNG bytes → GCS Upload → Public URL
```

Includes internal retry loop for rate limits and quota errors.

---

## Services

| Service | Purpose |
|---------|---------|
| `audio_agent.py` | Gemini 2.5 TTS with retry and WAV headers |
| `image_agent.py` | Imagen 4.0 with retry and rate limiting |
| `brand_monitoring_scanner.py` | Full brand scan orchestration |
| `adaptive_scan_service.py` | Dynamic scan scheduling based on threat level |
| `bigquery_service.py` | Analytics and audit logging |
| `structured_logger.py` | Structured JSON logging |

---

## Middleware

- **Observability** (`observability.py`): Request tracing, timing, and structured logging

---

## Configuration

Key environment variables:

```bash
# Media Generation
TTS_MODEL=gemini-2.5-flash-preview-tts
TTS_VOICE=Aoede
IMAGE_MODEL=imagen-4.0-generate-001

# GCP
GCS_BUCKET_NAME=your-bucket.appspot.com
PROJECT_ID=your-gcp-project

# Retry Settings
IMAGE_MAX_RETRIES=5
IMAGE_RETRY_BASE_DELAY=5
```

---

## Error Handling

All agents follow a consistent error handling pattern:

1. **Agent-level retry** (tenacity decorator for internal API calls)
2. **Orchestration-level retry** (for coordinating multiple asset generation)
3. **Graceful degradation** (return placeholder block on failure)
4. **Structured logging** (for troubleshooting agent analysis)
