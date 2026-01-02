# ALI Platform - Frontend Documentation

## Overview
The ALI Frontend is a modern single-page application (SPA) built with **React 19** and **Vite**. It provides a responsive, dynamic user interface for interacting with the ALI Platform's campaign generation and brand analysis tools.

## Tech Stack
- **Framework**: React 19
- **Build Tool**: Vite
- **Styling**: TailwindCSS, Autoprefixer, PostCSS
- **State/API**: Axios, Firebase SDK
- **Visualization**: Chart.js, React-Chartjs-2
- **UI Components**: React Icons, Framer Motion (for animations), @hello-pangea/dnd (drag & drop)

## Directory Structure
```
ali-frontend/
├── public/              # Static assets
├── src/
│   ├── assets/          # Images and styles
│   ├── components/      # Reusable UI components
│   ├── pages/           # Application views/routes
│   ├── App.jsx          # Root component
│   └── main.jsx         # Entry point
├── index.html           # HTML template
├── tailwind.config.js   # Tailwind configuration
└── vite.config.js       # Vite configuration
```

## Setup & Installation

### Prerequisites
- Node.js (Latest LTS recommended)
- npm or yarn

### Installation
1. Navigate to the frontend directory:
   ```bash
   cd ali-frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

### Configuration
Environment variables should be configured in `.env` files (e.g., `.env.local` for development).
Key variables often include:
- `VITE_API_URL`: URL of the backend API.
- Firebase config variables.

### Running Locally
Start the development server:
```bash
npm run dev
```
The application will run at `http://localhost:5173`.

## Key Features
- **Performance**: Optimized builds with Vite.
- **Linting**: configured with ESLint (plugin-react-hooks, plugin-react-refresh).
- **Security**: Nginx configuration included (`nginx.conf`) for production serving.
