# Cloud Scheduler Setup Guide

Follow these steps to enable automatic hourly monitoring for the Troubleshooting Agent.

## Prerequisite: Service Account

Ensure a service account exists for the Cloud Scheduler to identity itself.

```bash
# 1. Create Service Account (if not exists)
gcloud iam service-accounts create cloud-scheduler-invoker \
    --display-name "Cloud Scheduler Invoker"

# 2. Grant Cloud Run Invoker Role
gcloud run services add-iam-policy-binding ali-backend \
    --member=serviceAccount:cloud-scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com \
    --role=roles/run.invoker \
    --region=us-central1
```

## Create the Scheduler Job

Create a job that hits the `/internal/scheduler/watchdog` endpoint every hour.

```bash
# Replace $PROJECT_ID and the SERVICE_URL with your actual values

gcloud scheduler jobs create http watchdog-hourly \
    --schedule="0 * * * *" \
    --uri="https://ali-backend-SERVICE-URL.run.app/internal/scheduler/watchdog" \
    --http-method=POST \
    --oidc-service-account-email=cloud-scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com \
    --location=us-central1 \
    --description="Triggers AI Troubleshooting Watchdog hourly"
```

## Verification

Run the job manually to test:

```bash
gcloud scheduler jobs run watchdog-hourly --location=us-central1
```

Check the logs in GCP Console:
- **Cloud Scheduler Logs**: To see if the job triggered
- **Cloud Run Logs**: To see the `watchdog` logs (Look for "🐕 Scheduled Watchdog Complete")
