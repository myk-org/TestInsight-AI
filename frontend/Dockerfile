# Frontend Dockerfile for TestInsight AI
# Multi-stage build for optimized production image

# Build stage
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies for build)
RUN npm ci

# Copy source code
COPY . .

# Build the application (Vite)
RUN npm run build

# Production stage
FROM node:20-alpine as production

# Install curl for health checks
RUN apk add --no-cache curl

# Set working directory
WORKDIR /app

# Install serve globally to host static files
RUN npm install -g serve

# Copy built application from builder stage
COPY --from=builder /app/dist ./dist

# Create non-root user for security
RUN addgroup -g 1000 -S appuser && \
    adduser -u 1000 -D -S -G appuser appuser

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start the static file server
CMD ["serve", "-s", "dist", "-l", "3000"]
