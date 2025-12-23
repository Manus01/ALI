from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# --- ROUTER IMPORTS ---
# We verify these exist based on our work so far
from app.routers import (
    auth, 
    dashboard, 
    tutorials, 
    jobs,          
    assessments, 
    notifications,
    publisher,
    webhook,
    integration,
    admin
)

# These appear to be placeholders or future files you have. 
# Ensure these files actually exist in app/routers/, or the app will crash.
try:
    from app.routers import strategy, studio, repurpose, execution, maintenance
except ImportError:
    strategy = studio = repurpose = execution = maintenance = None
    print("⚠️ Warning: Some optional routers (strategy, studio, etc.) were not found. Skipping them.")

load_dotenv()

app = FastAPI(title="ALI Platform", version="4.0")

# --- 1. CORS CONFIGURATION (Mandatory for Frontend) ---
origins = [
    "http://localhost:5173",  # React Localhost
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. REGISTER ROUTERS ---

# Core Systems
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(webhook.router, prefix="/api", tags=["Webhooks"])
app.include_router(integration.router, prefix="/api", tags=["Integrations"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Research"])

# Publisher System
app.include_router(publisher.router, prefix="/api", tags=["Publisher"])

# Learning Engine
app.include_router(tutorials.router, prefix="/api", tags=["Tutorials"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"]) # <--- Added this
app.include_router(assessments.router, prefix="/api", tags=["Assessments"])

# Future Modules (Only include if import succeeded)
if strategy: app.include_router(strategy.router, prefix="/api", tags=["Strategy"])
if studio: app.include_router(studio.router, prefix="/api", tags=["Studio"])
if repurpose: app.include_router(repurpose.router, prefix="/api", tags=["Repurpose"])
if execution: app.include_router(execution.router, prefix="/api", tags=["Execution"])
if maintenance: app.include_router(maintenance.router, prefix="/api", tags=["Maintenance"])

@app.get("/")
def read_root():
    return {"status": "alive", "service": "ALI Platform v4.0"}