# ALI Platform - Deployment Guide

## Overview
The ALI Platform is designed to be deployed on **Google Cloud Platform (GCP)** using **Cloud Run** for serverless container execution. The deployment pipeline is managed via **Cloud Build**.

## Infrastructure

### Google Cloud Run
- **Frontend**: Deployed as a distinct service (serving static files via Nginx).
- **Backend**: Deployed as a distinct service (Uvicorn/FastAPI).
- **Scalability**: Auto-scaling configured based on request load.

### Google Cloud Firestore
- Used as the primary NoSQL database for user data, campaigns, and brand profiles.

## Build Process
The project includes a `cloudbuild.yaml` file in the root directory, which defines the CI/CD pipeline steps:
1. **Build**: Docker images are built for both `ali-backend` and `ali-frontend`.
2. **Push**: Images are pushed to Google Container Registry (GCR) or Artifact Registry.
3. **Deploy**: Images are deployed to Cloud Run services.

## Production Configuration

### Environment Variables
The following environment variables must be set in the Cloud Run service configuration for the Backend:
- `GOOGLE_APPLICATION_CREDENTIALS`: (If using a key file, though Workload Identity is preferred).
- `PROJECT_ID`: The GCP project ID.
- `MAX_REQUEST_SIZE_BYTES`: (Optional) request size limit.
- AI Service Credentials/Keys (if applicable).

### CORS & Security
Ensure that the Frontend URL is added to the Backend's `origins` list in `app/main.py` if the domain changes.

## Manual Deployment (Example)
To deploy manually using the `gcloud` CLI:

**Backend:**
```bash
cd ali-backend
gcloud run deploy ali-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

**Frontend:**
```bash
cd ali-frontend
gcloud run deploy ali-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```
