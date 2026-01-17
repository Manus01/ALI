# GCP Cloud Scheduler Setup for Brand Monitoring

## Overview

The Brand Monitoring scanner runs **every hour** to automatically:
1. Fetch new mentions for all users
2. Detect competitor actions  
3. Log everything to BigQuery
4. Identify PR opportunities

---

## Setup Instructions

### 1. Get Your Cloud Run URL

```bash
# Find your service URL
gcloud run services describe ali-backend --region=us-central1 --format='value(status.url)'
```

Example output: `https://ali-backend-ibayai5n2q-uc.a.run.app`

---

### 2. Create Service Account (if not exists)

```bash
# Create scheduler service account
gcloud iam service-accounts create cloud-scheduler-invoker \
    --display-name="Cloud Scheduler Invoker"

# Grant invoker permission
gcloud run services add-iam-policy-binding ali-backend \
    --region=us-central1 \
    --member="serviceAccount:cloud-scheduler-invoker@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

---

### 3. Create the Scheduler Job

```bash
gcloud scheduler jobs create http brand-monitoring-hourly-scan \
    --location=us-central1 \
    --schedule="0 * * * *" \
    --uri="https://YOUR-CLOUD-RUN-URL/internal/scheduler/brand-monitoring-scan" \
    --http-method=POST \
    --oidc-service-account-email="cloud-scheduler-invoker@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --oidc-token-audience="https://YOUR-CLOUD-RUN-URL"
```

**Replace:**
- `YOUR-PROJECT-ID` with your GCP project ID
- `YOUR-CLOUD-RUN-URL` with the URL from step 1

---

### 4. Verify Setup

```bash
# Test manually
gcloud scheduler jobs run brand-monitoring-hourly-scan --location=us-central1

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND textPayload:brand-monitoring" --limit=10
```

---

## Console Alternative (UI)

1. Go to [Cloud Scheduler Console](https://console.cloud.google.com/cloudscheduler)
2. Click **Create Job**
3. Fill in:
   - **Name**: `brand-monitoring-hourly-scan`
   - **Frequency**: `0 * * * *` (every hour at minute 0)
   - **Timezone**: UTC
4. Configure target:
   - **Target type**: HTTP
   - **URL**: `https://YOUR-CLOUD-RUN-URL/internal/scheduler/brand-monitoring-scan`
   - **HTTP method**: POST
5. Configure Auth:
   - **Add OIDC token**
   - **Service account**: `cloud-scheduler-invoker@YOUR-PROJECT-ID.iam.gserviceaccount.com`
   - **Audience**: Your Cloud Run URL
6. Click **Create**

---

## Monitoring

View scheduler logs in Cloud Console:
- [Cloud Scheduler Logs](https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_scheduler_job%22)
- [Cloud Run Logs](https://console.cloud.google.com/run)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check service account has `run.invoker` role |
| 403 Forbidden | Verify OIDC audience matches Cloud Run URL |
| Job never runs | Check timezone and cron expression |
| Empty results | Verify users have brand monitoring configured |
