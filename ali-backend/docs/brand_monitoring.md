# Brand Monitoring System

## Overview

The Brand Monitoring system provides real-time brand intelligence through automated scanning, threat detection, and competitive analysis.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (React)                             │
├─────────────────────────────────────────────────────────────────┤
│   BrandMonitoringPage → BrandMonitoringDashboard                │
│                       → PriorityActions                          │
│                       → ScanTimeline                             │
│                       → SystemHealthPanel                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ apiClient
┌─────────────────────▼───────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│   brand_monitoring.py (router)                                   │
│   scheduler.py (Cloud Scheduler trigger)                         │
├─────────────────────────────────────────────────────────────────┤
│   brand_monitoring_scanner.py (orchestrator)                     │
│   adaptive_scan_service.py (dynamic scheduling)                  │
├─────────────────────────────────────────────────────────────────┤
│   Agents:                                                        │
│   ├── competitor_agent.py    - Competitive intelligence          │
│   ├── protection_agent.py    - Threat detection                  │
│   ├── pr_agent.py           - PR monitoring                      │
│   └── learning_agent.py     - Learning recommendations           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Scanning Engine

### Adaptive Scan Scheduling

Scans are scheduled dynamically based on threat level:

| Threat Level | Scan Interval | Description |
|--------------|---------------|-------------|
| Critical (80+) | 5 minutes | Active threat detected |
| High (60-79) | 15 minutes | Concerning patterns |
| Medium (40-59) | 1 hour | Normal monitoring |
| Low (0-39) | 6 hours | Quiet period |

### Scan Process

1. Cloud Scheduler triggers `/internal/scheduler/brand-monitoring-scan` every 5 minutes
2. Query all scan policies where `next_scan_at <= now`
3. Calculate current threat score
4. Execute scans with idempotency (skip pending jobs)
5. Update `next_scan_at` based on new threat level
6. Log scan metadata to BigQuery

---

## Frontend Modules

The frontend uses a modular architecture (`lib/brand-monitoring/`):

```
lib/brand-monitoring/
├── client.ts          # brandMonitoringApi instance
├── endpoints.ts       # Endpoint registry
├── types.ts           # Shared TypeScript types
└── modules/
    ├── competitors/   # Competitor tracking
    ├── evidence/      # Evidence package management
    ├── scanning/      # Scan control & policy
    └── threats/       # Threat detection & analysis
```

### Using the API

```typescript
import { useDeepfakeCheck } from '@/lib/brand-monitoring/modules/threats';

function ThreatAnalyzer() {
  const { state, check } = useDeepfakeCheck();
  
  return (
    <button onClick={() => check({ url: mediaUrl })}>
      Analyze for Deepfake
    </button>
  );
}
```

---

## Agents

### Competitor Agent

Analyzes competitors' digital presence, strategies, and market positioning.

```python
from app.agents.competitor_agent import CompetitorAgent

agent = CompetitorAgent()
analysis = await agent.analyze_competitor("CompetitorCo")
```

### Protection Agent

Detects brand threats: counterfeits, deepfakes, trademark abuse.

### PR Agent

Monitors public relations, news coverage, and sentiment.

### Learning Agent

Generates personalized recommendations based on monitoring data.

---

## Evidence Packages

When threats are confirmed, evidence packages can be exported:

```
evidence-RPT-{hash}.zip
├── report.json       # Full threat report
├── sources.json      # Source URLs and metadata
├── provenance.json   # Export metadata (who, when, why)
├── manifest.json     # File hashes for integrity
└── integrity.json    # Package-level hash for tamper detection
```

Use `tools/verify_evidence_package.py` to validate packages offline.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/brand-monitoring/mentions` | GET | Fetch recent mentions |
| `/brand-monitoring/priority-actions` | POST | Get urgency-scored threats |
| `/brand-monitoring/recommend-action` | POST | AI action recommendation |
| `/brand-monitoring/deepfake-check` | POST | Analyze media for deepfakes |
| `/brand-monitoring/competitors` | GET/POST/DELETE | Manage competitors |
| `/brand-monitoring/evidence/{id}/export` | POST | Export evidence package |
| `/internal/scheduler/brand-monitoring-scan` | POST | Trigger adaptive scan |

---

## Setup

See [GCP Scheduler Setup](./gcp_scheduler_setup.md) for Cloud Scheduler configuration.
