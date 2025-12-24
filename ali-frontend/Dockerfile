# --- Stage 1: Build the React App ---
FROM node:18-alpine as build

WORKDIR /app

# Copy package info and install dependencies
COPY package*.json ./
# FIXED: Removed the extra 's' from the flag
RUN npm install --legacy-peer-deps

# Copy source code and build
COPY . .
RUN npm run build

# --- Stage 2: Serve with Nginx ---
FROM nginx:alpine

# Copy the built files from Stage 1 to Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copy our custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]