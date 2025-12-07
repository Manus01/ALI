// src/server.js
import express from 'express';
import path from 'path';

// Define the directory for static assets (your built React app)
// When building with Vite the build output is placed in /dist at the repo root.
const BUILD_DIR = path.join(process.cwd(), 'dist');

const app = express();
const PORT = process.env.PORT || 8080;

// Security: hide Express header
app.disable('x-powered-by');

// Serve static files from the 'dist' directory with caching for better performance
app.use(express.static(BUILD_DIR, {
  maxAge: '1d', // cache static assets for 1 day
  index: false, // do not serve index.html automatically for directory requests
}));

// Fallback: serve index.html for any navigation requests (HTML) to support client-side routing
app.get('*', (req, res) => {
  // Only handle requests that accept HTML (ignore API calls that expect JSON)
  const accepts = req.accepts(['html', 'json', 'xml']);
  if (accepts !== 'html') {
    return res.status(404).send();
  }

  res.sendFile(path.join(BUILD_DIR, 'index.html'), (err) => {
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