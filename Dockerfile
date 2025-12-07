# Multi-stage Dockerfile for building the Vite React app and running Express

# Builder stage: install deps and build the application (includes dev deps for build)
FROM node:20-slim AS builder
WORKDIR /usr/src/app

# Copy package metadata first for layer caching
COPY package*.json ./

# Install all dependencies (including dev dependencies required for build)
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# Copy the rest of the source and run the build (must produce ./dist)
COPY . .
RUN npm run build

# Remove devDependencies to leave only production modules for the runtime
RUN npm prune --production || true

# Runner stage: minimal Node image that runs the Express server and serves ./dist
FROM node:20-slim AS runner
WORKDIR /usr/src/app

# Copy production node_modules from builder
COPY --from=builder /usr/src/app/node_modules ./node_modules

# Copy built assets and server code from builder
COPY --from=builder /usr/src/app/dist ./dist
COPY --from=builder /usr/src/app/src/server.js ./src/server.js

# Ensure the container listens on the Cloud Run-provided port
ENV PORT=8080
EXPOSE 8080

# Start the Express server
CMD ["node", "src/server.js"]
