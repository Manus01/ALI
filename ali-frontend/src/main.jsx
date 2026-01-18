import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
// Note: apiClient from lib/api-client is initialized on first use - no side-effect import needed

import Logger from './services/Logger'
import ErrorBoundary from './components/ErrorBoundary.jsx'

// Global Error Listeners for Unhandled Exceptions
window.onerror = function (message, source, lineno, colno, error) {
  Logger.error(message, "GlobalWindowError", error ? error.stack : null, { source, lineno, colno });
};

window.onunhandledrejection = function (event) {
  Logger.error(
    "Unhandled Promise Rejection: " + (event.reason ? (event.reason.message || event.reason) : "Unknown"),
    "GlobalPromiseRejection",
    event.reason ? event.reason.stack : null
  );
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
