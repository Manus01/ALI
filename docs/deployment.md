# ALI Platform - Deployment Guide

## Overview
The ALI Platform is deployed on **Google Cloud Platform (GCP)** using **Cloud Run** for serverless container execution. CI/CD is managed via **Cloud Build**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Run Services                        │
├─────────────────────────────────────────────────────────────┤
│   ali-frontend (Nginx)        ali-backend (Uvicorn)         │
│        ↓                              ↓                      │
│   Static React App             FastAPI + AI Agents           │
└──────────────┬───────────────────────┬──────────────────────┘
               │                       │
               ▼                       ▼
         ┌───────────┐         ┌──────────────┐
         │ Firebase  │         │ Vertex AI    │
         │ Hosting   │         │ (Gemini,     │
         │ + Auth    │         │  Imagen)     │
         └───────────┘         └──────────────┘
               │
               ▼
         ┌───────────┐         ┌──────────────┐
         │ Firestore │         │ Cloud        │
         │ Database  │         │ Storage      │
         └───────────┘         └──────────────┘
```

## Cloud Run Services

| Service | Description |
|---------|-------------|
| `ali-frontend` | React app served via Nginx |
| `ali-backend` | FastAPI with AI agents |

## Automatic Deployments

Deployments are triggered via Cloud Build on push to `main`:

```yaml
# cloudbuild.yaml steps:
1. Build Docker images (backend + frontend)
2. Push to Artifact Registry
3. Deploy to Cloud Run
```

## Environment Variables

### Backend (Cloud Run)
```env
PROJECT_ID=your-gcp-project
GCS_BUCKET_NAME=your-bucket.appspot.com
TTS_MODEL=gemini-2.5-flash-preview-tts
IMAGE_MODEL=imagen-4.0-generate-001
```

### Frontend (Build-time)
```env
VITE_API_URL=https://ali-backend-xxx.run.app
VITE_FIREBASE_PROJECT_ID=your-project
```

## Scheduled Jobs

Cloud Scheduler triggers:
- **Brand Monitoring Scan**: Every 5 minutes (`*/5 * * * *`)
- **Watchdog**: Hourly (`0 * * * *`)

See [GCP Scheduler Setup](../ali-backend/docs/gcp_scheduler_setup.md) for configuration.

## Manual Deployment

### Backend
```bash
cd ali-backend
gcloud run deploy ali-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Frontend
```bash
cd ali-frontend
npm run build
gcloud run deploy ali-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## Security

- **CORS**: Backend configured for specific frontend origins
- **IAM**: Cloud Scheduler uses OIDC tokens for internal endpoints
- **Firestore**: Security rules enforce user-scoped data access
- **Storage**: Signed URLs for temporary media access
