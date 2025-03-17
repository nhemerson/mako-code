# Docker Commands for Mako

This document contains essential Docker commands for managing the Mako application.

## Basic Commands

### Build and Start Containers
```bash
# Build and start containers in detached mode
docker-compose up -d

# Build images before starting containers
docker-compose up -d --build
```

### Stop Containers
```bash
# Stop containers but don't remove them
docker-compose stop

# Stop and remove containers
docker-compose down
```

### Restart Containers
```bash
# Restart all services
docker-compose restart

# Restart just one service
docker-compose restart backend
docker-compose restart frontend
```

## Container Management

### View Running Containers
```bash
# List all running containers
docker ps

# List all containers (including stopped ones)
docker ps -a
```

### View Logs
```bash
# View logs from all containers
docker-compose logs

# View logs from a specific container
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f

# Show last 100 lines of logs
docker-compose logs --tail=100
```

### Shell Access
```bash
# Access shell in the backend container
docker-compose exec backend bash

# Access shell in the frontend container
docker-compose exec frontend sh
```

## Volume Management

### List Volumes
```bash
# List all Docker volumes
docker volume ls
```

### Inspect Volume
```bash
# Inspect the mako_data volume
docker volume inspect mako_data
```

### Clean Up Unused Volumes
```bash
# Remove unused volumes
docker volume prune
```

## Troubleshooting

### Check Docker Network
```bash
# List all Docker networks
docker network ls

# Inspect the default network
docker network inspect mako_default
```

### Check Container Health
```bash
# Get detailed container info including health status
docker inspect mako-backend-1
docker inspect mako-frontend-1
```

### Force Rebuild
```bash
# Force rebuild of images
docker-compose build --no-cache
```

### Clean Up
```bash
# Remove stopped containers, unused networks, and dangling images
docker system prune

# Remove all unused images (not just dangling ones)
docker system prune -a
```

## File Upload Specific Commands

### Check Data Directory in Backend Container
```bash
# Check if data directories exist and have correct permissions
docker-compose exec backend ls -la /app/data
docker-compose exec backend ls -la /app/data/local_storage
```

### Copy Files to/from Container
```bash
# Copy a file from host to container
docker cp ./local_file.parquet mako-backend-1:/app/data/local_storage/

# Copy a file from container to host
docker cp mako-backend-1:/app/data/local_storage/file.parquet ./local_copy.parquet
```

## Container Cleanup

### Remove Containers and Volumes
```bash
# Stop containers and remove volumes
docker-compose down -v
```

### Remove Orphaned Containers
```bash
# Remove containers not defined in the compose file
docker-compose down --remove-orphans
```

## Advanced Commands

### Check Container Resource Usage
```bash
# View resource usage statistics
docker stats
```

### Update Docker Images
```bash
# Pull latest base images
docker-compose pull
```

### Restart with New Configuration
```bash
# Restart with updated configuration
docker-compose up -d --force-recreate
```

## Handling Port Conflicts

If you encounter port conflicts:

```bash
# Find what's using a specific port (e.g., 8001)
lsof -i :8001

# Kill the process using that port
kill -9 <PID>
```
