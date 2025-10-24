# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Create non-root user for security
RUN adduser -D -u 1000 -g 'www' www

# Copy built application
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions for nginx to run as non-root
RUN chown -R www:www /usr/share/nginx/html \
    && chown -R www:www /var/cache/nginx \
    && chown -R www:www /var/log/nginx \
    && chown -R www:www /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R www:www /var/run/nginx.pid

# Expose port (using 8080 since non-root can't bind to port 80)
EXPOSE 8080

# Health check (updated port)
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Switch to non-root user
USER www

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 