# ALI Platform - Frontend Documentation

## Overview
The ALI Frontend is a modern single-page application (SPA) built with **React 19** and **Vite**. It provides a responsive, adaptive user interface for campaign management, brand monitoring, tutorials, and market intelligence.

## Tech Stack
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: TailwindCSS (responsive, mobile-first)
- **HTTP Client**: Custom `apiClient` with Result pattern
- **Firebase**: Authentication, real-time updates
- **Visualization**: Chart.js, react-chartjs-2
- **UI**: React Icons, Framer Motion, @hello-pangea/dnd

## Directory Structure
```
ali-frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── brand-monitoring/   # Brand monitoring components
│   │   └── market-radar/       # Market radar components
│   ├── lib/              # Core libraries
│   │   ├── api-client/         # Type-safe HTTP client
│   │   └── brand-monitoring/   # Brand monitoring modules
│   ├── pages/            # Route pages
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API services
│   └── App.jsx           # Root component
├── docs/                 # Frontend documentation
├── index.html            # HTML template
├── tailwind.config.js    # Tailwind configuration
└── vite.config.js        # Vite configuration
```

## Key Pages

| Page | Purpose |
|------|---------|
| `DashboardPage` | Main dashboard with metrics |
| `CampaignCenter` | Campaign creation wizard |
| `TutorialsPage` | Tutorial list with Saga Map |
| `TutorialDetailsPage` | Interactive tutorial viewer |
| `BrandMonitoringPage` | Threat monitoring dashboard |
| `MarketRadarPage` | Market intelligence |
| `AdminPage` | System administration |

## API Client

The frontend uses a type-safe `apiClient` with discriminated union results:

```typescript
import { apiClient } from '@/lib/api-client';

const result = await apiClient.get('/tutorials/123');

if (result.ok) {
  console.log(result.data);
} else {
  console.error(result.error.message);
}
```

See [API Client Documentation](docs/api-client.md) for full usage guide.

## Setup & Running

### Prerequisites
- Node.js 18+ (LTS recommended)
- npm

### Installation
```bash
cd ali-frontend
npm install
```

### Configuration
Create `.env.local`:
```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_PROJECT_ID=your-project-id
```

### Running Locally
```bash
npm run dev
```
Application runs at `http://localhost:5173`.

## Additional Documentation

See `ali-frontend/docs/` for detailed guides:
- [API Client Guide](ali-frontend/docs/api-client.md)
- [Endpoint Integration Checklist](ali-frontend/docs/integrate-endpoint-checklist.md)
- [Market Radar](ali-frontend/docs/market-radar.md)
