// src/server.js
import express from 'express';
import path from 'path';
import fs from 'fs';

// Define the directory for static assets (your built React app)
// When building with Vite the build output is placed in /dist at the repo root.
const BUILD_DIR = path.join(process.cwd(), 'dist');

const app = express();
const PORT = process.env.PORT || 8080;

// Security: hide Express header
app.disable('x-powered-by');

// Helper to set correct MIME types for JS module files
function setJsMime(res, filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.js' || ext === '.mjs') {
    // Ensure module scripts are served with JavaScript MIME type
    res.setHeader('Content-Type', 'text/javascript; charset=utf-8');
  } else if (ext === '.map') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
  }
}

// Serve static files from the 'dist' directory with caching for better performance
// Use setHeaders to ensure JS files get the correct MIME type for module imports
app.use(express.static(BUILD_DIR, {
  maxAge: '1d', // cache static assets for 1 day
  index: false, // do not serve index.html automatically for directory requests
  setHeaders: (res, filePath) => {
    try {
      setJsMime(res, filePath);
    } catch (e) {
      // ignore header set errors
    }
  }
}));

// Additionally, explicitly serve files under dist/assets (where chunks are placed)
const assetsPath = path.join(BUILD_DIR, 'assets');
if (fs.existsSync(assetsPath)) {
  app.use('/assets', express.static(assetsPath, {
    maxAge: '1d',
    setHeaders: (res, filePath) => {
      try {
        setJsMime(res, filePath);
      } catch (e) {}
    }
  }));
}

// Fallback: serve index.html for any navigation requests (HTML) to support client-side routing
app.get('*', (req, res) => {
  // Only handle requests that accept HTML (ignore API calls that expect JSON)
  const accepts = req.accepts(['html', 'json', 'xml']);
  if (accepts !== 'html') {
    return res.status(404).send();
  }

  const indexPath = path.join(BUILD_DIR, 'index.html');
  if (!fs.existsSync(indexPath)) {
    return res.status(500).send('index.html not found - run the build process');
  }

  res.sendFile(indexPath, (err) => {
    if (err) {
      console.error('Error sending index.html', err);
      res.status(500).send('Server error');
    }
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT} (serving ${BUILD_DIR})`);
});