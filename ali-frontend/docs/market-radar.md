# Market Radar

Real-time market intelligence and trend detection system.

## Overview

Market Radar provides competitive intelligence by monitoring:
- Industry news and trends
- Competitor activity
- Market signals and themes
- Emerging opportunities and threats

---

## Components

### Frontend

```
src/
├── pages/
│   └── MarketRadarPage.jsx       # Main page
└── components/market-radar/
    ├── EventFeedPanel.jsx        # Real-time event stream
    ├── FiltersBar.jsx            # Filter controls
    └── ThemeClustersPanel.jsx    # Theme visualization
```

### Backend

```
app/agents/
└── radar_agent.py                # Market intelligence agent
```

---

## Event Feed

The event feed displays real-time signals:

| Event Type | Description |
|------------|-------------|
| `news` | Industry news and press releases |
| `trend` | Emerging trends and patterns |
| `competitor` | Competitor moves and announcements |
| `opportunity` | Market opportunities |
| `threat` | Competitive threats |

---

## Theme Clusters

AI-powered theme detection groups related signals:

```
┌─────────────────────────────────────────┐
│ Theme: "Sustainability Focus"           │
│ ├── News: "Industry shifts to green"    │
│ ├── Competitor: "X launches eco line"   │
│ └── Trend: "Consumer demand for eco"    │
└─────────────────────────────────────────┘
```

---

## Radar Agent

The `RadarAgent` processes market signals and generates insights:

```python
from app.agents.radar_agent import RadarAgent

agent = RadarAgent()
signals = await agent.scan_market(industry="tech", timeframe="24h")
themes = await agent.cluster_themes(signals)
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/market-radar/signals` | GET | Fetch recent market signals |
| `/market-radar/themes` | GET | Get theme clusters |
| `/market-radar/scan` | POST | Trigger manual scan |
