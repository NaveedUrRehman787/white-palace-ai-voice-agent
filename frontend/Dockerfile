# ============================================
# White Palace Grill - Frontend
# Production-ready with Nginx
# ============================================

# Stage 1: Build
FROM node:18-alpine as build

WORKDIR /app

# Copy package files (Context is ./frontend)
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Stage 2: Runtime (Nginx)
FROM nginx:alpine

# Copy built files from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
