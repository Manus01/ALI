// src/server.js
import express from 'express';
import path from 'path';

// Define the directory for static assets (your built React app)
const BUILD_DIR = path.join(process.cwd(), 'dist');

const app = express();
const PORT = process.env.PORT || 8080;

// Serve static files from the 'dist' directory
app.use(express.static(BUILD_DIR));

// For any other request, serve the main index.html file
// This is necessary for client-side routing (react-router-dom)
app.get('*', (req, res) => {
    res.sendFile(path.join(BUILD_DIR, 'index.html'));
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server listening on port ${PORT}`);
});